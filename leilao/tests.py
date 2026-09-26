"""Testes do módulo de leilão.

    DJANGO_SETTINGS_MODULE=config.settings_leilao python manage.py test leilao

O foco é o que **quebra ao vivo, na frente de 50 pessoas**: corrida de lances,
cronômetro, prazo de pagamento, vazamento de dado privado no broadcast e as
armadilhas de template que este projeto já pagou caro.
"""

import itertools
import os
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
from . import views
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
        # Sem prazo: o pagamento é no fim, tudo de uma vez.
        self.assertIsNone(arremate.expira_em)

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

    def test_o_arremate_nasce_SEM_prazo(self):
        """Não há relógio: quem arremata paga no fim, tudo de uma vez."""
        self.assertIsNone(self.arremate.expira_em)
        self.assertEqual(self.arremate.status, "aguardando")

    def test_o_tempo_nao_devolve_o_item_a_fila(self):
        """O item fica com quem arrematou; quem não paga é cobrado pelo caixa.

        Antes, 15 minutos sem pagar devolviam o lote à fila — e isso punia
        quem estava sem o celular na mão no fim do leilão.
        """
        servicos.verificar_prazos()
        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "aguardando")
        self.assertEqual(self.lote.status, "vendido")
        self.assertEqual(self.lote.voltas, 0)

    def test_nao_existe_mais_expirar_arremate(self):
        """Guarda: a devolução automática não volta por descuido."""
        self.assertFalse(hasattr(servicos, "expirar_arremate"))
        self.assertFalse(hasattr(servicos, "estender_prazo"))

    def test_arremate_pago_continua_pago(self):
        servicos.marcar_pago(self.arremate, manual=True)
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
    """O chat fica aberto o leilão inteiro — sem intervalo e sem contagem.

    Antes ele abria por `chat_segundos` a cada intervalo e fechava quando um
    item ia a pregão. O clube pediu conversa aberta direto. Sobrou UMA
    condição: leilão no ar.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia")

    def test_com_o_leilao_no_ar_o_chat_esta_aberto(self):
        """Sem abrir nada: estar no ar já basta."""
        self.assertTrue(self.leilao.chat_aberto)
        self.assertIsNotNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_com_item_em_pregao_o_chat_continua_aberto(self):
        """Abrir item NÃO fecha mais o chat."""
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        self.leilao.refresh_from_db()
        self.assertTrue(self.leilao.chat_aberto)
        self.assertIsNotNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_leilao_fora_do_ar_nao_tem_chat(self):
        Leilao.objects.filter(pk=self.leilao.pk).update(status="encerrado")
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.chat_aberto)
        self.assertIsNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_locutor_fala_mesmo_fora_do_ar(self):
        """Aviso do locutor não depende do chat."""
        Leilao.objects.filter(pk=self.leilao.pk).update(status="rascunho")
        self.leilao.refresh_from_db()
        m = servicos.enviar_mensagem(self.leilao, None, "Começamos em 5 minutos!")
        self.assertIsNotNone(m)
        self.assertEqual(m.autor, "Locutor")

    def test_bloqueado_nao_fala(self):
        self.ana.bloqueado = True
        self.ana.save()
        self.assertIsNone(servicos.enviar_mensagem(self.leilao, self.ana, "oi"))

    def test_nao_existe_mais_abrir_nem_fechar_chat(self):
        """Guarda: o chat por tempo não volta por descuido."""
        self.assertFalse(hasattr(servicos, "abrir_chat"))
        self.assertFalse(hasattr(servicos, "fechar_chat"))

    def test_o_estado_nao_manda_mais_prazo_de_chat(self):
        dados = est.estado_publico(self.leilao)
        self.assertTrue(dados["chat"]["aberto"])
        self.assertNotIn("ate", dados["chat"])


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

    def test_o_incremento_e_FIXO_em_cinco_reais(self):
        """R$ 5 e ponto: nem o item nem o leilão mudam isso.

        Configurar o incremento existia (por leilão e por item) e saiu a pedido
        do clube: no pregão ao vivo o locutor anuncia "de cinco em cinco" uma
        vez, e incremento variável só criava a chance de um item sair com regra
        diferente da que foi falada em voz alta. As duas colunas ficaram
        dormentes — este teste garante que elas não voltem a ser lidas.
        """
        leilao = criar_leilao(incremento_padrao=Decimal("7.00"))
        lote = criar_lote(leilao, incremento=Decimal("50.00"))
        self.assertEqual(lote.incremento_efetivo, Decimal("5.00"))

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
        servicos.fechar_lote(self.lote)
        # A cobrança é da PESSOA da sessão, pelo total — não existe "o Pix do
        # arremate alheio" para pedir. Quem não arrematou nada não tem conta a
        # pagar, e o servidor recusa antes de olhar id nenhum.
        r = self.c.get("/conta/pix/")
        self.assertFalse(r.json()["ok"])
        self.assertNotIn("copia_e_cola", r.json())

    def test_stream_responde_event_stream(self):
        self._entrar()      # desde 24/09 o stream do público exige a porta
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
        """Com `follow`, porque a URL sem id agora REDIRECIONA para a com id.

        Sem seguir, `302` deixou de distinguir as duas coisas que este teste
        precisa separar: "não tem acesso" e "vá para a URL do leilão". O que
        importa é onde a pessoa **termina** — na tela, ou fora dela.
        """
        casos = {
            "preparacao": ("/preparacao/", ["/locutor/", "/caixa/"]),
            "locutor": ("/locutor/", ["/preparacao/", "/caixa/"]),
            "caixa": ("/caixa/", ["/preparacao/", "/locutor/"]),
        }
        for papel, (minha, alheias) in casos.items():
            self._pessoa("user_" + papel, papel)
            c = Client()
            c.login(username="user_" + papel, password="segredo-ficticio")
            r = c.get(minha, follow=True)
            self.assertEqual(r.status_code, 200, papel + " nao abriu " + minha)
            self.assertTrue(
                r.request["PATH_INFO"].startswith(minha),
                papel + " nao terminou em " + minha,
            )
            for outra in alheias:
                r = c.get(outra, follow=True)
                self.assertFalse(
                    r.request["PATH_INFO"].startswith(outra),
                    papel + " abriu " + outra,
                )

    def test_diretor_abre_as_tres(self):
        self._pessoa("chefe", "diretor")
        self.c.login(username="chefe", password="segredo-ficticio")
        for url in ["/preparacao/", "/locutor/", "/caixa/"]:
            self.assertEqual(self.c.get(url, follow=True).status_code, 200, url)

    def test_papeis_acumulam(self):
        """No evento pequeno, o mesmo voluntário faz duas coisas."""
        self._pessoa("dupla", "locutor", "caixa")
        self.c.login(username="dupla", password="segredo-ficticio")
        self.assertEqual(self.c.get("/locutor/", follow=True).status_code, 200)
        self.assertEqual(self.c.get("/caixa/", follow=True).status_code, 200)
        self.assertEqual(self.c.get("/preparacao/").status_code, 302)

    def test_quem_tem_uma_area_so_vai_direto_para_ela(self):
        self._pessoa("soLocutor", "locutor")
        self.c.login(username="soLocutor", password="segredo-ficticio")
        # O destino continua sendo `/locutor/`; de lá ele redireciona de novo
        # para `/locutor/<id>/` — daí o `target_status_code=302`.
        self.assertRedirects(
            self.c.get("/equipe/"), "/locutor/", target_status_code=302
        )

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
                "peso_kg": "1500", "altura_cm": "20",   # o campo é em GRAMAS
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
        r = self.c.get("/caixa/", follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["a_entregar"]), 1)
        # O roteiro leva endereço: é documento de quem entrega.
        self.assertIn("Rua Fictícia", r.context["roteiro"])
        self.assertIn("Ana Fictícia", r.context["roteiro"])

    def test_roteiro_vazio_quando_nao_ha_entrega(self):
        r = self.c.get("/caixa/", follow=True)
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
        servicos.fechar_lote(self.lote)
        # A venda é desfeita e o item volta a pregão. Não há mais relógio que
        # faça isso sozinho — o que importa aqui é a RODADA, não o motivo.
        Lote.objects.filter(pk=self.lote.pk).update(
            status="fila", valor_atual=Decimal("0.00"), lider=None,
            voltas=1, fechado_em=None,
        )
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
        """Sem credencial não nasce Pix: a tela diz isso em vez de "gerando…"."""
        servicos.liberar_pagamentos(self.leilao)
        r = self.c.get("/conta/pix/")
        corpo = r.json()
        self.assertFalse(corpo["ok"])
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
                # `follow`: as telas de equipe sem id na URL redirecionam para a
                # URL COM id. O que este teste quer saber é se a tela abre.
                self.assertEqual(self.c.get(url, follow=True).status_code, 200, url)

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


class ChatEUmFioSoTests(TestCase):
    """O chat é UM fio a noite inteira — não zera mais a cada intervalo.

    Enquanto o chat era "do intervalo", cada abertura começava uma conversa
    limpa (`chat_aberto_em`) para o participante não receber o fio inteiro de
    volta. Sem intervalo, esse corte perdeu o sentido: o que limita a tela é o
    teto das 40 últimas, que sempre existiu.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia")

    def test_as_mensagens_nao_somem_quando_um_item_abre(self):
        servicos.enviar_mensagem(self.leilao, self.ana, "antes do item")
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        self.leilao.refresh_from_db()
        textos = [m["texto"] for m in est.estado_publico(self.leilao)["chat"]["mensagens"]]
        self.assertIn("antes do item", textos)

    def test_o_fio_segue_depois_do_item_fechar(self):
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        servicos.enviar_mensagem(self.leilao, self.ana, "durante o item")
        servicos.fechar_lote(lote, motivo="locutor")
        self.leilao.refresh_from_db()
        textos = [m["texto"] for m in est.estado_publico(self.leilao)["chat"]["mensagens"]]
        self.assertIn("durante o item", textos)

    def test_o_locutor_continua_vendo_tudo(self):
        servicos.enviar_mensagem(self.leilao, self.ana, "primeira")
        servicos.enviar_mensagem(self.leilao, self.ana, "segunda")

        User = get_user_model()
        u = User.objects.create_user("loc_chat", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="loc_chat", password="segredo-ficticio")

        textos = [m["texto"] for m in c.get("/locutor/dados/").json()["chat"]]
        self.assertIn("primeira", textos)
        self.assertIn("segunda", textos)


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

        html = c.get("/locutor/", follow=True).content.decode("utf-8")
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
        r = self.c.get("/caixa/", follow=True)
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


class FuncaoQueOJsCHAMAExisteTests(TestCase):
    """Chamar função que não existe mata o arquivo de JS INTEIRO.

    É `ReferenceError`: o script morre naquela linha e **nada depois é
    executado** — a tela abre bonita, o item novo não aparece, o lance não
    desenha, e a sensação para quem está no evento é de "o sistema está com
    atraso". Foi exatamente o que aconteceu ao tirar a contagem de tempo do
    chat: a função saiu e **uma chamada ficou para trás**.

    O `BotoesQueOJsProcuraExistemTests` não pega isto — ele cuida do outro lado
    (id que o JS procura e o template não tem). Este aqui varre o caminho
    inverso: nome chamado como função que não está declarado em lugar nenhum
    do arquivo.

    É uma varredura de texto, não um interpretador: comentários e strings saem
    antes, e o que é global do navegador está na lista. Não pega tudo — pega a
    classe de erro que já derrubou a tela duas vezes, que é a que importa.
    """

    GLOBAIS = set("""
        fetch setTimeout setInterval clearTimeout clearInterval parseInt parseFloat isNaN
        Number String Boolean Array Object JSON Math Date Promise Error RegExp Map Set
        WeakMap Symbol encodeURIComponent decodeURIComponent alert confirm require define
        console escape unescape structuredClone queueMicrotask requestAnimationFrame
        cancelAnimationFrame getComputedStyle matchMedia atob btoa Intl AudioContext
        webkitAudioContext RTCPeerConnection EventSource URL Blob File FileReader FormData
        Headers Request Response AbortController DataTransfer Image Audio Notification
        IntersectionObserver MutationObserver ResizeObserver CustomEvent Event
        KeyboardEvent MouseEvent TouchEvent Uint8Array Uint8ClampedArray Float32Array
        Int16Array ArrayBuffer createImageBitmap
        if for while switch catch return typeof instanceof new delete void do else try
        finally function window document
    """.split())

    def test_toda_funcao_chamada_esta_declarada(self):
        import re

        pasta = Path(settings.BASE_DIR, "static", "leilao", "js")
        problemas = []
        for arquivo in sorted(pasta.glob("*.js")):
            txt = arquivo.read_text(encoding="utf-8")
            # Comentário e string saem ANTES: um comentário que cite uma função
            # removida não é uma chamada, e já houve falso positivo assim.
            limpo = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
            limpo = re.sub(r"//[^\n]*", " ", limpo)
            limpo = re.sub(r'"[^"\n]*"', '""', limpo)
            limpo = re.sub(r"'[^'\n]*'", "''", limpo)

            declarados = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)", limpo))
            declarados |= set(re.findall(r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)", limpo))
            declarados |= set(re.findall(r"([A-Za-z_$][\w$]*)\s*:\s*function", limpo))
            for params in re.findall(r"function[^(]*\(([^)]*)\)", limpo):
                for nome in params.split(","):
                    nome = nome.strip()
                    if nome:
                        declarados.add(nome)

            # `algo(` só conta quando NÃO vem depois de ponto: `obj.metodo()` é
            # método de outro objeto, não função deste arquivo.
            chamados = set(
                m.group(1)
                for m in re.finditer(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(", limpo)
            )
            faltam = sorted(chamados - declarados - self.GLOBAIS)
            if faltam:
                problemas.append(f"{arquivo.name} chama {', '.join(faltam)}, que não existe lá")

        self.assertEqual(problemas, [], "; ".join(problemas))


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

    Este era um bug de **duas fontes de verdade**: `chat_aberto_ate` era uma
    hora futura no banco que não sabia que o leilão tinha acabado, e a tela
    mostrava a caixa de conversa enquanto o servidor recusava cada mensagem —
    a pessoa digitando contra uma porta fechada.

    Com o chat sem contagem, `Leilao.chat_aberto` virou **uma expressão só**
    (`status == "ao_vivo"`), a mesma que o servidor usa para aceitar. A
    divergência deixou de ser possível por construção — mas a garantia continua
    valendo a pena testar, porque é dela que a tela depende.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia")

    def test_com_o_leilao_no_ar_o_chat_esta_aberto(self):
        self.assertTrue(self.leilao.chat_aberto)

    def test_encerrar_o_leilao_fecha_o_chat(self):
        servicos.mudar_status(self.leilao, "encerrado")
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.chat_aberto)

    def test_rascunho_tambem_nao_tem_chat(self):
        Leilao.objects.filter(pk=self.leilao.pk).update(status="rascunho")
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.chat_aberto)

    def test_sair_do_ar_avisa_as_telas(self):
        """Quem está com a caixa aberta precisa vê-la sumir, não descobrir no envio.

        O aviso agora é o próprio `estado` (que leva `chat.aberto`), e não um
        evento `chat_estado` à parte — que deixou de existir junto com o prazo.
        """
        publicados = []
        original = servicos.HUB.publicar
        servicos.HUB.publicar = lambda tipo, dados=None: publicados.append(tipo)
        try:
            servicos.mudar_status(self.leilao, "encerrado")
        finally:
            servicos.HUB.publicar = original
        self.assertIn("estado", publicados)

    def test_colocar_outro_no_ar_fecha_o_chat_do_anterior(self):
        outro = criar_leilao(nome="Outro leilão", status="rascunho")
        servicos.mudar_status(outro, "ao_vivo")
        self.leilao.refresh_from_db()
        self.assertEqual(self.leilao.status, "encerrado")
        self.assertFalse(self.leilao.chat_aberto)

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


class PagamentoNoFimTests(TestCase):
    """Ninguém sai do leilão para pagar: a conta fecha no fim.

    Era um Pix por item, com 15 minutos correndo — e o prazo fazia exatamente o
    que existia para evitar: tirava do pregão quem estava disputando, e ainda
    devolvia o item à fila de quem estava sem o celular na mão. Agora os itens
    se acumulam, o locutor abre a bilheteria no fim e a pessoa paga **tudo num
    código só**.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia")
        self.bruno = criar_pessoa("Bruno Fictício")

    def _arrematar(self, nome, quem, valor_inicial=Decimal("40.00")):
        lote = criar_lote(self.leilao, nome=nome, lance_inicial=valor_inicial)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.limpar_limites()
        servicos.dar_lance(lote.id, quem)
        lote.refresh_from_db()
        return servicos.fechar_lote(lote, motivo="locutor")

    # --- a conta ---
    def test_os_itens_se_acumulam_na_conta_da_pessoa(self):
        self._arrematar("Item um", self.ana, Decimal("40.00"))
        self._arrematar("Item dois", self.ana, Decimal("60.00"))
        self.assertEqual(servicos.arremates_em_aberto(self.ana).count(), 2)
        self.assertEqual(servicos.total_em_aberto(self.ana), Decimal("100.00"))

    def test_a_conta_de_cada_um_e_a_sua(self):
        self._arrematar("Item da Ana", self.ana, Decimal("40.00"))
        self._arrematar("Item do Bruno", self.bruno, Decimal("70.00"))
        self.assertEqual(servicos.total_em_aberto(self.ana), Decimal("40.00"))
        self.assertEqual(servicos.total_em_aberto(self.bruno), Decimal("70.00"))

    def test_o_que_foi_pago_sai_do_total(self):
        a1 = self._arrematar("Item um", self.ana, Decimal("40.00"))
        self._arrematar("Item dois", self.ana, Decimal("60.00"))
        servicos.marcar_pago(a1, manual=True)
        self.assertEqual(servicos.total_em_aberto(self.ana), Decimal("60.00"))

    # --- a bilheteria ---
    def test_o_leilao_comeca_com_o_pagamento_FECHADO(self):
        self.assertFalse(self.leilao.pagamentos_liberados)

    def test_liberar_e_uma_alavanca(self):
        servicos.liberar_pagamentos(self.leilao)
        self.leilao.refresh_from_db()
        self.assertTrue(self.leilao.pagamentos_liberados)
        servicos.liberar_pagamentos(self.leilao, False)
        self.leilao.refresh_from_db()
        self.assertFalse(self.leilao.pagamentos_liberados)

    def test_a_liberacao_vai_no_broadcast(self):
        """O botão de pagar aparece na tela de todo mundo sem recarregar."""
        dados = est.estado_publico(self.leilao)
        self.assertFalse(dados["leilao"]["pagamentos_liberados"])
        servicos.liberar_pagamentos(self.leilao)
        self.leilao.refresh_from_db()
        dados = est.estado_publico(self.leilao)
        self.assertTrue(dados["leilao"]["pagamentos_liberados"])

    def test_liberar_e_do_LOCUTOR(self):
        self.assertEqual(views.ACOES_AREAS["liberar"], ("locutor",))

    def test_o_caixa_nao_libera_pagamentos(self):
        """Quem confere o dinheiro não decide quando o pregão acabou."""
        User = get_user_model()
        u = User.objects.create_user("cx_lib", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        g, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(g)
        c = Client()
        c.login(username="cx_lib", password="segredo-ficticio")
        r = c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "liberar"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    # --- a trava do servidor ---
    def test_antes_de_liberar_o_SERVIDOR_recusa_o_pix(self):
        """Esconder o botão não impede POST forjado — a trava é do servidor."""
        self._arrematar("Item um", self.ana)
        c = Client()
        c.post("/entrar/", {
            "nome": self.ana.nome, "whatsapp": self.ana.whatsapp,
            "logradouro": "Rua Exemplo", "numero": "10",
            "bairro": "Centro", "cidade": "Cidade Exemplo",
        })
        r = c.get("/conta/pix/")
        self.assertEqual(r.status_code, 409)
        self.assertFalse(r.json()["ok"])

    # --- a referência ---
    def test_a_referencia_carrega_pessoa_e_leilao(self):
        """A âncora do dinheiro é a REFERÊNCIA, não a FK — lição já paga caro."""
        self.assertEqual(
            servicos._conta_da_referencia(f"LEILAOC-{self.ana.id}-{self.leilao.id}"),
            (self.ana.id, self.leilao.id),
        )
        self.assertEqual(
            servicos._conta_da_referencia(f"LEILAOC-{self.ana.id}-{self.leilao.id}-R123456"),
            (self.ana.id, self.leilao.id),
        )

    def test_a_referencia_antiga_continua_sendo_lida(self):
        """Cobranças do formato antigo existem no banco e ainda podem ser pagas."""
        self.assertEqual(servicos._id_da_referencia("LEILAO-7"), 7)
        self.assertIsNone(servicos._conta_da_referencia("LEILAO-7"))

    def test_o_pagamento_reencontra_os_arremates_pela_referencia(self):
        """Refazer o Pix troca a FK e deixa a cobrança anterior órfã.

        É ela que pode estar na tela da pessoa no instante em que ela paga.
        """
        self._arrematar("Item um", self.ana, Decimal("40.00"))
        self._arrematar("Item dois", self.ana, Decimal("60.00"))
        pagamento = PagamentoLeilao.objects.create(
            referencia=f"LEILAOC-{self.ana.id}-{self.leilao.id}",
            mp_payment_id="123",
            valor_bruto=Decimal("100.00"),
        )
        # Sem FK nenhuma apontando para ele — como a cobrança órfã fica.
        achados = servicos._arremates_do_pagamento(pagamento)
        self.assertEqual(len(achados), 2)

    def test_a_referencia_nao_pesca_a_pessoa_errada(self):
        """`LEILAOC-1-...` não pode alcançar o participante 12."""
        outro = PagamentoLeilao.objects.create(
            referencia=f"LEILAOC-{self.ana.id}9-{self.leilao.id}",
            mp_payment_id="999",
        )
        conta = servicos._conta_da_referencia(outro.referencia)
        self.assertNotEqual(conta[0], self.ana.id)


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

        html = c.get("/locutor/", follow=True).content.decode("utf-8")
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
        # A venda é desfeita e o item volta para a fila (hoje isso é decisão da
        # equipe, não de um relógio). O NÚMERO é que não pode mudar: ele está
        # colado na caixa da prateleira.
        Lote.objects.filter(pk=lote.pk).update(
            status="fila", valor_atual=Decimal("0.00"), lider=None,
            voltas=1, fechado_em=None,
        )
        Arremate.objects.filter(pk=arremate.pk).update(status="cancelado")

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
        servicos.fechar_lote(lote, motivo="locutor")
        Lote.objects.filter(pk=lote.pk).update(
            status="fila", valor_atual=Decimal("0.00"), lider=None,
            voltas=1, fechado_em=None,
        )

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

        self.assertIn(f"nº {lote.numero}", c.get("/caixa/", follow=True).context["roteiro"])


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
        html = c.get("/locutor/", follow=True).content.decode("utf-8")
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
        r = self.c.get("/caixa/entregas/", follow=True)
        # A volta é para o caixa DAQUELE leilão: a tela de equipe trabalha
        # sobre um leilão explícito, e o id vai na URL.
        self.assertEqual(r.request["PATH_INFO"], f"/caixa/{self.leilao.pk}/")

    def test_dividir_por_dois(self):
        # POST desde a revisão de 24/09: o número de entregadores cria e apaga
        # colunas, e por GET um link velho ou um prefetch apagava as de alguém.
        r = self.c.post("/caixa/%d/entregas/" % self.leilao.pk, {"entregadores": 2}, follow=True)
        self.assertEqual(len(r.context["colunas"]), 2)
        self.assertEqual([len(c["paradas"]) for c in r.context["colunas"]], [1, 1])
        # Nasce já distribuído: a divisão por bairro é o ponto de partida.
        self.assertEqual(r.context["a_distribuir"], [])

    def test_a_tela_avisa_que_nao_ha_mapa(self):
        """Precisão inventada é pior que limite declarado."""
        html = self.c.get("/caixa/?entregadores=2", follow=True).content.decode("utf-8")
        self.assertIn("não consulta mapa", html)

    def test_numero_invalido_nao_quebra(self):
        for valor in ("abc", "-3", "0", "999"):
            r = self.c.get("/caixa/?entregadores=" + valor, follow=True)
            self.assertEqual(r.status_code, 200)

    def test_o_campo_de_entrega_nao_pede_mais_rastreio(self):
        """Entrega é na mão, por voluntário: não existe código de rastreio."""
        html = self.c.get("/caixa/", follow=True).content.decode("utf-8")
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
        # POST (revisão de 24/09): mudar o número de entregadores mexe no banco.
        return self.c.post("/caixa/%d/entregas/" % self.leilao.pk, {"entregadores": quantos}, follow=True)

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
            r = self.c.post("/caixa/%d/entregas/" % self.leilao.pk, {"entregadores": valor}, follow=True)
            self.assertEqual(r.status_code, 200)

    # --- recomeçar ---

    def test_refazer_por_bairro_joga_fora_o_que_foi_arrastado(self):
        self._abrir(2)
        self._mover(self.ana, 2)
        r = self.c.post("/caixa/entregas/redistribuir/")
        self.assertRedirects(r, f"/caixa/{self.leilao.pk}/entregas/")
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
        self.assertNotIn("/equipe/usuarios/", c.get("/locutor/", follow=True).content.decode("utf-8"))

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
        self.assertEqual(c.get("/caixa/", follow=True).status_code, 200)

    def test_a_sessao_sobrevive_a_troca(self):
        """Sem `update_session_auth_hash` a pessoa cai no login logo depois de obedecer."""
        self._criar(nome="Maria Fictícia", papeis=("caixa",))
        c = Client()
        c.login(username="maria", password=equipe.SENHA_PADRAO)
        c.post("/equipe/senha/", {"senha": "123", "repetir": "123"})
        self.assertEqual(c.get("/caixa/", follow=True).status_code, 200)

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
        html = self.c.get("/caixa/", follow=True).content.decode("utf-8")
        self.assertIn("wa.me/", html)

    def test_a_tela_do_caixa_ouve_o_stream(self):
        """Sem isto o caixa só via 'Pago' depois de apertar F5."""
        html = self.c.get("/caixa/", follow=True).content.decode("utf-8")
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

    # --- Sem prazo ---
    def test_a_acao_de_esticar_prazo_NAO_EXISTE_MAIS(self):
        """Não há relógio para esticar: quem arremata paga no fim.

        A ação some do mapa `ACOES_AREAS`, e ação fora do mapa é recusada por
        padrão — que é o lado seguro.
        """
        r = self.c.post(
            "/equipe/acao/",
            data=json.dumps({"acao": "prazo", "arremate": self.arremate.id, "minutos": 30}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 403, 409))
        self.assertNotIn("prazo", views.ACOES_AREAS)

    def test_o_item_nao_volta_para_a_fila_com_o_tempo(self):
        servicos.verificar_prazos()
        self.arremate.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(self.arremate.status, "aguardando")
        self.assertEqual(self.lote.status, "vendido")

    # --- Combinado ---
    def test_combinado_nao_vence_nunca(self):
        servicos.marcar_combinado(self.arremate, None, "paga amanhã")
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


class FotoDoItemCameraOuArquivoTests(TestCase):
    """A foto do item precisa dos DOIS caminhos — e o celular não os dá sozinho.

    História, porque ela explica o desenho:

    1. o campo nasceu com `capture="environment"`, que **força** a câmera e
       esconde a galeria: quem já tinha a foto do item (tirada antes, ou
       recebida por WhatsApp) não conseguia cadastrar pelo celular;
    2. tirar o `capture` resolveu a galeria e **custou a câmera**: no Android
       13+ o navegador passa a abrir o seletor de fotos do sistema, que não tem
       câmera nenhuma.

    Nenhum dos dois sozinho serve, e o que o menu do celular oferece varia de
    aparelho para aparelho. Por isso a escolha saiu do menu do sistema e veio
    para a tela: dois botões, dois inputs (um com `capture`, outro sem), e o
    `lote_form.js` copia o da câmera para o campo que é enviado.
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("prep_foto", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="preparacao")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="prep_foto", password="segredo-ficticio")

    def test_o_campo_enviado_nao_forca_a_camera(self):
        """O input do formulário é o caminho do ARQUIVO — sem `capture`."""
        widget = forms.LoteForm().fields["foto"].widget
        self.assertNotIn("capture", widget.attrs)
        self.assertEqual(widget.attrs.get("accept"), "image/*")

    def test_a_tela_oferece_os_dois_caminhos(self):
        r = self.c.get(f"/preparacao/{self.leilao.id}/itens/novo/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for ident in ("btnFotoCamera", "btnFotoArquivo", "fotoCamera", "fotoBotoes"):
            self.assertIn(f'id="{ident}"', html, f"falta #{ident} na tela")

    def test_so_o_campo_do_formulario_tem_name(self):
        """O input da câmera não pode ser enviado: quem vai no POST é `id_foto`.

        Se ele tivesse `name="foto"`, os dois seriam enviados e o vazio poderia
        sobrescrever a foto escolhida.
        """
        r = self.c.get(f"/preparacao/{self.leilao.id}/itens/novo/")
        html = r.content.decode()
        camera = re.search(r'<input[^>]*id="fotoCamera"[^>]*>', html).group(0)
        self.assertIn("capture", camera)
        self.assertNotIn("name=", camera)

    def test_os_botoes_nascem_escondidos(self):
        """Sem JS (ou sem `DataTransfer`), o seletor nativo tem de continuar de pé."""
        r = self.c.get(f"/preparacao/{self.leilao.id}/itens/novo/")
        html = r.content.decode()
        bloco = re.search(r'<div class="foto-botoes"[^>]*>', html).group(0)
        self.assertIn("hidden", bloco)


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
            "peso_kg": "1500", "altura_cm": "20",   # o campo é em GRAMAS
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
                                   # Abaixo de 1 kg o texto sai em GRAMAS: quem
                                   # digitou 500 quer ler "500 g", não "0,5 kg".
                                   ("0.50", "500 g"), ("0.35", "350 g"),
                                   ("15.25", "15,25 kg")]:
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

    def test_editar_devolve_o_peso_em_GRAMAS_no_campo(self):
        """O campo volta como foi digitado — em gramas —, e não com o `Decimal`
        cru do banco (`1.50`) nem em quilos."""
        lote = criar_lote(self.leilao, peso_kg=Decimal("1.50"))
        r = self.c.get("/preparacao/itens/%d/editar/" % lote.pk)
        self.assertEqual(r.context["form"].initial["peso_kg"], "1500")

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

        r = cliente.get("/caixa/", follow=True)
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


