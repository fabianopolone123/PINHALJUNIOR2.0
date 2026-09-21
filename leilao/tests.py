"""Testes do módulo de leilão.

    DJANGO_SETTINGS_MODULE=config.settings_leilao python manage.py test leilao

O foco é o que **quebra ao vivo, na frente de 50 pessoas**: corrida de lances,
cronômetro, prazo de pagamento, vazamento de dado privado no broadcast e as
armadilhas de template que este projeto já pagou caro.
"""

import itertools
import json
import re
import threading
import unittest
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.conf import settings

# O `python manage.py test` do sistema do clube varre o diretório inteiro e
# encontra este arquivo. Sob as settings do clube o app `leilao` NÃO está
# instalado, e importar os models daqui estouraria — virando um "teste que falha
# ao importar" na suíte do clube. Pular o módulo inteiro é o comportamento certo:
# são duas suítes, cada uma com as suas settings.
if not apps.is_installed("leilao"):
    raise unittest.SkipTest(
        "Testes do leilão: rode com DJANGO_SETTINGS_MODULE=config.settings_leilao"
    )

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from django.db import IntegrityError, connections  # noqa: E402
from django.test import Client, TestCase, TransactionTestCase  # noqa: E402
from django.utils import timezone  # noqa: E402

from . import entregas
from . import equipe
from . import estado as est
from . import forms
from . import papeis
from . import reacoes
from . import servicos
from .forms import LeilaoForm
from .models import (  # noqa: E402
    Arremate,
    AtribuicaoEntrega,
    ConfigLeilao,
    EntregadorLeilao,
    Lance,
    Leilao,
    Lote,
    PagamentoLeilao,
    Participante,
)
from .sessao import CHAVE_SESSAO


def criar_leilao(**extra):
    dados = {
        "nome": "Leilão de teste",
        "status": "ao_vivo",
        "incremento_padrao": Decimal("5.00"),
        "segundos_por_lote": 60,
        "minutos_para_pagar": 15,
        "chat_segundos": 0,
    }
    dados.update(extra)
    return Leilao.objects.create(**dados)


def criar_lote(leilao, **extra):
    # Peso e dimensões vêm preenchidos porque é assim que todo item cadastrado
    # a partir de agora nasce (o `LoteForm` os exige). Quem for testar o item
    # ANTIGO, anterior a esses campos, passa `peso_kg=None` de propósito.
    dados = {
        "nome": "Cesta fictícia",
        "lance_inicial": Decimal("40.00"),
        "ordem": 1,
        "peso_kg": Decimal("2.50"),
        "altura_cm": 20,
        "largura_cm": 35,
        "profundidade_cm": 25,
    }
    dados.update(extra)
    return Lote.objects.create(leilao=leilao, **dados)


_seq_telefone = itertools.count(1)


def criar_pessoa(nome="Fulano de Teste", **extra):
    # Telefone DIFERENTE por pessoa, como na vida real: a trava de "ninguém
    # cobre o próprio lance" compara pela pessoa (telefone), então um número
    # repetido no fixture faria dois participantes virarem um só.
    dados = {
        "nome": nome,
        "whatsapp": "119%08d" % next(_seq_telefone),
        "cep": "00000-000",
        "logradouro": "Rua Fictícia",
        "numero": "1",
        "bairro": "Centro",
        "cidade": "Cidade Exemplo",
        "estado": "SP",
    }
    dados.update(extra)
    return Participante.objects.create(**dados)


# ===========================================================================
# O lance
# ===========================================================================
class LanceTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        self.ana = criar_pessoa("Ana Fictícia")
        self.bruno = criar_pessoa("Bruno Fictício")

    def test_primeiro_lance_vale_o_lance_inicial(self):
        """Sem lance nenhum, o primeiro toque paga o inicial — não inicial + incremento.

        Somar aqui faria o item nunca sair pelo preço anunciado.
        """
        ok, _, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertTrue(ok)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.valor_atual, Decimal("40.00"))
        self.assertEqual(self.lote.lider_id, self.ana.id)

    def test_lance_seguinte_sobe_um_incremento(self):
        servicos.dar_lance(self.lote.id, self.ana)
        ok, _, _ = servicos.dar_lance(self.lote.id, self.bruno)
        self.assertTrue(ok)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.valor_atual, Decimal("45.00"))
        self.assertEqual(self.lote.lider_id, self.bruno.id)

    def test_ninguem_cobre_o_proprio_lance(self):
        servicos.dar_lance(self.lote.id, self.ana)
        ok, msg, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertFalse(ok)
        self.assertIn("já está ganhando", msg)

    def test_bloqueado_nao_da_lance(self):
        self.ana.bloqueado = True
        self.ana.save()
        ok, msg, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertFalse(ok)
        self.assertIn("bloqueados", msg)

    def test_lance_recusado_quando_o_valor_pulou_mais_de_um_degrau(self):
        """A pessoa viu R$ 40 na tela; enquanto o dedo ia ao botão, subiu para R$ 55.

        Aceitar calado faria alguém pagar bem mais do que pretendia.
        """
        servicos.dar_lance(self.lote.id, self.ana)                      # 40
        servicos.dar_lance(self.lote.id, self.bruno)                    # 45
        servicos.dar_lance(self.lote.id, self.ana)                      # 50
        carla = criar_pessoa("Carla Fictícia")
        ok, msg, _ = servicos.dar_lance(self.lote.id, carla, valor_visto="40.00")
        self.assertFalse(ok)
        self.assertIn("subiu", msg)

    def test_lance_aceito_com_um_degrau_de_tolerancia(self):
        """Um degrau de diferença é o normal do jogo — não pode travar o botão."""
        servicos.dar_lance(self.lote.id, self.ana)  # valor vira 40; próximo = 45
        ok, _, _ = servicos.dar_lance(self.lote.id, self.bruno, valor_visto="40.00")
        self.assertTrue(ok)

    def test_lance_em_lote_fechado_e_recusado(self):
        self.lote.status = "fila"
        self.lote.save(update_fields=["status"])
        ok, _, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertFalse(ok)


class CorridaDeLancesTests(TransactionTestCase):
    """O teste que justifica o cadeado por lote.

    `TransactionTestCase` porque threads não enxergam a transação de teste do
    `TestCase` comum.
    """

    def test_lances_simultaneos_nao_pulam_valor(self):
        servicos.limpar_limites()
        leilao = criar_leilao()
        lote = criar_lote(leilao)
        servicos.abrir_lote(lote)
        pessoas = [criar_pessoa(f"Pessoa {i} Fictícia") for i in range(8)]

        # Sem o freio de repetição atrapalhando: aqui são pessoas diferentes.
        barreira = threading.Barrier(len(pessoas))
        resultados = []

        def tentar(p):
            barreira.wait()
            try:
                resultados.append(servicos.dar_lance(lote.id, p)[0])
            finally:
                connections.close_all()   # thread própria = conexão própria

        threads = [threading.Thread(target=tentar, args=(p,)) for p in pessoas]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lote.refresh_from_db()
        aceitos = sum(1 for r in resultados if r)
        # Cada lance aceito soma exatamente um incremento sobre o inicial.
        esperado = Decimal("40.00") + Decimal("5.00") * (aceitos - 1)
        self.assertEqual(lote.valor_atual, esperado)
        self.assertEqual(Lance.objects.filter(lote=lote, cancelado=False).count(), aceitos)


# ===========================================================================
# Fechamento, arremate e prazo
# ===========================================================================
class FechamentoTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()

    def test_fechar_com_lance_cria_arremate_com_prazo(self):
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        arremate = servicos.fechar_lote(self.lote)
        self.assertIsNotNone(arremate)
        self.assertEqual(arremate.participante_id, self.ana.id)
        self.assertEqual(arremate.valor, Decimal("40.00"))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")
        faltam = (arremate.expira_em - timezone.now()).total_seconds()
        self.assertGreater(faltam, 14 * 60)

    def test_fechar_sem_lance_nao_cria_arremate(self):
        arremate = servicos.fechar_lote(self.lote)
        self.assertIsNone(arremate)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "sem_lance")

    def test_fechar_duas_vezes_nao_duplica_arremate(self):
        """Cronômetro e botão do locutor podem cair no mesmo instante."""
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        servicos.fechar_lote(self.lote)
        self.assertIsNone(servicos.fechar_lote(self.lote))
        self.assertEqual(Arremate.objects.count(), 1)


class PrazoDePagamentoTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote)

    def test_nao_pagou_no_prazo_devolve_o_lote_a_fila(self):
        Arremate.objects.filter(pk=self.arremate.pk).update(
            expira_em=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "expirado")
        self.assertEqual(self.lote.status, "fila")
        self.assertEqual(self.lote.voltas, 1)

    def test_lote_devolvido_volta_limpo(self):
        """Quem não pagou não guarda direito sobre o item: valor e líder zeram."""
        Arremate.objects.filter(pk=self.arremate.pk).update(
            expira_em=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.lider_id)
        self.assertEqual(self.lote.valor_atual, Decimal("0.00"))
        self.assertEqual(self.lote.proximo_valor, Decimal("40.00"))

    def test_lote_devolvido_vai_para_o_fim_da_fila(self):
        outro = criar_lote(self.leilao, nome="Outro item", ordem=9)
        Arremate.objects.filter(pk=self.arremate.pk).update(
            expira_em=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertGreater(self.lote.ordem, outro.ordem)

    def test_arremate_pago_nao_expira(self):
        servicos.marcar_pago(self.arremate, manual=True)
        Arremate.objects.filter(pk=self.arremate.pk).update(
            expira_em=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "pago")
        self.assertEqual(self.lote.status, "vendido")

    def test_marcar_pago_e_idempotente(self):
        """O webhook do Mercado Pago repete o aviso — não pode trocar a data."""
        servicos.marcar_pago(self.arremate)
        primeiro = Arremate.objects.get(pk=self.arremate.pk).pago_em
        servicos.marcar_pago(Arremate.objects.get(pk=self.arremate.pk))
        self.assertEqual(Arremate.objects.get(pk=self.arremate.pk).pago_em, primeiro)


# ===========================================================================
# Estado público — o que NÃO pode vazar
# ===========================================================================
class EstadoPublicoTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa(
            "Ana Maria Fictícia da Silva", whatsapp="5511988887777",
            logradouro="Rua do Segredo", numero="42",
        )
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()

    def test_broadcast_nao_leva_telefone_nem_endereco(self):
        """O estado é transmitido para todo mundo: só entra o que pode ser dito
        em voz alta. Contato e endereço saem por GET autenticado pela sessão."""
        bruto = str(est.estado_publico(Leilao.ao_vivo()))
        self.assertNotIn("5511988887777", bruto)
        self.assertNotIn("Rua do Segredo", bruto)

    def test_broadcast_mostra_so_o_nome_curto(self):
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertEqual(dados["lote"]["lider"]["nome"], "Ana Silva")

    def test_estado_leva_o_relogio_do_servidor(self):
        """O relógio é do servidor, não do celular.

        Não há mais cronômetro, mas `servidor_em` continua indispensável: é por
        ele que a mesa calcula há quanto tempo a sala está calada. Com o relógio
        do aparelho, quem estivesse com a hora errada veria outro número.
        """
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertIn("servidor_em", dados)

    def test_sem_leilao_ao_vivo_o_estado_diz_inativo(self):
        self.leilao.status = "encerrado"
        self.leilao.save()
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertFalse(dados["ativo"])


class NomeCurtoTests(TestCase):
    def test_nome_curto_pega_primeiro_e_ultimo(self):
        p = criar_pessoa("Maria Clara de Souza Pereira")
        self.assertEqual(p.nome_curto, "Maria Pereira")

    def test_nome_unico_nao_quebra(self):
        p = criar_pessoa("Madonna")
        self.assertEqual(p.nome_curto, "Madonna")


# ===========================================================================
# Chat
# ===========================================================================
class ChatTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao(chat_segundos=120)
        self.ana = criar_pessoa("Ana Fictícia")

    def test_participante_nao_fala_com_chat_fechado(self):
        self.assertIsNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_participante_fala_com_chat_aberto(self):
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()
        self.assertIsNotNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_locutor_fala_mesmo_com_chat_fechado(self):
        """Aviso do locutor não depende do intervalo."""
        m = servicos.enviar_mensagem(self.leilao, None, "Começamos em 5 minutos!")
        self.assertIsNotNone(m)
        self.assertEqual(m.autor, "Locutor")

    def test_bloqueado_nao_fala(self):
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()
        self.ana.bloqueado = True
        self.ana.save()
        self.assertIsNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_chat_fecha_sozinho_no_prazo(self):
        servicos.abrir_chat(self.leilao, 120)
        Leilao.objects.filter(pk=self.leilao.pk).update(
            chat_aberto_ate=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.chat_aberto)

    def test_abrir_lote_fecha_o_chat(self):
        """Abriu pregão, a atenção volta para o item."""
        servicos.abrir_chat(self.leilao, 120)
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.chat_aberto)


# ===========================================================================
# Regras do leilão
# ===========================================================================
class LeilaoTests(TestCase):
    def test_abrir_lote_fecha_outro_que_ficou_aberto(self):
        """Dois lotes abertos seriam dois cronômetros — não pode existir."""
        servicos.limpar_limites()
        leilao = criar_leilao()
        a = criar_lote(leilao, nome="Item A", ordem=1)
        b = criar_lote(leilao, nome="Item B", ordem=2)
        servicos.abrir_lote(a)
        servicos.abrir_lote(b)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.status, "fila")
        self.assertEqual(b.status, "aberto")

    def test_incremento_do_lote_vence_o_do_leilao(self):
        leilao = criar_leilao(incremento_padrao=Decimal("5.00"))
        lote = criar_lote(leilao, incremento=Decimal("50.00"))
        self.assertEqual(lote.incremento_efetivo, Decimal("50.00"))

    def test_reabrir_lote_devolvido_recomeca_do_inicial(self):
        servicos.limpar_limites()
        leilao = criar_leilao()
        lote = criar_lote(leilao)
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, ana)
        lote.refresh_from_db()
        servicos.fechar_lote(lote)
        lote.refresh_from_db()
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        self.assertEqual(lote.proximo_valor, Decimal("40.00"))
        self.assertIsNone(lote.lider_id)


# ===========================================================================
# Views
# ===========================================================================
class ViewsParticipanteTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.c = Client()

    def _entrar(self):
        return self.c.post(
            "/entrar/",
            {
                "nome": "Fulano de Teste",
                "whatsapp": "(11) 90000-0000",
                "cep": "01001-000",
                "logradouro": "Rua Exemplo",
                "numero": "10",
                "bairro": "Centro",
                "cidade": "Cidade Exemplo",
                "estado": "SP",
            },
        )

    def test_sem_entrar_vai_para_a_porta(self):
        r = self.c.get("/")
        self.assertRedirects(r, "/entrar/")

    def test_entrada_cria_participante_e_abre_o_pregao(self):
        r = self._entrar()
        self.assertRedirects(r, "/")
        self.assertEqual(Participante.objects.count(), 1)
        self.assertIn(CHAVE_SESSAO, self.c.session)
        self.assertEqual(self.c.get("/").status_code, 200)

    def test_entrada_exige_nome_e_sobrenome(self):
        r = self.c.post("/entrar/", {"nome": "Fulano", "whatsapp": "(11) 90000-0000"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("nome", r.context["form"].errors)

    def test_entrada_guarda_so_digitos_do_whatsapp(self):
        self._entrar()
        self.assertEqual(Participante.objects.first().whatsapp, "11900000000")

    def test_lance_pela_view(self):
        self._entrar()
        servicos.abrir_lote(self.lote)
        r = self.c.post(
            "/lance/",
            data='{"lote": %d}' % self.lote.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_lance_sem_entrar_e_recusado(self):
        servicos.abrir_lote(self.lote)
        r = self.c.post(
            "/lance/",
            data='{"lote": %d}' % self.lote.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_pix_de_outra_pessoa_nao_abre(self):
        """O Pix é privado do arrematante — nem por link direto sai."""
        self._entrar()
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, ana)
        self.lote.refresh_from_db()
        arremate = servicos.fechar_lote(self.lote)
        r = self.c.get(f"/arremate/{arremate.id}/pix/")
        self.assertEqual(r.status_code, 404)

    def test_stream_responde_event_stream(self):
        r = self.c.get("/stream/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/event-stream")
        # Sem isso o Nginx segura os pedaços e o "tempo real" vira lote.
        self.assertEqual(r["X-Accel-Buffering"], "no")
        r.close()


class ViewsEquipeTests(TestCase):
    """Área da equipe: quem entra, e em quê.

    O ponto destes testes não é a tela — é a **regra**: esconder o botão no HTML
    não barra ninguém; quem barra é o `papeis.exige` na view.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.c = Client()

    def _pessoa(self, nome, *quais, staff=True):
        User = get_user_model()
        u = User.objects.create_user(nome, password="segredo-ficticio")
        u.is_staff = staff
        u.save()
        for papel in quais:
            grupo, _ = Group.objects.get_or_create(name=papel)
            u.groups.add(grupo)
        return u

    # --- acesso às áreas ---
    def test_sem_login_a_equipe_nao_abre(self):
        for url in ["/equipe/", "/locutor/", "/caixa/", "/preparacao/"]:
            self.assertEqual(self.c.get(url).status_code, 302, url)

    def test_conta_sem_papel_nao_ve_area_nenhuma(self):
        """`is_staff` sozinho não dá acesso: é preciso ter papel."""
        self._pessoa("semtudo")
        self.c.login(username="semtudo", password="segredo-ficticio")
        self.assertRedirects(self.c.get("/equipe/"), "/equipe/entrar/")
        for url in ["/locutor/", "/caixa/", "/preparacao/"]:
            self.assertEqual(self.c.get(url).status_code, 302, url)

    def test_cada_papel_abre_so_a_sua_area(self):
        casos = {
            "preparacao": ("/preparacao/", ["/locutor/", "/caixa/"]),
            "locutor": ("/locutor/", ["/preparacao/", "/caixa/"]),
            "caixa": ("/caixa/", ["/preparacao/", "/locutor/"]),
        }
        for papel, (minha, alheias) in casos.items():
            self._pessoa("user_" + papel, papel)
            c = Client()
            c.login(username="user_" + papel, password="segredo-ficticio")
            self.assertEqual(c.get(minha).status_code, 200, papel + " nao abriu " + minha)
            for outra in alheias:
                self.assertEqual(c.get(outra).status_code, 302, papel + " abriu " + outra)

    def test_diretor_abre_as_tres(self):
        self._pessoa("chefe", "diretor")
        self.c.login(username="chefe", password="segredo-ficticio")
        for url in ["/preparacao/", "/locutor/", "/caixa/"]:
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_papeis_acumulam(self):
        """No evento pequeno, o mesmo voluntário faz duas coisas."""
        self._pessoa("dupla", "locutor", "caixa")
        self.c.login(username="dupla", password="segredo-ficticio")
        self.assertEqual(self.c.get("/locutor/").status_code, 200)
        self.assertEqual(self.c.get("/caixa/").status_code, 200)
        self.assertEqual(self.c.get("/preparacao/").status_code, 302)

    def test_quem_tem_uma_area_so_vai_direto_para_ela(self):
        self._pessoa("soLocutor", "locutor")
        self.c.login(username="soLocutor", password="segredo-ficticio")
        self.assertRedirects(self.c.get("/equipe/"), "/locutor/")

    def test_quem_tem_duas_areas_escolhe(self):
        self._pessoa("duasAreas", "locutor", "caixa")
        self.c.login(username="duasAreas", password="segredo-ficticio")
        self.assertEqual(self.c.get("/equipe/").status_code, 200)

    # --- a regra que separa o pregão do dinheiro ---
    def test_locutor_conduz_o_pregao(self):
        self._pessoa("loc", "locutor")
        self.c.login(username="loc", password="segredo-ficticio")
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "abrir", "lote": self.lote.id}),
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")

    def test_locutor_NAO_da_baixa_de_pagamento(self):
        """Quem bate o martelo não confirma o recebimento."""
        self._pessoa("loc2", "locutor")
        self.c.login(username="loc2", password="segredo-ficticio")
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, ana)
        self.lote.refresh_from_db()
        arremate = servicos.fechar_lote(self.lote)

        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "pago", "arremate": arremate.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        arremate.refresh_from_db()
        self.assertEqual(arremate.status, "aguardando")

    def test_caixa_da_baixa_mas_nao_abre_lote(self):
        self._pessoa("cx", "caixa")
        self.c.login(username="cx", password="segredo-ficticio")
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "abrir", "lote": self.lote.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "fila")

    def test_acao_desconhecida_e_recusada(self):
        self._pessoa("chefe2", "diretor")
        self.c.login(username="chefe2", password="segredo-ficticio")
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "formatar_tudo"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)


class PreparacaoTests(TestCase):
    """O cadastro de item grava no leilão da URL — nunca no adivinhado."""

    def setUp(self):
        servicos.limpar_limites()
        User = get_user_model()
        u = User.objects.create_user("prep", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="preparacao")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="prep", password="segredo-ficticio")

    def test_item_novo_vai_para_o_leilao_da_url_e_nao_para_o_que_esta_ao_vivo(self):
        """O bug que isto fixa: preparar o leilão de dezembro com o de novembro
        rolando jogava os itens novos **dentro do pregão em andamento**."""
        ao_vivo = criar_leilao(nome="Leilão de novembro", status="ao_vivo")
        criar_lote(ao_vivo, nome="Item de novembro")
        proximo = criar_leilao(nome="Leilão de dezembro", status="rascunho")

        r = self.c.post(
            "/preparacao/%d/itens/novo/" % proximo.pk,
            {
                "nome": "Item de dezembro", "descricao": "", "lance_inicial": "30.00",
                # Peso e dimensões passaram a ser obrigatórios no cadastro.
                "peso_kg": "1,5", "altura_cm": "20",
                "largura_cm": "30", "profundidade_cm": "25",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(proximo.lotes.count(), 1)
        self.assertEqual(proximo.lotes.first().nome, "Item de dezembro")
        self.assertEqual(ao_vivo.lotes.count(), 1)

    def test_criar_leilao_leva_para_os_itens_dele(self):
        r = self.c.post("/preparacao/", {
            "nome": "Leilão novo", "descricao": "",
            "incremento_padrao": "5.00", "segundos_por_lote": "60",
            "segundos_extra": "30", "minutos_para_pagar": "15", "chat_segundos": "120",
        })
        novo = Leilao.objects.get(nome="Leilão novo")
        self.assertRedirects(r, "/preparacao/%d/itens/" % novo.pk)

    def test_nao_coloca_no_ar_leilao_sem_item(self):
        vazio = criar_leilao(nome="Leilão vazio", status="rascunho")
        self.c.post("/preparacao/%d/status/" % vazio.pk, {"status": "ao_vivo"})
        vazio.refresh_from_db()
        self.assertEqual(vazio.status, "rascunho")


class EntregaTests(TestCase):
    """Entrega é **depois**, na casa da pessoa — e só do que foi pago."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")

        User = get_user_model()
        u = User.objects.create_user("caixa1", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="caixa1", password="segredo-ficticio")

        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote)

    def _entregar(self, **extra):
        corpo = {"acao": "entregue", "arremate": self.arremate.id}
        corpo.update(extra)
        return self.c.post(
            "/equipe/acao/", data=json.dumps(corpo), content_type="application/json"
        )

    def test_nao_entrega_o_que_nao_foi_pago(self):
        """Mandar o item antes de o dinheiro cair é o erro que o prazo de 15
        minutos existe para evitar."""
        r = self._entregar()
        self.assertFalse(r.json()["ok"])
        self.arremate.refresh_from_db()
        self.assertIsNone(self.arremate.entregue_em)

    def test_entrega_o_que_foi_pago(self):
        servicos.marcar_pago(self.arremate, manual=True)
        r = self._entregar(observacao="Recebido pela vizinha")
        self.assertTrue(r.json()["ok"])
        self.arremate.refresh_from_db()
        self.assertIsNotNone(self.arremate.entregue_em)
        self.assertEqual(self.arremate.entrega_obs, "Recebido pela vizinha")
        self.assertEqual(self.arremate.entregue_por.username, "caixa1")

    def test_desfazer_entrega(self):
        servicos.marcar_pago(self.arremate, manual=True)
        self._entregar()
        self._entregar(desfazer=True)
        self.arremate.refresh_from_db()
        self.assertIsNone(self.arremate.entregue_em)

    def test_a_entregar_e_so_pago_e_nao_entregue(self):
        self.assertFalse(self.arremate.a_entregar)
        servicos.marcar_pago(self.arremate, manual=True)
        self.arremate.refresh_from_db()
        self.assertTrue(self.arremate.a_entregar)
        self._entregar()
        self.arremate.refresh_from_db()
        self.assertFalse(self.arremate.a_entregar)
        self.assertTrue(self.arremate.entregue)

    def test_tela_do_caixa_lista_o_que_ha_para_entregar(self):
        servicos.marcar_pago(self.arremate, manual=True)
        r = self.c.get("/caixa/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["a_entregar"]), 1)
        # O roteiro leva endereço: é documento de quem entrega.
        self.assertIn("Rua Fictícia", r.context["roteiro"])
        self.assertIn("Ana Fictícia", r.context["roteiro"])

    def test_roteiro_vazio_quando_nao_ha_entrega(self):
        r = self.c.get("/caixa/")
        self.assertEqual(r.context["roteiro"], "")


class WebhookTests(TestCase):
    def test_webhook_nunca_devolve_erro(self):
        """Webhook que devolve 500 faz o Mercado Pago reenviar em cascata."""
        c = Client()
        r = c.post("/webhooks/mercadopago/", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 200)

    def test_webhook_de_pagamento_desconhecido_e_silencioso(self):
        c = Client()
        r = c.post(
            "/webhooks/mercadopago/",
            data='{"data": {"id": "999999"}}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)

    def test_retorno_aprovado_quita_o_arremate(self):
        servicos.limpar_limites()
        leilao = criar_leilao()
        lote = criar_lote(leilao)
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, ana)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote)

        pagamento = PagamentoLeilao.objects.create(
            referencia=f"LEILAO-{arremate.id}",
            mp_payment_id="123",
            valor_bruto=arremate.valor,
        )
        arremate.pagamento = pagamento
        arremate.save(update_fields=["pagamento"])

        servicos._aplicar_retorno(
            pagamento,
            {"ok": True, "status": "aprovado", "taxa": Decimal("0.40"),
             "liquido": Decimal("39.60")},
        )
        arremate.refresh_from_db()
        pagamento.refresh_from_db()
        self.assertEqual(arremate.status, "pago")
        self.assertTrue(pagamento.finalizado)
        self.assertEqual(pagamento.taxa, Decimal("0.40"))


# ===========================================================================
# Armadilhas do projeto (custaram caro antes — ficam fixadas em teste)
# ===========================================================================
class ArmadilhasTests(TestCase):
    def test_nenhum_comentario_de_template_em_varias_linhas(self):
        """`{# ... #}` comenta UMA linha só.

        Em várias, o texto vaza para a tela — e se houver uma tag no meio, ela é
        EXECUTADA. Foi assim que o `_campo.html` passou a incluir a si mesmo e
        estourou a pilha. Para bloco, `{% comment %}`.
        """
        ruins = []
        for arquivo in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            texto = arquivo.read_text(encoding="utf-8")
            for achado in re.finditer(r"\{#", texto):
                fim = texto.find("#}", achado.start())
                if fim != -1 and "\n" in texto[achado.start():fim]:
                    ruins.append(str(arquivo.relative_to(settings.BASE_DIR)))
        self.assertEqual(ruins, [], f"Comentário {{# #}} em várias linhas: {ruins}")

    def test_bloco_flex_escondido_tem_regra_de_hidden(self):
        """Elemento `display:flex` NÃO some com `hidden` — a classe ganha do
        `[hidden]` do navegador. Todo bloco que o JS esconde precisa da regra."""
        css = Path(settings.BASE_DIR, "static", "leilao", "css", "leilao.css").read_text(
            encoding="utf-8"
        )
        for classe in [".palco-vazio[hidden]", ".palco-intervalo[hidden]", ".chat[hidden]"]:
            self.assertIn(classe, css, f"Falta a regra {classe}")

    def test_grade_do_locutor_usa_minmax(self):
        """`1fr` não encolhe abaixo do conteúdo e cria rolagem horizontal."""
        css = Path(settings.BASE_DIR, "static", "leilao", "css", "locutor.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("minmax(0, 1fr)", css)
        self.assertNotIn("grid-template-columns: 1fr 1fr", css)


class ConfiguracaoTests(TestCase):
    def test_ler_a_config_nao_escreve_no_banco(self):
        """`get_solo` roda a cada página e numa thread de fundo.

        Se ele criasse a linha, toda leitura viraria tentativa de escrita e
        disputaria a trava do SQLite com quem está dando lance.
        """
        ConfigLeilao.get_solo()
        ConfigLeilao.get_solo()
        self.assertEqual(ConfigLeilao.objects.count(), 0)

    def test_config_e_singleton_ao_salvar(self):
        cfg = ConfigLeilao.get_solo()
        cfg.site_url = "https://exemplo.com/leilao"
        cfg.save()
        outra = ConfigLeilao.get_solo()
        outra.modo = "producao"
        outra.save()
        self.assertEqual(ConfigLeilao.objects.count(), 1)
        self.assertEqual(ConfigLeilao.get_solo().site_url, "https://exemplo.com/leilao")

    def test_token_mascarado_nunca_mostra_inteiro(self):
        cfg = ConfigLeilao.get_solo()
        cfg.modo = "producao"
        cfg.access_token_prod = "APP_USR-1234567890-abcdef"
        cfg.save()
        self.assertNotIn("1234567890", cfg.token_mascarado)
        self.assertTrue(cfg.token_mascarado.endswith("cdef"))

    def test_banco_do_leilao_e_separado_do_clube(self):
        """O isolamento é a razão de existir do serviço próprio."""
        self.assertNotIn("core", settings.INSTALLED_APPS)
        self.assertIn("leilao", settings.INSTALLED_APPS)

    def test_cookie_de_sessao_tem_nome_proprio(self):
        """Repetir o nome do cookie derruba a sessão do sistema do clube."""
        self.assertEqual(settings.SESSION_COOKIE_NAME, "leilao_sessionid")
        self.assertNotEqual(settings.SESSION_COOKIE_NAME, "pinhaljunior2_sessionid")


class RodadaTests(TestCase):
    """Um lote pode ir a pregão mais de uma vez (quem arrematou não pagou).

    Os lances da rodada anterior continuam no banco — é histórico —, mas não
    podem aparecer como se fossem desta vez.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")
        self.bruno = criar_pessoa("Bruno Fictício")

        # 1ª rodada: Ana arremata e não paga.
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        arremate = servicos.fechar_lote(self.lote)
        Arremate.objects.filter(pk=arremate.pk).update(
            expira_em=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()

        # 2ª rodada.
        servicos.limpar_limites()
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()

    def test_lances_da_rodada_anterior_nao_contam_na_rodada_nova(self):
        self.assertEqual(self.lote.lances_da_rodada().count(), 0)
        # O lance antigo continua no banco: historico nao se apaga.
        self.assertEqual(Lance.objects.filter(lote=self.lote).count(), 1)


class AbrirOutroLoteTests(TestCase):
    """Abrir outro item com um pregão acontecendo devolve o atual à fila.

    O servidor aceita (é o locutor quem manda), mas o lote abandonado precisa
    voltar **limpo** — não pode ficar na fila exibindo líder e valor de uma
    disputa que foi jogada fora. A confirmação na tela do locutor é a camada que
    evita o acidente; esta é a que garante o estado coerente.
    """

    def test_lote_abandonado_volta_limpo_para_a_fila(self):
        servicos.limpar_limites()
        leilao = criar_leilao()
        a = criar_lote(leilao, nome="Item A", ordem=1)
        b = criar_lote(leilao, nome="Item B", ordem=2)
        ana = criar_pessoa("Ana Fictícia")

        servicos.abrir_lote(a)
        a.refresh_from_db()
        servicos.dar_lance(a.id, ana)
        a.refresh_from_db()
        self.assertEqual(a.valor_atual, Decimal("40.00"))

        servicos.abrir_lote(b)
        a.refresh_from_db()
        self.assertEqual(a.status, "fila")
        self.assertIsNone(a.lider_id)
        self.assertEqual(a.valor_atual, Decimal("0.00"))
        self.assertEqual(a.proximo_valor, Decimal("40.00"))
        # O lance continua no banco: histórico não se apaga.
        self.assertEqual(Lance.objects.filter(lote=a).count(), 1)


class SemMercadoPagoTests(TestCase):
    """O leilão não pode parar por falta de credencial de pagamento.

    Sem Mercado Pago configurado nenhum Pix nasce — e a tela precisa DIZER isso,
    em vez de prometer um "gerando…" que nunca termina. O locutor combina o
    pagamento e dá baixa manual.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.c = Client()
        self.c.post("/entrar/", {
            "nome": "Fulano de Teste", "whatsapp": "(11) 90000-0000",
            "cep": "01001-000", "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "cidade": "Cidade Exemplo", "estado": "SP",
        })
        self.pessoa = Participante.objects.get(nome="Fulano de Teste")

        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.pessoa)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote)

    def test_arremate_acontece_mesmo_sem_credencial(self):
        self.assertIsNotNone(self.arremate)
        self.assertEqual(self.arremate.status, "aguardando")

    def test_lista_avisa_que_o_pix_nao_e_possivel(self):
        r = self.c.get("/meus-arremates/")
        self.assertFalse(r.json()["pix_possivel"])

    def test_pedir_o_pix_nao_promete_o_que_nao_vem(self):
        r = self.c.get(f"/arremate/{self.arremate.id}/pix/")
        corpo = r.json()
        self.assertFalse(corpo["ok"])
        self.assertFalse(corpo["gerando"])
        self.assertIn("organização", corpo["msg"])

    def test_com_credencial_a_lista_libera_o_pix(self):
        cfg = ConfigLeilao.get_solo()
        cfg.access_token_teste = "TEST-token-ficticio-1234"
        cfg.save()
        r = self.c.get("/meus-arremates/")
        self.assertTrue(r.json()["pix_possivel"])