class AMesaSenteASalaTests(TestCase):
    """A mesa do locutor mostra o que a sala está fazendo — nome e emoji.

    Duas faltas do mesmo tipo, as duas pedidas pelo clube depois de usar a
    tela num pregão de verdade: quem conduz **não lê** a mesa, ele está
    falando, olhando o microfone e a lista. O que chega até ele é movimento.

    1. **O nome de quem está ganhando acende a cada lance.** Na tela do
       público isso já existia (`assume-a-ponta`), e pela mesma razão: a troca
       da ponta é a única coisa que muda de fato durante o pregão. Na mesa é
       ainda mais necessário, porque é o locutor que anuncia o nome em voz
       alta. O efeito dispara a CADA lance, não só quando o nome muda — na
       mesa o que interessa é "entrou lance agora".
    2. **As reações do público sobem na mesa também.** O locutor conduz sem
       plateia na frente (o público está em casa, no celular), e o emoji é o
       único aplauso que este leilão tem. O evento `reacoes` já chegava à
       conexão da mesa — o hub entrega tudo a todos —, e ela o jogava fora.

    É o MESMO `reacoes.js` e o MESMO trilho do público: um jeito só de
    desenhar emoji. A mesa apenas OUVE (não há botão de reagir aqui).
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("loc_sala", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="loc_sala", password="segredo-ficticio")

    def _js(self, nome):
        return Path(settings.BASE_DIR, "static", "leilao", "js", nome).read_text(
            encoding="utf-8"
        )

    def _css(self, nome):
        return Path(settings.BASE_DIR, "static", "leilao", "css", nome).read_text(
            encoding="utf-8"
        )

    def test_a_mesa_tem_o_trilho_e_carrega_o_reacoes(self):
        html = self.c.get("/locutor/", follow=True).content.decode()
        self.assertIn('id="reacoesTrilho"', html)
        # Sem o `.js`: em produção o ManifestStaticFilesStorage acrescenta o
        # hash do conteúdo ao nome (reacoes.abc123.js).
        self.assertIn("leilao/js/reacoes", html)

    def test_a_mesa_so_ouve_as_reacoes(self):
        """Quem reage é o público. Botão de reagir na mesa seria outro produto."""
        html = self.c.get("/locutor/", follow=True).content.decode()
        self.assertNotIn("btn-reacao", html)

    def test_o_locutor_js_ouve_o_evento_de_reacoes(self):
        js = self._js("locutor.js")
        self.assertIn('addEventListener("reacoes"', js)
        self.assertIn("window.Reacoes.receber", js)
        self.assertIn("window.Reacoes.ligar", js)

    def test_o_nome_acende_a_cada_lance(self):
        js = self._js("locutor.js")
        self.assertIn("acenderLider", js)
        self.assertIn("lance-novo", js)

    def test_a_classe_do_efeito_tem_regra_no_css(self):
        """Classe usada no JS sem regra em CSS nenhum não falha teste — só não
        acende. Já aconteceu no projeto; por isso esta guarda existe."""
        css = self._css("locutor.css")
        self.assertIn(".numero-valor.lance-novo", css)
        self.assertIn("@keyframes acende-o-nome", css)

    def test_o_efeito_nao_pode_criar_rolagem_horizontal(self):
        """`transform` não empurra o layout, mas CONTA para a área rolável.

        Nome comprido no pico da escala estouraria a coluna e criaria rolagem
        na página inteira — a armadilha que já mordeu no card do pregão. A
        trava é `clip` (não `hidden`, que criaria caixa de rolagem).
        """
        css = self._css("locutor.css")
        self.assertIn("overflow-x: clip", css)
        self.assertIn("overflow-clip-margin", css)

    def test_o_efeito_respeita_quem_pediu_menos_movimento(self):
        css = self._css("locutor.css")
        trecho = css[css.index(".numero-valor.lance-novo"):]
        self.assertIn("prefers-reduced-motion", trecho)
        self.assertIn(".numero-valor.lance-novo { animation: none; }", trecho)


class ATelaDaMesaNaoDeixaBuracoTests(TestCase):
    """Três cards não cabem em duas colunas — e foi isso que abriu a "faixa".

    A grade do pregão é de duas colunas. Ela nasceu com **dois** cards (o item
    em pregão e o microfone) e encaixava. Quando a bilheteria entrou como
    **terceiro** card, a conta deixou de fechar: o microfone caiu sozinho na
    segunda linha e sobrou uma célula vazia do lado dele — um retângulo morto
    de ~350px que o clube viu na tela e perguntou o que era.

    A remontagem seguiu o uso, não a simetria: **pregão, lances e chat** são as
    três coisas que o locutor acompanha ao mesmo tempo e ficam lado a lado;
    fila, microfone e pagamentos, que se usam uma vez na noite, vão para a
    linha de baixo. Três e três, nenhuma célula sobrando.

    Junto vai o `fecha em NaN:NaN` que aparecia no cabeçalho do chat: quando o
    chat passou a ficar aberto o leilão inteiro, o `ate` saiu do estado e esta
    linha continuou calculando com ele. Mesma família do erro que derrubou o JS
    no dia anterior — resto de uma remoção.
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("loc_faixa", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="loc_faixa", password="segredo-ficticio")

    def _css(self):
        return Path(settings.BASE_DIR, "static", "leilao", "css", "locutor.css").read_text(
            encoding="utf-8"
        )

    def test_as_duas_linhas_tem_os_cards_certos(self):
        """Em 24/09 a linha do pregão ganhou um 4º card, "Online agora" (pedido
        do clube). Ele não abre buraco: até caber ao lado (1280px) vira faixa
        inteira embaixo — ver `test_o_quarto_card_nunca_deixa_celula_vazia`."""
        html = self.c.get("/locutor/", follow=True).content.decode()
        # A ordem no HTML é a ordem na tela: o que se acompanha primeiro.
        # Em 26/09 entrou a linha da GENTE entre as duas (três cards).
        pregao = html.index('class="pregao-grade pregao-linha"')
        gente = html.index('class="pregao-grade tres gente"')
        segunda = html.index('class="pregao-grade tres"')
        linha1 = html[pregao:gente]
        linha_gente = html[gente:segunda]
        linha2 = html[segunda:html.index("</section>", segunda)]

        self.assertEqual(linha1.count('class="cartao'), 4, "a linha do pregão tem de ter 4 cards")
        self.assertEqual(linha_gente.count('class="cartao'), 3, "a linha da gente tem de ter 3 cards")
        self.assertEqual(linha2.count('class="cartao'), 3, "a última linha tem de ter 3 cards")
        for marca in ("Top 5 arremates", "Ainda sem lance", "Deram lance, sem arrematar"):
            self.assertIn(marca, linha_gente, f"{marca} saiu da linha da gente")

        # O martelo, os lances, o chat e quem está online juntos.
        for marca in ("lote-atual", "Lances deste item", "Chat ao vivo", "Online agora"):
            self.assertIn(marca, linha1, f"{marca} saiu da linha do pregão")
        # O que se usa uma vez por noite.
        for marca in ("Fila", "Sua voz", "Pagamentos"):
            self.assertIn(marca, linha2, f"{marca} saiu da segunda linha")

    def test_a_classe_da_linha_do_pregao_tem_regra_no_css(self):
        """Classe no HTML sem regra em CSS nenhum não falha teste — só renderiza
        feio. O projeto já se queimou com isso."""
        self.assertIn(".pregao-grade.pregao-linha", self._css())

    def test_tres_cards_nunca_caem_em_duas_colunas(self):
        """Entre 860 e 1000px a regra base daria `2fr 1fr` às duas grades — e a
        célula vazia voltaria pela porta dos fundos, numa largura de laptop."""
        css = self._css()
        trecho = css[css.index("@media (min-width: 860px)", css.index("Mesa: as linhas de TRÊS cards")):]
        trecho = trecho[: trecho.index("@media (min-width: 1000px)")]
        self.assertIn(".pregao-grade.tres", trecho)
        self.assertIn(".pregao-grade.pregao-linha", trecho)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", trecho)

    def test_o_quarto_card_nunca_deixa_celula_vazia(self):
        """Com três colunas (1000–1279px), o 4º card cairia sozinho numa célula
        e deixaria duas vazias ao lado — o mesmo buraco de antes. Ali ele ocupa
        a linha inteira; a partir de 1280px vira a quarta coluna."""
        css = self._css()
        inicio = css.index("@media (min-width: 1000px)", css.index("Mesa: as linhas de TRÊS cards"))
        entre = css[inicio: css.index("@media (min-width: 1280px)", inicio)]
        self.assertIn(".online-card { grid-column: 1 / -1; }", entre)

        largo = css[css.index("@media (min-width: 1280px)", inicio):]
        largo = largo[: largo.index("\n}\n")]
        regra = re.search(r"\.pregao-grade\.pregao-linha \{\s*grid-template-columns: ([^;]+);", largo)
        self.assertIsNotNone(regra, "falta a grade de 4 colunas da tela larga")
        self.assertEqual(regra.group(1).count("minmax("), 4)
        self.assertIn("grid-column: auto", largo)

    def test_o_chat_nao_promete_mais_hora_de_fechar(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "locutor.js").read_text(
            encoding="utf-8"
        )
        # Comentário sai ANTES: o comentário que explica a correção **cita** o
        # texto do bug, e sem esta limpeza a guarda acusaria a própria
        # documentação dela. É a mesma armadilha do scanner de funções.
        limpo = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        limpo = re.sub(r"//[^\n]*", " ", limpo)

        # O texto e o campo que o alimentava; sem o segundo, o primeiro vira NaN.
        self.assertNotIn("fecha em", limpo)
        self.assertNotIn("c.ate", limpo)


class OQueOLocutorLeEmVozAltaTests(TestCase):
    """Dois pedidos do clube sobre a mesa, depois de usá-la num pregão.

    **A lista do chat tem de rolar.** Ela rolava; parou de rolar quando o campo
    de falar foi preso no rodapé e o `max-height` saiu junto. Com 20 mensagens
    a lista ia a 1093px e levava a linha inteira — os três cards de uma linha
    têm a altura do mais alto —, empurrando a mesa para fora da tela. Guarda
    dupla, porque são dois jeitos de quebrar isso: sem o teto a lista cresce;
    sem o `min-height: 0` um item flex não encolhe abaixo do conteúdo e o
    `overflow-y` nunca entra em ação.

    **"Valor atual" e "Ganhando" são maiores que o resto.** São o que o locutor
    ANUNCIA, olhando de longe e de relance; o próximo lance é o valor atual
    mais cinco, e quem conduz já sabe. Por isso os dois dividem a linha de cima
    e o terceiro ocupa a de baixo, menor.

    E o **nome é menor que o valor**, de propósito: "R$ 1.234,00" tem tamanho
    previsível, um nome não. Na mesma letra do valor, dois sobrenomes longos
    viram quatro linhas e o card cresce empurrando o ▶ Abrir e o 🔨 VENDIDO
    para fora do alcance. Encolher é melhor do que cortar — o nome com
    reticências é justamente o que ele tem de ler em voz alta.
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("loc_voz", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="loc_voz", password="segredo-ficticio")

    def _css(self):
        return Path(settings.BASE_DIR, "static", "leilao", "css", "locutor.css").read_text(
            encoding="utf-8"
        )

    def _regra(self, seletor):
        """O corpo da regra CSS de um seletor (o que está entre as chaves)."""
        css = self._css()
        i = css.index(seletor)
        return css[i : css.index("}", i)]

    def test_a_lista_do_chat_rola_em_vez_de_crescer(self):
        regra = self._regra(".cartao.chat-card .chat-mesa")
        self.assertIn("max-height", regra)
        self.assertNotIn("max-height: none", regra)
        # Sem isto o item flex não encolhe abaixo do conteúdo e não há rolagem.
        self.assertIn("min-height: 0", regra)
        # O `overflow-y: auto` mora na regra base da lista. Procurado por
        # regex e não por `index`: `.chat-mesa` aparece antes num seletor
        # AGRUPADO (`.historico, .fila, …, .chat-mesa`), e o corpo daquele é
        # outro — foi nele que esta guarda caiu na primeira execução.
        self.assertRegex(self._css(), r"\.chat-mesa\s*\{[^}]*overflow-y:\s*auto")

    def test_os_dois_que_ele_anuncia_sao_os_grandes(self):
        html = self.c.get("/locutor/", follow=True).content.decode()
        numeros = html[html.index('class="mesa-numeros"') :]
        numeros = numeros[: numeros.index("mesa-crono")]

        # Valor atual e Ganhando grandes; Próximo lance não.
        self.assertEqual(numeros.count("numero-grande"), 2)
        antes_do_proximo = numeros[: numeros.index("Próximo lance")]
        self.assertEqual(antes_do_proximo.count("numero-grande"), 2)
        self.assertIn("numero-largo", numeros[numeros.index("Próximo lance") - 200 :])

    def test_as_classes_dos_subcards_tem_regra_no_css(self):
        css = self._css()
        for classe in (".numero-grande", ".numero-largo", ".numero-nome"):
            self.assertIn(classe, css, f"{classe} está no HTML sem regra em CSS nenhum")

    def test_o_nome_e_menor_que_o_valor(self):
        """Nome é de tamanho imprevisível; valor, não. Na mesma letra, o card
        cresce e empurra os botões do martelo para fora da tela."""
        def tamanho(seletor):
            corpo = self._regra(seletor)
            m = re.search(r"font-size:\s*([\d.]+)rem", corpo)
            self.assertIsNotNone(m, f"{seletor} sem font-size")
            return float(m.group(1))

        self.assertLess(
            tamanho(".numero-nome .numero-valor"),
            tamanho(".numero-grande .numero-valor"),
        )


class CardAltoNaoPerdeOTopoTests(TestCase):
    """Tela de cadastrar item cortada em cima — e sem jeito de rolar até lá.

    `html, body { height: 100% }`, então o `body.tela-entrada` é um flex com
    **exatamente** a altura da janela. Com `align-items: center`, um card mais
    alto do que ela sobra **dos dois lados**, e o que sobra em cima fica em
    coordenada **negativa** — que o navegador não deixa alcançar. Medido no
    cadastro de item (997px de altura): numa janela de 900 sumiam 80px; numa de
    540, **260px** — o título e os primeiros campos.

    `margin: auto` no filho faz as duas coisas certas: centraliza quando há
    espaço e vira **zero** quando o espaço é negativo, deixando o card começar
    no topo e a página rolar. Vale para todas as telas `tela-entrada` (entrar,
    troca de senha, configuração, cadastro de item); a do item só é a que
    estoura primeiro, por ser a mais alta.
    """

    def _css(self):
        return Path(settings.BASE_DIR, "static", "leilao", "css", "leilao.css").read_text(
            encoding="utf-8"
        )

    def _regra(self, seletor):
        css = self._css()
        i = css.index(seletor)
        return css[i : css.index("}", i)]

    def test_o_corpo_nao_centraliza_com_align_items(self):
        corpo = self._regra("body.tela-entrada {")
        self.assertIn("display: flex", corpo)
        self.assertNotIn("align-items: center", corpo)

    def test_quem_centraliza_e_a_margem_automatica(self):
        self.assertRegex(self._css(), r"\.entrada\s*\{[^}]*margin:\s*auto")

    def test_o_card_do_item_continua_sendo_o_mais_alto(self):
        """Se um dia esta tela encolher, a guarda perde o caso que a motivou —
        mas a regra vale para todas as `tela-entrada`, então ela fica."""
        html = Path(settings.BASE_DIR, "templates", "leilao", "lote_form.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("tela-entrada", html)
        self.assertIn('class="entrada"', html)


class ItemVoltaAoLeilaoTests(TestCase):
    """Devolver à fila um item que já foi batido — e **por quê**.

    Dois casos reais, e o dinheiro se comporta diferente em cada um:

    - **não pagou**: a pessoa desistiu. A dívida some junto, porque cobrar por
      um item que ela não vai receber seria errado;
    - **pagou**: ela **doou o item de volta** para o clube leiloar outra vez.
      Não é estorno — o dinheiro entrou e é do clube —, então o arremate
      continua `pago` e a arrecadação **não muda**. O que muda é que ela sai da
      **entrega**: sem isso um voluntário sairia para levar na casa dela um
      objeto que está de volta na prateleira.

    O **motivo é obrigatório**, e a trava é do servidor: um item reaparecendo
    na fila depois de batido é a coisa mais estranha que pode acontecer num
    leilão, e quem abrir a lista amanhã precisa saber por quê.
    """

    def setUp(self):
        # O freio de lance é por pessoa e mora na MEMÓRIA do processo; com o
        # rollback do TestCase os ids se repetem, então sem limpar o segundo
        # teste da classe leva "Calma!" e o item fecha sem lance nenhum.
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.pessoa = criar_pessoa("Ana Fictícia")
        self.lote = criar_lote(self.leilao, nome="Cesta fictícia")
        servicos.abrir_lote(self.lote)
        self.lote.refresh_from_db()
        servicos.dar_lance(self.lote.id, self.pessoa)
        self.lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(self.lote, motivo="locutor")
        self.lote.refresh_from_db()

    def test_o_item_volta_limpo_para_a_fila(self):
        voltas = self.lote.voltas
        servicos.devolver_ao_leilao(self.arremate, "Não pagou e desistiu.")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "fila")
        self.assertIsNone(self.lote.lider_id)
        self.assertEqual(self.lote.valor_atual, Decimal("0.00"))
        self.assertEqual(self.lote.voltas, voltas + 1)

    def test_o_numero_do_item_nao_muda(self):
        """É a etiqueta colada na caixa: se mudasse, a prateleira passaria a
        apontar para outra coisa."""
        numero = self.lote.numero
        servicos.devolver_ao_leilao(self.arremate, "Desistiu.")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.numero, numero)

    def test_sem_motivo_nao_devolve(self):
        for vazio in ("", "   ", None):
            with self.assertRaises(servicos.DevolucaoRecusada):
                servicos.devolver_ao_leilao(self.arremate, vazio)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")

    def test_quem_nao_pagou_deixa_de_dever(self):
        self.assertTrue(self.arremate.em_aberto)
        servicos.devolver_ao_leilao(self.arremate, "Desistiu.")
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "cancelado")
        self.assertFalse(self.arremate.em_aberto)
        # E some da cobrança: o Pix da pessoa não pode incluir este item.
        self.assertNotIn(
            self.arremate, list(servicos.arremates_em_aberto(self.pessoa))
        )

    def test_quem_pagou_e_doou_continua_pago(self):
        """Doação, não estorno: o dinheiro entrou e é do clube."""
        servicos.marcar_pago(self.arremate, manual=True)
        self.arremate.refresh_from_db()
        servicos.devolver_ao_leilao(self.arremate, "Doou o item de volta.")
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.status, "pago")
        self.assertIsNotNone(self.arremate.pago_em)

    def test_quem_doou_sai_da_entrega(self):
        servicos.marcar_pago(self.arremate, manual=True)
        self.arremate.refresh_from_db()
        self.assertTrue(self.arremate.a_entregar)
        servicos.devolver_ao_leilao(self.arremate, "Doou o item de volta.")
        self.arremate.refresh_from_db()
        self.assertFalse(
            self.arremate.a_entregar,
            "quem devolveu o item não pode continuar na lista de entrega",
        )

    def test_o_motivo_e_quem_devolveu_ficam_registrados(self):
        User = get_user_model()
        u = User.objects.create_user("caixa_dev", password="segredo-ficticio")
        servicos.devolver_ao_leilao(self.arremate, "  Doou de volta ao clube.  ", por=u)
        self.arremate.refresh_from_db()
        self.assertEqual(self.arremate.motivo_devolucao, "Doou de volta ao clube.")
        self.assertEqual(self.arremate.devolvido_por_id, u.id)
        self.assertIsNotNone(self.arremate.devolvido_em)
        self.assertTrue(self.arremate.devolvido)

    def test_devolver_duas_vezes_nao_conta_duas_voltas(self):
        """O botão sobrevive na tela até a página se refazer."""
        servicos.devolver_ao_leilao(self.arremate, "Desistiu.")
        self.lote.refresh_from_db()
        voltas = self.lote.voltas
        with self.assertRaises(servicos.DevolucaoRecusada):
            servicos.devolver_ao_leilao(self.arremate, "De novo.")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.voltas, voltas)

    def test_item_em_pregao_agora_nao_e_devolvido(self):
        """Devolver no meio da disputa apagaria os lances de quem está no ar."""
        outro = criar_lote(self.leilao, nome="Outro item fictício")
        servicos.abrir_lote(outro)
        outro.refresh_from_db()
        # Outra pessoa: o freio de 0,3 s é por pessoa, e o `setUp` acabou de
        # dar um lance com a primeira.
        segunda = criar_pessoa("Bruno Fictício")
        servicos.dar_lance(outro.id, segunda)
        outro.refresh_from_db()
        arremate = servicos.fechar_lote(outro, motivo="locutor")
        # Reabre o mesmo item: agora ele está em pregão de novo.
        outro.refresh_from_db()
        servicos.abrir_lote(outro)
        outro.refresh_from_db()
        self.assertEqual(outro.status, "aberto")
        with self.assertRaises(servicos.DevolucaoRecusada):
            servicos.devolver_ao_leilao(arremate, "Tentando no meio do pregão.")


class CadaTelaSabeDeQualLeilaoTests(TestCase):
    """A tela de equipe trabalha sobre o leilão que está **na URL**.

    A regra já valia para o cadastro de item (ele jogava item novo dentro do
    pregão em andamento). Mesa, caixa e quadro de entregas continuavam
    adivinhando — "o que está no ar, ou o mais recente" —, e o custo era real:
    o locutor abria a mesa **sem saber qual leilão estava conduzindo**, e
    depois do evento não havia como olhar o caixa da noite passada sem
    colocá-la no ar de novo.

    A URL sem id continua existindo (link antigo, favorito, atalho do hub): ela
    escolhe o padrão e **redireciona**, em vez de trabalhar sobre o palpite.
    """

    def setUp(self):
        self.antigo = criar_leilao(nome="Leilão de agosto", status="encerrado")
        self.atual = criar_leilao(nome="Leilão de setembro", status="ao_vivo")
        User = get_user_model()
        u = User.objects.create_user("equipe_sel", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        for nome in ("locutor", "caixa"):
            grupo, _ = Group.objects.get_or_create(name=nome)
            u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="equipe_sel", password="segredo-ficticio")

    def test_a_url_sem_id_redireciona_para_a_url_com_id(self):
        for caminho, nome in (("/locutor/", "locutor"), ("/caixa/", "caixa")):
            r = self.c.get(caminho)
            self.assertEqual(r.status_code, 302, caminho)
            self.assertEqual(r["Location"], "/%s/%d/" % (nome, self.atual.pk))

    def test_da_para_abrir_o_leilao_ANTIGO(self):
        """O caixa da noite passada, sem colocá-la no ar de novo."""
        r = self.c.get("/caixa/%d/" % self.antigo.pk)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["leilao"], self.antigo)

    def test_o_seletor_lista_todos_os_leiloes(self):
        r = self.c.get("/caixa/%d/" % self.atual.pk)
        html = r.content.decode()
        self.assertIn('id="seletorLeilao"', html)
        for leilao in (self.antigo, self.atual):
            self.assertIn("/caixa/%d/" % leilao.pk, html, leilao.nome)

    def test_o_redirect_nao_perde_a_query_string(self):
        """O `?entregadores=2` do quadro viaja no GET: redirecionar seco o
        descartava, e a tela voltava pedindo o número que a pessoa acabou de
        informar."""
        r = self.c.get("/caixa/entregas/?entregadores=2")
        self.assertEqual(r.status_code, 302)
        self.assertIn("entregadores=2", r["Location"])

    def test_leilao_que_nao_existe_e_404(self):
        self.assertEqual(self.c.get("/caixa/99999/").status_code, 404)

    def test_sem_leilao_nenhum_a_area_nao_entra_em_laco(self):
        """Hub → área → hub → área: uma página que nunca carrega.

        Acontecia com quem tem UMA área só (o hub manda direto para ela) e
        nenhum leilão criado (a área manda de volta para o hub). O `follow` do
        teste é o que expõe o laço.
        """
        Leilao.objects.all().delete()
        User = get_user_model()
        u = User.objects.create_user("so_locutor_sem", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        c = Client()
        c.login(username="so_locutor_sem", password="segredo-ficticio")
        r = c.get("/equipe/", follow=True)   # sem a guarda: RedirectCycleError
        self.assertEqual(r.status_code, 200)


class CaixaCobraPorPessoaTests(TestCase):
    """No caixa, o pagamento aparece por PESSOA — porque é assim que se cobra.

    O pagamento deixou de ser por item: cada um leva o que levar e paga tudo
    num Pix só, no fim. A tela, porém, continuou sendo uma lista de itens, e o
    caixa tinha de somar de cabeça o que cada pessoa devia, caçando linhas
    espalhadas. Com dez pessoas e trinta itens é onde o dinheiro se perde.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia Souza")
        self.arremates = []
        nomes = ["Cesta fictícia", "Quadro fictício", "Bolo fictício"]
        for i, nome in enumerate(nomes, 1):
            lote = criar_lote(self.leilao, nome=nome, ordem=i)
            servicos.limpar_limites()
            servicos.abrir_lote(lote)
            lote.refresh_from_db()
            servicos.dar_lance(lote.id, self.ana)
            lote.refresh_from_db()
            self.arremates.append(servicos.fechar_lote(lote, motivo="locutor"))

        User = get_user_model()
        u = User.objects.create_user("caixa_pessoa", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="caixa_pessoa", password="segredo-ficticio")

    def _contas(self):
        return self.c.get("/caixa/%d/" % self.leilao.pk).context["contas"]

    def test_os_itens_de_uma_pessoa_viram_UMA_linha(self):
        contas = self._contas()
        self.assertEqual(len(contas), 1)
        self.assertEqual(len(contas[0]["itens"]), 3)
        self.assertEqual(contas[0]["participante"], self.ana)

    def test_a_conta_soma_o_que_ela_deve(self):
        contas = self._contas()
        total = sum(a.valor for a in self.arremates)
        self.assertEqual(contas[0]["total"], total)
        self.assertEqual(contas[0]["falta"], total)
        self.assertFalse(contas[0]["quitada"])

    def test_pagar_um_item_move_o_valor_de_falta_para_pago(self):
        servicos.marcar_pago(self.arremates[0], manual=True)
        conta = self._contas()[0]
        self.assertEqual(conta["pago"], self.arremates[0].valor)
        self.assertEqual(conta["falta"], sum(a.valor for a in self.arremates[1:]))
        self.assertFalse(conta["quitada"])

    def test_quitada_quando_nao_falta_nada(self):
        for a in self.arremates:
            servicos.marcar_pago(a, manual=True)
        conta = self._contas()[0]
        self.assertTrue(conta["quitada"])
        self.assertEqual(conta["falta"], Decimal("0.00"))

    def test_quem_deve_vem_antes_de_quem_quitou(self):
        """É a fila de trabalho do caixa."""
        for a in self.arremates:
            servicos.marcar_pago(a, manual=True)
        servicos.limpar_limites()
        bruno = criar_pessoa("Bruno Fictício")
        lote = criar_lote(self.leilao, nome="Item do Bruno", ordem=9)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, bruno)
        lote.refresh_from_db()
        servicos.fechar_lote(lote, motivo="locutor")

        contas = self._contas()
        self.assertEqual(contas[0]["participante"], bruno, "quem deve vem primeiro")
        self.assertTrue(contas[-1]["quitada"])

    def test_item_devolvido_sai_da_conta(self):
        """O item voltou ao leilão: não é mais dela e não entra na soma."""
        servicos.devolver_ao_leilao(self.arremates[0], "Desistiu.")
        conta = self._contas()[0]
        self.assertEqual(len(conta["itens"]), 2)
        self.assertEqual(conta["total"], sum(a.valor for a in self.arremates[1:]))