class ReinicioDoServicoTests(TestCase):
    """O que sobrevive a um restart do serviço no meio do pregão.

    Tudo: o estado vive no banco, não em memória. Item aberto continua aberto,
    com líder e valor. Sem cronômetro não há nem o risco antigo — um reinício
    demorado não bate martelo nenhum, porque quem bate é o locutor. O que a
    equipe perde é só os segundos de reconexão das telas, e isso basta para não
    reiniciar com disputa rolando (ver `docs/DEPLOY_LEILAO.md`).
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()

    def test_lote_aberto_continua_aberto_com_lider_e_valor(self):
        # Nada de estado em memória: só o que está no banco.
        servicos.limpar_limites()
        de_novo = Lote.objects.get(pk=self.lote.pk)
        self.assertEqual(de_novo.status, "aberto")
        self.assertEqual(de_novo.lider_id, self.ana.id)
        self.assertEqual(de_novo.valor_atual, Decimal("40.00"))

    def test_reinicio_demorado_NAO_bate_martelo(self):
        """O risco antigo era este, e ele não existe mais.

        Com cronômetro, um reinício mais longo do que o tempo restante fazia o
        laço central subir com o prazo vencido e fechar o item na hora — sem
        ninguém pedir. Sem cronômetro, o item espera o locutor o tempo que for.
        """
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")
        self.assertEqual(Arremate.objects.filter(lote=self.lote).count(), 0)


class EstadoSemLeilaoTests(TestCase):
    def test_estado_inativo_leva_o_contador_de_online(self):
        """Antes de o pregão começar é quando o locutor mais quer saber quantos
        já estão esperando — e é como se confere que o hub não ficou com
        conexões penduradas depois de um pico."""
        dados = est.estado_publico(None)
        self.assertFalse(dados["ativo"])
        self.assertIn("online", dados)
        self.assertIn("servidor_em", dados)


class TelasEquipeRenderizamTests(TestCase):
    """Fumaça: toda tela da equipe abre. Erro de template só aparece rodando."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        User = get_user_model()
        u = User.objects.create_user("chefao", password="segredo-ficticio")
        u.is_staff = True
        u.is_superuser = True
        u.save()
        self.c = Client()
        self.c.login(username="chefao", password="segredo-ficticio")

    def test_todas_as_telas_abrem(self):
        urls = [
            "/equipe/",
            "/equipe/usuarios/",
            "/equipe/senha/",
            "/locutor/",
            "/locutor/dados/",
            "/caixa/",
            "/preparacao/",
            "/preparacao/config/",
            "/preparacao/%d/itens/" % self.leilao.pk,
            "/preparacao/%d/itens/novo/" % self.leilao.pk,
            "/preparacao/itens/%d/editar/" % self.lote.pk,
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_tela_de_entrada_abre_para_quem_nao_esta_logado(self):
        self.assertEqual(Client().get("/equipe/entrar/").status_code, 200)

    def test_quem_ja_entrou_nao_ve_a_tela_de_login_de_novo(self):
        self.assertRedirects(self.c.get("/equipe/entrar/"), "/equipe/")


class TravaAutoLanceTests(TestCase):
    """Ninguém cobre o próprio lance — nem entrando de dois aparelhos.

    A entrada cria um `Participante` novo a cada vez. Comparar só pelo id
    deixava a mesma pessoa, aberta no celular E no computador, dar lance contra
    si mesma e inflar o próprio preço.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()

    def test_mesmo_registro_nao_cobre_o_proprio_lance(self):
        ana = criar_pessoa("Ana Fictícia", whatsapp="11900000001")
        servicos.dar_lance(self.lote.id, ana)
        servicos.limpar_limites()
        ok, msg, _ = servicos.dar_lance(self.lote.id, ana)
        self.assertFalse(ok)
        self.assertIn("já está ganhando", msg)

    def test_mesma_pessoa_em_dois_aparelhos_nao_cobre_a_si_mesma(self):
        celular = criar_pessoa("Ana Fictícia", whatsapp="11900000001")
        computador = criar_pessoa("Ana Fictícia", whatsapp="11900000001")
        self.assertNotEqual(celular.pk, computador.pk)  # são dois registros

        servicos.dar_lance(self.lote.id, celular)
        servicos.limpar_limites()
        ok, msg, _ = servicos.dar_lance(self.lote.id, computador)
        self.assertFalse(ok)
        self.assertIn("já está ganhando", msg)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.valor_atual, Decimal("40.00"))  # não subiu

    def test_telefone_com_e_sem_ddi_e_a_mesma_pessoa(self):
        """Um aparelho manda "(11) 90000-0001", o outro "5511900000001"."""
        um = criar_pessoa("Ana Fictícia", whatsapp="11900000001")
        outro = criar_pessoa("Ana Fictícia", whatsapp="5511900000001")
        servicos.dar_lance(self.lote.id, um)
        servicos.limpar_limites()
        ok, _, _ = servicos.dar_lance(self.lote.id, outro)
        self.assertFalse(ok)

    def test_pessoas_diferentes_continuam_disputando(self):
        """A trava não pode travar o leilão."""
        ana = criar_pessoa("Ana Fictícia", whatsapp="11900000001")
        bruno = criar_pessoa("Bruno Fictício", whatsapp="11900000002")
        servicos.dar_lance(self.lote.id, ana)
        servicos.limpar_limites()
        ok, _, _ = servicos.dar_lance(self.lote.id, bruno)
        self.assertTrue(ok)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.valor_atual, Decimal("45.00"))
        self.assertEqual(self.lote.lider_id, bruno.pk)

    def test_chave_da_pessoa_nao_expoe_o_telefone(self):
        """A chave vai no broadcast para 100 pessoas: não pode ser o número."""
        ana = criar_pessoa("Ana Fictícia", whatsapp="11987654321")
        chave = ana.chave_pessoa
        self.assertNotIn("11987654321", chave)
        self.assertNotIn("987654321", chave)
        # Estável entre registros diferentes da mesma pessoa.
        outra_entrada = criar_pessoa("Ana Fictícia", whatsapp="5511987654321")
        self.assertEqual(chave, outra_entrada.chave_pessoa)

    def test_estado_publico_leva_a_chave_e_nao_o_telefone(self):
        ana = criar_pessoa("Ana Fictícia", whatsapp="11987654321")
        servicos.dar_lance(self.lote.id, ana)
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertEqual(dados["lote"]["lider"]["chave"], ana.chave_pessoa)
        self.assertNotIn("11987654321", str(dados))


class BloqueioSegueAPessoaTests(TestCase):
    """Bloqueio que se escapa entrando de novo não é bloqueio."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        self.c = Client()

    def _entrar(self, nome="Fulano de Teste", tel="(11) 90000-0009"):
        c = Client()
        c.post("/entrar/", {
            "nome": nome, "whatsapp": tel,
            "cep": "01001-000", "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "cidade": "Cidade Exemplo", "estado": "SP",
        })
        return c

    def test_entrar_de_novo_nao_limpa_o_bloqueio(self):
        self._entrar()
        pessoa = Participante.objects.get(whatsapp="11900000009")
        pessoa.bloqueado = True
        pessoa.save()

        self._entrar()  # mesma pessoa, outro aparelho
        novos = Participante.objects.filter(whatsapp="11900000009")
        self.assertEqual(novos.count(), 2)
        self.assertTrue(all(p.bloqueado for p in novos))

    def test_bloquear_alcanca_os_dois_cadastros(self):
        self._entrar()
        self._entrar()
        primeiro = Participante.objects.filter(whatsapp="11900000009").first()

        User = get_user_model()
        u = User.objects.create_user("locbloq", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        self.c.login(username="locbloq", password="segredo-ficticio")

        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "bloquear", "participante": primeiro.pk}),
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.assertEqual(
            Participante.objects.filter(whatsapp="11900000009", bloqueado=True).count(), 2
        )

    def test_pessoa_diferente_nao_e_afetada(self):
        self._entrar(tel="(11) 90000-0009")
        self._entrar(nome="Outra Pessoa", tel="(11) 90000-0008")
        alvo = Participante.objects.get(whatsapp="11900000009")
        servicos.bloquear_pessoa(alvo, True)
        outra = Participante.objects.get(whatsapp="11900000008")
        self.assertFalse(outra.bloqueado)


class QuemBateOMarteloTests(TestCase):
    """Por padrão o tempo NÃO fecha nada — quem bate o martelo é o locutor.

    É assim que um leilão de verdade funciona: o "dou-lhe uma, dou-lhe duas" é
    do leiloeiro. Fechar sozinho tiraria dele o momento que mais importa.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")

    def test_o_padrao_e_fechamento_manual(self):
        self.assertFalse(self.leilao.fechamento_automatico)

    def test_lote_aberto_nasce_sem_cronometro(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.fecha_em)

    def test_o_tempo_passa_e_o_lote_continua_aberto(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        # Uma hora depois da abertura, e nada de martelo.
        Lote.objects.filter(pk=self.lote.pk).update(
            aberto_em=timezone.now() - timedelta(hours=1)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")
        self.assertEqual(Arremate.objects.count(), 0)

    def test_o_locutor_fecha_pelo_botao(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        arremate = servicos.fechar_lote(self.lote, motivo="locutor")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")
        self.assertIsNotNone(arremate)

    def test_parado_ha_conta_para_cima(self):
        """O que ajuda o locutor a decidir é há quanto tempo a sala está calada."""
        servicos.abrir_lote(self.lote)
        Lote.objects.filter(pk=self.lote.pk).update(
            aberto_em=timezone.now() - timedelta(seconds=40)
        )
        self.lote.refresh_from_db()
        self.assertGreaterEqual(self.lote.parado_ha, 39)

        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        self.assertLess(self.lote.parado_ha, 5)   # o lance zerou o silêncio


class TelaDoParticipanteEscondeTests(TestCase):
    """O que a tela do participante NÃO pode contar.

    Saber o que vem pela frente muda como a pessoa dá lance: quem descobre que
    falta pouco segura o dinheiro, quem vê 20 itens economiza no primeiro. O
    suspense é do leilão.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao, nome="Item em pregao", ordem=1)
        criar_lote(self.leilao, nome="Segredo de dezembro", ordem=2)
        criar_lote(self.leilao, nome="Outro segredo", ordem=3)
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()

    def test_nao_diz_quantos_faltam_nem_quais_sao(self):
        dados = est.estado_publico(Leilao.ao_vivo())
        bruto = str(dados)
        self.assertNotIn("restam_na_fila", dados)
        self.assertNotIn("fila", dados)
        self.assertNotIn("Segredo de dezembro", bruto)
        self.assertNotIn("Outro segredo", bruto)

    def test_nao_lista_o_historico_de_lances(self):
        ana = criar_pessoa("Ana Fictícia")
        servicos.dar_lance(self.lote.id, ana)
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertNotIn("ultimos_lances", dados)

    def test_manda_so_a_foto_do_proximo_para_precarregar(self):
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertIn("proxima_foto", dados)      # a URL, para a troca ser instantânea
        self.assertNotIn("Segredo", str(dados))   # mas não o nome

    def test_a_mesa_do_locutor_ve_a_fila_inteira(self):
        User = get_user_model()
        u = User.objects.create_user("loc_fila", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_fila", password="segredo-ficticio")

        d = c.get("/locutor/dados/").json()
        nomes = [x["nome"] for x in d["fila"]]
        self.assertIn("Segredo de dezembro", nomes)
        self.assertEqual(d["restam_na_fila"], 2)


class ChatPorRodadaTests(TestCase):
    """Cada intervalo é uma conversa NOVA para quem participa."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao(chat_segundos=120)
        self.ana = criar_pessoa("Ana Fictícia")

    def test_intervalo_novo_abre_o_chat_limpo(self):
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()
        servicos.enviar_mensagem(self.leilao, self.ana, "oi do primeiro intervalo")
        dados = est.estado_publico(self.leilao)
        self.assertEqual(len(dados["chat"]["mensagens"]), 1)

        # Segundo intervalo: a conversa recomeça.
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()
        dados = est.estado_publico(self.leilao)
        self.assertEqual(dados["chat"]["mensagens"], [])

    def test_o_locutor_continua_vendo_tudo(self):
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()
        servicos.enviar_mensagem(self.leilao, self.ana, "primeira rodada")
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()
        servicos.enviar_mensagem(self.leilao, self.ana, "segunda rodada")

        User = get_user_model()
        u = User.objects.create_user("loc_chat", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_chat", password="segredo-ficticio")

        textos = [m["texto"] for m in c.get("/locutor/dados/").json()["chat"]]
        self.assertIn("primeira rodada", textos)
        self.assertIn("segunda rodada", textos)


class ReacoesTests(TestCase):
    """Emojis: o que segura isto em pé é a AGREGAÇÃO."""

    def setUp(self):
        servicos.limpar_limites()
        reacoes.limpar()
        self.leilao = criar_leilao()
        self.c = Client()
        self.c.post("/entrar/", {
            "nome": "Fulano de Teste", "whatsapp": "(11) 90000-0077",
            "cep": "01001-000", "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "cidade": "Cidade Exemplo", "estado": "SP",
        })

    def test_cem_toques_viram_um_resumo(self):
        """É isto que impede 50 pessoas martelando emoji de derrubar o pregão."""
        for _ in range(100):
            reacoes.registrar("❤️")
        resumo = reacoes.drenar()
        self.assertEqual(len(resumo), 1)
        self.assertEqual(reacoes.drenar(), {})   # drenar esvazia

    def test_o_despejo_tem_teto(self):
        for _ in range(500):
            reacoes.registrar("🔥")
        self.assertLessEqual(reacoes.drenar()["🔥"], reacoes.TETO_POR_DESPEJO)

    def test_emoji_de_fora_da_lista_e_recusado(self):
        self.assertFalse(reacoes.registrar("💣"))
        self.assertEqual(reacoes.drenar(), {})

    def test_reagir_pela_view(self):
        r = self.c.post(
            "/reagir/", data=json.dumps({"emoji": "👏", "quantos": 3}),
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        # Três TOQUES, cada um valendo uma rajada: o que o servidor guarda é o
        # que vai subir na tela, não o número de toques.
        self.assertEqual(reacoes.drenar(), {"👏": 3 * reacoes.EMOJIS_POR_TOQUE})

    def test_sem_entrar_nao_reage(self):
        r = Client().post(
            "/reagir/", data=json.dumps({"emoji": "👏"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_bloqueado_nao_reage(self):
        Participante.objects.filter(whatsapp="11900000077").update(bloqueado=True)
        r = self.c.post(
            "/reagir/", data=json.dumps({"emoji": "👏"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)


    def test_quantos_invalido_nao_derruba_a_view(self):
        """Vem de JSON da internet: texto, lista ou nada. Um 500 por um emoji, não."""
        for valor in ("abc", [1, 2], {"a": 1}):
            self.assertFalse(reacoes.registrar("❤️", valor))

class SemMusicaDeFundoTests(TestCase):
    """Não há música de fundo. O clube ouviu pronta e resolveu que não queria.

    O que sobrou no banco são duas colunas dormentes (`musica_ligada`,
    `musica_volume`) e o `ConfigLeilao.musica`. Estes testes existem para que o
    recurso não volte por descuido — por um `data-acao` copiado, uma chave
    reposta no estado, um botão reaproveitado de outra tela.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()

    def test_o_estado_nao_fala_de_musica(self):
        self.assertNotIn("musica", est.estado_publico(self.leilao))

    def test_nao_existe_acao_de_musica(self):
        from .views import ACOES_AREAS
        self.assertNotIn("musica", ACOES_AREAS)

    def test_a_mesa_do_locutor_nao_tem_controle_de_musica(self):
        User = get_user_model()
        u = User.objects.create_user("loc_sem_musica", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_sem_musica", password="segredo-ficticio")

        html = c.get("/locutor/").content.decode("utf-8")
        self.assertNotIn("btnMusica", html)
        self.assertNotIn("musicaVolume", html)

    def test_o_servidor_recusa_a_acao_mesmo_forjada(self):
        """Botão escondido não protege nada — quem recusa é o servidor."""
        User = get_user_model()
        u = User.objects.create_user("loc_forja", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_forja", password="segredo-ficticio")

        r = c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "musica", "ligada": True}),
            content_type="application/json",
        )
        self.assertFalse(r.json()["ok"])

    def test_o_player_saiu_do_javascript(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "som.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("SomLeilao", js)          # os efeitos de lance FICAM
        self.assertNotIn("MusicaLeilao", js)


class FestaDoIntervaloTests(TestCase):
    """O intervalo não diz quantos faltam — comemora quem acabou de arrematar."""

    def test_o_intervalo_comemora_quem_arrematou(self):
        servicos.limpar_limites()
        leilao = criar_leilao()
        lote = criar_lote(leilao, nome="Cesta fictícia")
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, ana)
        lote.refresh_from_db()
        servicos.fechar_lote(lote, motivo="locutor")

        v = est.estado_publico(Leilao.ao_vivo())["ultimo_vendido"]
        self.assertEqual(v["item"], "Cesta fictícia")
        self.assertEqual(v["vencedor"], "Ana Fictícia")
        self.assertEqual(v["valor"], "40.00")

    def test_sem_venda_nao_ha_festa(self):
        leilao = criar_leilao()
        criar_lote(leilao)
        self.assertIsNone(est.estado_publico(leilao)["ultimo_vendido"])


class PagarDepoisTests(TestCase):
    """"Falei com a pessoa, ela paga depois."

    Sem este estado, quem combinou de pagar amanhã perdia o item para o relógio
    dos 15 minutos — o oposto do que o caixa acabou de acertar.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote, motivo="locutor")

        User = get_user_model()
        u = User.objects.create_user("caixa_pd", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="caixa_pd", password="segredo-ficticio")

    def test_combinado_NAO_devolve_o_item_para_a_fila(self):
        servicos.marcar_combinado(self.arremate, observacao="Paga amanhã de manhã")
        # Mesmo muito depois do prazo original.
        Arremate.objects.filter(pk=self.arremate.pk).update(
            expira_em=timezone.now() - timedelta(hours=5)
        )
        servicos.verificar_prazos()

        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "combinado")
        self.assertEqual(self.lote.status, "vendido")
        self.assertEqual(self.lote.voltas, 0)

    def test_guarda_o_que_foi_combinado_e_quem_falou(self):
        User = get_user_model()
        quem = User.objects.get(username="caixa_pd")
        servicos.marcar_combinado(self.arremate, quem, "Vai passar no clube sábado")
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.observacao, "Vai passar no clube sábado")
        self.assertEqual(self.arremate.combinado_por, quem)
        self.assertIsNotNone(self.arremate.combinado_em)

    def test_depois_de_combinado_ainda_da_para_marcar_pago(self):
        servicos.marcar_combinado(self.arremate)
        self.arremate.refresh_from_db()
        servicos.marcar_pago(self.arremate, manual=True)
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "pago")

    def test_combinado_NAO_entra_na_entrega(self):
        """Entrega é só do que foi PAGO — combinado ainda não é pago."""
        servicos.marcar_combinado(self.arremate)
        self.arremate.refresh_from_db()
        self.assertFalse(self.arremate.a_entregar)
        self.assertTrue(self.arremate.em_aberto)

    def test_quem_ja_pagou_nao_vira_combinado(self):
        servicos.marcar_pago(self.arremate, manual=True)
        self.arremate.refresh_from_db()
        servicos.marcar_combinado(self.arremate)
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "pago")

    def test_pela_tela_do_caixa(self):
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({
                "acao": "combinado",
                "arremate": self.arremate.id,
                "observacao": "Paga na segunda",
            }),
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "combinado")
        self.assertEqual(self.arremate.observacao, "Paga na segunda")

    def test_o_locutor_nao_combina_pagamento(self):
        """Combinar pagamento é mexer em dinheiro: é do caixa."""
        User = get_user_model()
        u = User.objects.create_user("loc_pd", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_pd", password="segredo-ficticio")
        r = c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "combinado", "arremate": self.arremate.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_entra_no_a_receber_do_caixa(self):
        servicos.marcar_combinado(self.arremate)
        r = self.c.get("/caixa/")
        self.assertEqual(r.context["resumo"]["combinados"], 1)
        self.assertEqual(r.context["resumo"]["a_receber"], self.arremate.valor)


class ColocarNoArAvisaTests(TestCase):
    """A tela diz "assim que iniciarmos, isto acende sozinho" — e tem de acender.

    Antes, colocar o leilão no ar não publicava evento nenhum: quem estava com o
    celular na mão desde antes continuava vendo a tela de espera até alguém
    abrir o primeiro item.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao(status="rascunho")
        criar_lote(self.leilao)

    def test_colocar_no_ar_publica_o_estado(self):
        publicados = []
        original = servicos.HUB.publicar
        servicos.HUB.publicar = lambda tipo, dados=None: publicados.append(tipo)
        try:
            servicos.mudar_status(self.leilao, "ao_vivo")
        finally:
            servicos.HUB.publicar = original

        self.assertIn("estado", publicados)
        self.leilao.refresh_from_db()
        self.assertEqual(self.leilao.status, "ao_vivo")

    def test_tirar_do_ar_tambem_avisa(self):
        servicos.mudar_status(self.leilao, "ao_vivo")
        publicados = []
        original = servicos.HUB.publicar
        servicos.HUB.publicar = lambda tipo, dados=None: publicados.append(tipo)
        try:
            servicos.mudar_status(self.leilao, "encerrado")
        finally:
            servicos.HUB.publicar = original
        self.assertIn("estado", publicados)

    def test_colocar_um_no_ar_encerra_o_outro(self):
        servicos.mudar_status(self.leilao, "ao_vivo")
        outro = criar_leilao(nome="Outro leilão", status="rascunho")
        servicos.mudar_status(outro, "ao_vivo")
        self.leilao.refresh_from_db()
        self.assertEqual(self.leilao.status, "encerrado")
        self.assertEqual(Leilao.objects.filter(status="ao_vivo").count(), 1)


class AcoesDosBotoesTests(TestCase):
    """Todo `data-acao` de template tem de existir no servidor.

    Sem esta guarda, um nome errado só aparece **no evento**, como um segundo
    balão dizendo "Ação desconhecida" ao lado do que deu certo — foi assim que o
    botão da música apareceu quebrado. Erro de digitação aqui é silencioso até
    alguém clicar.
    """

    # Ações tratadas só no navegador, que nunca chegam ao servidor com esse nome.
    SO_NO_CLIENTE = {"chat-fechar"}

    def test_todo_data_acao_existe_no_servidor(self):
        from .views import ACOES_AREAS

        usados = set()
        for arquivo in Path(settings.BASE_DIR, "templates", "leilao").rglob("*.html"):
            usados.update(re.findall(r'data-acao="([^"]+)"', arquivo.read_text(encoding="utf-8")))

        desconhecidos = usados - set(ACOES_AREAS) - self.SO_NO_CLIENTE
        self.assertEqual(
            desconhecidos, set(),
            f"Botões com ação que o servidor não conhece: {sorted(desconhecidos)}",
        )

    def test_toda_acao_do_servidor_tem_area(self):
        """Ação sem área seria ação sem dono — e o padrão tem de ser recusar."""
        from .views import ACOES_AREAS

        for acao, areas in ACOES_AREAS.items():
            self.assertTrue(areas, f"A ação {acao} não tem área nenhuma.")


class ArquivosDeJsExistemTests(TestCase):
    """`<script src>` apontando para arquivo que não existe é falha silenciosa.

    O Django devolve 404 no estático, o navegador engole e a tela só fica sem
    aquele pedaço. Nada no log do servidor, nada na tela. Um `{% static %}` com
    nome errado passaria por todos os outros testes.
    """

    def test_todo_script_de_template_tem_arquivo(self):
        padrao = re.compile(r"""\{%\s*static\s*['"](leilao/(?:js|css)/[^'"]+)['"]""")
        faltando = []
        for arquivo in Path(settings.BASE_DIR, "templates", "leilao").rglob("*.html"):
            for caminho in padrao.findall(arquivo.read_text(encoding="utf-8")):
                if not Path(settings.BASE_DIR, "static", caminho).exists():
                    faltando.append(f"{arquivo.name} → {caminho}")
        self.assertEqual(faltando, [], f"Estático citado e inexistente: {faltando}")


class TelaNaoApagaTests(TestCase):
    """O celular não pode apagar a tela no meio do pregão.

    Entre um lance e outro ninguém toca em nada — para o Android/iOS isso é
    aparelho ocioso, e o protetor de tela entra em 30 s. A pessoa perde o item
    por causa do economizador de bateria, que é a pior forma de perder.
    """

    CAMINHO = Path(settings.BASE_DIR, "static", "leilao", "js", "tela_acesa.js")

    def test_o_modulo_existe(self):
        self.assertTrue(self.CAMINHO.exists())

    def test_repoe_o_bloqueio_quando_a_aba_volta(self):
        """O sistema DERRUBA o bloqueio toda vez que a aba sai da frente.

        Sem ouvir `visibilitychange`, quem atende uma ligação volta com a tela
        apagando de novo — e parece que a proteção nunca existiu.
        """
        js = self.CAMINHO.read_text(encoding="utf-8")
        self.assertIn("visibilitychange", js)
        self.assertIn('wakeLock.request("screen")', js)

    def test_as_duas_telas_carregam_o_modulo(self):
        for nome in ("leilao.html", "locutor.html"):
            html = Path(settings.BASE_DIR, "templates", "leilao", nome).read_text(
                encoding="utf-8"
            )
            self.assertIn("leilao/js/tela_acesa.js", html, f"{nome} não segura a tela")

    def test_entrar_ja_segura_a_tela(self):
        """O toque na porta é o gesto que a API exige — é ali que se pede."""
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(
            encoding="utf-8"
        )
        trecho = js[js.index('$("btnPortaSom")'):]
        trecho = trecho[:trecho.index("});")]
        self.assertIn("segurarTela()", trecho)


class SoSeEntraComSomTests(TestCase):
    """A porta tem UM caminho, e ele liga o som.

    O botão "entrar sem som" saiu: quem errava o toque caía num leilão mudo e
    concluía que o site estava quebrado — não há como a pessoa adivinhar que o
    silêncio foi escolha dela. Sem o som não existe narração, não existe aviso
    de lance novo; é outro produto.
    """

    HTML = Path(settings.BASE_DIR, "templates", "leilao", "leilao.html")

    def test_a_porta_nao_tem_saida_muda(self):
        html = self.HTML.read_text(encoding="utf-8")
        porta = html[html.index('id="portaSom"'):html.index("<main")]
        botoes = re.findall(r'<button[^>]*id="(bt[^"]+)"', porta)
        self.assertEqual(botoes, ["btnPortaSom"], f"Porta com mais de um caminho: {botoes}")

    def test_mas_da_para_desligar_depois(self):
        """Tirar a saída da porta não é prender ninguém no som."""
        html = self.HTML.read_text(encoding="utf-8")
        self.assertIn('id="btnSom"', html)


class BotoesQueOJsProcuraExistemTests(TestCase):
    """`$("id").addEventListener` num id que não existe derruba o arquivo TODO.

    É `TypeError` em cima de `null`: o script morre naquela linha e tudo que
    vinha depois — lance, chat, reações — simplesmente não é ligado. A tela
    abre bonita e nenhum botão funciona. Foi o que quase aconteceu ao remover
    o "entrar sem som": o listener dele ficou para trás.
    """

    def test_ids_do_js_existem_no_template(self):
        pares = [("leilao.js", "leilao.html"), ("locutor.js", "locutor.html")]
        faltando = []
        for js_nome, html_nome in pares:
            js = Path(settings.BASE_DIR, "static", "leilao", "js", js_nome).read_text(
                encoding="utf-8"
            )
            html = Path(settings.BASE_DIR, "templates", "leilao", html_nome).read_text(
                encoding="utf-8"
            )
            # Só os acessos SEM guarda: `$("x").metodo`. Quem faz `var b = $("x");
            # if (b)` já está tratando a ausência de propósito.
            for ident in set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)\s*\.', js)):
                # `json_script:"x"` só vira `id="x"` na renderização — para o
                # scanner do arquivo cru os dois valem como declaração do id.
                if f'id="{ident}"' not in html and f'json_script:"{ident}"' not in html:
                    faltando.append(f"{js_nome} procura #{ident}, que não existe em {html_nome}")
        self.assertEqual(faltando, [], "; ".join(faltando))


class EnderecoCurtoTests(TestCase):
    """A entrada pede o mínimo que entrega o item: rua, número, bairro, cidade.

    CEP e UF saíram da tela. Cada campo a menos é uma desistência a menos numa
    tela preenchida com pressa, com o leilão já rolando — e nenhum dos dois
    ajuda alguém a achar a casa que os outros quatro já acham. A UF continua
    gravada (SP), porque o **roteiro de entrega** é endereço de verdade e
    endereço sem estado é endereço pela metade; o CEP fica em branco no model,
    para quem já foi cadastrado não perder o que tinha.
    """

    DADOS = {
        "nome": "Fulano de Teste", "whatsapp": "(11) 90000-0123",
        "logradouro": "Rua Exemplo", "numero": "10",
        "bairro": "Centro", "cidade": "Cidade Exemplo",
    }

    def test_entra_sem_cep(self):
        r = Client().post("/entrar/", self.DADOS)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Participante.objects.get(whatsapp="11900000123").cep, "")

    def test_a_tela_nao_pede_cep(self):
        html = Client().get("/entrar/").content.decode("utf-8")
        self.assertNotIn('name="cep"', html)

    def test_entra_sem_informar_a_uf(self):
        r = Client().post("/entrar/", self.DADOS)
        self.assertEqual(r.status_code, 302)
        p = Participante.objects.get(whatsapp="11900000123")
        self.assertEqual(p.estado, "SP")

    def test_o_endereco_da_entrega_sai_completo(self):
        Client().post("/entrar/", self.DADOS)
        linha = Participante.objects.get(whatsapp="11900000123").endereco_uma_linha
        self.assertIn("SP", linha)
        self.assertIn("Cidade Exemplo", linha)

    def test_nao_ha_campo_de_uf_para_digitar(self):
        html = Client().get("/entrar/").content.decode("utf-8")
        self.assertNotIn('placeholder="UF"', html)
        self.assertIn('name="estado"', html)   # continua indo, oculto

    def test_uf_forjada_vazia_nao_apaga_o_estado(self):
        """Campo oculto é editável por quem quiser — o servidor decide."""
        dados = dict(self.DADOS, estado="")
        Client().post("/entrar/", dados)
        self.assertEqual(Participante.objects.get(whatsapp="11900000123").estado, "SP")


class ChatNaoSobreviveAoLeilaoTests(TestCase):
    """O chat não pode ficar de pé depois de o leilão sair do ar.

    `chat_aberto_ate` é só uma hora futura gravada no banco: ela não sabe que o
    leilão acabou. Sem esta regra, a tela continuava mostrando a caixa de
    conversa (o relógio ainda não tinha vencido) e o servidor recusava cada
    mensagem com "nenhum leilão ao vivo" — a pessoa digitando contra uma porta
    fechada, sem entender por quê. Foi exatamente o que aconteceu no teste do
    clube.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao(chat_segundos=120)
        self.ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_chat(self.leilao, 120)
        self.leilao.refresh_from_db()

    def test_com_o_leilao_no_ar_o_chat_esta_aberto(self):
        self.assertTrue(self.leilao.chat_aberto)

    def test_encerrar_o_leilao_fecha_o_chat(self):
        servicos.mudar_status(self.leilao, "encerrado")
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.chat_aberto)
        self.assertIsNone(self.leilao.chat_aberto_ate)

    def test_o_relogio_futuro_sozinho_nao_abre_o_chat(self):
        """A trava é de status, não de hora — mesmo com o prazo intacto."""
        Leilao.objects.filter(pk=self.leilao.pk).update(status="encerrado")
        self.leilao.refresh_from_db()
        self.assertIsNotNone(self.leilao.chat_aberto_ate)   # prazo ainda de pé
        self.assertFalse(self.leilao.chat_aberto)

    def test_sair_do_ar_avisa_as_telas(self):
        """Quem está com a caixa aberta precisa vê-la sumir, não descobrir no envio."""
        publicados = []
        original = servicos.HUB.publicar
        servicos.HUB.publicar = lambda tipo, dados=None: publicados.append(tipo)
        try:
            servicos.mudar_status(self.leilao, "encerrado")
        finally:
            servicos.HUB.publicar = original
        self.assertIn("chat_estado", publicados)

    def test_colocar_outro_no_ar_fecha_o_chat_do_anterior(self):
        outro = criar_leilao(nome="Outro leilão", status="rascunho")
        servicos.mudar_status(outro, "ao_vivo")
        self.leilao.refresh_from_db()
        self.assertEqual(self.leilao.status, "encerrado")
        self.assertIsNone(self.leilao.chat_aberto_ate)

    def test_a_recusa_explica_o_que_houve(self):
        """"Nenhum leilão ao vivo" é verdade para o servidor e mentira para quem lê."""
        c = Client()
        c.post("/entrar/", {
            "nome": "Fulano de Teste", "whatsapp": "(11) 90000-0456",
            "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "cidade": "Cidade Exemplo",
        })
        servicos.mudar_status(self.leilao, "encerrado")
        r = c.post(
            "/chat/enviar/", data=json.dumps({"texto": "oi"}),
            content_type="application/json",
        )
        self.assertFalse(r.json()["ok"])
        self.assertIn("encerrado", r.json()["msg"].lower())


class PregaoNaoSobreviveAoLeilaoTests(TestCase):
    """Leilão fora do ar não pode ter item em pregão.

    Caso real da produção: os três leilões estavam `encerrado`, `Leilao.ao_vivo()`
    devolvia `None` — e a mesa do locutor mostrava "item em pregão, sala calada",
    contando o silêncio de um item aberto dias antes. Dois defeitos somados:

    1. `mudar_status` aprendeu a fechar o **chat** ao sair do ar e esqueceu o
       **lote**, que ficava `aberto` no banco para sempre;
    2. `estado_publico` respondia `ativo: True` para qualquer leilão não-nulo,
       confiando em quem chamava ter passado o que está no ar. A tela pública
       acertava por acidente (passa `Leilao.ao_vivo()`); a mesa **cai para o
       leilão mais recente** e entregava um encerrado.

    É a mesma lição do chat: o que é do pregão morre com o pregão, e a trava
    mora no estado, não em quem o chama.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()

    def test_com_o_leilao_no_ar_o_item_esta_em_pregao(self):
        self.assertEqual(self.lote.status, "aberto")
        self.assertTrue(est.estado_publico(self.leilao)["ativo"])

    def test_encerrar_o_leilao_devolve_o_item_para_a_fila(self):
        servicos.mudar_status(self.leilao, "encerrado")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "fila")

    def test_o_item_volta_LIMPO_para_a_fila(self):
        """Na fila exibindo líder e valor de uma disputa abandonada, não."""
        ana = criar_pessoa("Ana Fictícia")
        servicos.dar_lance(self.lote.id, ana)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.lider_id, ana.id)

        servicos.mudar_status(self.leilao, "encerrado")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "fila")
        self.assertIsNone(self.lote.lider_id)
        self.assertEqual(self.lote.valor_atual, Decimal("0.00"))

    def test_leilao_encerrado_nao_tem_pregao_no_estado(self):
        """A guarda é do ESTADO, não de quem chama — mesmo com o lote `aberto`.

        É este o teste que pega o caso da mesa: ela passa o leilão mais recente,
        e o lote continua `aberto` no banco (dado antigo, anterior à correção).
        """
        Leilao.objects.filter(pk=self.leilao.pk).update(status="encerrado")
        self.leilao.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")   # o órfão continua lá
        self.assertFalse(est.estado_publico(self.leilao)["ativo"])

    def test_rascunho_tambem_nao_e_pregao(self):
        """Leilão que ainda está sendo preparado não é leilão no ar."""
        Leilao.objects.filter(pk=self.leilao.pk).update(status="rascunho")
        self.leilao.refresh_from_db()
        self.assertFalse(est.estado_publico(self.leilao)["ativo"])

    def test_colocar_outro_no_ar_devolve_o_item_do_anterior(self):
        """O leilão que sai para dar lugar a outro também deixa o item limpo."""
        outro = criar_leilao(nome="Outro leilão", status="rascunho")
        servicos.mudar_status(outro, "ao_vivo")
        self.leilao.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.leilao.status, "encerrado")
        self.assertEqual(self.lote.status, "fila")