class DevolverItemPelaTelaTests(TestCase):
    """A devolução é do CAIXA, e o motivo é exigido pelo SERVIDOR."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        pessoa = criar_pessoa("Ana Fictícia")
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        self.arremate = servicos.fechar_lote(lote, motivo="locutor")
        self.lote = lote

    def _cliente(self, *areas):
        User = get_user_model()
        nome = "dev_" + "_".join(areas or ["nada"])
        u = User.objects.create_user(nome, password="segredo-ficticio")
        u.is_staff = True
        u.save()
        for area in areas:
            grupo, _ = Group.objects.get_or_create(name=area)
            u.groups.add(grupo)
        c = Client()
        c.login(username=nome, password="segredo-ficticio")
        return c

    def _devolver(self, c, **extra):
        corpo = {"acao": "devolver", "arremate": self.arremate.pk}
        corpo.update(extra)
        return c.post(
            "/equipe/acao/", data=json.dumps(corpo), content_type="application/json"
        )

    def test_o_caixa_devolve(self):
        r = self._devolver(self._cliente("caixa"), motivo="Doou de volta.")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "fila")

    def test_o_locutor_nao_devolve(self):
        """Quem bate o martelo não mexe na conta de ninguém."""
        r = self._devolver(self._cliente("locutor"), motivo="Tentando.")
        self.assertEqual(r.status_code, 403)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")

    def test_sem_motivo_o_servidor_recusa(self):
        """Esconder o botão ou marcar `required` no HTML não barra POST forjado."""
        c = self._cliente("caixa")   # um cliente só: o login sai do nome da área
        for vazio in ("", "   "):
            r = self._devolver(c, motivo=vazio)
            self.assertEqual(r.status_code, 409)
            self.assertFalse(r.json()["ok"])
        r = self._devolver(c)   # sem o campo nenhum
        self.assertEqual(r.status_code, 409)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")

    def test_a_tela_do_caixa_oferece_o_botao(self):
        html = self._cliente("caixa").get("/caixa/%d/" % self.leilao.pk).content.decode()
        self.assertIn("data-devolver=", html)
        self.assertIn("modalDevolver", html)


class NovoLeilaoEmJanelaSuspensaTests(TestCase):
    """A tela de preparação é a LISTA; criar é uma janela suspensa."""

    def setUp(self):
        User = get_user_model()
        u = User.objects.create_user("prep_modal", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="preparacao")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="prep_modal", password="segredo-ficticio")

    def test_a_tela_tem_o_botao_e_o_modal(self):
        html = self.c.get("/preparacao/").content.decode()
        self.assertIn('id="btnNovoLeilao"', html)
        self.assertIn('id="modalNovoLeilao"', html)

    def test_o_modal_nasce_fechado(self):
        r = self.c.get("/preparacao/")
        self.assertIn('id="modalNovoLeilao" hidden', r.content.decode())
        self.assertFalse(r.context["abrir_modal"])

    def test_erro_no_formulario_devolve_o_modal_ABERTO(self):
        """Fechado, a pessoa redigitaria tudo sem ver o que estava errado."""
        r = self.c.post("/preparacao/", {"nome": ""})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["abrir_modal"])
        self.assertNotIn('id="modalNovoLeilao" hidden', r.content.decode())

    def test_criar_leva_para_os_itens(self):
        r = self.c.post("/preparacao/", {"nome": "Leilão fictício"})
        novo = Leilao.objects.get(nome="Leilão fictício")
        self.assertRedirects(r, "/preparacao/%d/itens/" % novo.pk)

    def test_a_lista_nao_promete_mais_prazo_para_pagar(self):
        """`minutos_para_pagar` é coluna dormente desde 21/09 — e a tela ainda
        anunciava "15 min para pagar", prometendo uma regra revogada."""
        criar_leilao(nome="Leilão fictício")
        html = self.c.get("/preparacao/").content.decode()
        self.assertNotIn("min para pagar", html)


class ModalDaContaEEscuroTests(TestCase):
    """Letra clara em fundo branco: o que o clube viu ao abrir os itens.

    O `.modal-caixa` do `base.css` é **branco** — ele nasceu para o sistema do
    clube, que é claro. O conteúdo que entra no modal da conta, porém, é o da
    própria mesa, **clonado**: `.arremate-linha`, selos e valores, todos
    pintados com `--palco-texto` (#eaf3fb) porque foram feitos para o card
    escuro. Um em cima do outro dá texto quase branco em fundo branco.

    A correção é **escopada aos dois modais novos**, e não ao
    `body.tela-locutor`: o modal do **Pix**, na mesma tela, usa as cores do tema
    claro de propósito (`--azul-escuro`, `--texto-suave`) e está correto sobre o
    branco. Escurecer todos resolveria um e quebraria o outro.

    O fundo precisa ser **opaco** (`--palco-fundo-2`), não o `--palco-card`, que
    é `rgba(255,255,255,0.06)`: translúcido, o branco de baixo atravessaria e o
    problema voltaria pela metade.
    """

    def _css(self):
        return Path(settings.BASE_DIR, "static", "leilao", "css", "locutor.css").read_text(
            encoding="utf-8"
        )

    def test_a_janela_da_conta_tem_fundo_escuro_e_opaco(self):
        css = self._css()
        self.assertIn("#modalConta .modal-caixa", css)
        trecho = css[css.index("#modalConta .modal-caixa") :]
        trecho = trecho[: trecho.index("}")]
        self.assertIn("var(--palco-fundo-2)", trecho)
        self.assertNotIn("var(--palco-card)", trecho)

    def test_a_janela_de_devolver_tambem(self):
        css = self._css()
        self.assertIn("#modalDevolver .modal-caixa", css)

    def test_o_modal_do_PIX_continua_claro(self):
        """Ele usa as cores do tema claro e está certo assim. Escurecer todos os
        modais da tela resolveria um problema e criaria outro."""
        css = self._css()
        self.assertNotIn("body.tela-locutor .modal-caixa", css)
        self.assertNotIn("#modalPix .modal-caixa", css)


class UmPixPorPessoaTests(TestCase):
    """UM código pelo total — não um botão de Pix por item.

    O clube contou: quem arrematou três itens via **três botões de Pix** na
    janela da conta. Era pior do que repetição — os três devolviam o **mesmo**
    código (a cobrança é uma só, da pessoa, desde 21/09), mas cada um anunciava
    o **valor daquele item**. O caixa diria "é R$ 10" com um código que cobra
    R$ 20, e a mensagem do WhatsApp nomeava um item só.
    """

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia Souza")
        self.arremates = []
        for i, nome in enumerate(["Cesta fictícia", "Quadro fictício", "Bolo fictício"], 1):
            lote = criar_lote(self.leilao, nome=nome, ordem=i)
            servicos.limpar_limites()
            servicos.abrir_lote(lote)
            lote.refresh_from_db()
            servicos.dar_lance(lote.id, self.ana)
            lote.refresh_from_db()
            self.arremates.append(servicos.fechar_lote(lote, motivo="locutor"))

        User = get_user_model()
        u = User.objects.create_user("caixa_pix", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="caixa")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="caixa_pix", password="segredo-ficticio")

    def test_a_janela_tem_UM_botao_de_pix(self):
        html = self.c.get("/caixa/%d/" % self.leilao.pk).content.decode()
        self.assertEqual(
            html.count("data-pix="), 1,
            "três itens não podem render três botões de Pix",
        )

    def test_o_botao_aponta_para_a_PESSOA(self):
        html = self.c.get("/caixa/%d/" % self.leilao.pk).content.decode()
        self.assertIn('data-pix="%d"' % self.ana.pk, html)

    def test_a_mensagem_do_whatsapp_lista_tudo_e_fecha_no_total(self):
        from leilao.views import _texto_pix_whatsapp

        class PagamentoFalso:
            qr_code = "00020126-codigo-ficticio"

        total = sum((a.valor for a in self.arremates), Decimal("0.00"))
        texto = _texto_pix_whatsapp(self.ana, self.arremates, total, PagamentoFalso())
        for a in self.arremates:
            self.assertIn(a.lote.nome, texto, "faltou um item na mensagem")
        self.assertIn("Total: R$ %s" % total, texto)
        # O código fica na ÚLTIMA linha: é assim que se copia no celular.
        self.assertTrue(texto.rstrip().endswith(PagamentoFalso.qr_code))

    def test_com_um_item_so_a_mensagem_nomeia_o_item(self):
        """Listar "1 item" e repetir o total abaixo seria burocracia."""
        from leilao.views import _texto_pix_whatsapp

        class PagamentoFalso:
            qr_code = "00020126-codigo-ficticio"

        a = self.arremates[0]
        texto = _texto_pix_whatsapp(self.ana, [a], a.valor, PagamentoFalso())
        self.assertIn(a.lote.nome, texto)
        self.assertNotIn("Total:", texto)


class PesoEmGramasTests(TestCase):
    """O peso é digitado em GRAMAS — e guardado em quilos.

    Quem cadastra pensa em grama. Pedir "0,35" para uma caneca é convidar ao
    erro de vírgula, e no celular a vírgula é justamente a tecla que o teclado
    numérico de muitos aparelhos não mostra. Em grama o campo é inteiro: não há
    separador para errar.

    O banco continua em **quilos** de propósito: os itens já cadastrados valem
    como estão e nenhuma tela que lê `peso_kg` precisou mudar.
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("prep_gramas", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="preparacao")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="prep_gramas", password="segredo-ficticio")

    def _post(self, peso, nome="Item fictício"):
        return self.c.post(
            "/preparacao/%d/itens/novo/" % self.leilao.pk,
            {
                "nome": nome, "descricao": "", "lance_inicial": "30.00",
                "peso_kg": peso, "altura_cm": "20",
                "largura_cm": "30", "profundidade_cm": "25",
            },
        )

    def test_a_tela_pede_GRAMAS(self):
        html = self.c.get("/preparacao/%d/itens/novo/" % self.leilao.pk).content.decode()
        self.assertIn("Peso (g)", html)
        self.assertNotIn("Peso (kg)", html)

    def test_gramas_viram_quilos_no_banco(self):
        for gramas, esperado in [("1500", "1.50"), ("350", "0.35"), ("20", "0.02")]:
            with self.subTest(gramas=gramas):
                self._post(gramas, nome="Item " + gramas)
                lote = self.leilao.lotes.get(nome="Item " + gramas)
                self.assertEqual(lote.peso_kg, Decimal(esperado))

    def test_peso_pequeno_demais_e_recusado_em_vez_de_virar_zero(self):
        """5 g não cabe em duas casas de quilo. Salvar viraria 0,00 — peso
        zerado disfarçado, que é o que os validadores existem para impedir."""
        r = self._post("5", nome="Item minúsculo")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.leilao.lotes.filter(nome="Item minúsculo").exists())

    def test_o_teto_continua_valendo_em_gramas(self):
        maximo_g = int(Lote.MAX_PESO_KG * 1000)
        r = self._post(str(maximo_g + 1), nome="Item pesadíssimo")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.leilao.lotes.filter(nome="Item pesadíssimo").exists())

    def test_abaixo_de_um_quilo_a_tela_escreve_em_gramas(self):
        """Quem digitou 350 quer ler "350 g", não "0,35 kg": a segunda forma faz
        o voluntário parar para converter, e ele está decidindo se cabe no
        carro."""
        self.assertEqual(Lote(peso_kg=Decimal("0.35")).peso_texto, "350 g")
        self.assertEqual(Lote(peso_kg=Decimal("0.02")).peso_texto, "20 g")
        # De 1 kg para cima vale o contrário.
        self.assertEqual(Lote(peso_kg=Decimal("1.50")).peso_texto, "1,5 kg")

    def test_o_campo_volta_em_gramas_na_edicao(self):
        lote = criar_lote(self.leilao, peso_kg=Decimal("0.35"))
        r = self.c.get("/preparacao/itens/%d/editar/" % lote.pk)
        self.assertEqual(r.context["form"].initial["peso_kg"], "350")


class FotoSobeReduzidaTests(TestCase):
    """O que demora ao cadastrar item é o UPLOAD, não o servidor.

    A foto sai do celular com 2 a 5 MB e, numa internet de celular, isso são
    dezenas de segundos com a tela parada — para o servidor receber tudo e
    jogar 90% fora, já que a maior largura que ele guarda é 1280.

    Duas frentes: o navegador reduz antes de enviar, e o servidor deixou de
    decodificar 12 MP inteiros para descartá-los (`draft`, a escala do próprio
    JPEG). Medido no pipeline real: **433 ms → 177 ms**, com o arquivo final do
    mesmo tamanho.
    """

    def _js(self):
        return Path(settings.BASE_DIR, "static", "leilao", "js", "lote_form.js").read_text(
            encoding="utf-8"
        )

    def test_o_navegador_reduz_antes_de_enviar(self):
        js = self._js()
        self.assertIn("createImageBitmap", js)
        self.assertIn("toBlob", js)

    def test_a_reducao_confere_a_ORIENTACAO_antes_de_confiar(self):
        """Desenhar num canvas apaga o EXIF. Se a rotação não tiver sido
        aplicada na leitura, a foto sobe deitada e o servidor não tem mais como
        consertar — item deitado no pregão é pior do que cadastro lento.

        O gabarito é o `<img>`, que orienta pelo EXIF desde sempre: se o
        `createImageBitmap` devolver o tamanho trocado em relação a ele, aquele
        navegador ignorou o `imageOrientation` e a redução é **pulada**.
        """
        js = self._js()
        self.assertIn('imageOrientation: "from-image"', js)
        self.assertIn("naturalWidth", js)
        self.assertIn("medidasCertas", js)

    def test_sem_suporte_o_arquivo_original_sobe_inteiro(self):
        """Melhoria progressiva: é ganho de tempo, não a garantia do tamanho.
        Quem entra sem JS manda o arquivo inteiro e o cadastro funciona igual —
        o servidor continua reduzindo do lado dele."""
        js = self._js()
        self.assertIn("podeReduzir", js)
        self.assertIn("return Promise.resolve(null);", js)

    def test_o_servidor_nao_decodifica_12MP_para_jogar_fora(self):
        imagens = Path(settings.BASE_DIR, "leilao", "imagens.py").read_text(encoding="utf-8")
        self.assertIn("draft", imagens)
        # A miniatura sai da GRANDE, não da original: 1280 → 420 custa quase
        # nada, e reduzir 4032 → 420 seria refazer o trabalho caro.
        self.assertIn("_reduzir(grande, LARGURA_MINI)", imagens)