class SemDesfazerLanceTests(TestCase):
    """Não há "desfazer lance". O clube olhou a mesa e não quis o botão.

    Ele existia para o caso de o locutor errar. Some junto a regra de negócio
    inteira: sem botão, sem ação no servidor e sem o evento `lance_desfeito`.
    O que **fica** é `Lance.cancelado` no model — coluna dormente, como as da
    música.
    """

    def test_nao_existe_acao_de_desfazer(self):
        from .views import ACOES_AREAS
        self.assertNotIn("desfazer", ACOES_AREAS)

    def test_o_servico_saiu(self):
        self.assertFalse(hasattr(servicos, "desfazer_ultimo_lance"))

    def test_a_mesa_nao_tem_o_botao(self):
        User = get_user_model()
        u = User.objects.create_user("loc_sem_desfazer", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_sem_desfazer", password="segredo-ficticio")

        html = c.get("/locutor/").content.decode("utf-8")
        self.assertNotIn('data-acao="desfazer"', html)

    def test_o_servidor_recusa_a_acao_forjada(self):
        User = get_user_model()
        u = User.objects.create_user("loc_forja_desf", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_forja_desf", password="segredo-ficticio")

        r = c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "desfazer"}),
            content_type="application/json",
        )
        self.assertFalse(r.json()["ok"])