class QuemJaChegouTests(TestCase):
    """Clicar no contador de gente abre a lista de quem está no leilão.

    O número é a informação pela qual o locutor decide a hora de começar, e a
    pergunta seguinte é sempre "quem já chegou?".

    **Os nomes saem só pelo `/locutor/dados/`**, que é autenticado. Eles nunca
    entram no broadcast: o estado público é lido por todos os celulares da
    sala, e quem está online não é coisa que se diga em voz alta — é a mesma
    regra que mantém Pix, telefone e endereço fora do stream.
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("loc_quem", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        grupo, _ = Group.objects.get_or_create(name="locutor")
        u.groups.add(grupo)
        self.c = Client()
        self.c.login(username="loc_quem", password="segredo-ficticio")

    def tearDown(self):
        servicos.HUB._assinantes.clear()

    def test_a_mesa_tem_o_contador_clicavel_e_o_modal(self):
        html = self.c.get("/locutor/%d/" % self.leilao.pk).content.decode()
        self.assertIn('id="btnQuemChegou"', html)
        self.assertIn('id="modalQuemChegou"', html)

    def test_o_card_online_agora_fica_no_pregao(self):
        """Pedido do clube em 24/09: a lista à vista, sem clicar."""
        html = self.c.get("/locutor/%d/" % self.leilao.pk).content.decode()
        pregao = html[html.index('class="pregao-grade pregao-linha"'):html.index('class="pregao-grade tres"')]
        self.assertIn('class="cartao online-card"', pregao)
        self.assertIn('id="onlineLista"', pregao)
        self.assertIn('id="contaOnline"', pregao)

    def test_o_card_online_nao_leva_nome_no_html(self):
        """Os nomes chegam pelo JS, do endpoint autenticado — a página não os
        traz prontos (ela ficaria velha no minuto seguinte)."""
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        html = self.c.get("/locutor/%d/" % self.leilao.pk).content.decode()
        self.assertNotIn("Ana Fictícia", html)

    def test_o_card_se_atualiza_quando_alguem_entra_ou_sai(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "locutor.js").read_text(encoding="utf-8")
        limpo = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        limpo = re.sub(r"//[^\n]*", " ", limpo)
        # A recarga da mesa desenha o card...
        recarga = limpo[limpo.index("function recarregarDados"):]
        recarga = recarga[: recarga.index("var fonte")]
        self.assertIn("desenharOnline(d)", recarga)
        # ...e o evento `online` (entrou/saiu alguém) pede a recarga.
        online = limpo[limpo.index('addEventListener("online"'):]
        online = online[: online.index("});")]
        self.assertIn("recarregarDados()", online)
        # Um desenho só para a janela e para o card.
        self.assertIn('desenharQuemChegou(dados, $("onlineLista")', limpo)

    def test_o_hub_guarda_quem_esta_conectado(self):
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        servicos.HUB.assinar(publico=True, nome="Bruno Fictício")
        nomes = [p["nome"] for p in servicos.HUB.nomes_conectados()]
        self.assertEqual(nomes, ["Ana Fictícia", "Bruno Fictício"])

    def test_a_mesma_pessoa_em_duas_abas_e_UMA_entrada(self):
        """Celular e computador da mesma pessoa. A lista dobra num nome só e
        diz quantas telas — senão pareceria que há duas pessoas."""
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        lista = servicos.HUB.nomes_conectados()
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0]["telas"], 2)
        self.assertEqual(servicos.HUB.conectados, 2)   # conexões continuam sendo duas

    def test_a_equipe_nao_entra_na_lista_nem_na_contagem(self):
        servicos.HUB.assinar(publico=False, nome="mesa")
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        self.assertEqual(servicos.HUB.conectados, 1)
        self.assertEqual([p["nome"] for p in servicos.HUB.nomes_conectados()], ["Ana Fictícia"])

    def test_quem_ainda_nao_se_cadastrou_conta_mas_nao_tem_nome(self):
        """A pessoa abriu o link e está na tela de entrada."""
        servicos.HUB.assinar(publico=True, nome=None)
        self.assertEqual(servicos.HUB.conectados, 1)
        self.assertEqual(servicos.HUB.nomes_conectados(), [])

    def test_os_nomes_vem_pelo_endpoint_autenticado(self):
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        dados = self.c.get("/locutor/dados/").json()
        self.assertIn("conectados_nomes", dados)
        self.assertEqual([p["nome"] for p in dados["conectados_nomes"]], ["Ana Fictícia"])

    def test_os_nomes_NAO_entram_no_estado_publico(self):
        """O stream é lido por todos os celulares da sala."""
        servicos.HUB.assinar(publico=True, nome="Ana Fictícia")
        publico = json.dumps(est.estado_publico(self.leilao), default=str)
        self.assertNotIn("Ana Fictícia", publico)
        self.assertNotIn("conectados_nomes", publico)


class SonsDoLeilaoTests(TestCase):
    """Caixa registradora no lance, palmas e gritaria no martelo.

    Começou sintetizado — palma é uma rajada curta de ruído filtrado, torcida é
    ruído de banda média com a frequência varrendo — porque a regra do projeto
    era não ter arquivo de áudio: zero download (50 celulares baixando o mesmo
    arquivo no instante em que o pregão pega fogo é banda desperdiçada), zero
    latência e zero binário versionado.

    **O clube trouxe os próprios arquivos** e eles passaram a valer. Os três
    motivos não sumiram, então a troca veio com três amarras: os arquivos
    baixam **na entrada** (não no primeiro lance), têm **teto de tamanho**, e o
    sintetizado **continua como reserva** — rede ruim ou formato não suportado
    não pode deixar o leilão mudo.
    """

    def _som(self):
        return Path(settings.BASE_DIR, "static", "leilao", "js", "som.js").read_text(
            encoding="utf-8"
        )

    def test_o_lance_toca_caixa_registradora(self):
        js = self._som()
        trecho = js[js.index("lance: function"):]
        trecho = trecho[: trecho.index("superado:")]
        # O sino (duas parciais) e a gaveta (grave, curta).
        self.assertIn("sopro(", trecho)
        self.assertIn("nota(", trecho)

    def test_o_martelo_toca_palmas_e_torcida(self):
        js = self._som()
        for nome in ("vendido: function", "arrematei: function"):
            trecho = js[js.index(nome):]
            trecho = trecho[: trecho.index("},")]
            self.assertIn("palmas(", trecho, nome)
            self.assertIn("torcida(", trecho, nome)

    def test_palma_e_torcida_sao_sintetizadas(self):
        js = self._som()
        self.assertIn("function palma(", js)
        self.assertIn("function palmas(", js)
        self.assertIn("function torcida(", js)
        self.assertIn("createBuffer(", js)   # o ruído é gerado, não baixado

    def test_o_ruido_e_gerado_UMA_vez_e_reaproveitado(self):
        """Gerar dois segundos de ruído a cada palma seria trabalho de CPU no
        meio do pregão — justamente a hora em que ela falta."""
        js = self._som()
        self.assertIn("bufferRuido", js)

    def test_o_audio_do_clube_esta_onde_o_template_procura(self):
        """O clube trouxe dois arquivos, e eles substituem os sintetizados.

        A regra anterior era "nenhum áudio no repositório", pelos três motivos
        que continuam valendo em parte (download, latência, binário versionado).
        Ela caiu por decisão de quem conduz o evento — e o que sobrou destes
        testes é garantir que a troca não traga de volta os problemas que a
        regra evitava.
        """
        som = Path(settings.BASE_DIR, "static", "leilao", "som")
        self.assertTrue((som / "lance.wav").exists())
        self.assertTrue((som / "arremate.mp3").exists())

    def test_o_audio_tem_TETO_de_tamanho(self):
        """O motivo técnico da regra antiga não desapareceu: 50 celulares
        baixam esses arquivos. Meio megabyte cada é o limite em que isso
        continua sendo um download na entrada, e não um problema."""
        som = Path(settings.BASE_DIR, "static", "leilao", "som")
        for arquivo in som.glob("*"):
            with self.subTest(arquivo=arquivo.name):
                mb = arquivo.stat().st_size / 1e6
                self.assertLess(mb, 0.5, "%s tem %.2f MB" % (arquivo.name, mb))

    def test_o_audio_baixa_na_ENTRADA_e_nao_no_primeiro_lance(self):
        """Buscar o arquivo no primeiro lance atrasaria justamente o som que
        precisa sair no instante do evento, e poria tráfego na hora de maior
        disputa. Ele baixa quando a pessoa toca "Entrar com som" — momento em
        que ela está parada, lendo a tela."""
        js = self._som()
        ativar = js[js.index("function ativar("):]
        ativar = ativar[: ativar.index(chr(10) + "    }")]
        self.assertIn('carregar("lance"', ativar)
        self.assertIn('carregar("arremate"', ativar)

    def test_o_sintetizado_continua_como_RESERVA(self):
        """Rede ruim, formato que o navegador não decodifica, arquivo trocado:
        o leilão não pode ficar mudo por causa de um download."""
        js = self._som()
        for nome in ("lance: function", "vendido: function"):
            trecho = js[js.index(nome):]
            trecho = trecho[: trecho.index("},")]
            self.assertIn("tocarArquivo(", trecho, nome)
            # Depois do `return` do arquivo vem o sintetizado — é ele que toca
            # quando o buffer não chegou.
            self.assertTrue(
                "sopro(" in trecho or "palmas(" in trecho,
                nome + " ficou sem reserva sintetizada",
            )

    def test_o_caminho_do_audio_vem_do_SERVIDOR(self):
        """Em produção o `static` acrescenta o hash do conteúdo ao nome; um
        caminho chumbado no JS apontaria para a versão antiga depois do
        primeiro deploy."""
        html = Path(
            settings.BASE_DIR, "templates", "leilao", "leilao.html"
        ).read_text(encoding="utf-8")
        self.assertIn("data-som-lance=", html)
        self.assertIn("data-som-arremate=", html)
        js = self._som()
        self.assertNotIn("leilao/som/lance.wav", js)

    def test_o_aviso_de_arremate_nao_promete_mais_prazo(self):
        """Não há prazo para pagar desde 21/09, e o toast ainda dizia
        "Pague em até 15 minutos"."""
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(
            encoding="utf-8"
        )
        limpo = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        limpo = re.sub(r"//[^\n]*", " ", limpo)
        self.assertNotIn("15 minutos", limpo)


class SomDaSalaSempreLigadoTests(TestCase):
    """O som da sala é SEMPRE ligado (pedido do clube em 26/09).

    Até ali o locutor tinha dois interruptores — caixa registradora e palmas —
    que calavam a tela de todo mundo. Saíram: o leilão soa sempre. As colunas
    `som_lance`/`som_arremate` ficaram dormentes, e o que se guarda aqui é que
    nada volte a ler delas nem a desligá-las.
    """

    def setUp(self):
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("som_locutor", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="locutor")[0])
        self.c = Client()
        self.c.login(username="som_locutor", password="segredo-ficticio")

    def test_a_mesa_nao_tem_mais_os_interruptores(self):
        html = self.c.get("/locutor/%d/" % self.leilao.pk).content.decode()
        self.assertNotIn("data-som=", html)
        self.assertNotIn("Som na tela de quem assiste", html)

    def test_a_acao_de_desligar_o_som_nao_existe_mais(self):
        """Nem por POST forjado: o som não se cala."""
        r = self.c.post("/equipe/acao/", data=json.dumps({"acao": "som", "qual": "lance", "ligar": False}),
                        content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertNotIn("som", views.ACOES_AREAS)

    def test_o_broadcast_nao_leva_mais_a_chave(self):
        """Mesmo um leilão com a coluna antiga em False soa: a chave não viaja."""
        self.leilao.som_lance = False
        self.leilao.som_arremate = False
        self.leilao.save()
        publico = est.estado_publico(self.leilao)
        self.assertNotIn("som_lance", publico["leilao"])
        self.assertNotIn("som_arremate", publico["leilao"])

    def test_a_tela_do_publico_toca_sem_portao(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(encoding="utf-8")
        self.assertNotIn("somLiberado", js)
        self.assertIn("window.SomLeilao.lance()", js)
        self.assertIn("window.SomLeilao.vendido()", js)
        self.assertIn("window.SomLeilao.arrematei()", js)

    def test_a_mesa_nao_manda_mais_desligar(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "locutor.js").read_text(encoding="utf-8")
        self.assertNotIn('acao: "som"', js)
        self.assertNotIn("[data-som]", js)


class AudioVoltaQuandoOLocutorVoltaTests(TestCase):
    """O locutor encerra a transmissão, volta minutos depois — e alguns
    celulares ficavam mudos até **reiniciar o aparelho**.

    Relatado pelo clube. Eram duas causas somadas, e nenhuma delas aparecia
    como erro na tela:

    1. **A reconexão desistia de vez.** Depois de 8 falhas o módulo parava de
       tentar até a aba sair e voltar. Só que o caso real é a pessoa **olhando
       a tela o tempo todo** enquanto o locutor está fora do ar: a aba nunca sai
       da frente, nada dispara `retomar()`, e o silêncio é definitivo.
    2. **O contador de tentativas não zerava no clique.** Tocar o 🔊 chamava
       `conectar()` sem zerar `tentativas`; depois de uma sequência ruim ele já
       estava no teto, então cada clique valia UMA tentativa que nascia
       estourada — e se o locutor ainda não tivesse voltado naquele instante, o
       módulo desistia na hora. É o "nem clicando no ícone volta".

    E havia um terceiro buraco, esse silencioso: quando a fonte some, a conexão
    costuma continuar **"connected"** — o ICE não cai e o `connectionState` não
    muda. Nenhum handler disparava, então nada percebia que não vinha mais som.
    """

    def _js(self):
        return Path(settings.BASE_DIR, "static", "leilao", "js", "audio_ouvir.js").read_text(
            encoding="utf-8"
        )

    def test_a_reconexao_NAO_desiste_mais(self):
        """O freio passou a ser o INTERVALO, não um teto de desistência: 50
        celulares tentando a cada 20 s são 2,5 pedidos por segundo, cada um um
        404 curto enquanto não há ninguém no ar."""
        js = self._js()
        religar = js[js.index("function religar()"):]
        religar = religar[: religar.index(chr(10) + "    }")]
        self.assertNotIn("desistiu", religar)
        self.assertIn("Math.min", religar)   # a espera tem teto

    def test_a_espera_e_SORTEADA_para_o_bando_se_espalhar(self):
        """Cem celulares percebem o silêncio no MESMO instante — é o mesmo
        evento para todo mundo.

        Com espera fixa, as tentativas ficam **sincronizadas** para o resto da
        noite: em vez de 100 aparelhos espalhados em 20 segundos, são 100
        pedidos no mesmo segundo, de 20 em 20. E a rajada cai justamente no
        pior momento — quando o locutor volta, as 100 negociações acontecem
        juntas, no mesmo vCPU que roda o leilão e o MediaMTX.
        """
        js = self._js()
        religar = js[js.index("function religar()"):]
        religar = religar[: religar.index(chr(10) + "    }")]
        self.assertIn("Math.random()", religar)

    def test_o_clique_no_icone_zera_o_contador(self):
        """Pedido explícito é começo do zero."""
        js = self._js()
        ligar = js[js.index("ligar: function"):]
        ligar = ligar[: ligar.index("},")]
        self.assertIn("tentativas = 0", ligar)

    def test_a_flag_de_desistencia_nao_ficou_dormente(self):
        """Ela não é mais marcada em lugar nenhum: some, não fica pendurada."""
        self.assertNotIn("desistiu", self._js())

    def test_percebe_conectado_e_MUDO(self):
        """Quando a fonte some, o ICE não cai: sem ouvir a faixa, nada percebe."""
        js = self._js()
        self.assertIn("onmute", js)
        self.assertIn("onunmute", js)
        self.assertIn("onended", js)

    def test_tem_o_segundo_vigia_por_bytes(self):
        """Nem todo navegador dispara `mute` — e falha justamente nos celulares
        mais antigos, que são os que mais aparecem num evento de clube."""
        js = self._js()
        self.assertIn("getStats", js)
        self.assertIn("bytesReceived", js)
        self.assertIn("inbound-rtp", js)

    def test_os_vigias_morrem_com_a_conexao(self):
        """Relógio sobrevivente religa uma conexão que já foi substituída."""
        js = self._js()
        desligar = js[js.index("function desligarConexao()"):]
        desligar = desligar[: desligar.index(chr(10) + "    }")]
        self.assertIn("clearTimeout", desligar)
        self.assertIn("clearInterval", desligar)

    def test_a_tela_PEDE_o_toque_quando_o_som_cai(self):
        """O caso que nenhuma reconexão conserta.

        Quando o navegador **recusa tocar** (política de autoplay, aparelho que
        voltou do bloqueio), só um **gesto** libera o áudio. Religar a conexão
        mil vezes não adianta — o que adianta é pedir um toque. Por isso a
        janela não é um aviso: o botão dentro dela **é** o gesto.
        """
        html = Path(
            settings.BASE_DIR, "templates", "leilao", "leilao.html"
        ).read_text(encoding="utf-8")
        self.assertIn('id="modalSomCaiu"', html)
        self.assertIn('id="btnVoltarASomar"', html)

        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("aoMudar", js)
        # O botão refaz o caminho inteiro da porta do som.
        botao = js[js.index('$("btnVoltarASomar")'):]
        botao = botao[: botao.index("});")]
        self.assertIn("ligarSom()", botao)

    def test_o_play_recusado_avisa_a_tela(self):
        """É a diferença entre "o som sumiu" e "o som sumiu e ninguém soube"."""
        js = self._js()
        tocar = js[js.index("function tocar()"):]
        tocar = tocar[: tocar.index(chr(10) + "    }")]
        self.assertIn('avisar(false, "recusado")', tocar)
        self.assertIn("avisar(true)", tocar)

    def test_desligar_de_proposito_NAO_pede_para_religar(self):
        """A pessoa acabou de calar o som: pedir o toque de volta seria brigar
        com ela."""
        js = self._js()
        desligar = js[js.index("desligar: function"):]
        desligar = desligar[: desligar.index("},")]
        self.assertIn("ouvindo = null", desligar)   # nem "ouvindo" nem "perdeu" (26/09)
        self.assertNotIn("avisar(", desligar)

    def test_a_janela_nao_insiste_com_quem_fechou(self):
        """Insistir num leilão ao vivo é pior do que ficar quieto."""
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("caladoDesde", js)
        self.assertIn("60000", js)

    def test_o_elemento_e_limpo_antes_de_receber_a_stream_nova(self):
        """O elemento segurando a stream anterior é um dos jeitos de o celular
        travar o áudio de vez — o caso em que nem desligar e ligar resolve."""
        js = self._js()
        ontrack = js[js.index("conexao.ontrack"):]
        ontrack = ontrack[: ontrack.index("tocar();")]
        self.assertIn("srcObject = null", ontrack)


class TelaShowTests(TestCase):
    """A tela "show" do pregão — a PADRÃO desde 24/09; a clássica é o backup.

    Ela é só DESENHO: roda sobre o mesmo motor (`leilao.js`) e os mesmos
    endpoints. Por isso o que se guarda aqui é o que faria as duas telas
    divergirem — um id que o motor procura e a nova não tem, um efeito que
    pega toque, o número do item vazando para o público — e que a clássica
    continua de pé em `/classico/`.
    """

    HTML = Path(settings.BASE_DIR, "templates", "leilao", "leilao_show.html")
    JS_MOTOR = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js")
    JS_SHOW = Path(settings.BASE_DIR, "static", "leilao", "js", "palco_show.js")
    CSS_SHOW = Path(settings.BASE_DIR, "static", "leilao", "css", "palco_show.css")

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.c = Client()

    def _logar(self):
        p = criar_pessoa()
        sessao = self.c.session
        sessao[CHAVE_SESSAO] = p.token
        sessao.save()
        return p

    @staticmethod
    def _sem_comentarios(js):
        limpo = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        return re.sub(r"//[^\n]*", " ", limpo)

    # --- As duas telas convivem -------------------------------------------
    def test_a_show_e_a_padrao(self):
        """Pedido do clube em 24/09: a show virou a tela de todo mundo."""
        self._logar()
        r = self.c.get("/")
        self.assertTemplateUsed(r, "leilao/leilao_show.html")
        self.assertTemplateNotUsed(r, "leilao/leilao.html")

    def test_a_classica_fica_de_backup_em_classico(self):
        self._logar()
        r = self.c.get("/classico/")
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "leilao/leilao.html")

    def test_o_link_antigo_da_nova_leva_a_padrao(self):
        self.assertRedirects(self.c.get("/nova/"), "/", fetch_redirect_response=False)

    def test_sem_cadastro_a_classica_manda_para_a_porta_e_volta_para_ela(self):
        r = self.c.get("/classico/")
        self.assertRedirects(r, "/entrar/")
        r = self.c.post("/entrar/", {
            "nome": "Fulano de Teste", "whatsapp": "(11) 90000-0000", "cep": "01001-000",
            "logradouro": "Rua Exemplo", "numero": "10", "bairro": "Centro",
            "cidade": "Cidade Exemplo", "estado": "SP",
        })
        self.assertRedirects(r, "/classico/")

    def test_quem_volta_a_padrao_nao_e_mais_mandado_para_a_classica(self):
        self.c.get("/classico/")
        self.c.get("/")          # sem cadastro: vai para a porta, mas esquece a clássica
        self.assertNotIn(views.CHAVE_TELA, self.c.session)

    # --- O motor encontra tudo o que procura ------------------------------
    def test_todo_id_que_o_motor_procura_existe_na_nova(self):
        js = self.JS_MOTOR.read_text(encoding="utf-8")
        html = self.HTML.read_text(encoding="utf-8")
        faltando = [
            i for i in set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)', js))
            if f'id="{i}"' not in html and f'json_script:"{i}"' not in html
        ]
        self.assertEqual(sorted(faltando), [], "o motor procura ids que a tela nova não tem")

    def test_todo_id_que_os_efeitos_procuram_existe_na_nova(self):
        js = self._sem_comentarios(self.JS_SHOW.read_text(encoding="utf-8"))
        html = self.HTML.read_text(encoding="utf-8")
        faltando = [i for i in set(re.findall(r'\$\("([A-Za-z0-9_]+)"\)', js)) if f'id="{i}"' not in html]
        self.assertEqual(sorted(faltando), [])

    def test_o_placar_tem_a_classe_que_o_motor_liga(self):
        """O motor faz `querySelector(".pregao")` para ligar `eu-ganhando` e
        `superado` — sem a classe, a coroa e o tremor nunca acenderiam."""
        html = self.HTML.read_text(encoding="utf-8")
        self.assertRegex(html, r'<section class="pregao show-placar"')

    def test_os_efeitos_carregam_antes_do_motor(self):
        """O primeiro `leilao:estado` sai na carga do motor; ouvinte registrado
        depois perderia a primeira pintura."""
        html = self.HTML.read_text(encoding="utf-8")
        self.assertLess(html.index("leilao/js/palco_show.js"), html.index("leilao/js/leilao.js"))

    def test_a_nova_segura_a_tela_e_liga_o_som(self):
        html = self.HTML.read_text(encoding="utf-8")
        self.assertIn("leilao/js/tela_acesa.js", html)
        self.assertIn("leilao/js/audio_ouvir.js", html)
        self.assertIn("data-som-lance=", html)

    def test_a_porta_da_nova_tambem_so_tem_um_caminho(self):
        html = self.HTML.read_text(encoding="utf-8")
        porta = html[html.index('id="portaSom"'):html.index("<main")]
        self.assertEqual(re.findall(r'<button[^>]*id="(bt[^"]+)"', porta), ["btnPortaSom"])

    # --- O motor avisa, e o aviso não pode derrubá-lo ---------------------
    def test_o_motor_emite_os_avisos_que_os_efeitos_escutam(self):
        motor = self._sem_comentarios(self.JS_MOTOR.read_text(encoding="utf-8"))
        show = self._sem_comentarios(self.JS_SHOW.read_text(encoding="utf-8"))
        for aviso in ("estado", "lance", "lote_aberto", "vendido", "chat", "toque_lance"):
            self.assertIn(f'emitir("{aviso}"', motor, f"o motor não emite {aviso}")
            self.assertIn(f'"leilao:{aviso}"', show, f"os efeitos não escutam {aviso}")

    def test_aviso_que_falha_nao_derruba_o_motor(self):
        motor = self.JS_MOTOR.read_text(encoding="utf-8")
        emitir = motor[motor.index("function emitir"):]
        emitir = emitir[: emitir.index("\n    }\n")]
        self.assertIn("try", emitir)
        self.assertIn("catch", emitir)

    # --- Nada flutua em cima de controle ----------------------------------
    def test_camadas_de_efeito_nao_pegam_toque(self):
        css = self.CSS_SHOW.read_text(encoding="utf-8")
        for seletor in (".show-fx {", ".show-vinheta {", ".show-foto-brilho {", ".show-carimbo {",
                        ".show-combo {", ".show-estouro {", ".show-btn-brilho {"):
            bloco = css[css.index(seletor):]
            bloco = bloco[: bloco.index("}")]
            self.assertIn("pointer-events: none", bloco, f"{seletor} pegaria o toque")

    def test_emojis_e_barra_moram_no_fluxo(self):
        """Regra do projeto: elemento que não flutua não cobre nada."""
        css = self.CSS_SHOW.read_text(encoding="utf-8")
        for seletor in (".tela-show .show-reacoes {", ".tela-show .show-barra {"):
            bloco = css[css.index(seletor):]
            bloco = bloco[: bloco.index("}")]
            self.assertNotIn("position: fixed", bloco)

    def test_blocos_flex_escondidos_tem_regra_de_hidden(self):
        css = self.CSS_SHOW.read_text(encoding="utf-8")
        for classe in (".show-pregao[hidden]", ".show-ticker[hidden]", ".show-folha[hidden]",
                       ".show-chat[hidden]", ".show-acao[hidden]"):
            self.assertIn(classe, css)

    # --- O público não aprende o que não pode saber -----------------------
    def test_a_nova_nao_mostra_o_numero_do_item(self):
        """"Item 12" conta que existem pelo menos 12 — e quantos faltam é o
        que o público não pode saber. O carimbo diz só NOVO ITEM."""
        self._logar()
        servicos.abrir_lote(self.lote)
        html = self.c.get("/").content.decode()
        self.assertNotIn("numero_atual", html)
        show = self._sem_comentarios(self.JS_SHOW.read_text(encoding="utf-8"))
        self.assertNotIn(".numero", show)

    def test_a_nova_nao_cria_requisicao_nenhuma(self):
        """Enfeite não gasta banda do pregão: o termômetro conta os lances que
        já chegam pelo stream."""
        show = self._sem_comentarios(self.JS_SHOW.read_text(encoding="utf-8"))
        self.assertNotIn("fetch(", show)
        self.assertNotIn("XMLHttpRequest", show)
        self.assertNotIn("EventSource", show)

    def test_texto_de_gente_entra_como_texto(self):
        """Nome e mensagem vêm de quem está do outro lado: `textContent`, nunca
        `innerHTML` com o conteúdo deles."""
        show = self._sem_comentarios(self.JS_SHOW.read_text(encoding="utf-8"))
        for linha in show.splitlines():
            if "innerHTML" in linha:
                self.assertRegex(linha, r'innerHTML\s*=\s*""', linha.strip())

    # --- Os limites do "cassino" ------------------------------------------
    def test_sem_contagem_regressiva_nem_prazo(self):
        """O martelo é do locutor: nenhuma contagem na tela promete um prazo
        que o sistema não cumpre (nem pressiona quem está dando lance)."""
        show = self._sem_comentarios(self.JS_SHOW.read_text(encoding="utf-8")).lower()
        for proibido in ("cronometro", "cronômetro", "contagem", "restam", "segundos para"):
            self.assertNotIn(proibido, show)

    def test_o_teto_de_particulas_cai_quando_o_aparelho_sofre(self):
        show = self.JS_SHOW.read_text(encoding="utf-8")
        self.assertIn("quadrosLentos", show)
        self.assertIn("teto = Math.max(24, Math.floor(teto / 2))", show)
        self.assertIn("prefers-reduced-motion", show)

    def test_a_festa_nao_fica_parada_em_zero(self):
        """A contagem do valor da festa tem garantia de valor final — um
        prêmio parado em "R$ 0,00" seria pior do que nenhuma animação."""
        show = self.JS_SHOW.read_text(encoding="utf-8")
        trecho = show[show.index('"leilao:vendido"'):]
        self.assertIn("Math.max(0,", trecho)
        self.assertIn("DURACAO + 250", trecho)


class ConferirPixNaoMorreTests(TestCase):
    """O reforço da conferência do Pix (QR aberto) usava um `id` que deixou de
    existir quando o pagamento virou UM Pix pelo total. O `ReferenceError`
    matava a volta, e a conferência parava na primeira tentativa."""

    def test_a_conferencia_nao_usa_variavel_que_nao_existe(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(encoding="utf-8")
        trecho = js[js.index("function conferirPagamento"):]
        trecho = trecho[: trecho.index("\n    }\n")]
        limpo = re.sub(r"//[^\n]*", " ", trecho)
        self.assertNotIn("=== id", limpo)
        self.assertIn("conferirPagamento(geracao); }, 5000)", limpo)


class DinheiroDaRevisaoTests(TestCase):
    """Os buracos de dinheiro achados na revisão geral de 24/09.

    Todos têm a mesma raiz: a cobrança não sabia QUAIS itens cobria. A FK
    `Arremate.pagamento` aponta só para a mais nova, e o resto era palpite —
    "reaproveita se os itens apontam para ela", "quita tudo o que a pessoa tem
    em aberto". Desde a mig. 0014 a cobrança grava a lista (`cobre`), e cada
    teste aqui é um dos cenários em que o palpite errava o dinheiro.
    """

    def setUp(self):
        from unittest import mock

        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia Souza")
        cfg = ConfigLeilao.get_solo()
        cfg.access_token_teste = "TEST-token-ficticio"
        cfg.save()

        self.gerados = []

        def criar_pix_falso(cfg, *, referencia, valor, **_):
            self.gerados.append((referencia, valor))
            return {
                "ok": True, "mp_payment_id": "mp-%d" % len(self.gerados),
                "status": "pendente", "qr_code": "pix-%s-%s" % (referencia, valor),
                "qr_code_base64": "", "ticket_url": "", "raw": {},
            }

        p = mock.patch.object(servicos.mercadopago, "criar_pix", side_effect=criar_pix_falso)
        p.start()
        self.addCleanup(p.stop)

    def _arrematar(self, nome, lance_inicial, pessoa=None, leilao=None):
        leilao = leilao or self.leilao
        lote = criar_lote(leilao, nome=nome, ordem=leilao.lotes.count() + 1,
                          lance_inicial=Decimal(lance_inicial))
        servicos.limpar_limites()
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa or self.ana)
        lote.refresh_from_db()
        return servicos.fechar_lote(lote, motivo="locutor")

    def _aprovar(self, pagamento):
        return servicos._aplicar_retorno(pagamento, {"status": "aprovado"})

    # --- 1. O Pix reaproveitado com o valor antigo ------------------------
    def test_baixa_na_mao_de_um_item_refaz_o_pix_pelo_valor_novo(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        b = self._arrematar("Quadro fictício", "30.00")
        p1 = servicos.cobranca_do_participante(self.ana)
        self.assertEqual(p1.valor_bruto, Decimal("80.00"))

        a.refresh_from_db()
        servicos.marcar_pago(a, manual=True)          # pagou A em dinheiro
        p2 = servicos.cobranca_do_participante(self.ana)
        self.assertNotEqual(p2.pk, p1.pk, "reaproveitou o Pix de R$ 80")
        self.assertEqual(p2.valor_bruto, Decimal("30.00"))
        self.assertEqual(p2.cobre, [b.pk])

    def test_mesma_conta_reaproveita_o_mesmo_pix(self):
        self._arrematar("Cesta fictícia", "50.00")
        p1 = servicos.cobranca_do_participante(self.ana)
        p2 = servicos.cobranca_do_participante(self.ana)
        self.assertEqual(p1.pk, p2.pk)
        self.assertEqual(len(self.gerados), 1)

    def test_pix_antigo_pago_nao_ressuscita_item_devolvido(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        b = self._arrematar("Quadro fictício", "30.00")
        p1 = servicos.cobranca_do_participante(self.ana)
        a.refresh_from_db()
        servicos.devolver_ao_leilao(a, "Desistiu (teste).")

        with self.assertLogs("leilao.servicos", level="ERROR"):
            self._aprovar(p1)                          # pagou o código velho
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.status, "cancelado", "item devolvido virou pago")
        self.assertEqual(b.status, "pago")

    def test_webhook_repetido_nao_gera_alarme(self):
        self._arrematar("Cesta fictícia", "50.00")
        p = servicos.cobranca_do_participante(self.ana)
        self._aprovar(p)
        with self.assertNoLogs("leilao.servicos", level="ERROR"):
            self._aprovar(p)

    # --- 2. O Pix antigo quitando item que não cobria ---------------------
    def test_pix_antigo_so_quita_o_que_ele_cobria(self):
        c = self._arrematar("Cesta fictícia", "10.00")
        q1 = servicos.cobranca_do_participante(self.ana)          # R$ 10, só C
        d = self._arrematar("Quadro fictício", "100.00")
        q2 = servicos.cobranca_do_participante(self.ana)          # R$ 110, C + D
        self.assertEqual(q2.valor_bruto, Decimal("110.00"))

        self._aprovar(q1)                                          # pagou o de R$ 10
        c.refresh_from_db()
        d.refresh_from_db()
        self.assertEqual(c.status, "pago")
        self.assertEqual(d.status, "aguardando", "o item de R$ 100 foi quitado com R$ 10")

    def test_cobranca_antiga_sem_lista_so_quita_se_o_valor_bate(self):
        """Cobrança anterior à 0014 (sem `cobre`) e órfã: o palpite pelo que
        está em aberto só vale se o valor bater."""
        self._arrematar("Cesta fictícia", "10.00")
        self._arrematar("Quadro fictício", "100.00")
        velha = PagamentoLeilao.objects.create(
            referencia="LEILAOC-%d-%d" % (self.ana.pk, self.leilao.pk),
            valor_bruto=Decimal("10.00"), qr_code="pix-velho",
        )
        with self.assertLogs("leilao.servicos", level="ERROR"):
            self._aprovar(velha)
        self.assertFalse(Arremate.objects.filter(participante=self.ana, status="pago").exists())

    # --- 3. Pix depois de encerrado ---------------------------------------
    def test_depois_de_encerrado_a_pessoa_consegue_o_pix(self):
        self._arrematar("Cesta fictícia", "50.00")
        self.leilao.status = "encerrado"
        self.leilao.pagamentos_liberados = False
        self.leilao.save()
        c = Client()
        s = c.session
        s[CHAVE_SESSAO] = self.ana.token
        s.save()
        d = c.get("/conta/pix/").json()
        self.assertTrue(d["ok"], d)
        self.assertEqual(Decimal(d["valor"]), Decimal("50.00"))
        self.assertTrue(c.get("/meus-arremates/").json()["liberado"])

    def test_no_ar_e_sem_liberar_continua_travado(self):
        self._arrematar("Cesta fictícia", "50.00")
        c = Client()
        s = c.session
        s[CHAVE_SESSAO] = self.ana.token
        s.save()
        self.assertEqual(c.get("/conta/pix/").status_code, 409)

    def test_o_caixa_gera_o_pix_de_quem_nunca_abriu(self):
        self._arrematar("Cesta fictícia", "50.00")
        self.leilao.status = "encerrado"
        self.leilao.save()
        User = get_user_model()
        u = User.objects.create_user("caixa_rev", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="caixa")[0])
        c = Client()
        c.login(username="caixa_rev", password="segredo-ficticio")
        d = c.get("/caixa/pessoa/%d/pix/" % self.ana.pk).json()
        self.assertTrue(d["ok"], d)
        self.assertEqual(Decimal(d["valor"]), Decimal("50.00"))

    # --- Conta de um leilão só --------------------------------------------
    def test_a_conta_nao_mistura_leiloes(self):
        self._arrematar("Cesta fictícia", "50.00")
        self.leilao.status = "encerrado"
        self.leilao.save()
        outro = criar_leilao(nome="Leilão fictício 2")
        self._arrematar("Quadro fictício", "30.00", leilao=outro)
        self.assertEqual(servicos.total_em_aberto(self.ana), Decimal("50.00"))
        p = servicos.cobranca_do_participante(self.ana)
        self.assertEqual(p.valor_bruto, Decimal("50.00"))
        self.assertTrue(p.referencia.startswith("LEILAOC-%d-%d" % (self.ana.pk, self.leilao.pk)))

    # --- Estorno ----------------------------------------------------------
    def test_estorno_devolve_a_divida(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        p = servicos.cobranca_do_participante(self.ana)
        self._aprovar(p)
        with self.assertLogs("leilao.servicos", level="ERROR"):
            servicos._aplicar_retorno(p, {"status": "estornado"})
        a.refresh_from_db()
        self.assertEqual(a.status, "aguardando")
        self.assertFalse(a.a_entregar)

    def test_estorno_nao_mexe_na_baixa_manual(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        p = servicos.cobranca_do_participante(self.ana)
        a.refresh_from_db()
        servicos.marcar_pago(a, manual=True)
        servicos._aplicar_retorno(p, {"status": "estornado"})
        a.refresh_from_db()
        self.assertEqual(a.status, "pago")

    # --- 4. Reabrir item vendido ------------------------------------------
    def _locutor(self):
        User = get_user_model()
        u = User.objects.create_user("loc_rev", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="locutor")[0])
        c = Client()
        c.login(username="loc_rev", password="segredo-ficticio")
        return c

    def test_a_mesa_nao_reabre_item_vendido(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        r = self._locutor().post("/equipe/acao/", json.dumps({"acao": "abrir", "lote": a.lote_id}),
                                 content_type="application/json")
        self.assertEqual(r.status_code, 409)
        a.lote.refresh_from_db()
        self.assertEqual(a.lote.status, "vendido")
        self.assertEqual(Arremate.objects.filter(lote=a.lote).count(), 1)

    def test_a_mesa_nao_abre_item_de_leilao_fora_do_ar(self):
        self.leilao.status = "rascunho"
        self.leilao.save()
        lote = criar_lote(self.leilao, nome="Bolo fictício")
        r = self._locutor().post("/equipe/acao/", json.dumps({"acao": "abrir", "lote": lote.id}),
                                 content_type="application/json")
        self.assertEqual(r.status_code, 409)

    def test_lance_em_leilao_fora_do_ar_e_recusado(self):
        lote = criar_lote(self.leilao, nome="Bolo fictício")
        servicos.abrir_lote(lote)
        self.leilao.status = "rascunho"
        self.leilao.save()
        ok, msg, _ = servicos.dar_lance(lote.id, self.ana)
        self.assertFalse(ok)

    # --- Item devolvido fora da conta -------------------------------------
    def test_item_devolvido_nao_volta_a_ser_cobrado_nem_pago(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        servicos.devolver_ao_leilao(a, "Desistiu (teste).")
        User = get_user_model()
        u = User.objects.create_user("caixa_dev", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="caixa")[0])
        c = Client()
        c.login(username="caixa_dev", password="segredo-ficticio")
        for acao in ("combinado", "pago", "entregue"):
            r = c.post("/equipe/acao/", json.dumps({"acao": acao, "arremate": a.pk}),
                       content_type="application/json")
            self.assertEqual(r.status_code, 409, acao)
        a.refresh_from_db()
        self.assertEqual(a.status, "cancelado")


class RevisaoTelasEEquipeTests(TestCase):
    """O resto da revisão geral de 24/09: leilão da tela, conexão que desiste,
    lance atrasado, peso, IP do freio de login, foto e quadro de entregas."""

    JS = Path(settings.BASE_DIR, "static", "leilao", "js")
    TPL = Path(settings.BASE_DIR, "templates", "leilao")

    def setUp(self):
        servicos.limpar_limites()
        self.no_ar = criar_leilao(nome="Leilão fictício no ar")
        self.rascunho = criar_leilao(nome="Leilão fictício do mês que vem", status="rascunho")

    def _equipe(self, papel, login):
        User = get_user_model()
        u = User.objects.create_user(login, password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name=papel)[0])
        c = Client()
        c.login(username=login, password="segredo-ficticio")
        return c

    def _acao(self, c, **corpo):
        return c.post("/equipe/acao/", json.dumps(corpo), content_type="application/json")

    @staticmethod
    def _limpo(txt):
        txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
        return re.sub(r"//[^\n]*", " ", txt)

    def _ler(self, *partes):
        return Path(settings.BASE_DIR, *partes).read_text(encoding="utf-8")

    # --- O leilão da TELA, não o adivinhado -------------------------------
    def test_a_acao_age_no_leilao_que_a_tela_mandou(self):
        c = self._equipe("locutor", "loc_tela")
        r = self._acao(c, acao="liberar", leilao=self.rascunho.pk)
        self.assertTrue(r.json()["ok"])
        self.rascunho.refresh_from_db()
        self.no_ar.refresh_from_db()
        self.assertTrue(self.rascunho.pagamentos_liberados)
        self.assertFalse(self.no_ar.pagamentos_liberados, "mexeu no leilão que está no ar")

    def test_sem_leilao_na_acao_vale_o_palpite_antigo(self):
        """Aba aberta antes da correção continua funcionando."""
        c = self._equipe("locutor", "loc_velho")
        self._acao(c, acao="liberar")
        self.no_ar.refresh_from_db()
        self.assertTrue(self.no_ar.pagamentos_liberados)

    def test_os_dados_da_mesa_sao_do_leilao_da_url(self):
        criar_lote(self.rascunho, nome="Quadro fictício do mês que vem")
        c = self._equipe("locutor", "loc_dados")
        d = c.get("/locutor/dados/?leilao=%d" % self.rascunho.pk).json()
        self.assertEqual([x["nome"] for x in d["fila"]], ["Quadro fictício do mês que vem"])

    def test_as_telas_da_equipe_mandam_o_leilao(self):
        for tpl in ("locutor.html", "caixa.html", "lotes.html", "entregas_quadro.html"):
            self.assertIn('data-leilao="{{ leilao.pk }}"', self._ler("templates", "leilao", tpl), tpl)
        for js in ("locutor.js", "caixa.js", "entregas_quadro.js"):
            self.assertIn("corpo.leilao = dados.dataset.leilao", self._limpo(self._ler("static", "leilao", "js", js)), js)
        self.assertIn("leilao: dados.dataset.leilao", self._ler("static", "leilao", "js", "lotes.js"))
        self.assertIn('"leilao="', self._ler("static", "leilao", "js", "locutor.js"))

    # --- Quadro de entregas -----------------------------------------------
    def test_numero_de_entregadores_por_get_nao_mexe_no_banco(self):
        c = self._equipe("caixa", "caixa_get")
        c.get("/caixa/%d/entregas/?entregadores=3" % self.rascunho.pk)
        self.assertEqual(self.rascunho.entregadores.count(), 0)

    def test_os_formularios_do_quadro_levam_o_leilao(self):
        caixa = self._ler("templates", "leilao", "caixa.html")
        self.assertIn("{% url 'leilao:entregas_quadro_leilao' leilao.pk %}", caixa)
        quadro = self._ler("templates", "leilao", "entregas_quadro.html")
        self.assertIn('<input type="hidden" name="leilao" value="{{ leilao.pk }}">', quadro)
        self.assertIn("{% url 'leilao:caixa_leilao' leilao.pk %}", quadro)
        self.assertNotIn('method="get" class="form-entregadores"', quadro + caixa)

    def test_respostas_fora_de_ordem_do_quadro_sao_ignoradas(self):
        js = self._ler("static", "leilao", "js", "entregas_quadro.js")
        self.assertIn("if (seq < ultimoAplicado) return;", js)
        self.assertEqual(js.count("var seq = ++pedidoSeq;"), 2)

    # --- Devolver item de leilão encerrado não apaga o pregão -------------
    def test_devolver_publica_o_estado_do_leilao_no_ar(self):
        from unittest import mock

        lote = criar_lote(self.no_ar)
        pessoa = criar_pessoa()
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        arremate = servicos.fechar_lote(lote, motivo="locutor")
        encerrado = criar_leilao(nome="Leilão fictício encerrado", status="encerrado")
        Lote.objects.filter(pk=lote.pk).update(leilao=encerrado)
        arremate.refresh_from_db()
        with mock.patch.object(servicos.HUB, "publicar") as publicar:
            servicos.devolver_ao_leilao(arremate, "Desistiu (teste).")
        estado = publicar.call_args[0][1]
        self.assertTrue(estado["ativo"], "mandou 'sem leilão' para a sala")

    # --- A conexão ao vivo que não desiste --------------------------------
    def test_as_quatro_telas_usam_a_fonte_viva(self):
        for tpl in ("leilao.html", "leilao_show.html", "locutor.html", "caixa.html"):
            self.assertIn("leilao/js/fonte_viva.js", self._ler("templates", "leilao", tpl), tpl)
        for js in ("leilao.js", "locutor.js", "caixa.js"):
            self.assertIn("window.FonteViva.abrir(", self._ler("static", "leilao", "js", js), js)

    def test_a_fonte_viva_reabre_quando_o_navegador_desiste(self):
        js = self._limpo(self._ler("static", "leilao", "js", "fonte_viva.js"))
        self.assertIn("es.readyState === 2) agendar()", js)
        self.assertIn("Math.random()", js, "espera fixa sincroniza 100 celulares")
        self.assertIn("ouvintes.forEach", js, "os ouvintes têm de ser religados na conexão nova")

    def test_a_fonte_viva_carrega_antes_de_quem_a_usa(self):
        for tpl, js in (("leilao_show.html", "leilao.js"), ("leilao.html", "leilao.js"),
                        ("locutor.html", "locutor.js"), ("caixa.html", "caixa.js")):
            html = self._ler("templates", "leilao", tpl)
            self.assertLess(html.index("leilao/js/fonte_viva.js"), html.index("leilao/js/" + js + "'"), tpl)

    # --- Motor do público --------------------------------------------------
    def test_resposta_atrasada_do_lance_nao_sobrescreve_lance_mais_novo(self):
        js = self._limpo(self._ler("static", "leilao", "js", "leilao.js"))
        dar = js[js.index("function darLance"):]
        dar = dar[: dar.index("function abrirGaveta")]
        self.assertEqual(dar.count("respostaAindaVale(d.lote)"), 2)
        self.assertNotIn("if (d.lote) { estado.lote = d.lote", dar)

    def test_item_reaberto_zera_o_estado_da_rodada(self):
        js = self._limpo(self._ler("static", "leilao", "js", "leilao.js"))
        trecho = js[js.index('addEventListener("lote_aberto"'):]
        trecho = trecho[: trecho.index("render(")]
        self.assertIn("loteId = null", trecho)
        self.assertIn("fecharGaveta()", trecho)

    def test_o_pix_refeito_atualiza_o_qr_aberto(self):
        js = self._limpo(self._ler("static", "leilao", "js", "leilao.js"))
        trecho = js[js.index('addEventListener("arremate_pix"'):]
        trecho = trecho[: trecho.index("});")]
        self.assertNotIn("String(arremateAberto)", trecho)
        self.assertIn("abrirQr()", trecho)

    def test_mensagem_do_chat_leva_a_chave_da_pessoa(self):
        pessoa = criar_pessoa()
        m = servicos.enviar_mensagem(self.no_ar, pessoa, "Oi, pessoal!")
        publico = est.mensagem_publica(m)
        self.assertEqual(publico["autor_chave"], pessoa.chave_pessoa)
        self.assertNotIn(pessoa.whatsapp, json.dumps(publico))

    # --- Mesa -------------------------------------------------------------
    def test_o_abrir_da_fila_passa_pela_confirmacao(self):
        js = self._limpo(self._ler("static", "leilao", "js", "locutor.js"))
        self.assertIn('b.dataset.acao = "abrir"', js)
        self.assertNotIn('acao({ acao: "abrir", lote: l.id })', js)
        self.assertIn('var travar = qual === "abrir" || qual === "fechar"', js)

    # --- Peso, IP, foto ---------------------------------------------------
    def _form(self, peso):
        return forms.LoteForm(data={
            "nome": "Caneca fictícia", "lance_inicial": "10", "peso_kg": peso,
            "altura_cm": "10", "largura_cm": "10", "profundidade_cm": "10",
        })

    def test_peso_com_ponto_de_milhar_e_lido_em_gramas(self):
        f = self._form("12.500")
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data["peso_kg"], Decimal("12.50"))

    def test_peso_com_decimal_e_recusado_em_vez_de_virar_10_g(self):
        for valor in ("15,5", "1.5", "0,35"):
            f = self._form(valor)
            self.assertFalse(f.is_valid(), valor)
            self.assertIn("GRAMAS", str(f.errors["peso_kg"]))

    def test_o_freio_de_login_usa_o_ip_que_o_nosso_proxy_viu(self):
        from django.test import RequestFactory

        r = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 203.0.113.9")
        self.assertEqual(views._ip_do(r), "203.0.113.9")

    def test_limpar_a_foto_tira_a_miniatura(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (60, 40), (200, 120, 40)).save(buf, format="JPEG")
        c = self._equipe("preparacao", "prep_foto")
        dados = {"nome": "Caneca fictícia", "lance_inicial": "10", "peso_kg": "350",
                 "altura_cm": "10", "largura_cm": "10", "profundidade_cm": "10"}
        c.post("/preparacao/%d/itens/novo/" % self.no_ar.pk,
               {**dados, "foto": SimpleUploadedFile("f.jpg", buf.getvalue(), "image/jpeg")})
        lote = Lote.objects.get(nome="Caneca fictícia")
        self.assertTrue(lote.foto_mini)
        c.post("/preparacao/itens/%d/editar/" % lote.pk, {**dados, "foto-clear": "on"})
        lote.refresh_from_db()
        self.assertFalse(lote.foto)
        self.assertFalse(lote.foto_mini, "a miniatura ficou para trás")

    def test_editar_sem_mexer_na_foto_nao_a_recomprime(self):
        from unittest import mock

        lote = criar_lote(self.no_ar, nome="Caneca fictícia")
        c = self._equipe("preparacao", "prep_edita")
        with mock.patch.object(views, "preparar_foto") as preparar:
            c.post("/preparacao/itens/%d/editar/" % lote.pk, {
                "nome": "Caneca fictícia azul", "lance_inicial": "10", "peso_kg": "350",
                "altura_cm": "10", "largura_cm": "10", "profundidade_cm": "10",
            })
        lote.refresh_from_db()
        self.assertEqual(lote.nome, "Caneca fictícia azul")
        preparar.assert_not_called()


class SegundaRevisaoTests(TestCase):
    """A segunda conferência geral de 24/09: privacidade do telefone, dinheiro
    na mão de quem pode, "pago" falso, lotação por script, comando de demo,
    freio de login, fotos e os menores."""

    def setUp(self):
        from unittest import mock

        servicos.limpar_limites()
        equipe.limpar_tentativas()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia Souza")
        cfg = ConfigLeilao.get_solo()
        cfg.access_token_teste = "TEST-token-ficticio"
        cfg.save()
        self.n = 0

        def criar_pix_falso(cfg, *, referencia, valor, **_):
            self.n += 1
            return {"ok": True, "mp_payment_id": "mp-%d" % self.n, "status": "pendente",
                    "qr_code": "pix-%s" % referencia, "qr_code_base64": "", "ticket_url": "", "raw": {}}

        for alvo, efeito in (("criar_pix", criar_pix_falso),
                             ("consultar_pagamento", lambda cfg, pid: {"ok": True, "status": "pendente"})):
            p = mock.patch.object(servicos.mercadopago, alvo, side_effect=efeito)
            p.start()
            self.addCleanup(p.stop)

    def _arrematar(self, nome, valor, pessoa=None):
        lote = criar_lote(self.leilao, nome=nome, ordem=self.leilao.lotes.count() + 1,
                          lance_inicial=Decimal(valor))
        servicos.limpar_limites()
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa or self.ana)
        lote.refresh_from_db()
        return servicos.fechar_lote(lote, motivo="locutor")

    def _equipe(self, papel, login):
        User = get_user_model()
        u = User.objects.create_user(login, password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name=papel)[0])
        c = Client()
        c.login(username=login, password="segredo-ficticio")
        return c

    def _sessao(self, pessoa):
        c = Client()
        s = c.session
        s[CHAVE_SESSAO] = pessoa.token
        s.save()
        return c

    # --- 1. O telefone não sai do código da pessoa ------------------------
    def test_a_chave_nao_e_o_hash_puro_do_telefone(self):
        import hashlib

        tel = self.ana.telefone_normalizado
        self.assertNotIn(hashlib.sha256(tel.encode()).hexdigest()[:12], self.ana.chave_pessoa)

    def test_a_chave_depende_do_segredo_do_servidor(self):
        from django.test import override_settings

        antes = self.ana.chave_pessoa
        with override_settings(SECRET_KEY="outro-segredo-ficticio"):
            self.assertNotEqual(self.ana.chave_pessoa, antes)

    def test_a_chave_continua_reconhecendo_a_mesma_pessoa(self):
        outro_aparelho = criar_pessoa("Ana Fictícia Souza", whatsapp=self.ana.whatsapp)
        self.assertEqual(outro_aparelho.chave_pessoa, self.ana.chave_pessoa)

    # --- 2. Mercado Pago só com o Diretor ---------------------------------
    def test_a_preparacao_nao_abre_a_config_do_mercado_pago(self):
        r = self._equipe("preparacao", "prep_mp").get("/preparacao/config/")
        self.assertEqual(r.status_code, 302)

    def test_o_diretor_abre_a_config(self):
        r = self._equipe("diretor", "dir_mp").get("/preparacao/config/")
        self.assertEqual(r.status_code, 200)

    # --- 3. "Pagamento confirmado" só quando a conta fecha ----------------
    def test_pix_antigo_aprovado_nao_confirma_a_conta_nova(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        p1 = servicos.cobranca_do_participante(self.ana)
        servicos._aplicar_retorno(p1, {"status": "aprovado"})
        a.refresh_from_db()
        self.assertEqual(a.status, "pago")
        self._arrematar("Quadro fictício", "30.00")
        servicos.cobranca_do_participante(self.ana)
        d = self._sessao(self.ana).get("/conta/conferir/").json()
        self.assertFalse(d["pago"], "disse 'pago' com o item novo em aberto")
        self.assertEqual(d["quantos_abertos"], 1)

    # --- 5. Estado publicado é sempre o do leilão no ar -------------------
    def test_liberar_em_outro_leilao_nao_apaga_o_pregao(self):
        from unittest import mock

        rascunho = criar_leilao(nome="Leilão fictício 2", status="rascunho")
        with mock.patch.object(servicos.HUB, "publicar") as publicar:
            servicos.liberar_pagamentos(rascunho, True)
        self.assertTrue(publicar.call_args[0][1]["ativo"])

    # --- 6. Referência do Pix nunca repete --------------------------------
    def test_refazer_no_mesmo_instante_nao_repete_a_referencia(self):
        from unittest import mock

        self._arrematar("Cesta fictícia", "50.00")
        fixo = timezone.now()
        with mock.patch.object(servicos.timezone, "now", return_value=fixo):
            p1 = servicos.cobranca_do_participante(self.ana, refazer=True)
            p2 = servicos.cobranca_do_participante(self.ana, refazer=True)
        self.assertNotEqual(p1.referencia, p2.referencia)

    # --- 9. Stream: só quem passou pela porta, e com teto por pessoa -----
    def test_stream_sem_cadastro_e_recusado(self):
        self.assertEqual(Client().get("/stream/").status_code, 403)

    def test_equipe_1_sem_login_nao_vale(self):
        self.assertEqual(Client().get("/stream/?equipe=1").status_code, 403)

    def test_muitas_telas_da_mesma_pessoa_sao_recusadas(self):
        try:
            for _ in range(6):
                servicos.HUB.assinar(publico=True, nome="Ana", dono=self.ana.pk)
            r = self._sessao(self.ana).get("/stream/")
            self.assertEqual(r.status_code, 429)
        finally:
            servicos.HUB._assinantes.clear()

    def test_a_equipe_nao_entra_no_teto(self):
        from django.test import override_settings

        c = self._equipe("locutor", "loc_teto")
        try:
            servicos.HUB.assinar(publico=True, nome="Ana", dono=self.ana.pk)
            with override_settings(LEILAO_MAX_CONEXOES=1):
                r = c.get("/stream/?equipe=1")
                # Sem `r.close()`: fechar a resposta em streaming dispara o
                # `request_finished`, que fecha a conexão do banco de teste
                # para os testes seguintes. O status já diz o que importa.
                self.assertEqual(r.status_code, 200)
        finally:
            servicos.HUB._assinantes.clear()

    def test_a_contagem_do_hub_percorre_uma_copia(self):
        hub = Path(settings.BASE_DIR, "leilao", "hub.py").read_text(encoding="utf-8")
        self.assertIn("list(self._assinantes.values())", hub)
        self.assertNotIn("in self._assinantes.values():", hub)

    # --- 8. Comando de demonstração ---------------------------------------
    def test_leilao_demo_se_recusa_fora_do_desenvolvimento(self):
        from django.core.management import CommandError, call_command

        with self.assertRaises(CommandError):
            call_command("leilao_demo")
        self.leilao.refresh_from_db()
        self.assertEqual(self.leilao.status, "ao_vivo")

    # --- Freio de login ---------------------------------------------------
    def _login(self, c, usuario, senha):
        return c.post("/equipe/entrar/", {"usuario": usuario, "senha": senha})

    def test_acertar_a_propria_senha_nao_zera_o_freio_dos_outros(self):
        User = get_user_model()
        u = User.objects.create_user("joao_ficticio", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="caixa")[0])
        c = Client()
        for i in range(10):
            self._login(c, "maria_ficticia", "1234")
            if i == 5:
                self._login(Client(), "joao_ficticio", "segredo-ficticio")   # acerto no meio
        self.assertTrue(equipe.login_barrado("127.0.0.1|maria_ficticia"))

    def test_erros_de_um_nao_trancam_o_outro_no_mesmo_wifi(self):
        User = get_user_model()
        u = User.objects.create_user("joao_ficticio", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="caixa")[0])
        for _ in range(10):
            self._login(Client(), "maria_ficticia", "errada")
        r = self._login(Client(), "joao_ficticio", "segredo-ficticio")
        self.assertEqual(r.status_code, 302, "o Wi-Fi do evento trancou a equipe inteira")

    # --- Menores ------------------------------------------------------------
    def test_nao_se_exclui_item_em_pregao(self):
        lote = criar_lote(self.leilao, nome="Bolo fictício")
        servicos.abrir_lote(lote)
        self._equipe("preparacao", "prep_exc").post("/preparacao/itens/%d/excluir/" % lote.pk)
        self.assertTrue(Lote.objects.filter(pk=lote.pk).exists())

    def test_leilao_nao_volta_a_rascunho(self):
        c = self._equipe("preparacao", "prep_rasc")
        r = c.post("/preparacao/%d/status/" % self.leilao.pk, {"status": "rascunho"})
        self.assertEqual(r.status_code, 404)

    def test_item_sem_lance_pode_ser_aberto_de_novo(self):
        lote = criar_lote(self.leilao, nome="Bolo fictício")
        servicos.abrir_lote(lote)
        servicos.fechar_lote(lote, motivo="locutor")
        lote.refresh_from_db()
        self.assertEqual(lote.status, "sem_lance")
        c = self._equipe("locutor", "loc_sem")
        r = c.post("/equipe/acao/", json.dumps({"acao": "abrir", "lote": lote.pk}),
                   content_type="application/json")
        self.assertTrue(r.json()["ok"], r.json())

    def test_foto_ganha_nome_sorteado_e_o_original_sai(self):
        from io import BytesIO

        from django.core.files.base import ContentFile
        from PIL import Image

        from .imagens import preparar_foto

        buf = BytesIO()
        Image.new("RGB", (80, 60), (10, 120, 200)).save(buf, format="JPEG")
        lote = criar_lote(self.leilao, nome="Caneca fictícia")
        lote.foto.save("original-do-celular.jpg", ContentFile(buf.getvalue()), save=True)
        original = lote.foto.name
        self.assertTrue(preparar_foto(lote))
        lote.refresh_from_db()
        self.assertNotRegex(lote.foto.name, r"lote-%d\.jpg$" % lote.pk)
        self.assertRegex(lote.foto.name, r"lote-%d-[0-9a-f]{12}\.jpg$" % lote.pk)
        self.assertFalse(lote.foto.storage.exists(original), "o original (com EXIF) ficou no disco")
        for campo in (lote.foto, lote.foto_mini):
            campo.storage.delete(campo.name)

    def test_foto_com_pixels_demais_e_recusada(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("1", (9000, 9000)).save(buf, format="PNG")     # 81 Mpx, poucos KB
        f = forms.LoteForm(
            data={"nome": "Quadro fictício", "lance_inicial": "10", "peso_kg": "350",
                  "altura_cm": "10", "largura_cm": "10", "profundidade_cm": "10"},
            files={"foto": SimpleUploadedFile("g.png", buf.getvalue(), "image/png")},
        )
        self.assertFalse(f.is_valid())
        self.assertIn("grande demais", str(f.errors.get("foto")))

    def test_estorno_de_quem_pagou_em_dobro_nao_volta_a_divida(self):
        a = self._arrematar("Cesta fictícia", "50.00")
        p1 = servicos.cobranca_do_participante(self.ana)
        p2 = servicos.cobranca_do_participante(self.ana, refazer=True)
        servicos._aplicar_retorno(p1, {"status": "aprovado"})
        a.refresh_from_db()
        a.pagamento = p1
        a.save(update_fields=["pagamento"])
        with self.assertLogs("leilao.servicos", level="ERROR"):
            servicos._aplicar_retorno(p2, {"status": "aprovado"})      # pagou em dobro
        servicos._aplicar_retorno(p1, {"status": "estornado"})
        a.refresh_from_db()
        self.assertEqual(a.status, "pago", "o segundo pagamento continua de pé")
        self.assertEqual(a.pagamento_id, p2.pk)

    def test_o_qr_aberto_se_refaz_quando_um_item_e_quitado(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(encoding="utf-8")
        trecho = js[js.index('addEventListener("pagamento"'):]
        trecho = trecho[: trecho.index("});")]
        self.assertIn("if (arremateAberto) abrirQr();", trecho)
        gaveta = js[js.index("function fecharGaveta"):]
        gaveta = gaveta[: gaveta.index("\n    }\n")]
        self.assertIn('$("modalQr").hidden', gaveta)



class VozMudoEFichaTests(TestCase):
    """Voz ao vivo (mudo, queda do locutor, "a voz voltou") e a ficha completa
    da pessoa no caixa — pedidos do clube em 24/09.

    O comportamento do áudio em si foi medido num laboratório com o MediaMTX
    da mesma versão da produção e dois Chrome (locutor com microfone simulado
    e ouvinte): mudo sem queda de conexão e volta imediata; parar e voltar em
    0,7 s com o aviso (4,9 s sem ele); queda do servidor percebida pelo locutor
    e religada. Aqui ficam as guardas de estrutura.
    """

    JS = Path(settings.BASE_DIR, "static", "leilao", "js")

    def _js(self, nome):
        txt = (self.JS / nome).read_text(encoding="utf-8")
        txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
        return re.sub(r"//[^\n]*", " ", txt)

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()

    def _locutor(self):
        User = get_user_model()
        u = User.objects.create_user("loc_voz", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="locutor")[0])
        c = Client()
        c.login(username="loc_voz", password="segredo-ficticio")
        return c

    # --- Servidor ---------------------------------------------------------
    def test_a_voz_voltou_e_avisada_a_sala(self):
        from unittest import mock

        with mock.patch.object(views.HUB, "publicar") as publicar:
            r = self._locutor().post("/equipe/acao/", json.dumps({"acao": "voz", "no_ar": True,
                                                                   "leilao": self.leilao.pk}),
                                     content_type="application/json")
        self.assertTrue(r.json()["ok"])
        publicar.assert_called_once_with("voz", {"no_ar": True})
        self.assertNotIn("msg", r.json(), "o aviso da voz não pode virar toast na mesa")

    def test_voz_de_leilao_fora_do_ar_nao_avisa_ninguem(self):
        from unittest import mock

        rascunho = criar_leilao(nome="Leilão fictício 2", status="rascunho")
        with mock.patch.object(views.HUB, "publicar") as publicar:
            self._locutor().post("/equipe/acao/", json.dumps({"acao": "voz", "no_ar": True,
                                                               "leilao": rascunho.pk}),
                                 content_type="application/json")
        publicar.assert_not_called()

    def test_so_o_locutor_avisa_a_voz(self):
        self.assertEqual(views.ACOES_AREAS["voz"], ("locutor",))

    # --- Transmissor (locutor) --------------------------------------------
    def test_o_mudo_desliga_a_faixa_sem_derrubar_a_transmissao(self):
        js = self._js("audio_falar.js")
        self.assertIn("t.enabled = !mudoAgora", js)
        mudo = js[js.index("mudo: function"):]
        mudo = mudo[: mudo.index("},")]
        self.assertNotIn("parar(", mudo, "mudo não pode parar a transmissão")
        self.assertNotIn("close(", mudo)

    def test_a_queda_do_locutor_e_percebida(self):
        js = self._js("audio_falar.js")
        self.assertIn('s === "failed"', js)
        self.assertIn('s === "disconnected"', js)
        self.assertIn("pc !== conexao || !rodando", js, "o close() do parar não é queda")

    def test_a_mesa_religa_sozinha_e_respeita_o_parar(self):
        js = self._js("locutor.js")
        self.assertIn("window.AudioFalar.aoCair(", js)
        self.assertIn("function religarVoz", js)
        self.assertIn("if (ok && !querNoAr)", js, "Parar durante a religação ligaria a voz de novo")
        self.assertIn('acao({ acao: "voz", no_ar: true })', js)

    def test_a_mesa_tem_o_botao_de_mudo(self):
        html = Path(settings.BASE_DIR, "templates", "leilao", "locutor.html").read_text(encoding="utf-8")
        self.assertIn('id="btnMudo"', html)

    def test_o_mudo_fica_sempre_a_vista_ao_lado_do_transmitir(self):
        """Pedido de 26/09: escondido até a transmissão começar, o locutor
        achava que não existia e parava a transmissão para pausar."""
        html = Path(settings.BASE_DIR, "templates", "leilao", "locutor.html").read_text(encoding="utf-8")
        botao = re.search(r'<button[^>]*id="btnMudo"[^>]*>', html).group(0)
        self.assertNotIn("hidden", botao)
        bloco = html[html.index('<div class="micro-botoes">'):]
        bloco = bloco[: bloco.index("</div>")]
        self.assertIn('id="btnMicrofone"', bloco)
        self.assertIn('id="btnMudo"', bloco)

    def test_o_mudo_e_independente_do_transmitir(self):
        js = self._js("locutor.js")
        self.assertNotIn("btnMudo.hidden", js, "o mudo não pode sumir")
        clique = js[js.index("btnMudo.addEventListener"):]
        clique = clique[: clique.index("});")]
        self.assertNotIn("iniciar(", clique, "mudo não liga a transmissão")
        self.assertNotIn("parar(", clique, "mudo não derruba a transmissão")
        self.assertNotIn("mudo(false)", js[js.index("btnMic.addEventListener"):js.index("btnMudo && window")],
                      "parar a transmissão não pode soltar o mudo sozinho")

    # --- Ouvinte ----------------------------------------------------------
    def test_o_ouvinte_reconecta_ja_quando_a_voz_volta(self):
        js = self._js("audio_ouvir.js")
        volta = js[js.index("vozVoltou: function"):]
        volta = volta[: volta.index("\n        }")]
        self.assertIn("if (parado) return;", volta, "quem desligou o som não é religado")
        self.assertIn("tentativas = 0", volta)
        self.assertIn("conectar()", volta)

    def test_a_tentativa_agendada_e_cancelada_ao_reconectar(self):
        js = self._js("audio_ouvir.js")
        conectar = js[js.index("async function conectar"):]
        conectar = conectar[: conectar.index("desligarConexao();")]
        self.assertIn("clearTimeout(relogioReligar)", conectar, "duas conexões seguidas")

    def test_os_celulares_se_espalham_ao_voltar(self):
        js = self._js("leilao.js")
        trecho = js[js.index('addEventListener("voz"'):]
        trecho = trecho[: trecho.index("});")]
        self.assertIn("Math.random() * 4000", trecho)
        self.assertIn("!somLigado", trecho)

    # --- Ficha da pessoa no caixa -----------------------------------------
    def test_o_caixa_mostra_todos_os_dados_da_pessoa(self):
        pessoa = criar_pessoa("Ana Fictícia Souza", complemento="Casa 2 (fictícia)")
        lote = criar_lote(self.leilao)
        servicos.abrir_lote(lote)
        lote.refresh_from_db()
        servicos.dar_lance(lote.id, pessoa)
        lote.refresh_from_db()
        servicos.fechar_lote(lote, motivo="locutor")
        User = get_user_model()
        u = User.objects.create_user("caixa_ficha", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="caixa")[0])
        c = Client()
        c.login(username="caixa_ficha", password="segredo-ficticio")
        html = c.get("/caixa/%d/" % self.leilao.pk).content.decode()
        ficha = html[html.index('id="conta-detalhe-%d"' % pessoa.pk):]
        ficha = ficha[: ficha.index("conta-resumo")]
        for dado in ("Ana Fictícia Souza", pessoa.whatsapp, "Rua Fictícia", "Casa 2 (fictícia)",
                     "Centro", "Cidade Exemplo / SP", "00000-000", "Copiar dados", "Abrir no mapa"):
            self.assertIn(dado, ficha, dado)

    def test_a_ficha_de_texto_leva_endereco_e_escapa_html(self):
        pessoa = criar_pessoa("Ana <b>Fictícia</b>", complemento="Fundos")
        texto = pessoa.ficha_texto
        self.assertIn("Rua Fictícia 1 — Fundos", texto)
        self.assertIn("CEP: 00000-000", texto)
        from django.template import Context, Template

        saida = Template("{{ p.ficha_texto }}").render(Context({"p": pessoa}))
        self.assertNotIn("<b>", saida, "a ficha vai numa <textarea>: tem de sair escapada")

    def test_o_link_do_mapa_codifica_o_endereco(self):
        pessoa = criar_pessoa(logradouro="Rua & Travessa #1")
        self.assertIn("query=", pessoa.mapa_link)
        self.assertNotIn(" ", pessoa.mapa_link)
        self.assertNotIn("#", pessoa.mapa_link.split("query=")[1])
        self.assertEqual(criar_pessoa(logradouro="").mapa_link, "")

    # --- Teste de carga ---------------------------------------------------
    def test_a_carga_passa_pela_porta(self):
        from leilao.management.commands.leilao_carga import Ouvinte

        o = Ouvinte("http://exemplo.invalid", threading.Event(), [], cookie="leilao_sessionid=x")
        self.assertEqual(o.cookie, "leilao_sessionid=x")
        cmd = Path(settings.BASE_DIR, "leilao", "management", "commands", "leilao_carga.py").read_text(encoding="utf-8")
        self.assertIn('"--cadastrar"', cmd)
        self.assertIn('headers={"Referer": url + "/entrar/"}', cmd)


class VozCorridasTests(TestCase):
    """As corridas da voz achadas na revisão (e medidas no laboratório: duas
    ligações ao mesmo tempo terminam com UMA viva; parar e voltar em menos de
    1 s volta em 2 s)."""

    def _js(self, nome):
        txt = Path(settings.BASE_DIR, "static", "leilao", "js", nome).read_text(encoding="utf-8")
        txt = re.sub(r"/\*.*?\*/", " ", txt, flags=re.S)
        return re.sub(r"//[^\n]*", " ", txt)

    def test_cada_ligacao_da_voz_tem_a_sua_vez(self):
        js = self._js("audio_falar.js")
        iniciar = js[js.index("async function iniciar"):js.index("function caiu")]
        self.assertIn("var minha = ++geracao;", iniciar)
        self.assertGreaterEqual(iniciar.count("if (superada()) return false;"), 5)
        self.assertIn("if (!superada()) parar();", iniciar, "o catch derrubava a ligação da outra chamada")
        self.assertIn("geracao++", js[js.index("function parar"):])

    def test_reconexao_substituida_nao_agenda_outra(self):
        js = self._js("audio_ouvir.js")
        self.assertIn("const minha = ++geracaoConexao;", js)
        self.assertIn("if (minha !== geracaoConexao) return false;", js)

    def test_a_voz_voltou_confere_os_bytes_antes_de_confiar(self):
        js = self._js("audio_ouvir.js")
        volta = js[js.index("vozVoltou: function"):]
        self.assertIn("bytesDe(viva)", volta)
        self.assertIn("if (depois > antes) { tocar(); return; }", volta)

    def test_copiar_so_diz_copiado_quando_copiou(self):
        js = self._js("caixa.js")
        self.assertIn('ok = document.execCommand("copy")', js)
        self.assertIn("if (ok) pronto();", js)

    def test_a_carga_exige_confirmacao_para_cadastrar(self):
        from django.core.management import CommandError, call_command

        with self.assertRaises(CommandError):
            call_command("leilao_carga", url="http://exemplo.invalid", cadastrar=1, ouvintes=0,
                         stdout=open(os.devnull, "w"))


class DouLheTests(TestCase):
    """O martelo em três tempos: dou-lhe uma, dou-lhe duas, VENDIDO (26/09).

    Os dois primeiros são ANÚNCIO para a sala — vão no broadcast e não mexem
    em nada no banco. Quem fecha continua sendo o VENDIDO: não há cronômetro, e
    o "dou-lhe" não pode virar um.
    """

    def setUp(self):
        from unittest import mock  # noqa: F401 — usado nos testes

        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.c = self._cliente("locutor", "doulhe_loc")

    def _cliente(self, area, nome):
        User = get_user_model()
        u = User.objects.create_user(nome, password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name=area)[0])
        c = Client()
        c.login(username=nome, password="segredo-ficticio")
        return c

    def _abrir_com_lance(self):
        servicos.abrir_lote(self.lote)
        servicos.dar_lance(self.lote.id, criar_pessoa())

    def _dou_lhe(self, c=None, **extra):
        corpo = {"acao": "dou_lhe", "leilao": self.leilao.pk}
        corpo.update(extra)
        return (c or self.c).post("/equipe/acao/", data=json.dumps(corpo), content_type="application/json")

    def test_anuncia_para_a_sala_pelo_broadcast(self):
        from unittest import mock

        self._abrir_com_lance()
        for vez in (1, 2):
            with self.subTest(vez=vez), mock.patch.object(servicos.HUB, "publicar") as publicar:
                r = self._dou_lhe(vez=vez, lote=self.lote.pk)
                self.assertEqual(r.status_code, 200, r.content)
                tipo, dados = publicar.call_args[0]
                self.assertEqual(tipo, "dou_lhe")
                self.assertEqual(dados["vez"], vez)
                self.assertEqual(dados["lote"], self.lote.pk)
                self.assertNotIn("msg", r.json(), "o anúncio não vira toast duplo na mesa")

    def test_nao_fecha_nada_nem_mexe_no_banco(self):
        self._abrir_com_lance()
        self._dou_lhe(vez=2, lote=self.lote.pk)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")
        self.assertFalse(Arremate.objects.exists())

    def test_sem_lance_nao_ha_o_que_anunciar(self):
        from unittest import mock

        servicos.abrir_lote(self.lote)
        with mock.patch.object(servicos.HUB, "publicar") as publicar:
            r = self._dou_lhe(vez=1, lote=self.lote.pk)
        self.assertEqual(r.status_code, 409)
        publicar.assert_not_called()

    def test_item_que_ja_trocou_e_recusado(self):
        """O "dou-lhe duas" do item anterior não cai em cima do item novo."""
        from unittest import mock

        outro = criar_lote(self.leilao, nome="Outro item fictício", ordem=2)
        self._abrir_com_lance()
        with mock.patch.object(servicos.HUB, "publicar") as publicar:
            r = self._dou_lhe(vez=2, lote=outro.pk)
        self.assertEqual(r.status_code, 409)
        publicar.assert_not_called()

    def test_vez_fora_de_1_e_2_e_recusada(self):
        self._abrir_com_lance()
        for vez in (0, 3, "tres", None, -1):
            with self.subTest(vez=vez):
                self.assertEqual(self._dou_lhe(vez=vez, lote=self.lote.pk).status_code, 409)

    def test_leilao_fora_do_ar_nao_anuncia(self):
        self._abrir_com_lance()
        Leilao.objects.filter(pk=self.leilao.pk).update(status="encerrado")
        self.assertEqual(self._dou_lhe(vez=1, lote=self.lote.pk).status_code, 409)

    def test_so_o_locutor_anuncia(self):
        self._abrir_com_lance()
        r = self._dou_lhe(self._cliente("caixa", "doulhe_caixa"), vez=1, lote=self.lote.pk)
        self.assertEqual(r.status_code, 403)

    def test_a_mesa_tem_os_tres_botoes_na_ordem(self):
        html = self.c.get("/locutor/%d/" % self.leilao.pk).content.decode()
        bloco = html[html.index('class="mesa-botoes martelo"'):]
        bloco = bloco[: bloco.index("</div>")]
        ordem = re.findall(r'data-acao="([a-z_]+)"(?: data-vez="(\d)")?', bloco)
        self.assertEqual(ordem, [("dou_lhe", "1"), ("dou_lhe", "2"), ("fechar", "")])

    # --- A escada: um só depois do outro, sem confirmação (26/09) --------
    def _fechar(self):
        return self.c.post("/equipe/acao/", data=json.dumps({"acao": "fechar", "leilao": self.leilao.pk}),
                           content_type="application/json")

    def test_duas_antes_do_uma_e_recusado(self):
        self._abrir_com_lance()
        self.assertEqual(self._dou_lhe(vez=2, lote=self.lote.pk).status_code, 409)

    def test_vendido_antes_do_duas_e_recusado_no_servidor(self):
        """A escada vale na view, não só no botão apagado."""
        self._abrir_com_lance()
        self.assertEqual(self._fechar().status_code, 409)
        self._dou_lhe(vez=1, lote=self.lote.pk)
        self.assertEqual(self._fechar().status_code, 409)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")

    def test_uma_duas_e_vendido_fecha(self):
        self._abrir_com_lance()
        self.assertEqual(self._dou_lhe(vez=1, lote=self.lote.pk).status_code, 200)
        self.assertEqual(self._dou_lhe(vez=2, lote=self.lote.pk).status_code, 200)
        self.assertEqual(self._fechar().status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")

    def test_lance_novo_recomeca_a_escada(self):
        self._abrir_com_lance()
        self._dou_lhe(vez=1, lote=self.lote.pk)
        self._dou_lhe(vez=2, lote=self.lote.pk)
        servicos.limpar_limites()
        servicos.dar_lance(self.lote.id, criar_pessoa("Outra Pessoa Fictícia"))
        self.assertEqual(self._fechar().status_code, 409, "o duas de antes do lance não vale mais")
        self.assertEqual(self._dou_lhe(vez=2, lote=self.lote.pk).status_code, 409)

    def test_item_sem_lance_encerra_direto(self):
        """Sem lance não há "dou-lhe" — o VENDIDO não pode ficar preso."""
        servicos.abrir_lote(self.lote)
        self.assertEqual(self._fechar().status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "sem_lance")

    def test_a_mesa_recarregada_recebe_o_degrau(self):
        self._abrir_com_lance()
        self._dou_lhe(vez=1, lote=self.lote.pk)
        d = self.c.get(f"/locutor/dados/?leilao={self.leilao.pk}").json()
        self.assertEqual(d["martelo"], 1)

    def test_o_martelo_nao_pede_mais_confirmacao(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "locutor.js").read_text(encoding="utf-8")
        self.assertNotIn("Bater o martelo e fechar este item?", js)
        pintar = js[js.index("function pintarMartelo"):]
        pintar = pintar[: pintar.index("\n    }\n")]
        self.assertIn("vale < vez - 1", pintar, "cada dou-lhe só depois do anterior")
        self.assertIn("comLance && vale < 2", pintar, "o VENDIDO só depois do duas")
        lance = js[js.index('fonte.addEventListener("lance"'):]
        lance = lance[: lance.index("});")]
        self.assertIn("martelo = { lote: null, valor: null, vez: 0 }", lance, "lance novo tem de zerar o martelo")

class DouLheNaTelaDoPublicoTests(TestCase):
    """O efeito do "dou-lhe" na tela de quem disputa (26/09).

    Mais intenso no "duas" que no "uma", nas DUAS telas do pregão, sem pegar
    toque e sem pedir nada ao servidor.
    """

    TELAS = ("leilao_show.html", "leilao.html")

    @staticmethod
    def _ler(*partes):
        return Path(settings.BASE_DIR, *partes).read_text(encoding="utf-8")

    @staticmethod
    def _sem_comentarios(js):
        limpo = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
        return re.sub(r"//[^\n]*", " ", limpo)

    def test_as_duas_telas_tem_o_carimbo_dentro_da_foto(self):
        for tpl in self.TELAS:
            with self.subTest(tpl=tpl):
                html = self._ler("templates", "leilao", tpl)
                foto = html[html.index('id="loteFoto"'):]
                foto = foto[: foto.index('id="loteNome"')]
                self.assertIn('id="douLhe"', foto, "o carimbo tem de morar dentro da foto")

    def test_o_efeito_carrega_antes_do_motor_nas_duas(self):
        for tpl in self.TELAS:
            with self.subTest(tpl=tpl):
                html = self._ler("templates", "leilao", tpl)
                self.assertLess(html.index("leilao/js/dou_lhe.js"), html.index("leilao/js/leilao.js"))

    def test_o_motor_ouve_o_anuncio_e_repassa(self):
        js = self._sem_comentarios(self._ler("static", "leilao", "js", "leilao.js"))
        trecho = js[js.index('fonte.addEventListener("dou_lhe"'):]
        trecho = trecho[: trecho.index("});")]
        self.assertIn("lote.id !== d.lote", trecho, "anúncio de item que trocou não vale")
        self.assertIn('emitir("dou_lhe"', trecho)
        self.assertIn("SomLeilao.douLhe(d.vez)", trecho)

    def test_o_duas_e_mais_intenso_que_o_uma(self):
        css = self._ler("static", "leilao", "css", "leilao.css")
        self.assertIn(".dou-lhe-carimbo.vez-2", css)
        self.assertIn("body.dou-lhe-2 .dou-lhe-vinheta.duas", css)
        self.assertIn("body.dou-lhe-2 #btnLance", css)
        self.assertIn("treme-forte", css)
        js = self._ler("static", "leilao", "js", "dou_lhe.js")
        self.assertIn('vez === 2 ? "treme-forte" : "treme"', js)

    def test_o_efeito_nao_pega_toque(self):
        css = self._ler("static", "leilao", "css", "leilao.css")
        for seletor in (".dou-lhe-carimbo {", ".dou-lhe-vinheta {"):
            bloco = css[css.index(seletor):]
            bloco = bloco[: bloco.index("}")]
            self.assertIn("pointer-events: none", bloco, seletor)

    def test_acontecimento_no_pregao_apaga_o_dou_lhe(self):
        js = self._ler("static", "leilao", "js", "dou_lhe.js")
        for aviso in ("leilao:lance", "leilao:lote_aberto", "leilao:vendido"):
            self.assertIn(f'"{aviso}"', js)

    def test_o_efeito_nao_fala_com_o_servidor(self):
        js = self._sem_comentarios(self._ler("static", "leilao", "js", "dou_lhe.js"))
        self.assertNotIn("fetch(", js)
        self.assertNotIn("XMLHttpRequest", js)

    def test_o_som_do_martelo_e_sintetizado(self):
        js = self._ler("static", "leilao", "js", "som.js")
        trecho = js[js.index("douLhe: function"):]
        trecho = trecho[: trecho.index("        },")]
        self.assertNotIn("tocarArquivo", trecho, "nada de arquivo novo para baixar")

    def test_movimento_reduzido_desliga_a_tremedeira(self):
        css = self._ler("static", "leilao", "css", "leilao.css")
        # O bloco de movimento reduzido DO DOU-LHE (não o último do arquivo:
        # outros blocos entram depois dele).
        inicio = css.index("@media (prefers-reduced-motion: reduce)", css.index(".dou-lhe-carimbo {"))
        reduzido = css[inicio: css.index("\n}\n", inicio)]
        self.assertIn("body.treme-forte", reduzido)


class EmocaoDoLanceNaMesaTests(TestCase):
    """A cada lance, a mesa do locutor sente o movimento (26/09).

    Borda do card piscando, valor pulando, "+R$ 5" e moedas saindo da caixa do
    valor, selo de ritmo com lances rápidos — tudo DENTRO do card, sem pegar
    toque, e sem som (o microfone aberto devolveria o som para a sala).
    """

    def _ler(self, *partes):
        return Path(settings.BASE_DIR, *partes).read_text(encoding="utf-8")

    def test_o_lance_dispara_a_festa_na_mesa(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        lance = js[js.index('fonte.addEventListener("lance"'):]
        lance = lance[: lance.index("});")]
        self.assertIn("festejarLance(d.lote)", lance)

    def test_as_moedas_ficam_presas_na_caixa_do_valor(self):
        html = self._ler("templates", "leilao", "locutor.html")
        caixa = html[html.index('class="numero numero-grande numero-valor-atual"'):]
        caixa = caixa[: caixa.index("</div>")]
        self.assertIn('id="mesaFx"', caixa)
        css = self._ler("static", "leilao", "css", "locutor.css")
        bloco = css[css.index(".mesa-fx {"):]
        bloco = bloco[: bloco.index("}")]
        self.assertIn("pointer-events: none", bloco)
        self.assertIn("overflow: hidden", bloco)

    def test_a_festa_tem_teto_e_nao_toca_som(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        festa = js[js.index("function festejarLance"):js.index("function esfriarMesa")]
        self.assertIn("Math.min(14", festa, "teto de moedas")
        self.assertNotIn("SomLeilao", festa, "som na mesa voltaria pela transmissão")

    def test_item_novo_e_martelo_esfriam_a_mesa(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        for evento in ('fonte.addEventListener("lote_aberto"', 'fonte.addEventListener("lote_vendido"'):
            trecho = js[js.index(evento):]
            trecho = trecho[: trecho.index("});")]
            self.assertIn("esfriarMesa()", trecho, evento)

    def test_o_tempo_do_martelo_aparece_no_card(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        pintar = js[js.index("function pintarMartelo"):]
        pintar = pintar[: pintar.index("\n    }\n")]
        self.assertIn('"martelo-2"', pintar)

    def test_movimento_reduzido_desliga(self):
        css = self._ler("static", "leilao", "css", "locutor.css")
        self.assertIn(".mesa-fx { display: none; }", css)


class DisputaDoItemNaMesaTests(TestCase):
    """"Lances deste item" por PESSOA, com os 4 que mais deram lance em cima (26/09)."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        servicos.abrir_lote(self.lote)
        User = get_user_model()
        u = User.objects.create_user("disputa_loc", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="locutor")[0])
        self.c = Client()
        self.c.login(username="disputa_loc", password="segredo-ficticio")
        self.p = {n: criar_pessoa(f"{n} Fictício") for n in ("Ana", "Beto", "Caio", "Duda", "Edu")}

    def _lances(self, *nomes):
        for n in nomes:
            servicos.limpar_limites()
            ok, msg, _ = servicos.dar_lance(self.lote.id, self.p[n])
            self.assertTrue(ok, msg)

    def _disputa(self):
        return self.c.get(f"/locutor/dados/?leilao={self.leilao.pk}").json()["disputa"]

    def test_uma_linha_por_pessoa_com_os_4_que_mais_deram_em_cima(self):
        self._lances("Ana", "Beto", "Ana", "Beto", "Caio", "Ana", "Duda", "Edu")
        d = self._disputa()
        nomes = [x["quem"] for x in d]
        curto = {n: p.nome_curto for n, p in self.p.items()}
        # Ana 3, Beto 2; entre os de 1 lance, quem foi mais alto: Edu, Duda.
        self.assertEqual(nomes, [curto["Ana"], curto["Beto"], curto["Edu"], curto["Duda"], curto["Caio"]])
        self.assertEqual([x["topo"] for x in d], [True, True, True, True, False])
        self.assertEqual([x["n"] for x in d], [3, 2, 1, 1, 1])

    def test_a_lista_e_completa(self):
        self._lances("Ana", "Beto", "Caio", "Duda", "Edu", "Ana")
        self.assertEqual(len(self._disputa()), 5, "ninguém que deu lance pode ficar de fora")

    def test_a_coroa_e_de_quem_esta_ganhando(self):
        self._lances("Ana", "Beto", "Ana")
        d = self._disputa()
        lideres = [x["quem"] for x in d if x["lider"]]
        self.assertEqual(lideres, [self.p["Ana"].nome_curto])

    def test_lance_cancelado_nao_conta(self):
        self._lances("Ana", "Beto")
        Lance.objects.filter(participante=self.p["Beto"]).update(cancelado=True)
        nomes = [x["quem"] for x in self._disputa()]
        self.assertEqual(nomes, [self.p["Ana"].nome_curto])

    def test_sem_item_em_pregao_a_lista_vem_vazia(self):
        self._lances("Ana")
        servicos.fechar_lote(Lote.objects.get(pk=self.lote.pk))
        self.assertEqual(self._disputa(), [])

    def test_a_disputa_nao_vai_para_o_broadcast(self):
        self._lances("Ana", "Beto")
        publico = json.dumps(est.estado_publico(self.leilao), default=str)
        self.assertNotIn('"disputa"', publico)

    def test_a_lista_da_mesa_tem_teto(self):
        css = Path(settings.BASE_DIR, "static", "leilao", "css", "locutor.css").read_text(encoding="utf-8")
        bloco = css[css.index(".disputa {"):]
        bloco = bloco[: bloco.index("}")]
        self.assertIn("max-height", bloco)
        self.assertIn("overflow-y: auto", bloco)


class GenteDaNoiteNaMesaTests(TestCase):
    """A linha da GENTE na mesa (26/09): top 5 arremates, quem está online sem
    lance, quem deu lance e não arrematou."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("gente_loc", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="locutor")[0])
        self.c = Client()
        self.c.login(username="gente_loc", password="segredo-ficticio")
        self.p = {n: criar_pessoa(f"{n} Fictício") for n in ("Ana", "Beto", "Caio", "Duda", "Edu", "Fabi")}
        self.ordem = itertools.count(1)

    def _vender(self, vencedor, *outros, valor_extra=0):
        """Abre um item, dá os lances (os `outros` antes) e bate o martelo."""
        lote = criar_lote(self.leilao, nome=f"Item fictício {next(self.ordem)}")
        servicos.abrir_lote(lote)
        for n in list(outros) + [vencedor]:
            servicos.limpar_limites()
            ok, msg, _ = servicos.dar_lance(lote.id, self.p[n])
            self.assertTrue(ok, msg)
        servicos.fechar_lote(Lote.objects.get(pk=lote.pk))
        return lote

    def _gente(self, online=()):
        from unittest import mock

        pks = {self.p[n].pk for n in online}
        with mock.patch.object(servicos.HUB, "donos_conectados", return_value=pks):
            return self.c.get(f"/locutor/dados/?leilao={self.leilao.pk}").json()["gente"]

    def test_top_5_pelo_total_arrematado(self):
        self._vender("Ana", "Beto")
        self._vender("Ana", "Caio")
        self._vender("Beto", "Duda")
        top = self._gente()["top"]
        self.assertEqual(top[0]["quem"], self.p["Ana"].nome_curto)
        self.assertEqual(top[0]["itens"], 2)
        self.assertEqual([t["quem"] for t in top], [self.p["Ana"].nome_curto, self.p["Beto"].nome_curto])

    def test_top_para_no_quinto(self):
        for n in ("Ana", "Beto", "Caio", "Duda", "Edu", "Fabi"):
            self._vender(n)
        self.assertEqual(len(self._gente()["top"]), 5)

    def test_arremate_cancelado_nao_entra_no_top(self):
        lote = self._vender("Ana")
        Arremate.objects.filter(lote=lote).update(status="cancelado")
        self.assertEqual(self._gente()["top"], [])

    def test_sem_lance_e_so_quem_esta_online_e_nao_deu_lance(self):
        self._vender("Ana", "Beto")
        g = self._gente(online=("Ana", "Caio", "Duda"))
        self.assertEqual({x["quem"] for x in g["sem_lance"]},
                         {self.p["Caio"].nome_curto, self.p["Duda"].nome_curto})
        self.assertEqual(g["online"], 3)

    def test_quem_deu_lance_e_nao_arrematou(self):
        self._vender("Ana", "Beto", "Caio")      # Beto e Caio tentaram
        self._vender("Caio", "Beto")             # Caio levou; Beto tentou de novo
        g = self._gente(online=("Beto",))
        sem = g["sem_arremate"]
        self.assertEqual([x["quem"] for x in sem], [self.p["Beto"].nome_curto])
        self.assertEqual(sem[0]["lances"], 2)
        self.assertTrue(sem[0]["online"])

    def test_a_gente_nao_vai_para_o_broadcast(self):
        self._vender("Ana", "Beto")
        publico = json.dumps(est.estado_publico(self.leilao), default=str)
        for chave in ('"gente"', '"sem_lance"', '"sem_arremate"'):
            self.assertNotIn(chave, publico)

    def test_o_hub_conta_so_telas_do_publico_com_cadastro(self):
        from .hub import Hub

        hub = Hub()
        hub.assinar(publico=True, nome="Ana", dono=1)
        hub.assinar(publico=True, nome="Ana", dono=1)     # 2ª aba da mesma pessoa
        hub.assinar(publico=True, nome=None, dono=None)   # ainda na porta
        hub.assinar(publico=False, nome="Equipe", dono=9)  # mesa/caixa
        self.assertEqual(hub.donos_conectados(), {1})

    def test_as_listas_tem_teto(self):
        css = Path(settings.BASE_DIR, "static", "leilao", "css", "locutor.css").read_text(encoding="utf-8")
        bloco = css[css.index(".gente-lista {"):]
        bloco = bloco[: bloco.index("}")]
        self.assertIn("max-height", bloco)
        self.assertIn("overflow-y: auto", bloco)


class FundoSemFaixaTests(TestCase):
    """O degradê do fundo não pode se repetir (26/09).

    Com a tela mais alta que a janela (a mesa de três linhas é), o degradê
    repetia a cada altura de janela e a borda da cópia aparecia como uma faixa
    clara atravessando os cards.
    """

    def test_os_fundos_com_degrade_nao_se_repetem(self):
        base = Path(settings.BASE_DIR, "static", "leilao", "css")
        for arquivo, seletor in (("locutor.css", "body.tela-locutor {"),
                                 ("leilao.css", "body.tela-palco {"),
                                 ("palco_show.css", "body.tela-show {")):
            with self.subTest(seletor=seletor):
                css = (base / arquivo).read_text(encoding="utf-8")
                bloco = css[css.index(seletor):]
                bloco = bloco[: bloco.index("\n}")]
                self.assertIn("radial-gradient", bloco)
                self.assertIn("background-repeat: no-repeat", bloco)


class RevisaoDaMesaNovaTests(TestCase):
    """Achados da revisão de 26/09 nas mudanças da mesa."""

    def _js(self, nome):
        return Path(settings.BASE_DIR, "static", "leilao", "js", nome).read_text(encoding="utf-8")

    def test_a_escada_da_mesa_e_amarrada_ao_valor(self):
        js = self._js("locutor.js")
        pintar = js[js.index("function pintarMartelo"):]
        pintar = pintar[: pintar.index("\n    }\n")]
        self.assertIn("martelo.valor === String(lote.valor_atual)", pintar)

    def test_resposta_atrasada_nao_rebaixa_o_degrau(self):
        """O fetch que saiu antes do clique no "dou-lhe" chegava depois do aviso
        do stream e zerava a escada: o "duas" apagava sozinho."""
        js = self._js("locutor.js")
        self.assertIn("Math.max(martelo.vez, d.martelo)", js)

    def test_o_tremor_nao_fica_preso(self):
        js = self._js("dou_lhe.js")
        self.assertIn('corpo.classList.remove("treme", "treme-forte")', js)

    def test_cada_lance_limpa_so_as_suas_moedas(self):
        js = self._js("locutor.js")
        festa = js[js.index("function festejarLance"):js.index("function esfriarMesa")]
        self.assertNotIn("while (fx.firstChild)", festa)
        self.assertIn("criadas.forEach", festa)


class RevisaoGeralLoteATests(TestCase):
    """Lote A da revisão geral de 26/09: dinheiro e segurança."""

    def setUp(self):
        from unittest import mock

        servicos.limpar_limites()
        equipe.limpar_tentativas()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia Souza")
        self.beto = criar_pessoa("Beto Fictício Lima")
        cfg = ConfigLeilao.get_solo()
        cfg.access_token_teste = "TEST-token-ficticio"
        cfg.save()
        self.gerados = []
        self.valor_devolvido = None

        def criar_pix_falso(cfg, *, referencia, valor, **_):
            self.gerados.append((referencia, valor))
            devolve = self.valor_devolvido if len(self.gerados) == 1 and self.valor_devolvido else valor
            return {"ok": True, "mp_payment_id": "mp-%d" % len(self.gerados), "status": "pendente",
                    "qr_code": "pix-%s" % referencia, "qr_code_base64": "", "ticket_url": "",
                    "raw": {"transaction_amount": float(devolve)}}

        p = mock.patch.object(servicos.mercadopago, "criar_pix", side_effect=criar_pix_falso)
        p.start()
        self.addCleanup(p.stop)

    def _usuario(self, nome, *, superuser=False, area="caixa"):
        User = get_user_model()
        u = User.objects.create_user(nome, password="segredo-ficticio")
        u.is_staff = True
        u.is_superuser = superuser
        u.save()
        u.groups.add(Group.objects.get_or_create(name=area)[0])
        return u

    def _arrematar(self, nome, inicial, pessoa=None):
        lote = criar_lote(self.leilao, nome=nome, ordem=self.leilao.lotes.count() + 1,
                          lance_inicial=Decimal(inicial))
        servicos.abrir_lote(lote)
        servicos.limpar_limites()
        servicos.dar_lance(lote.id, pessoa or self.ana)
        return servicos.fechar_lote(Lote.objects.get(pk=lote.pk), motivo="locutor")

    # --- 1. /admin/ ------------------------------------------------------
    def test_equipe_nao_entra_pelo_login_do_admin(self):
        self._usuario("voluntaria_ficticia")
        c = Client()
        c.post("/admin/login/", {"username": "voluntaria_ficticia", "password": "segredo-ficticio"})
        self.assertNotIn("_auth_user_id", c.session, "conta da equipe entrou pelo admin")

    def test_superusuario_entra_pelo_admin(self):
        self._usuario("admin_ficticio", superuser=True)
        c = Client()
        c.post("/admin/login/", {"username": "admin_ficticio", "password": "segredo-ficticio"})
        self.assertIn("_auth_user_id", c.session)

    def test_o_login_do_admin_tem_freio(self):
        self._usuario("admin_ficticio", superuser=True)
        c = Client()
        for _ in range(equipe.MAX_TENTATIVAS):
            c.post("/admin/login/", {"username": "admin_ficticio", "password": "errada"})
        c.post("/admin/login/", {"username": "admin_ficticio", "password": "segredo-ficticio"})
        self.assertNotIn("_auth_user_id", c.session, "o freio não segurou a varredura")

    # --- 2. Lance com tempo máximo ---------------------------------------
    def test_o_lance_tem_tempo_maximo_de_espera(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "leilao.js").read_text(encoding="utf-8")
        self.assertIn("new AbortController()", js)
        self.assertIn("valor_visto: pretendido }, 8000)", js)

    # --- 3. Baixa manual e depois o Pix ----------------------------------
    def test_pix_pago_depois_da_baixa_manual_gera_alerta(self):
        a = self._arrematar("Cesta fictícia", "30.00")
        pag = servicos.cobranca_do_participante(self.ana)
        a.refresh_from_db()
        servicos.marcar_pago(a, manual=True)
        with self.assertLogs("leilao.servicos", level="ERROR") as log:
            servicos._aplicar_retorno(pag, {"status": "aprovado", "valor": pag.valor_bruto})
        self.assertIn("conferir com a pessoa", "\n".join(log.output))

    # --- 4. Valor pago e valor antigo ------------------------------------
    def test_pagamento_a_menor_nao_quita(self):
        a = self._arrematar("Cesta fictícia", "30.00")
        pag = servicos.cobranca_do_participante(self.ana)
        with self.assertLogs("leilao.servicos", level="ERROR"):
            servicos._aplicar_retorno(pag, {"status": "aprovado", "valor": Decimal("10.00")})
        a.refresh_from_db()
        self.assertEqual(a.status, "aguardando")

    def test_pix_que_volta_com_valor_antigo_e_refeito(self):
        self._arrematar("Cesta fictícia", "30.00")
        self.valor_devolvido = Decimal("10.00")   # a chave repetida devolveu a cobrança velha
        pag = servicos.cobranca_do_participante(self.ana)
        self.assertEqual(len(self.gerados), 2, "tinha de pedir outra cobrança")
        self.assertNotEqual(self.gerados[0][0], self.gerados[1][0], "com referência nova")
        self.assertEqual(pag.valor_bruto, Decimal("30.00"))

    # --- 5. VENDIDO e abrir conferem a tela --------------------------------
    def _locutor(self):
        u = self._usuario("locutor_ficticio", area="locutor")
        c = Client()
        c.force_login(u)
        return c

    def _acao(self, c, **corpo):
        corpo.setdefault("leilao", self.leilao.pk)
        return c.post("/equipe/acao/", json.dumps(corpo), content_type="application/json")

    def test_vendido_recusa_se_entrou_lance_novo(self):
        c = self._locutor()
        lote = criar_lote(self.leilao, nome="Item fictício", lance_inicial=Decimal("20"))
        servicos.abrir_lote(lote)
        servicos.dar_lance(lote.id, self.ana)
        self._acao(c, acao="dou_lhe", vez=1, lote=lote.pk)
        self._acao(c, acao="dou_lhe", vez=2, lote=lote.pk)
        visto = str(Lote.objects.get(pk=lote.pk).valor_atual)
        servicos.limpar_limites()
        servicos.dar_lance(lote.id, self.beto)            # entrou depois do "duas"
        r = self._acao(c, acao="fechar", lote=lote.pk, valor=visto)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Lote.objects.get(pk=lote.pk).status, "aberto")

    def test_vendido_com_a_tela_certa_fecha(self):
        c = self._locutor()
        lote = criar_lote(self.leilao, nome="Item fictício", lance_inicial=Decimal("20"))
        servicos.abrir_lote(lote)
        servicos.dar_lance(lote.id, self.ana)
        self._acao(c, acao="dou_lhe", vez=1, lote=lote.pk)
        self._acao(c, acao="dou_lhe", vez=2, lote=lote.pk)
        visto = str(Lote.objects.get(pk=lote.pk).valor_atual)
        r = self._acao(c, acao="fechar", lote=lote.pk, valor=visto)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Lote.objects.get(pk=lote.pk).status, "vendido")

    def test_sem_lance_na_tela_nao_vende_item_que_ganhou_lance(self):
        c = self._locutor()
        lote = criar_lote(self.leilao, nome="Item fictício", lance_inicial=Decimal("20"))
        servicos.abrir_lote(lote)
        servicos.dar_lance(lote.id, self.ana)             # a mesa ainda via "sem lance"
        r = self._acao(c, acao="fechar", lote=lote.pk, valor="")
        self.assertEqual(r.status_code, 409)

    def test_vendido_atrasado_nao_fecha_o_item_seguinte(self):
        c = self._locutor()
        a = criar_lote(self.leilao, nome="Item A fictício")
        b = criar_lote(self.leilao, nome="Item B fictício", ordem=2)
        servicos.abrir_lote(a)
        servicos.abrir_lote(Lote.objects.get(pk=b.pk))    # outra aba abriu o B
        r = self._acao(c, acao="fechar", lote=a.pk, valor="")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Lote.objects.get(pk=b.pk).status, "aberto")

    def test_toque_duplo_em_abrir_nao_troca_o_item(self):
        c = self._locutor()
        criar_lote(self.leilao, nome="Item A fictício")
        criar_lote(self.leilao, nome="Item B fictício", ordem=2)
        r1 = self._acao(c, acao="abrir", atual=0)
        r2 = self._acao(c, acao="abrir", atual=0)         # o 2º toque ainda via "nenhum"
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 409)
        self.assertEqual(Leilao.objects.get(pk=self.leilao.pk).lote_atual.nome, "Item A fictício")

    def test_item_em_disputa_so_troca_com_forcar(self):
        c = self._locutor()
        a = criar_lote(self.leilao, nome="Item A fictício")
        criar_lote(self.leilao, nome="Item B fictício", ordem=2)
        servicos.abrir_lote(a)
        servicos.dar_lance(a.id, self.ana)
        self.assertEqual(self._acao(c, acao="abrir", atual=a.pk).status_code, 409)
        self.assertEqual(self._acao(c, acao="abrir", atual=a.pk, forcar=True).status_code, 200)

    # --- 16. Estorno de item doado de volta ------------------------------
    def test_estorno_de_item_devolvido_nao_volta_a_cobrar(self):
        a = self._arrematar("Cesta fictícia", "30.00")
        pag = servicos.cobranca_do_participante(self.ana)
        servicos._aplicar_retorno(pag, {"status": "aprovado", "valor": pag.valor_bruto})
        Arremate.objects.filter(pk=a.pk).update(devolvido_em=timezone.now())
        servicos._aplicar_retorno(pag, {"status": "estornado"})
        a.refresh_from_db()
        self.assertEqual(a.status, "cancelado")

    # --- 17. Lance inicial ----------------------------------------------
    def test_inicial_zero_ou_negativo_nao_vira_lance_de_zero(self):
        for inicial in ("0", "-10"):
            lote = criar_lote(self.leilao, nome=f"Item {inicial}", lance_inicial=Decimal(inicial))
            self.assertEqual(lote.proximo_valor, lote.incremento_efetivo)

    def test_o_cadastro_recusa_inicial_abaixo_de_um_real(self):
        for inicial in ("0", "0.50", "-10"):
            f = forms.LoteForm(data={"nome": "Caneca fictícia", "lance_inicial": inicial, "peso_kg": "500",
                                     "altura_cm": "10", "largura_cm": "10", "profundidade_cm": "10"})
            self.assertFalse(f.is_valid(), inicial)
            self.assertIn("lance_inicial", f.errors)


class RevisaoGeralLoteBTests(TestCase):
    """Lote B da revisão geral de 26/09: a tela do público."""

    @staticmethod
    def _js(nome):
        texto = Path(settings.BASE_DIR, "static", "leilao", "js", nome).read_text(encoding="utf-8")
        limpo = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
        return re.sub(r"//[^\n]*", " ", limpo)

    def test_resposta_de_lance_sem_item_na_tela_e_descartada(self):
        js = self._js("leilao.js")
        guarda = js[js.index("function respostaAindaVale"):]
        guarda = guarda[: guarda.index("function souEu")]
        self.assertIn("if (!atual) return false;", guarda)

    def test_evento_de_lance_velho_nao_volta_atras(self):
        js = self._js("leilao.js")
        lance = js[js.index('fonte.addEventListener("lance"'):]
        lance = lance[: lance.index("desenharLote(d.lote)")]
        self.assertIn("parseFloat(d.lote.valor_atual || 0) < parseFloat(lote.valor_atual || 0)", lance)

    def test_a_gaveta_so_abre_no_aparelho_que_arrematou(self):
        js = self._js("leilao.js")
        self.assertIn("if (d.vencedor_id === EU)", js)
        self.assertIn("agora.id === loteDoMartelo", js, "a gaveta não cobre o item seguinte")

    def test_o_som_caido_nao_cobre_o_botao_no_pregao(self):
        js = self._js("leilao.js")
        mostrar = js[js.index("function mostrarSomCaiu"):]
        mostrar = mostrar[: mostrar.index("modalSom.abrir()")]
        self.assertIn("if (emPregao())", mostrar)
        self.assertIn('classList.add("caiu")', mostrar)
        self.assertIn("if (somLigado && somCaiu)", js, "o 🔊 religa em vez de desligar")

    def test_o_servidor_manda_ping_nomeado(self):
        views_py = Path(settings.BASE_DIR, "leilao", "views.py").read_text(encoding="utf-8")
        self.assertIn('yield "event: ping\\ndata: {}\\n\\n"', views_py)

    def test_a_fonte_viva_reabre_a_conexao_muda(self):
        js = self._js("fonte_viva.js")
        self.assertIn("SILENCIO_MAXIMO", js)
        self.assertIn('es.addEventListener("ping", sinal)', js)
        self.assertIn("var comSinal = function (e) { sinal(); return fn(e); };", js)

    def test_telefone_com_ddi_nao_e_cortado_errado(self):
        js = self._js("entrar.js")
        self.assertIn('d.slice(0, 2) === "55"', js)
        self.assertLess(js.index('d.slice(0, 2) === "55"'), js.index("d = d.slice(0, 11)"))

    def test_o_som_volta_no_iphone(self):
        js = self._js("som.js")
        self.assertNotIn('ctx.state === "suspended"', js)
        self.assertEqual(js.count('ctx.state !== "running"'), 2)


class RevisaoGeralLoteCTests(TestCase):
    """Lote C da revisão geral de 26/09: a mesa e o caixa."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.ana = criar_pessoa("Ana Fictícia Souza")

    @staticmethod
    def _ler(*partes):
        return Path(settings.BASE_DIR, *partes).read_text(encoding="utf-8")

    def _cliente(self, area):
        User = get_user_model()
        u = User.objects.create_user(f"{area}_c_ficticio", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name=area)[0])
        c = Client()
        c.force_login(u)
        return c

    # 7 ---------------------------------------------------------------
    def test_resposta_velha_da_mesa_e_descartada(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        self.assertIn("if (eventosDoPregao !== eventosNaSaida) return;", js)
        for evento in ('"lance"', '"lote_aberto"', '"lote_vendido"'):
            trecho = js[js.index("fonte.addEventListener(" + evento):]
            trecho = trecho[: trecho.index("});")]
            self.assertIn("eventosDoPregao++", trecho, evento)

    # 8 ---------------------------------------------------------------
    def test_clique_duplo_em_bloquear_nao_desbloqueia(self):
        c = self._cliente("locutor")
        corpo = {"acao": "bloquear", "participante": self.ana.pk, "bloquear": True, "leilao": self.leilao.pk}
        for _ in range(2):
            c.post("/equipe/acao/", json.dumps(corpo), content_type="application/json")
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.bloqueado)

    def test_a_mesa_manda_o_estado_desejado_e_trava(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        self.assertIn('corpo.bloquear = alvo.dataset.bloquear === "1"', js)
        self.assertIn('|| qual === "bloquear"', js)
        self.assertIn("if (movendo) return;", self._ler("static", "leilao", "js", "lotes.js"))

    # 9 ---------------------------------------------------------------
    def test_pix_do_caixa_nao_sai_de_outro_leilao(self):
        anterior = criar_leilao(nome="Leilão fictício de outubro", status="encerrado")
        lote = criar_lote(anterior, nome="Item antigo fictício")
        Arremate.objects.create(lote=lote, participante=self.ana, valor=Decimal("30.00"))
        c = self._cliente("caixa")
        d = c.get(f"/caixa/pessoa/{self.ana.pk}/pix/?leilao={self.leilao.pk}").json()
        self.assertFalse(d["ok"])
        self.assertIn("Leilão fictício de outubro", d["msg"])
        self.assertIn("R$ 30,00", d["msg"])

    # 10 --------------------------------------------------------------
    def test_ligacao_substituida_nao_derruba_a_voz(self):
        js = self._ler("static", "leilao", "js", "locutor.js")
        self.assertIn('if (minha !== vezDaVoz) return "substituida";', js)
        self.assertLess(js.index("if (ok && !querNoAr)"), js.index('if (minha !== vezDaVoz) return "substituida";'),
                        "o Parar tem de desligar antes de a vez ser conferida")
        religar = js[js.index("function religarVoz"):]
        religar = religar[: religar.index("\n    }\n")]
        self.assertIn('if (ok === "substituida") return;', religar)

    # 20, 21, 28 ------------------------------------------------------
    def test_a_fila_tem_teto(self):
        css = self._ler("static", "leilao", "css", "locutor.css")
        self.assertRegex(css, r"\.fila \{ max-height: \d+px; overflow-y: auto; \}")

    def test_o_caixa_nao_recarrega_com_janela_aberta(self):
        js = self._ler("static", "leilao", "js", "caixa.js")
        ocupado = js[js.index("function ocupado"):]
        ocupado = ocupado[: ocupado.index("\n    }\n")]
        self.assertIn('$("modalConta")', ocupado)
        self.assertIn('$("modalDevolver")', ocupado)

    def test_a_mesa_cresce_com_a_quarta_coluna(self):
        css = self._ler("static", "leilao", "css", "locutor.css")
        self.assertIn(".mesa { max-width: 1440px; }", css)


class RevisaoGeralLoteDTests(TestCase):
    """Lote D da revisão geral de 26/09: robustez."""

    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        self.ana = criar_pessoa("Ana Fictícia Souza")
        self.c = Client()
        sessao = self.c.session
        sessao[CHAVE_SESSAO] = self.ana.token
        sessao.save()

    def _post(self, url, corpo):
        return self.c.post(url, corpo if isinstance(corpo, str) else json.dumps(corpo),
                           content_type="application/json")

    def _equipe(self, area):
        User = get_user_model()
        u = User.objects.create_user(f"{area}_d_ficticio", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name=area)[0])
        c = Client()
        c.force_login(u)
        return c

    # 15 --------------------------------------------------------------
    def test_o_chat_tem_freio(self):
        respostas = [self._post("/chat/enviar/", {"texto": f"oi {i}"}).status_code for i in range(12)]
        self.assertIn(429, respostas)
        self.assertLessEqual(respostas.count(200), servicos.CHAT_MAX_POR_JANELA)

    def test_a_porta_tem_freio_por_ip(self):
        dados = {"nome": "Pessoa Fictícia", "cep": "01001-000", "logradouro": "Rua Exemplo",
                 "numero": "10", "bairro": "Centro", "cidade": "Cidade Exemplo", "estado": "SP"}
        antes = Participante.objects.count()
        for i in range(servicos.ENTRADAS_MAX_POR_IP + 5):
            Client().post("/entrar/", {**dados, "whatsapp": "(11) 9%04d-0000" % i})
        self.assertEqual(Participante.objects.count() - antes, servicos.ENTRADAS_MAX_POR_IP)

    # 18 --------------------------------------------------------------
    def test_entrada_forjada_nao_da_500(self):
        servicos.abrir_lote(self.lote)
        for corpo in ({"lote": "abc"}, {"lote": [1]}, {"lote": self.lote.pk, "valor_visto": "NaN"},
                      {"lote": self.lote.pk, "valor_visto": "Infinity"}, "[1]", "5"):
            with self.subTest(corpo=corpo):
                servicos.limpar_limites()
                self.assertLess(self._post("/lance/", corpo).status_code, 500)
        self.assertLess(self._post("/chat/enviar/", {"texto": 5}).status_code, 500)

    def test_ids_forjados_na_mesa_nao_dao_500(self):
        c = self._equipe("caixa")
        for corpo in ({"acao": "pago", "arremate": "abc"}, {"acao": "bloquear", "participante": "x"}):
            with self.subTest(corpo=corpo):
                r = c.post("/equipe/acao/", json.dumps(corpo), content_type="application/json")
                self.assertEqual(r.status_code, 400)

    def test_o_cadeado_e_por_numero(self):
        servicos.abrir_lote(self.lote)
        servicos.dar_lance(str(self.lote.pk), self.ana)
        self.assertIn(self.lote.pk, servicos._locks)
        self.assertNotIn(str(self.lote.pk), servicos._locks)

    # 22 --------------------------------------------------------------
    def test_sair_so_por_post(self):
        self.assertEqual(self.c.get("/sair/").status_code, 405)
        self.assertEqual(self.c.session.get(CHAVE_SESSAO), self.ana.token, "o GET deslogou")

    # 23 --------------------------------------------------------------
    def test_a_mesa_so_lista_quem_esta_neste_leilao_sem_endereco(self):
        de_outra_noite = criar_pessoa("Pessoa De Outra Noite")
        servicos.abrir_lote(self.lote)
        servicos.dar_lance(self.lote.id, self.ana)
        html = self._equipe("locutor").get(f"/locutor/{self.leilao.pk}/").content.decode()
        pessoas = html[html.index('id="listaPessoas"'):]
        self.assertIn(self.ana.nome, pessoas)
        self.assertNotIn(de_outra_noite.nome, pessoas)
        self.assertNotIn(self.ana.endereco_uma_linha, pessoas)
        self.assertNotIn(self.ana.whatsapp, pessoas)

    # 24 --------------------------------------------------------------
    def test_aviso_de_pagamento_nao_diz_de_quem(self):
        from unittest import mock

        servicos.abrir_lote(self.lote)
        servicos.dar_lance(self.lote.id, self.ana)
        arremate = servicos.fechar_lote(Lote.objects.get(pk=self.lote.pk))
        with mock.patch.object(servicos.HUB, "publicar") as publicar:
            servicos.marcar_pago(arremate, manual=True)
        tipo, dados = publicar.call_args[0]
        self.assertEqual(tipo, "pagamento")
        self.assertEqual(set(dados), {"para"})
        self.assertEqual(dados["para"], self.ana.chave_avisos)
        self.assertNotEqual(dados["para"], self.ana.chave_pessoa, "não pode casar com o lance")

    def test_a_tela_da_pessoa_conhece_a_propria_chave(self):
        html = self.c.get("/").content.decode()
        self.assertIn(f'data-eu-avisos="{self.ana.chave_avisos}"', html)

    # 25 --------------------------------------------------------------
    def test_arremate_antigo_nao_desmancha_a_revenda(self):
        antigo = Arremate.objects.create(lote=self.lote, participante=self.ana, valor=Decimal("40"),
                                         status="expirado")
        beto = criar_pessoa("Beto Fictício Lima")
        Arremate.objects.create(lote=self.lote, participante=beto, valor=Decimal("45"), status="pago")
        Lote.objects.filter(pk=self.lote.pk).update(status="vendido")
        with self.assertRaises(servicos.DevolucaoRecusada):
            servicos.devolver_ao_leilao(antigo, "teste fictício")
        self.assertEqual(Lote.objects.get(pk=self.lote.pk).status, "vendido")

    # 26, 27 ----------------------------------------------------------
    def test_o_cadastro_de_item_nao_sai_em_dobro(self):
        js = Path(settings.BASE_DIR, "static", "leilao", "js", "lote_form.js").read_text(encoding="utf-8")
        self.assertIn("if (enviado) { e.preventDefault(); return; }", js)

    def test_a_vinheta_do_duas_anima_so_opacidade(self):
        css = Path(settings.BASE_DIR, "static", "leilao", "css", "leilao.css").read_text(encoding="utf-8")
        quadro = css[css.index("@keyframes dou-lhe-pulso"):]
        quadro = quadro[: quadro.index("\n}")]
        self.assertNotIn("box-shadow", quadro)