class NumeroDoItemTests(TestCase):
    """Cada item ganha um número, e ele é a etiqueta colada no objeto físico.

    É o que liga o que está na tela ao que está na prateleira. Por isso ele
    nasce sozinho (numeração escrita à mão repete, pula e desencontra) e **não
    muda nunca** — se mudasse, a etiqueta na caixa passaria a apontar para
    outro item, e o desencontro só apareceria na hora de entregar.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()

    def test_numera_sozinho_a_partir_de_um(self):
        a = criar_lote(self.leilao, nome="Primeiro")
        b = criar_lote(self.leilao, nome="Segundo")
        self.assertEqual(a.numero, 1)
        self.assertEqual(b.numero, 2)

    def test_cada_leilao_comeca_do_um(self):
        """A etiqueta é do evento daquela noite — começar em 87 não diz nada."""
        criar_lote(self.leilao, nome="Item de novembro")
        outro = criar_leilao(nome="Leilão de dezembro")
        self.assertEqual(criar_lote(outro, nome="Item de dezembro").numero, 1)

    def test_apagar_um_item_nao_recicla_o_numero(self):
        """Reaproveitar número já colado numa caixa é o pior dos dois mundos.

        Contar pelo MAIOR número em uso não resolve: apagando o último, o maior
        volta a ser o anterior e o próximo cadastro repete um número que talvez
        já esteja etiquetado. Por isso o contador fica no leilão e só sobe.
        """
        criar_lote(self.leilao, nome="Primeiro")
        segundo = criar_lote(self.leilao, nome="Segundo")
        segundo.delete()
        self.assertEqual(criar_lote(self.leilao, nome="Terceiro").numero, 3)

    def test_item_que_volta_para_a_fila_mantem_o_numero(self):
        """O arrematante não pagou: o item volta a leilão — com a MESMA etiqueta.

        A etiqueta está colada no objeto. Se o número mudasse ao voltar para a
        fila, a caixa na prateleira passaria a apontar para outra coisa.
        """
        lote = criar_lote(self.leilao, nome="Cesta fictícia")
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, ana)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote, motivo="locutor")

        numero_antes = lote.numero
        servicos.expirar_arremate(arremate)   # não pagou no prazo

        lote.refresh_from_db()
        self.assertEqual(lote.status, "fila")     # voltou a leilão
        self.assertEqual(lote.voltas, 1)
        self.assertEqual(lote.numero, numero_antes)

    def test_e_continua_o_mesmo_depois_de_arrematado_de_novo(self):
        lote = criar_lote(self.leilao, nome="Cesta fictícia")
        ana = criar_pessoa("Ana Fictícia")
        bruno = criar_pessoa("Bruno Fictício")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, ana)
        lote.refresh_from_db()
        servicos.expirar_arremate(servicos.fechar_lote(lote, motivo="locutor"))

        lote.refresh_from_db()
        servicos.abrir_lote(lote)             # segunda volta
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, bruno)
        lote.refresh_from_db()
        servicos.fechar_lote(lote, motivo="locutor")

        lote.refresh_from_db()
        self.assertEqual(lote.numero, 1)

    def test_o_numero_nao_muda_ao_editar(self):
        lote = criar_lote(self.leilao, nome="Cesta")
        lote.nome = "Cesta de café da manhã"
        lote.ordem = 9
        lote.save()
        lote.refresh_from_db()
        self.assertEqual(lote.numero, 1)

    def test_nao_repete_dentro_do_leilao(self):
        criar_lote(self.leilao, nome="Primeiro")
        repetido = Lote(leilao=self.leilao, nome="Clone", numero=1,
                        lance_inicial=Decimal("10.00"))
        with self.assertRaises(IntegrityError):
            repetido.save()

    def test_o_publico_NAO_ve_o_numero(self):
        """"Item nº 12" conta que existem pelo menos 12 itens.

        Quantos faltam é justamente o que o público não pode saber — quem
        descobre que falta pouco segura o dinheiro.
        """
        lote = criar_lote(self.leilao, nome="Cesta")
        criar_lote(self.leilao, nome="Outro")
        criar_lote(self.leilao, nome="Mais outro")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()

        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertNotIn("numero", dados["lote"])

    def test_a_mesa_do_locutor_ve(self):
        lote = criar_lote(self.leilao, nome="Cesta")
        na_fila = criar_lote(self.leilao, nome="Depois")
        servicos.abrir_lote(lote)

        User = get_user_model()
        u = User.objects.create_user("loc_numero", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_numero", password="segredo-ficticio")

        d = c.get("/locutor/dados/").json()
        self.assertEqual(d["numero_atual"], lote.numero)
        self.assertEqual([x["numero"] for x in d["fila"]], [na_fila.numero])

    def test_o_roteiro_de_entrega_leva_o_numero(self):
        """Quem separa as caixas procura a etiqueta, não o nome do item."""
        lote = criar_lote(self.leilao, nome="Cesta fictícia")
        ana = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, ana)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote, motivo="locutor")
        servicos.marcar_pago(arremate, manual=True)

        User = get_user_model()
        u = User.objects.create_user("cx_numero", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        c = Client()
        c.login(username="cx_numero", password="segredo-ficticio")

        self.assertIn(f"nº {lote.numero}", c.get("/caixa/").context["roteiro"])


class SemCronometroTests(TestCase):
    """Não há cronômetro em lugar nenhum do pregão.

    Nenhum item fecha sozinho: quem bate o martelo é o locutor. Os campos de
    configuração ("tempo por lote", "tempo extra", "reiniciar a cada lance") e o
    botão +Ns saíram — config para um recurso que não existe só confunde quem
    monta o leilão. O que ficou no banco são colunas dormentes.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia")

    def test_o_lote_abre_sem_hora_para_fechar(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.fecha_em)

    def test_o_lance_nao_liga_relogio_nenhum(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.fecha_em)

    def test_o_tempo_passa_e_o_item_continua_aberto(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.ana)
        Lote.objects.filter(pk=self.lote.pk).update(
            aberto_em=timezone.now() - timedelta(hours=2)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")
        self.assertEqual(Arremate.objects.count(), 0)

    def test_o_estado_nao_transmite_relogio(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        lote = est.estado_publico(Leilao.ao_vivo())["lote"]
        for chave in ("fecha_em", "total_segundos", "fechamento_automatico"):
            self.assertNotIn(chave, lote)

    def test_nao_existe_acao_de_tempo(self):
        from .views import ACOES_AREAS
        self.assertNotIn("tempo", ACOES_AREAS)

    def test_o_servico_de_somar_tempo_saiu(self):
        self.assertFalse(hasattr(servicos, "somar_tempo"))

    def test_a_configuracao_nao_pede_tempo(self):
        campos = LeilaoForm().fields
        for chave in ("segundos_por_lote", "segundos_extra", "reiniciar_cronometro"):
            self.assertNotIn(chave, campos)

    def test_nao_existe_mais_pausar(self):
        """Para segurar o pregão, o locutor simplesmente não abre o próximo item.

        Pausar só fazia diferença DURANTE um item já aberto, e mesmo aí a saída
        é bater o martelo ou deixar rolar. Um botão a menos numa mesa que se
        opera falando ao mesmo tempo.
        """
        from .views import ACOES_AREAS
        self.assertNotIn("pausar", ACOES_AREAS)
        self.assertNotIn("retomar", ACOES_AREAS)
        self.assertFalse(hasattr(servicos, "pausar_lote"))

    def test_a_mesa_nao_tem_botao_de_pausa(self):
        User = get_user_model()
        u = User.objects.create_user("loc_sem_pausa", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_sem_pausa", password="segredo-ficticio")
        html = c.get("/locutor/").content.decode("utf-8")
        self.assertNotIn("btnPausa", html)

    def test_o_estado_nao_fala_de_pausa(self):
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        self.assertNotIn("pausado", est.estado_publico(Leilao.ao_vivo())["lote"])

class DividirEntregasTests(TestCase):
    """Dividir as entregas entre os voluntários que vão rodar a cidade.

    **Não há mapa.** O clube guarda rua, número, bairro e cidade — não guarda
    coordenada. A divisão é por BAIRRO, que é o recorte que as pessoas usam para
    falar de região, equilibrando o número de paradas. A tela diz isso em voz
    alta: precisão inventada seria pior que o limite declarado.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()

    def _entregar(self, nome, bairro, cidade="Cidade Exemplo", quantos=1):
        """Cria uma pessoa com N itens PAGOS, prontos para entrega."""
        pessoa = criar_pessoa(nome, bairro=bairro, cidade=cidade,
                              logradouro="Rua Exemplo", numero="10")
        arremates = []
        for i in range(quantos):
            # O freio de 300 ms entre lances da mesma pessoa é real e vale aqui:
            # sem zerar, o segundo lance do fixture é recusado e o lote fecha
            # "sem lance" — e o teste falha por um motivo que não é o dele.
            servicos.limpar_limites()
            lote = criar_lote(self.leilao, nome=nome + " item " + str(i))
            servicos.abrir_lote(lote)
            lote.refresh_from_db()
            servicos.dar_lance(lote.id, pessoa)
            lote.refresh_from_db()
            a = servicos.fechar_lote(lote, motivo="locutor")
            servicos.marcar_pago(a, manual=True)
            a.refresh_from_db()
            arremates.append(a)
        return arremates

    def test_um_entregador_leva_tudo(self):
        a = self._entregar("Ana Fictícia", "Centro")
        b = self._entregar("Bruno Fictício", "Jardim Exemplo")
        rotas = entregas.dividir(a + b, 1)
        self.assertEqual(len(rotas), 1)
        self.assertEqual(len(rotas[0]), 2)

    def test_bairros_diferentes_vao_para_entregadores_diferentes(self):
        a = self._entregar("Ana Fictícia", "Centro")
        b = self._entregar("Bruno Fictício", "Jardim Exemplo")
        rotas = entregas.dividir(a + b, 2)
        self.assertEqual([len(r) for r in rotas], [1, 1])

    def test_o_mesmo_bairro_NAO_e_partido(self):
        """Partir um bairro é o que a divisão existe para evitar."""
        juntos = []
        for nome in ("Ana Fictícia", "Bruno Fictício", "Carla Fictícia"):
            juntos += self._entregar(nome, "Centro")
        rotas = entregas.dividir(juntos, 3)
        cheias = [r for r in rotas if r]
        self.assertEqual(len(cheias), 1)
        self.assertEqual(len(cheias[0]), 3)

    def test_bairro_escrito_de_outro_jeito_conta_como_o_mesmo(self):
        """Grafias diferentes do mesmo bairro não podem virar duas regiões."""
        a = self._entregar("Ana Fictícia", "Jardim Exemplo")
        b = self._entregar("Bruno Fictício", "  jardim  exemplo ")
        cheias = [r for r in entregas.dividir(a + b, 2) if r]
        self.assertEqual(len(cheias), 1)

    def test_acento_tambem_nao_separa(self):
        a = self._entregar("Ana Fictícia", "Jardim Acadêmico")
        b = self._entregar("Bruno Fictício", "jardim academico")
        cheias = [r for r in entregas.dividir(a + b, 2) if r]
        self.assertEqual(len(cheias), 1)

    def test_dois_itens_da_mesma_casa_sao_UMA_parada(self):
        """Contar item em vez de visita faria um entregador parecer sobrecarregado."""
        ana = self._entregar("Ana Fictícia", "Centro", quantos=3)
        rotas = entregas.dividir(ana, 1)
        self.assertEqual(len(rotas[0]), 1)
        self.assertEqual(len(rotas[0][0]["itens"]), 3)

    def test_equilibra_a_carga_entre_os_entregadores(self):
        todos = []
        todos += self._entregar("Ana Fictícia", "Centro")
        todos += self._entregar("Bruno Fictício", "Centro")
        todos += self._entregar("Carla Fictícia", "Centro")
        todos += self._entregar("Davi Fictício", "Jardim Exemplo")
        todos += self._entregar("Elza Fictícia", "Vila Exemplo")
        rotas = entregas.dividir(todos, 2)
        tamanhos = sorted(len(r) for r in rotas)
        # 3 (Centro) de um lado, 1 + 1 do outro: o melhor equilíbrio possível
        # sem partir bairro nenhum.
        self.assertEqual(tamanhos, [2, 3])

    def test_mais_entregadores_do_que_bairros_deixa_alguem_sem_rota(self):
        """E isso tem de aparecer, não quebrar: a tela avisa."""
        a = self._entregar("Ana Fictícia", "Centro")
        rotas = entregas.dividir(a, 3)
        self.assertEqual(len(rotas), 3)
        self.assertEqual(sum(1 for r in rotas if r), 1)

    def test_a_divisao_e_sempre_a_mesma(self):
        """A equipe reabre a tela e precisa ver o mesmo resultado."""
        todos = []
        for nome, bairro in [("Ana Fictícia", "Centro"),
                             ("Bruno Fictício", "Vila Exemplo"),
                             ("Carla Fictícia", "Centro"),
                             ("Davi Fictício", "Jardim Exemplo")]:
            todos += self._entregar(nome, bairro)
        primeira = [[p["pessoa"].id for p in r] for r in entregas.dividir(todos, 2)]
        segunda = [[p["pessoa"].id for p in r] for r in entregas.dividir(todos, 2)]
        self.assertEqual(primeira, segunda)

    def test_sem_bairro_cadastrado_nao_quebra(self):
        pessoa = criar_pessoa("Sem Bairro Fictício", bairro="", cidade="")
        lote = criar_lote(self.leilao, nome="Cesta")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        a = servicos.fechar_lote(lote, motivo="locutor")
        servicos.marcar_pago(a, manual=True)
        a.refresh_from_db()

        rotas = entregas.dividir([a], 1)
        self.assertEqual(rotas[0][0]["rotulo"], "Sem bairro informado")

    def test_o_texto_da_rota_leva_endereco_e_numero_do_item(self):
        ana = self._entregar("Ana Fictícia", "Centro")
        rotas = entregas.dividir(ana, 1)
        texto = entregas.texto_da_rota(self.leilao, 1, rotas[0], 1)
        self.assertIn("Ana Fictícia", texto)
        self.assertIn("Rua Exemplo", texto)
        self.assertIn("Centro", texto)
        self.assertIn("nº " + str(ana[0].lote.numero), texto)
        self.assertIn("1/1", texto)


class TelaDeDividirEntregasTests(TestCase):
    """A divisão pela tela do caixa."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("cx_rotas", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="cx_rotas", password="segredo-ficticio")

        for nome, bairro in [("Ana Fictícia", "Centro"),
                             ("Bruno Fictício", "Vila Exemplo")]:
            pessoa = criar_pessoa(nome, bairro=bairro, cidade="Cidade Exemplo",
                                  logradouro="Rua Exemplo", numero="10")
            lote = criar_lote(self.leilao, nome="Item de " + nome)
            servicos.abrir_lote(lote)
            lote.refresh_from_db()
            servicos.dar_lance(lote.id, pessoa)
            lote.refresh_from_db()
            servicos.marcar_pago(
                servicos.fechar_lote(lote, motivo="locutor"), manual=True
            )

    def test_sem_entregador_nenhum_o_quadro_manda_de_volta(self):
        """O quadro precisa saber quantas colunas desenhar; quem chega sem dizer
        volta para a tela que pergunta."""
        r = self.c.get("/caixa/entregas/")
        self.assertRedirects(r, "/caixa/")

    def test_dividir_por_dois(self):
        r = self.c.get("/caixa/entregas/?entregadores=2")
        self.assertEqual(len(r.context["colunas"]), 2)
        self.assertEqual([len(c["paradas"]) for c in r.context["colunas"]], [1, 1])
        # Nasce já distribuído: a divisão por bairro é o ponto de partida.
        self.assertEqual(r.context["a_distribuir"], [])

    def test_a_tela_avisa_que_nao_ha_mapa(self):
        """Precisão inventada é pior que limite declarado."""
        html = self.c.get("/caixa/?entregadores=2").content.decode("utf-8")
        self.assertIn("não consulta mapa", html)

    def test_numero_invalido_nao_quebra(self):
        for valor in ("abc", "-3", "0", "999"):
            r = self.c.get("/caixa/?entregadores=" + valor)
            self.assertEqual(r.status_code, 200)

    def test_o_campo_de_entrega_nao_pede_mais_rastreio(self):
        """Entrega é na mão, por voluntário: não existe código de rastreio."""
        html = self.c.get("/caixa/").content.decode("utf-8")
        self.assertNotIn("rastreio", html.lower())
        self.assertIn("Quem recebeu", html)


class QuadroDeEntregasTests(TestCase):
    """O quadro onde a equipe arrasta quem leva o quê.

    A divisão automática **não sabe que um bairro é perto do outro** — ela só
    compara nomes de bairro, que é tudo o que dá para fazer sem mapa. O quadro é
    onde quem conhece a cidade corrige isso, e o que ele guarda é essa correção.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("cx_quadro", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="caixa")[0])
        self.c = Client()
        self.c.login(username="cx_quadro", password="segredo-ficticio")
        self.ana = self._entregar("Ana Fictícia", "Centro")
        self.bruno = self._entregar("Bruno Fictício", "Vila Exemplo")

    def _entregar(self, nome, bairro):
        """Uma pessoa com um item PAGO, pronta para entrega."""
        servicos.limpar_limites()
        pessoa = criar_pessoa(nome, bairro=bairro, cidade="Cidade Exemplo",
                              logradouro="Rua Exemplo", numero="10")
        lote = criar_lote(self.leilao, nome="Item de " + nome)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        servicos.marcar_pago(servicos.fechar_lote(lote, motivo="locutor"), manual=True)
        return pessoa

    def _abrir(self, quantos=2):
        return self.c.get("/caixa/entregas/?entregadores=" + str(quantos))

    def _mover(self, pessoa, entregador):
        return self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "entrega_mover", "participante": pessoa.id,
                             "entregador": entregador}),
            content_type="application/json",
        )

    # --- montagem ---

    def test_o_quadro_nasce_dividido_por_bairro(self):
        """Ponto de partida: corrigir o que já está quase certo é mais rápido do
        que montar do zero."""
        self._abrir(2)
        self.assertEqual(AtribuicaoEntrega.objects.filter(leilao=self.leilao).count(), 2)
        self.assertEqual(AtribuicaoEntrega.objects.filter(entregador=0).count(), 0)

    def test_abrir_de_novo_nao_desfaz_o_que_foi_arrastado(self):
        """O quadro é a memória do trabalho manual: resemear por cima apagaria
        exatamente aquilo que ele existe para guardar."""
        self._abrir(2)
        self._mover(self.ana, 2)
        self._abrir(2)
        self.assertEqual(
            AtribuicaoEntrega.objects.get(participante=self.ana).entregador, 2
        )

    def test_quem_paga_depois_cai_em_a_distribuir(self):
        """Entrar sozinho na rota de alguém seria pior: ninguém repara no que
        aparece já resolvido."""
        self._abrir(2)
        atrasada = self._entregar("Carla Fictícia", "Centro")
        r = self._abrir(2)
        nomes = [p["pessoa"].nome for p in r.context["a_distribuir"]]
        self.assertEqual(nomes, [atrasada.nome])

    # --- arrastar ---

    def test_arrastar_salva_na_hora(self):
        self._abrir(2)
        r = self._mover(self.ana, 2)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(
            AtribuicaoEntrega.objects.get(participante=self.ana).entregador, 2
        )

    def test_arrastar_de_volta_para_a_fila(self):
        self._abrir(2)
        self._mover(self.ana, 0)
        self.assertEqual(
            AtribuicaoEntrega.objects.get(participante=self.ana).entregador, 0
        )
        self.assertEqual(len(self._abrir(2).context["a_distribuir"]), 1)

    def test_a_resposta_traz_o_texto_novo_da_rota(self):
        """O texto copiável vem do servidor a cada movimento — se o navegador o
        montasse, a mensagem do WhatsApp e a tela poderiam discordar."""
        self._abrir(2)
        dados = self._mover(self.ana, 2).json()
        coluna2 = next(c for c in dados["colunas"] if c["numero"] == 2)
        self.assertIn("Ana Fictícia", coluna2["texto"])
        self.assertEqual(coluna2["paradas"], 2)

    def test_pessoa_sem_entrega_pendente_e_recusada(self):
        """Esconder o cartão não protege nada: a conferência é do servidor."""
        self._abrir(2)
        estranha = criar_pessoa("Estranha Fictícia", bairro="Centro",
                                cidade="Cidade Exemplo")
        r = self._mover(estranha, 1)
        self.assertEqual(r.status_code, 404)
        self.assertFalse(AtribuicaoEntrega.objects.filter(participante=estranha).exists())

    def test_entregador_que_nao_existe_e_recusado(self):
        self._abrir(2)
        r = self._mover(self.ana, 9)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(
            AtribuicaoEntrega.objects.get(participante=self.ana).entregador, 1
        )

    def test_o_locutor_nao_mexe_no_quadro(self):
        """Quem protege é a view, nunca o menu."""
        self._abrir(2)
        User = get_user_model()
        loc = User.objects.create_user("loc_quadro", password="segredo-ficticio")
        loc.is_staff = True
        loc.save()
        loc.groups.add(Group.objects.get_or_create(name="locutor")[0])
        outro = Client()
        outro.login(username="loc_quadro", password="segredo-ficticio")
        r = outro.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "entrega_mover", "participante": self.ana.id,
                             "entregador": 2}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    # --- nome do entregador ---

    def test_nome_do_entregador_entra_no_texto_da_rota(self):
        """A mensagem vai no particular do voluntário: "ENTREGAS 2/4" não diz a
        quem ela pertence quando ele reabre a conversa dois dias depois."""
        self._abrir(2)
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "entrega_nome", "entregador": 1,
                             "nome": "Voluntária Fictícia"}),
            content_type="application/json",
        )
        dados = r.json()
        self.assertEqual(dados["rotulo"], "Voluntária Fictícia")
        coluna1 = next(c for c in dados["colunas"] if c["numero"] == 1)
        self.assertIn("ENTREGAS DE VOLUNTÁRIA FICTÍCIA", coluna1["texto"])

    def test_sem_nome_a_coluna_continua_sendo_o_numero(self):
        self._abrir(2)
        coluna = EntregadorLeilao.objects.get(leilao=self.leilao, numero=2)
        self.assertEqual(coluna.rotulo, "Entregador 2")

    # --- mudar o número de colunas ---

    def test_diminuir_as_colunas_devolve_as_paradas_para_a_fila(self):
        """A atribuição não é apagada, mas a tela nunca mostra parada num
        entregador que não está mais lá."""
        self._abrir(2)
        self._mover(self.ana, 2)
        r = self._abrir(1)
        self.assertEqual(len(r.context["colunas"]), 1)
        nomes = [p["pessoa"].nome for p in r.context["a_distribuir"]]
        self.assertIn(self.ana.nome, nomes)

    def test_aumentar_as_colunas_nao_remexe_no_que_ja_estava(self):
        self._abrir(2)
        r = self._abrir(4)
        self.assertEqual(len(r.context["colunas"]), 4)
        self.assertEqual(
            AtribuicaoEntrega.objects.get(participante=self.ana).entregador, 1
        )

    def test_numero_invalido_de_entregadores_nao_quebra(self):
        self._abrir(2)
        for valor in ("abc", "-3", "999"):
            r = self.c.get("/caixa/entregas/?entregadores=" + valor)
            self.assertEqual(r.status_code, 200)

    # --- recomeçar ---

    def test_refazer_por_bairro_joga_fora_o_que_foi_arrastado(self):
        self._abrir(2)
        self._mover(self.ana, 2)
        r = self.c.post("/caixa/entregas/redistribuir/")
        self.assertRedirects(r, "/caixa/entregas/")
        self.assertEqual(
            AtribuicaoEntrega.objects.get(participante=self.ana).entregador, 1
        )

    # --- a tela ---

    def test_a_tela_diz_que_nao_ha_mapa(self):
        """Precisão inventada é pior que limite declarado — e é o motivo de o
        quadro existir."""
        self.assertIn("não consulta mapa", self._abrir(2).content.decode("utf-8"))

    def test_a_tela_mostra_o_bairro_em_destaque(self):
        """É por ele que a equipe decide o que é perto do quê."""
        html = self._abrir(2).content.decode("utf-8")
        self.assertIn("parada-bairro", html)
        self.assertIn("Centro — Cidade Exemplo", html)


class ContasDaEquipeTests(TestCase):
    """A tela de Usuários: o diretor cria a conta de quem vai ajudar hoje.

    O que estes testes seguram é a regra, não a tela: a senha padrão vale para
    **uma** entrada, e enquanto ela não for trocada nada mais abre — nem pelo
    botão, nem por POST forjado.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        User = get_user_model()
        self.chefe = User.objects.create_user("diretora", password="segredo-ficticio")
        self.chefe.is_staff = True
        self.chefe.save()
        grupo, _ = Group.objects.get_or_create(name="diretor")
        self.chefe.groups.add(grupo)
        self.c = Client()
        self.c.login(username="diretora", password="segredo-ficticio")

    def _criar(self, nome="Maria Fictícia", usuario="", papeis=("caixa",)):
        return self.c.post(
            "/equipe/usuarios/",
            {"nome": nome, "usuario": usuario, "papeis": list(papeis)},
        )

    # --- quem abre a tela ---
    def test_a_tela_abre_para_o_diretor(self):
        self.assertEqual(self.c.get("/equipe/usuarios/").status_code, 200)

    def test_quem_nao_e_diretor_nao_abre(self):
        """Ter papel não basta: cadastrar equipe é do diretor."""
        User = get_user_model()
        u = User.objects.create_user("so_caixa", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        c = Client()
        c.login(username="so_caixa", password="segredo-ficticio")
        # `target_status_code=302`: quem tem UMA área só não para no hub — ele
        # manda direto para a tela dela (aqui, /caixa/).
        self.assertRedirects(
            c.get("/equipe/usuarios/"), "/equipe/", target_status_code=302
        )

    def test_sem_login_nao_abre(self):
        self.assertEqual(Client().get("/equipe/usuarios/").status_code, 302)

    def test_a_aba_aparece_para_o_diretor_e_some_para_os_outros(self):
        html = self.c.get("/equipe/").content.decode("utf-8")
        self.assertIn("/equipe/usuarios/", html)

        User = get_user_model()
        u = User.objects.create_user("so_loc", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="so_loc", password="segredo-ficticio")
        self.assertNotIn("/equipe/usuarios/", c.get("/locutor/").content.decode("utf-8"))

    # --- cadastro ---
    def test_cadastro_cria_a_conta_com_a_senha_padrao(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        User = get_user_model()
        u = User.objects.get(username="maria")
        self.assertTrue(u.is_staff)
        self.assertTrue(u.check_password(equipe.SENHA_PADRAO))
        self.assertEqual(papeis.papeis_do(u), {"caixa"})
        self.assertTrue(u.conta_leilao.senha_provisoria)

    def test_o_usuario_sai_do_nome_quando_nao_e_digitado(self):
        self._criar(nome="Joana Fictícia da Silva")
        self.assertTrue(get_user_model().objects.filter(username="joana").exists())

    def test_nome_repetido_nao_derruba_o_cadastro(self):
        """Duas Marias na mesma noite acontece — a segunda vira maria.souza."""
        self._criar(nome="Maria Fictícia")
        self._criar(nome="Maria Souza")
        nomes = set(get_user_model().objects.values_list("username", flat=True))
        self.assertIn("maria", nomes)
        self.assertIn("maria.souza", nomes)

    def test_da_para_escolher_o_usuario(self):
        self._criar(nome="Pedro Fictício", usuario="pedrinho")
        self.assertTrue(get_user_model().objects.filter(username="pedrinho").exists())

    def test_usuario_repetido_e_recusado(self):
        self._criar(nome="Pedro Fictício", usuario="pedrinho")
        r = self._criar(nome="Outro Fictício", usuario="pedrinho")
        self.assertEqual(r.status_code, 200)  # volta com erro, não redireciona
        self.assertEqual(get_user_model().objects.filter(username="pedrinho").count(), 1)

    def test_papeis_acumulam(self):
        self._criar(nome="Duas Funcoes", papeis=("locutor", "caixa"))
        u = get_user_model().objects.get(username="duas")
        self.assertEqual(papeis.papeis_do(u), {"locutor", "caixa"})

    def test_sem_funcao_o_cadastro_e_recusado(self):
        """Conta sem papel entra e não vê tela nenhuma — não é cadastro, é armadilha."""
        r = self._criar(nome="Ninguem Fictício", papeis=())
        self.assertEqual(r.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(username="ninguem").exists())

    # --- a troca obrigatória ---
    def test_a_conta_nova_so_abre_a_tela_de_senha(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa", "locutor"))
        c = Client()
        self.assertTrue(c.login(username="maria", password=equipe.SENHA_PADRAO))
        for url in ["/equipe/", "/caixa/", "/locutor/", "/equipe/usuarios/"]:
            with self.subTest(url=url):
                self.assertRedirects(c.get(url), "/equipe/senha/")

    def test_o_post_da_equipe_tambem_e_barrado_ate_a_troca(self):
        """Esconder a tela não protege: o botão responde por fetch."""
        self._criar(nome="Maria Fictícia", papeis=("locutor",))
        lote = criar_lote(self.leilao)
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        r = c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "abrir", "lote": lote.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)
        lote.refresh_from_db()
        self.assertEqual(lote.status, "fila")

    def test_depois_de_trocar_as_telas_abrem(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        r = c.post("/equipe/senha/", {"senha": "123", "repetir": "123"})
        self.assertRedirects(r, "/equipe/", target_status_code=302)
        self.assertEqual(c.get("/caixa/").status_code, 200)

    def test_a_sessao_sobrevive_a_troca(self):
        """Sem `update_session_auth_hash` a pessoa cai no login logo depois de obedecer."""
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        c.post("/equipe/senha/", {"senha": "123", "repetir": "123"})
        self.assertEqual(c.get("/caixa/").status_code, 200)

    def test_senha_curta_e_aceita(self):
        """Decisão do clube: voluntário no celular, no meio do evento."""
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        c.post("/equipe/senha/", {"senha": "123", "repetir": "123"})
        u = get_user_model().objects.get(username="maria")
        self.assertTrue(u.check_password("123"))
        self.assertFalse(u.conta_leilao.senha_provisoria)

    def test_repetir_a_senha_padrao_e_recusado(self):
        """Aceitar faria a troca não trocar nada."""
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        r = c.post(
            "/equipe/senha/",
            {"senha": equipe.SENHA_PADRAO, "repetir": equipe.SENHA_PADRAO},
        )
        self.assertEqual(r.status_code, 200)
        u = get_user_model().objects.get(username="maria")
        self.assertTrue(u.conta_leilao.senha_provisoria)

    def test_senhas_diferentes_sao_recusadas(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        r = c.post("/equipe/senha/", {"senha": "abc", "repetir": "abd"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            get_user_model().objects.get(username="maria").conta_leilao.senha_provisoria
        )

    def test_quem_ja_tinha_conta_nao_e_obrigado_a_trocar(self):
        """Conta antiga (ou do `leilao_papel`) nunca teve senha padrão."""
        self.assertFalse(equipe.precisa_trocar_senha(self.chefe))
        self.assertEqual(self.c.get("/equipe/usuarios/").status_code, 200)

    # --- manutenção ---
    def test_trocar_as_funcoes(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        u = get_user_model().objects.get(username="maria")
        self.c.post(
            "/equipe/usuarios/%d/" % u.pk, {"acao": "papeis", "papeis": ["locutor"]}
        )
        self.assertEqual(papeis.papeis_do(u), {"locutor"})

    def test_resetar_a_senha_devolve_o_bilhete(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        u = get_user_model().objects.get(username="maria")
        equipe.definir_senha(u, "minha-senha")
        self.c.post("/equipe/usuarios/%d/" % u.pk, {"acao": "resetar"})
        u.refresh_from_db()
        self.assertTrue(u.check_password(equipe.SENHA_PADRAO))
        self.assertTrue(u.conta_leilao.senha_provisoria)

    def test_desligar_e_religar_a_conta(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        u = get_user_model().objects.get(username="maria")
        self.c.post("/equipe/usuarios/%d/" % u.pk, {"acao": "ativo"})
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.assertFalse(Client().login(username="maria", password=equipe.SENHA_PADRAO))

    def test_ninguem_desliga_a_propria_conta(self):
        self.c.post("/equipe/usuarios/%d/" % self.chefe.pk, {"acao": "ativo"})
        self.chefe.refresh_from_db()
        self.assertTrue(self.chefe.is_active)

    def test_ninguem_tira_o_proprio_diretor(self):
        """Seria perder esta tela — e com ela o caminho de volta."""
        self.c.post(
            "/equipe/usuarios/%d/" % self.chefe.pk,
            {"acao": "papeis", "papeis": ["locutor"]},
        )
        self.assertTrue(papeis.eh_diretor(self.chefe))

    def test_diretor_comum_nao_mexe_em_superusuario(self):
        User = get_user_model()
        dono = User.objects.create_user("dono_ficticio", password="segredo-ficticio")
        dono.is_staff = True
        dono.is_superuser = True
        dono.save()
        self.c.post("/equipe/usuarios/%d/" % dono.pk, {"acao": "resetar"})
        dono.refresh_from_db()
        self.assertFalse(dono.check_password(equipe.SENHA_PADRAO))

    # --- o bilhete ---
    def test_o_recado_traz_usuario_e_senha(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        u = get_user_model().objects.get(username="maria")
        texto = equipe.recado_de_acesso(u, "https://exemplo.com/leilao")
        self.assertIn("maria", texto)
        self.assertIn(equipe.SENHA_PADRAO, texto)
        self.assertIn("https://exemplo.com/leilao/equipe/entrar/", texto)

    def test_a_lista_marca_quem_ainda_esta_com_a_senha_padrao(self):
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        html = self.c.get("/equipe/usuarios/").content.decode("utf-8")
        self.assertIn("senha %s" % equipe.SENHA_PADRAO, html)


class UsuarioSugeridoTests(TestCase):
    """A geração do login, sem tocar no banco (`ocupado` injetado)."""

    def test_primeiro_nome_minusculo_e_sem_acento(self):
        self.assertEqual(
            equipe.usuario_sugerido("José Fictício", ocupado=lambda u: False), "jose"
        )

    def test_repetido_cai_no_sobrenome(self):
        ocupados = {"jose"}
        self.assertEqual(
            equipe.usuario_sugerido("José Fictício", ocupado=lambda u: u in ocupados),
            "jose.ficticio",
        )

    def test_repetido_duas_vezes_ganha_numero(self):
        ocupados = {"jose", "jose.ficticio"}
        self.assertEqual(
            equipe.usuario_sugerido("José Fictício", ocupado=lambda u: u in ocupados),
            "jose.ficticio2",
        )

    def test_nome_so_de_simbolos_nao_gera_login_vazio(self):
        self.assertEqual(equipe.usuario_sugerido("!!!", ocupado=lambda u: False), "equipe")


class BoasVindasTests(TestCase):
    """A tela de quem chega ANTES do primeiro item.

    "Intervalo" é mentira para quem acabou de entrar — não há intervalo nenhum,
    o leilão ainda não começou, e a palavra dá a impressão de que ela perdeu o
    começo.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)

    def test_antes_do_primeiro_item_o_leilao_nao_comecou(self):
        self.assertFalse(est.estado_publico(self.leilao)["comecou"])

    def test_depois_de_abrir_um_item_comecou(self):
        servicos.abrir_lote(self.lote)
        self.assertTrue(est.estado_publico(self.leilao)["comecou"])

    def test_continua_comecado_depois_de_vender(self):
        """O intervalo entre itens não pode voltar a dizer 'bem-vindo'."""
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, criar_pessoa())
        self.lote.refresh_from_db()
        servicos.fechar_lote(self.lote, motivo="locutor")
        self.assertTrue(est.estado_publico(self.leilao)["comecou"])

    def test_o_texto_vai_no_estado_em_linhas(self):
        self.leilao.boas_vindas_titulo = "Bem-vindo ao leilão!"
        self.leilao.boas_vindas_texto = "Primeira linha\n\nSegunda linha  \n"
        self.leilao.save()
        bv = est.estado_publico(self.leilao)["boas_vindas"]
        self.assertEqual(bv["titulo"], "Bem-vindo ao leilão!")
        self.assertEqual(bv["linhas"], ["Primeira linha", "Segunda linha"])

    def test_a_tela_do_participante_traz_o_bloco(self):
        c = Client()
        p = criar_pessoa()
        sessao = c.session
        sessao[CHAVE_SESSAO] = p.token
        sessao.save()
        html = c.get("/").content.decode("utf-8")
        self.assertIn('id="boasVindas"', html)
        self.assertIn('id="bvOnline"', html)


class EditarLeilaoTests(TestCase):
    """Editar o leilão — inclusive com ele no ar (é o caso de uso, não a exceção)."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        criar_lote(self.leilao)
        User = get_user_model()
        u = User.objects.create_user("prep_edit", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        g, _ = Group.objects.get_or_create(name="preparacao")
        u.groups.add(g)
        self.c = Client()
        self.c.login(username="prep_edit", password="segredo-ficticio")

    def test_a_tela_abre(self):
        r = self.c.get("/preparacao/%d/editar/" % self.leilao.pk)
        self.assertEqual(r.status_code, 200)

    def test_salvar_muda_as_boas_vindas_com_o_leilao_no_ar(self):
        r = self.c.post(
            "/preparacao/%d/editar/" % self.leilao.pk,
            {
                "nome": self.leilao.nome,
                "descricao": "",
                "incremento_padrao": "5.00",
                "minutos_para_pagar": "15",
                "chat_segundos": "0",
                "boas_vindas_titulo": "Boa noite!",
                "boas_vindas_texto": "Começamos às 20h",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.leilao.refresh_from_db()
        self.assertEqual(self.leilao.boas_vindas_titulo, "Boa noite!")
        self.assertEqual(self.leilao.status, "ao_vivo")

    def test_quem_e_so_caixa_nao_edita(self):
        User = get_user_model()
        u = User.objects.create_user("cx_edit", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        g, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(g)
        c = Client()
        c.login(username="cx_edit", password="segredo-ficticio")
        r = c.get("/preparacao/%d/editar/" % self.leilao.pk)
        self.assertEqual(r.status_code, 302)


class CaixaAoVivoTests(TestCase):
    """O caixa: WhatsApp, Pix na mão e prazo esticado."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.pessoa = criar_pessoa("Maria Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.pessoa)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote, motivo="locutor")

        User = get_user_model()
        u = User.objects.create_user("cx_vivo", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        g, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(g)
        self.c = Client()
        self.c.login(username="cx_vivo", password="segredo-ficticio")

    # --- WhatsApp ---
    def test_o_link_do_whatsapp_sai_com_o_ddi(self):
        p = criar_pessoa(whatsapp="11988887777")
        self.assertEqual(p.whatsapp_link, "https://wa.me/5511988887777")

    def test_telefone_incompleto_nao_vira_link_quebrado(self):
        p = criar_pessoa(whatsapp="123")
        self.assertEqual(p.whatsapp_link, "")

    def test_a_tela_do_caixa_traz_o_botao_de_whatsapp(self):
        html = self.c.get("/caixa/").content.decode("utf-8")
        self.assertIn("wa.me/", html)

    def test_a_tela_do_caixa_ouve_o_stream(self):
        """Sem isto o caixa só via 'Pago' depois de apertar F5."""
        html = self.c.get("/caixa/").content.decode("utf-8")
        self.assertIn("data-stream=", html)

    # --- Pix na mão do caixa ---
    def test_sem_pix_gerado_a_resposta_explica(self):
        r = self.c.get("/caixa/arremate/%d/pix/" % self.arremate.id)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["ok"])

    def test_com_pix_o_caixa_recebe_codigo_e_mensagem_pronta(self):
        pagamento = PagamentoLeilao.objects.create(
            referencia="LEILAO-TESTE-1", valor_bruto=self.arremate.valor,
            qr_code="00020126ficticio5204000053039865802BR",
        )
        self.arremate.pagamento = pagamento
        self.arremate.save(update_fields=["pagamento"])

        d = self.c.get("/caixa/arremate/%d/pix/" % self.arremate.id).json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["copia_e_cola"], pagamento.qr_code)
        self.assertIn("wa.me/", d["whatsapp"])
        # A mensagem termina NO código: é assim que a pessoa consegue copiá-lo
        # no celular sem pegar texto junto.
        self.assertTrue(d["texto"].rstrip().endswith(pagamento.qr_code))
        self.assertIn(self.lote.nome, d["texto"])

    def test_o_pix_do_caixa_e_so_da_equipe(self):
        self.assertEqual(
            Client().get("/caixa/arremate/%d/pix/" % self.arremate.id).status_code, 302
        )

    def test_locutor_nao_abre_o_pix_do_caixa(self):
        """Quem bate o martelo não cuida do dinheiro — regra do módulo."""
        User = get_user_model()
        u = User.objects.create_user("loc_pix", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        g, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(g)
        c = Client()
        c.login(username="loc_pix", password="segredo-ficticio")
        r = c.get("/caixa/arremate/%d/pix/" % self.arremate.id)
        self.assertEqual(r.status_code, 302)

    # --- Prazo esticado ---
    def test_esticar_o_prazo_soma_a_partir_de_agora(self):
        self.arremate.expira_em = timezone.now() - timedelta(minutes=5)
        self.arremate.save(update_fields=["expira_em"])
        servicos.estender_prazo(self.arremate, 15)
        self.arremate.refresh_from_db()
        # Somar ao prazo VENCIDO daria tempo nenhum: o caso real é a pessoa
        # pedindo mais tempo justamente quando o relógio está no fim.
        self.assertGreater(self.arremate.segundos_para_pagar, 14 * 60)

    def test_o_item_nao_volta_para_a_fila_depois_de_esticar(self):
        self.arremate.expira_em = timezone.now() - timedelta(minutes=1)
        self.arremate.save(update_fields=["expira_em"])
        servicos.estender_prazo(self.arremate, 20)
        servicos.verificar_prazos()
        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "aguardando")
        self.assertEqual(self.lote.status, "vendido")

    def test_esticar_pela_tela_e_do_caixa(self):
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "prazo", "arremate": self.arremate.id, "minutos": 30}),
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.arremate.refresh_from_db()
        self.assertGreater(self.arremate.segundos_para_pagar, 25 * 60)

    def test_quem_ja_pagou_nao_tem_prazo_para_esticar(self):
        servicos.marcar_pago(self.arremate, manual=True)
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "prazo", "arremate": self.arremate.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 409)

    def test_o_locutor_nao_estica_prazo(self):
        User = get_user_model()
        u = User.objects.create_user("loc_prazo", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        g, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(g)
        c = Client()
        c.login(username="loc_prazo", password="segredo-ficticio")
        r = c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "prazo", "arremate": self.arremate.id}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    # --- Combinado ---
    def test_combinado_nao_vence_nunca(self):
        servicos.marcar_combinado(self.arremate, None, "paga amanhã")
        self.arremate.expira_em = timezone.now() - timedelta(hours=5)
        self.arremate.save(update_fields=["expira_em"])
        servicos.verificar_prazos()
        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "combinado")
        self.assertEqual(self.lote.status, "vendido")

    def test_o_pix_do_combinado_dura_dias_nao_minutos(self):
        """15 minutos era o prazo que o caixa acabou de dispensar."""
        self.assertGreaterEqual(servicos.MINUTOS_PIX_COMBINADO, 60 * 24)


class PixRefeitoTests(TestCase):
    """Quando o Pix é refeito, o código ANTIGO continua na tela da pessoa.

    Ela pode pagar aquele. Se o sistema só olhar a cobrança mais nova, o
    dinheiro entra e ninguém é marcado como pago — o caixa segue cobrando quem
    já pagou. Este é o caminho que estes testes seguram.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.pessoa = criar_pessoa("Maria Fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.pessoa)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote, motivo="locutor")

        # A cobrança original (a que está na tela da pessoa)…
        self.velha = PagamentoLeilao.objects.create(
            referencia="LEILAO-%d" % self.arremate.id,
            mp_payment_id="1111", valor_bruto=self.arremate.valor,
            qr_code="00020126velho",
        )
        # …e a refeita, depois de esticar o prazo.
        self.nova = PagamentoLeilao.objects.create(
            referencia="LEILAO-%d-R999" % self.arremate.id,
            mp_payment_id="2222", valor_bruto=self.arremate.valor,
            qr_code="00020126novo",
        )
        self.arremate.pagamento = self.nova
        self.arremate.save(update_fields=["pagamento"])

    def test_pagar_o_codigo_antigo_da_baixa(self):
        servicos._aplicar_retorno(self.velha, {"status": "aprovado"})
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "pago")

    def test_a_baixa_aponta_para_a_cobranca_que_foi_paga(self):
        """É dela que sai a taxa — apontar para a que ninguém pagou mente no extrato."""
        servicos._aplicar_retorno(self.velha, {"status": "aprovado"})
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.pagamento_id, self.velha.id)

    def test_a_lista_de_cobrancas_traz_as_duas(self):
        refs = {p.id for p in servicos.cobrancas_do_arremate(self.arremate)}
        self.assertEqual(refs, {self.velha.id, self.nova.id})

    def test_nao_confunde_o_arremate_12_com_o_1(self):
        """`startswith("LEILAO-1")` pegaria LEILAO-12 junto."""
        outra = PagamentoLeilao.objects.create(
            referencia="LEILAO-%d0" % self.arremate.id,
            mp_payment_id="3333", valor_bruto=Decimal("1.00"),
        )
        refs = {p.id for p in servicos.cobrancas_do_arremate(self.arremate)}
        self.assertNotIn(outra.id, refs)

    def test_referencia_estranha_nao_quebra_o_webhook(self):
        estranho = PagamentoLeilao.objects.create(
            referencia="QUALQUER-COISA", mp_payment_id="4444", valor_bruto=Decimal("1.00")
        )
        self.assertEqual(servicos._arremates_do_pagamento(estranho), [])


class CombinadoIdempotenteTests(TestCase):
    """Dois cliques em "vai pagar depois" não podem gerar dois Pix vivos."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        pessoa = criar_pessoa("João Fictício")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, pessoa)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote, motivo="locutor")

    def test_o_segundo_clique_nao_muda_nada(self):
        servicos.marcar_combinado(self.arremate, None, "paga amanhã")
        self.arremate.refresh_from_db()
        quando = self.arremate.combinado_em

        servicos.marcar_combinado(self.arremate, None, "outra coisa")
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.combinado_em, quando)
        self.assertEqual(self.arremate.observacao, "paga amanhã")

    def test_quem_ja_pagou_nao_vira_combinado(self):
        servicos.marcar_pago(self.arremate, manual=True)
        servicos.marcar_combinado(self.arremate, None, "")
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "pago")


class ContagemDeGenteTests(TestCase):
    """O número que o locutor usa para decidir a hora de começar.

    As telas da equipe também ficam conectadas o tempo todo; contá-las faria
    três voluntários parecerem três pessoas esperando.
    """

    def setUp(self):
        from leilao.hub import HUB

        self.HUB = HUB

    def test_a_equipe_nao_entra_na_contagem(self):
        import asyncio

        async def cenario():
            publico = self.HUB.assinar()
            equipe_fila = self.HUB.assinar(publico=False)
            try:
                return self.HUB.conectados, self.HUB.total
            finally:
                self.HUB.cancelar(publico)
                self.HUB.cancelar(equipe_fila)

        conectados, total = asyncio.run(cenario())
        self.assertEqual(conectados, 1)
        self.assertEqual(total, 2)

    def test_cancelar_tira_das_duas_contas(self):
        import asyncio

        async def cenario():
            fila = self.HUB.assinar()
            self.HUB.cancelar(fila)
            return self.HUB.conectados, self.HUB.total

        self.assertEqual(asyncio.run(cenario()), (0, 0))


class RevisaoDaEquipeTests(TestCase):
    """O que a revisão pegou nas contas da equipe."""

    def setUp(self):
        from leilao import equipe as eq

        eq.limpar_tentativas()
        self.eq = eq
        User = get_user_model()
        self.chefe = User.objects.create_user("dir_rev", password="segredo-ficticio")
        self.chefe.is_staff = True
        self.chefe.save()
        g, _ = Group.objects.get_or_create(name="diretor")
        self.chefe.groups.add(g)
        self.c = Client()
        self.c.login(username="dir_rev", password="segredo-ficticio")

    def test_o_recado_para_de_prometer_a_senha_padrao_depois_da_troca(self):
        novo = self.eq.criar_conta("Maria Fictícia", ["caixa"])
        self.assertIn(self.eq.SENHA_PADRAO, self.eq.recado_de_acesso(novo))

        self.eq.definir_senha(novo, "escolhida")
        texto = self.eq.recado_de_acesso(novo)
        self.assertNotIn("Senha: %s" % self.eq.SENHA_PADRAO, texto)
        self.assertIn(novo.get_username(), texto)

    def test_muitas_tentativas_travam_o_login(self):
        self.eq.criar_conta("Maria Fictícia", ["caixa"])
        c = Client()
        for _ in range(self.eq.MAX_TENTATIVAS):
            c.post("/equipe/entrar/", {"usuario": "maria", "senha": "errada"})
        # Agora nem a senha CERTA passa — é isso que impede varrer 1234 de fora.
        c.post("/equipe/entrar/", {"usuario": "maria", "senha": self.eq.SENHA_PADRAO})
        self.assertNotIn("_auth_user_id", c.session)

    def test_acertar_a_senha_limpa_o_freio(self):
        self.eq.criar_conta("Maria Fictícia", ["caixa"])
        c = Client()
        c.post("/equipe/entrar/", {"usuario": "maria", "senha": "errada"})
        c.post("/equipe/entrar/", {"usuario": "maria", "senha": self.eq.SENHA_PADRAO})
        self.assertIn("_auth_user_id", c.session)

    def test_o_admin_do_leilao_e_so_de_superusuario(self):
        """`is_staff` é o que toda conta da equipe tem — não pode abrir o admin."""
        self.eq.criar_conta("Maria Fictícia", ["caixa"])
        c = Client()
        c.login(username="maria", password=self.eq.SENHA_PADRAO)
        r = c.get("/admin/", follow=True)
        self.assertNotContains(r, "Administração do leilão", status_code=200)
        # O admin manda para a própria tela de login quando não há permissão.
        self.assertTrue(r.redirect_chain)

    def test_tempo_invalido_no_prazo_devolve_json(self):
        """Toda recusa desta view é JSON — um 500 de HTML deixaria a tela muda."""
        leilao = criar_leilao()
        lote = criar_lote(leilao)
        pessoa = criar_pessoa("Ana Fictícia")
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote, motivo="locutor")

        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "prazo", "arremate": arremate.id, "minutos": "abc"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])


class RajadaDeReacoesTests(TestCase):
    """Cada toque solta vários emojis — **sem** requisição a mais.

    O que viaja é a contagem dentro do resumo que já ia de meio em meio
    segundo; o número de mensagens no stream não muda.
    """

    def setUp(self):
        reacoes.limpar()

    def tearDown(self):
        reacoes.limpar()

    def test_um_toque_vale_uma_rajada(self):
        reacoes.registrar("❤️", 1)
        self.assertEqual(reacoes.drenar(), {"❤️": reacoes.EMOJIS_POR_TOQUE})

    def test_a_rajada_multiplica_o_numero_de_toques(self):
        reacoes.registrar("👏", 3)
        self.assertEqual(reacoes.drenar(), {"👏": 3 * reacoes.EMOJIS_POR_TOQUE})

    def test_o_teto_do_despejo_continua_valendo(self):
        """Com rajada o teto é alcançado mais rápido — e é ele que segura a tela."""
        for _ in range(50):
            reacoes.registrar("🔥", 10)
        self.assertEqual(reacoes.drenar(), {"🔥": reacoes.TETO_POR_DESPEJO})

    def test_a_multiplicacao_e_do_servidor(self):
        """Toque forjado com `quantos` alto não pode encher a tela de todo mundo.

        O limite por chamada continua sendo o de TOQUES (10); a rajada é
        aplicada depois, e o despejo tem teto.
        """
        reacoes.registrar("🎉", 9999)
        self.assertLessEqual(reacoes.drenar()["🎉"], reacoes.TETO_POR_DESPEJO)

    def test_a_tela_recebe_o_numero_da_rajada(self):
        """O cliente precisa do mesmo número para não desenhar em dobro o que mandou."""
        c = Client()
        p = criar_pessoa()
        sessao = c.session
        sessao[CHAVE_SESSAO] = p.token
        sessao.save()
        html = c.get("/").content.decode("utf-8")
        self.assertIn('data-rajada="%d"' % reacoes.EMOJIS_POR_TOQUE, html)

    def test_reagir_pela_view_tambem_multiplica(self):
        c = Client()
        p = criar_pessoa()
        sessao = c.session
        sessao[CHAVE_SESSAO] = p.token
        sessao.save()
        r = c.post(
            "/reagir/",
            data=json.dumps({"emoji": "❤️", "quantos": 2}),
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.assertEqual(reacoes.drenar(), {"❤️": 2 * reacoes.EMOJIS_POR_TOQUE})


class TetoDoResumoTests(TestCase):
    """O resumo tem teto no TODO, não em cada emoji.

    Por emoji parecia igual e não era: são seis emojis, e um resumo podia pedir
    240 desenhos a um celular que mostra 30.
    """

    def setUp(self):
        reacoes.limpar()

    def tearDown(self):
        reacoes.limpar()

    def test_o_resumo_inteiro_respeita_o_teto(self):
        for emoji in reacoes.EMOJIS:
            for _ in range(50):
                reacoes.registrar(emoji, 10)
        resumo = reacoes.drenar()
        self.assertLessEqual(sum(resumo.values()), reacoes.TETO_POR_DESPEJO + len(reacoes.EMOJIS))

    def test_todo_emoji_tocado_aparece_pelo_menos_uma_vez(self):
        """A tela precisa mostrar que a sala mandou coisas diferentes."""
        reacoes.registrar("❤️", 10)
        for _ in range(200):
            reacoes.registrar("🔥", 10)
        resumo = reacoes.drenar()
        self.assertGreaterEqual(resumo.get("❤️", 0), 1)
        self.assertGreater(resumo["🔥"], resumo["❤️"])

    def test_abaixo_do_teto_nada_e_cortado(self):
        reacoes.registrar("👏", 1)
        self.assertEqual(reacoes.drenar(), {"👏": reacoes.EMOJIS_POR_TOQUE})


class EmojiNaoAtrapalhaOPregaoTests(TestCase):
    """A ordem de importância do dia, em teste: **voz e lance são o leilão;
    emoji é enfeite** — e enfeite é a primeira coisa que se descarta quando o
    processo aperta.
    """

    def setUp(self):
        servicos.limpar_limites()
        reacoes.limpar()
        self.leilao = criar_leilao()
        self.c = Client()
        self.c.post("/entrar/", {
            "nome": "Fulano de Teste", "whatsapp": "(11) 90000-0099",
            "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "cidade": "Cidade Exemplo", "estado": "SP",
        })

    def tearDown(self):
        reacoes.limpar()

    def test_uma_pessoa_sozinha_nao_passa_de_duas_por_segundo(self):
        """O `reacoes.js` já se segura, mas o servidor não acredita no cliente."""
        aceitas = sum(1 for _ in range(20) if reacoes.aceitar(1))
        self.assertEqual(aceitas, 1)

    def test_pessoas_diferentes_nao_atrapalham_uma_a_outra(self):
        self.assertTrue(reacoes.aceitar(1))
        self.assertTrue(reacoes.aceitar(2))
        self.assertTrue(reacoes.aceitar(3))

    def test_a_sala_inteira_martelando_tem_teto_no_processo(self):
        """Passou do teto do segundo, o resto é descartado — o lance vem antes."""
        aceitas = sum(1 for i in range(reacoes.TETO_POR_SEGUNDO * 3) if reacoes.aceitar(i))
        self.assertLessEqual(aceitas, reacoes.TETO_POR_SEGUNDO)

    def test_a_reacao_descartada_nao_vira_erro_na_tela(self):
        """Quem tocou já viu o emoji subir; um erro só faria o celular insistir."""
        corpo = json.dumps({"emoji": "❤️"})
        primeira = self.c.post("/reagir/", data=corpo, content_type="application/json")
        segunda = self.c.post("/reagir/", data=corpo, content_type="application/json")
        self.assertEqual(primeira.status_code, 200)
        self.assertEqual(segunda.status_code, 200)
        self.assertTrue(segunda.json()["ok"])
        self.assertTrue(segunda.json().get("freio"))

    def test_o_freio_do_emoji_nao_encosta_no_lance(self):
        """O lance tem o freio DELE (`INTERVALO_MIN_LANCE`) e não divide contador."""
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()

        for i in range(reacoes.TETO_POR_SEGUNDO * 2):
            reacoes.aceitar(i)

        pessoa = criar_pessoa("Maria Fictícia")
        ok, msg, _ = servicos.dar_lance(lote.id, pessoa)
        self.assertTrue(ok, msg)


class PesoEDimensoesTests(TestCase):
    """Peso e dimensões do item — obrigatórios, e presentes em toda tela.

    Existem por causa da **entrega**: o voluntário escolhe o carro antes de
    sair de casa, e descobrir na porta que o item não cabe custa a viagem
    inteira. De quebra, quem dá lance passa a saber o tamanho do que compra.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("prep_medidas", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="preparacao")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="prep_medidas", password="segredo-ficticio")

    def _post(self, **extra):
        dados = {
            "nome": "Item fictício", "descricao": "", "lance_inicial": "30.00",
            "peso_kg": "1,5", "altura_cm": "20",
            "largura_cm": "30", "profundidade_cm": "25",
        }
        dados.update(extra)
        return self.c.post("/preparacao/%d/itens/novo/" % self.leilao.pk, dados)

    # ---------- obrigatoriedade ----------

    def test_cadastro_completo_salva(self):
        self.assertEqual(self._post().status_code, 302)
        lote = self.leilao.lotes.get(nome="Item fictício")
        self.assertEqual(lote.peso_kg, Decimal("1.5"))
        self.assertEqual((lote.altura_cm, lote.largura_cm, lote.profundidade_cm),
                         (20, 30, 25))

    def test_nao_salva_sem_peso(self):
        r = self._post(peso_kg="")
        self.assertEqual(r.status_code, 200)   # volta com erro, não redireciona
        self.assertFalse(self.leilao.lotes.exists())

    def test_nao_salva_sem_cada_uma_das_dimensoes(self):
        for lado in ["altura_cm", "largura_cm", "profundidade_cm"]:
            with self.subTest(lado=lado):
                r = self._post(**{lado: "", "nome": "Item " + lado})
                self.assertEqual(r.status_code, 200)
                self.assertFalse(self.leilao.lotes.filter(nome="Item " + lado).exists())

    def test_peso_zero_nao_passa(self):
        """"Obrigatório" que aceita zero não obriga nada — 0 kg é campo vazio
        disfarçado, e chega na entrega valendo o mesmo que em branco."""
        self.assertEqual(self._post(peso_kg="0").status_code, 200)
        self.assertFalse(self.leilao.lotes.exists())

    def test_dimensao_zero_nao_passa(self):
        self.assertEqual(self._post(altura_cm="0").status_code, 200)
        self.assertFalse(self.leilao.lotes.exists())

    def test_dedo_escorregado_no_teclado_nao_passa(self):
        """`999999999999 cm` na tela do pregão quebra o layout para as 100
        pessoas que estão olhando. O teto (1.000 kg / 1.000 cm = 10 m) não é
        regra de negócio: é o freio do dígito a mais."""
        self.assertEqual(self._post(altura_cm="999999999999").status_code, 200)
        self.assertEqual(self._post(peso_kg="99999999").status_code, 200)
        self.assertFalse(self.leilao.lotes.exists())

    def test_negativo_avisa_o_minimo_certo(self):
        """O `PositiveIntegerField` entrega o campo com `min_value=0` e era
        esse validador que respondia primeiro: a pessoa lia "maior ou igual a
        0" quando o mínimo de verdade é 1."""
        r = self._post(altura_cm="-5")
        self.assertEqual(r.status_code, 200)
        self.assertIn("1", str(r.context["form"].errors["altura_cm"]))
        self.assertNotIn("igual a 0", str(r.context["form"].errors["altura_cm"]))

    def test_entrada_estranha_nao_estoura_a_tela(self):
        """Nenhum caminho de entrada pode virar 500 — a recusa é uma mensagem
        no formulário."""
        for campo, valor in [
            ("peso_kg", "abc"), ("peso_kg", "1,23456"), ("peso_kg", "-2"),
            ("altura_cm", "abc"), ("altura_cm", "1,5"), ("largura_cm", "-1"),
        ]:
            with self.subTest(campo=campo, valor=valor):
                r = self._post(**{campo: valor})
                self.assertEqual(r.status_code, 200)
        self.assertFalse(self.leilao.lotes.exists())

    # ---------- o peso aceita os dois separadores ----------

    def test_peso_aceita_virgula_e_ponto(self):
        """A vírgula é a do teclado português; o ponto é o que muitos teclados
        numéricos de celular oferecem. Recusar um dos dois faz a pessoa brigar
        com o teclado no meio do cadastro."""
        for digitado, esperado in [("1,5", "1.5"), ("1.5", "1.5"), ("12", "12")]:
            with self.subTest(digitado=digitado):
                self.assertEqual(
                    forms.peso_para_decimal(digitado), Decimal(esperado)
                )

    def test_peso_com_ponto_nao_e_lido_como_milhar(self):
        """A armadilha que fez este campo NÃO usar `localize=True`: em pt-BR o
        Django lê "1.5" como separador de milhar e devolve 15 — um item de
        1,5 kg viraria um de 15 kg sem avisar ninguém."""
        self.assertEqual(forms.peso_para_decimal("1.5"), Decimal("1.5"))

    def test_peso_invalido_nao_estoura(self):
        self.assertIsNone(forms.peso_para_decimal("abc"))
        self.assertIsNone(forms.peso_para_decimal(""))
        self.assertIsNone(forms.peso_para_decimal(None))

    def test_nan_e_infinito_nao_derrubam_a_tela(self):
        """Bug encontrado conferindo os caminhos de entrada: `Decimal("nan")`
        **não** levanta na conversão — levanta na primeira comparação de ordem
        (`peso <= 0`), e aí já era **500 na tela de cadastro**. `"inf"` converte
        e compara, mas não é peso de coisa nenhuma."""
        for texto in ["nan", "NaN", "-nan", "snan", "inf", "-inf", "Infinity"]:
            with self.subTest(texto=texto):
                self.assertIsNone(forms.peso_para_decimal(texto))

    def test_nan_no_formulario_e_recusa_educada_e_nao_500(self):
        r = self._post(peso_kg="nan")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.leilao.lotes.exists())

    # ---------- o texto, decidido num lugar só ----------

    def test_texto_das_medidas(self):
        lote = criar_lote(self.leilao, peso_kg=Decimal("1.50"),
                          altura_cm=40, largura_cm=30, profundidade_cm=25)
        self.assertEqual(lote.peso_texto, "1,5 kg")
        self.assertEqual(lote.dimensoes, "40 × 30 × 25 cm")
        self.assertEqual(lote.medidas_texto, "1,5 kg · 40 × 30 × 25 cm")

    def test_peso_redondo_nao_perde_o_zero_da_dezena(self):
        """`10,00` não pode virar `1`: o corte dos zeros à direita para no
        ponto decimal."""
        for guardado, esperado in [("10.00", "10 kg"), ("100.00", "100 kg"),
                                   ("0.50", "0,5 kg"), ("15.25", "15,25 kg")]:
            with self.subTest(guardado=guardado):
                lote = Lote(peso_kg=Decimal(guardado))
                self.assertEqual(lote.peso_texto, esperado)

    def test_item_antigo_sem_medida_nao_inventa_texto(self):
        """Item cadastrado antes destes campos existirem. A tela diz "—"; o
        sistema não chuta uma medida para quem vai dirigir até lá."""
        antigo = criar_lote(self.leilao, peso_kg=None, altura_cm=None,
                            largura_cm=None, profundidade_cm=None)
        self.assertEqual(antigo.medidas_texto, "")

    def test_meia_dimensao_nao_vira_texto_quebrado(self):
        """"40 × ? × 25" parece defeito do sistema, não item incompleto."""
        meio = criar_lote(self.leilao, altura_cm=40, largura_cm=None,
                          profundidade_cm=25)
        self.assertEqual(meio.dimensoes, "")

    # ---------- onde aparece ----------

    def test_vai_no_broadcast_do_pregao(self):
        """Medida pode ser dita em voz alta: é o tamanho do que está à venda,
        não dado de ninguém."""
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        dados = est.estado_publico(self.leilao)
        self.assertEqual(dados["lote"]["medidas"], lote.medidas_texto)
        self.assertTrue(dados["lote"]["medidas"])

    def test_a_mesa_do_locutor_recebe_pelo_mesmo_caminho(self):
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        self.assertEqual(
            est.lote_publico(Lote.objects.get(pk=lote.pk))["medidas"],
            lote.medidas_texto,
        )

    def test_aparece_na_lista_da_preparacao(self):
        criar_lote(self.leilao)
        r = self.c.get("/preparacao/%d/itens/" % self.leilao.pk)
        self.assertContains(r, "2,5 kg · 20 × 35 × 25 cm")

    def test_a_lista_avisa_quando_o_item_antigo_esta_sem_medida(self):
        """A linha não some: é nela que se descobre o que falta completar
        antes da noite da entrega."""
        criar_lote(self.leilao, peso_kg=None, altura_cm=None,
                   largura_cm=None, profundidade_cm=None)
        r = self.c.get("/preparacao/%d/itens/" % self.leilao.pk)
        self.assertContains(r, "sem peso/medidas")

    def test_editar_devolve_o_peso_com_virgula_no_campo(self):
        """O campo volta com o texto que a pessoa digitou, não com o `Decimal`
        cru do banco (`1.50`)."""
        lote = criar_lote(self.leilao, peso_kg=Decimal("1.50"))
        r = self.c.get("/preparacao/itens/%d/editar/" % lote.pk)
        self.assertEqual(r.context["form"].initial["peso_kg"], "1,5")

    def test_aparece_na_tela_do_caixa(self):
        """O caixa combina a entrega no WhatsApp a partir dessa lista, e
        "cabe no seu carro?" é a primeira pergunta da conversa."""
        User = get_user_model()
        cx = User.objects.create_user("cx_medidas", password="segredo-ficticio")
        cx.is_staff = True
        cx.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        cx.groups.add(grupo)
        cliente = Client()
        cliente.login(username="cx_medidas", password="segredo-ficticio")

        pessoa = criar_pessoa("Carla Fictícia")
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        servicos.fechar_lote(lote, motivo="locutor")

        r = cliente.get("/caixa/")
        self.assertContains(r, lote.medidas_texto)

    def test_vai_no_roteiro_de_entrega(self):
        """É o que diz se a parada cabe no carro — e o roteiro é lido longe do
        sistema, na rua, pelo voluntário."""
        pessoa = criar_pessoa("Ana Fictícia", bairro="Centro",
                              logradouro="Rua Exemplo", numero="10")
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote, motivo="locutor")
        servicos.marcar_pago(arremate, manual=True)
        arremate.refresh_from_db()

        rotas = entregas.dividir([arremate], 1)
        texto = entregas.texto_da_rota(self.leilao, 1, rotas[0], 1)
        self.assertIn(lote.medidas_texto, texto)

    def test_o_roteiro_do_item_antigo_nao_ganha_linha_vazia(self):
        pessoa = criar_pessoa("Bruno Fictício", bairro="Centro",
                              logradouro="Rua Exemplo", numero="10")
        lote = criar_lote(self.leilao, peso_kg=None, altura_cm=None,
                          largura_cm=None, profundidade_cm=None)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote, motivo="locutor")
        servicos.marcar_pago(arremate, manual=True)
        arremate.refresh_from_db()

        texto = entregas.texto_da_rota(
            self.leilao, 1, entregas.dividir([arremate], 1)[0], 1
        )
        self.assertNotIn("📦", texto)