class RevisaoDaVozTests(TestCase):
    """Revisão final da voz ao vivo (26/09): microfone, mudo e escuta.

    Estas guardas estruturais acompanham o simulador de voz
    (`ferramentas/simulador_voz/`), que roda as telas reais no Chrome com o
    WebRTC falso e provou cada cenário nos dois lados: falha no código antigo,
    passa no novo.
    """

    @staticmethod
    def _js(nome):
        texto = Path(settings.BASE_DIR, "static", "leilao", "js", nome).read_text(encoding="utf-8")
        limpo = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
        return re.sub(r"//[^\n]*", " ", limpo)

    # --- Quem fala --------------------------------------------------------
    def test_no_ar_so_com_a_conexao_de_pe(self):
        js = self._js("audio_falar.js")
        iniciar = js[js.index("async function iniciar"):js.index("function caiu")]
        self.assertIn("await esperarConectar(conexao, 12000)", iniciar)
        self.assertLess(iniciar.index("esperarConectar(conexao"), iniciar.index("rodando = true"))

    def test_microfone_que_termina_e_queda(self):
        js = self._js("audio_falar.js")
        self.assertIn('t.onended = function () {', js)
        self.assertIn('caiu("microfone")', js)

    def test_o_whip_tem_tempo_maximo(self):
        js = self._js("audio_falar.js")
        self.assertIn("controle.abort(); }, 15000)", js)

    def test_soluco_de_rede_reaproveita_a_conexao(self):
        falar = self._js("audio_falar.js")
        self.assertIn("reaproveitar: function ()", falar)
        mesa = self._js("locutor.js")
        religar = mesa[mesa.index("function religarVoz"):]
        religar = religar[: religar.index("\n    }\n")]
        self.assertLess(religar.index("AudioFalar.reaproveitar()"), religar.index("ligarVoz().then"))

    def test_mudo_na_religacao_nao_diz_no_ar(self):
        mesa = self._js("locutor.js")
        clique = mesa[mesa.index("btnMudo.addEventListener"):]
        clique = clique[: clique.index("});")]
        self.assertIn("if (querNoAr && window.AudioFalar.ativo())", clique)

    def test_a_espera_da_religacao_so_zera_com_a_voz_estavel(self):
        mesa = self._js("locutor.js")
        ligar = mesa[mesa.index("function ligarVoz"):mesa.index("function religarVoz")]
        self.assertNotIn("quedasSeguidas = 0;\n                mostrarNoAr", ligar)
        self.assertIn("relogioEstavel = setTimeout(", ligar)

    def test_o_mudo_sobrevive_a_recarregar_a_mesa(self):
        mesa = self._js("locutor.js")
        self.assertIn('sessionStorage.getItem("leilao_mudo")', mesa)
        self.assertIn("guardarMudo(mudo);", mesa)

    # --- Quem escuta ------------------------------------------------------
    def test_o_toque_destrava_o_audio_no_iphone(self):
        js = self._js("audio_ouvir.js")
        ligar = js[js.index("ligar: function (endereco, elementoAudio)"):]
        ligar = ligar[: ligar.index("return conectar();")]
        self.assertIn("destravar(elemento);", ligar)

    def test_a_primeira_recusa_do_navegador_pede_o_toque(self):
        js = self._js("audio_ouvir.js")
        self.assertIn("let ouvindo = null;", js)
        self.assertIn('ouvindo = null; avisar(false, "recusado");', js)

    def test_oscilacao_curta_nao_derruba_quem_escuta(self):
        js = self._js("audio_ouvir.js")
        ice = js[js.index("conexao.oniceconnectionstatechange"):]
        ice = ice[: ice.index("};")]
        self.assertIn('s === "disconnected"', ice)
        self.assertIn("vigiaIce = setTimeout(", ice)

    def test_a_espera_de_quem_escuta_so_zera_conectado(self):
        js = self._js("audio_ouvir.js")
        self.assertIn('if (s === "connected") tentativas = 0;', js)
        antes = js[js.index("await conexao.setRemoteDescription"):js.index("iniciarVigiaBytes(conexao);\n            log")]
        self.assertNotIn("tentativas = 0", antes)

    def test_locutor_fora_do_ar_nao_vira_alarme_no_publico(self):
        js = self._js("leilao.js")
        self.assertIn('if (!estaOuvindo && motivo === "silencio" && vozNoAr === false) return;', js)

    def test_a_voz_no_ar_vai_no_estado(self):
        leilao = criar_leilao()
        est.VOZ["no_ar"] = True
        try:
            self.assertTrue(est.estado_publico(leilao)["leilao"]["voz_no_ar"])
        finally:
            est.VOZ["no_ar"] = False

    def test_a_mesa_guarda_a_voz_no_ar(self):
        leilao = criar_leilao()
        User = get_user_model()
        u = User.objects.create_user("voz_loc_ficticio", password="segredo-ficticio")
        u.is_staff = True
        u.save()
        u.groups.add(Group.objects.get_or_create(name="locutor")[0])
        c = Client()
        c.force_login(u)
        try:
            c.post("/equipe/acao/", json.dumps({"acao": "voz", "no_ar": True, "leilao": leilao.pk}),
                   content_type="application/json")
            self.assertTrue(est.VOZ["no_ar"])
            c.post("/equipe/acao/", json.dumps({"acao": "voz", "no_ar": False, "leilao": leilao.pk}),
                   content_type="application/json")
            self.assertFalse(est.VOZ["no_ar"])
        finally:
            est.VOZ["no_ar"] = False
