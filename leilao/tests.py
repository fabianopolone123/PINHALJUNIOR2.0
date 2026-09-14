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
from django.db import connections  # noqa: E402
from django.test import Client, TestCase, TransactionTestCase  # noqa: E402
from django.utils import timezone  # noqa: E402

from . import estado as est
from . import servicos
from .models import Arremate, ConfigLeilao, Lance, Leilao, Lote, PagamentoLeilao, Participante
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
    dados = {"nome": "Cesta fictícia", "lance_inicial": Decimal("40.00"), "ordem": 1}
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

    def test_lance_reinicia_o_cronometro(self):
        self.lote.fecha_em = timezone.now() + timedelta(seconds=5)
        self.lote.save(update_fields=["fecha_em"])
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        restante = (self.lote.fecha_em - timezone.now()).total_seconds()
        self.assertGreater(restante, 50)

    def test_lance_fora_do_prazo_e_recusado(self):
        self.lote.fecha_em = timezone.now() - timedelta(seconds=1)
        self.lote.save(update_fields=["fecha_em"])
        ok, msg, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertFalse(ok)
        self.assertIn("Tempo esgotado", msg)

    def test_lance_em_lote_fechado_e_recusado(self):
        self.lote.status = "fila"
        self.lote.save(update_fields=["status"])
        ok, _, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertFalse(ok)

    def test_lance_com_cronometro_pausado_e_recusado(self):
        servicos.pausar_lote(self.lote, pausar=True)
        self.lote.refresh_from_db()
        ok, msg, _ = servicos.dar_lance(self.lote.id, self.ana)
        self.assertFalse(ok)
        self.assertIn("pausou", msg)

    def test_desfazer_lance_volta_o_lider_anterior(self):
        servicos.dar_lance(self.lote.id, self.ana)     # 40
        servicos.dar_lance(self.lote.id, self.bruno)   # 45
        ok, _ = servicos.desfazer_ultimo_lance(self.lote)
        self.assertTrue(ok)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.lider_id, self.ana.id)
        self.assertEqual(self.lote.valor_atual, Decimal("40.00"))

    def test_desfazer_unico_lance_zera_o_lote(self):
        servicos.dar_lance(self.lote.id, self.ana)
        servicos.desfazer_ultimo_lance(self.lote)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.lider_id)
        self.assertEqual(self.lote.valor_atual, Decimal("0.00"))
        self.assertEqual(self.lote.proximo_valor, Decimal("40.00"))

    def test_desfazer_nao_apaga_o_lance(self):
        """Desfeito continua no histórico — é o que responde a 'mas eu dei esse lance!'."""
        servicos.dar_lance(self.lote.id, self.ana)
        servicos.desfazer_ultimo_lance(self.lote)
        self.assertEqual(Lance.objects.filter(cancelado=True).count(), 1)


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

    def test_cronometro_vencido_fecha_no_laco_central(self):
        servicos.dar_lance(self.lote.id, self.ana)
        Lote.objects.filter(pk=self.lote.pk).update(
            fecha_em=timezone.now() - timedelta(seconds=1)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")

    def test_pausado_nao_fecha_sozinho(self):
        servicos.dar_lance(self.lote.id, self.ana)
        self.lote.refresh_from_db()
        servicos.pausar_lote(self.lote, pausar=True)
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")

    def test_pausar_e_retomar_preserva_o_tempo(self):
        Lote.objects.filter(pk=self.lote.pk).update(
            fecha_em=timezone.now() + timedelta(seconds=30)
        )
        self.lote.refresh_from_db()
        servicos.pausar_lote(self.lote, pausar=True)
        self.lote.refresh_from_db()
        self.assertIsNotNone(self.lote.pausado_restante)
        self.assertAlmostEqual(self.lote.pausado_restante, 30, delta=2)
        servicos.pausar_lote(self.lote, pausar=False)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.pausado_restante)
        self.assertAlmostEqual((self.lote.fecha_em - timezone.now()).total_seconds(), 30, delta=2)


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
        """Sem isso, celular com a hora errada veria outro cronômetro."""
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertIn("servidor_em", dados)
        self.assertIn("total_segundos", dados["lote"])

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
            {"nome": "Item de dezembro", "descricao": "", "lance_inicial": "30.00"},
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

    def test_lances_da_rodada_anterior_nao_aparecem(self):
        dados = est.estado_publico(Leilao.ao_vivo())
        self.assertEqual(dados["ultimos_lances"], [])
        self.assertEqual(Lance.objects.filter(lote=self.lote).count(), 1)  # o antigo continua no banco

    def test_desfazer_nao_ressuscita_lider_da_rodada_anulada(self):
        ok, msg = servicos.desfazer_ultimo_lance(self.lote)
        self.assertFalse(ok)
        self.assertIn("Não há lance", msg)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.lider_id)

    def test_desfazer_na_rodada_nova_zera_em_vez_de_voltar_para_a_antiga(self):
        servicos.dar_lance(self.lote.id, self.bruno)
        self.lote.refresh_from_db()
        servicos.desfazer_ultimo_lance(self.lote)
        self.lote.refresh_from_db()
        self.assertIsNone(self.lote.lider_id)
        self.assertEqual(self.lote.valor_atual, Decimal("0.00"))


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
        self.assertIn("locutor", corpo["msg"])

    def test_com_credencial_a_lista_libera_o_pix(self):
        cfg = ConfigLeilao.get_solo()
        cfg.access_token_teste = "TEST-token-ficticio-1234"
        cfg.save()
        r = self.c.get("/meus-arremates/")
        self.assertTrue(r.json()["pix_possivel"])


class ReinicioDoServicoTests(TestCase):
    """O que sobrevive a um restart do serviço no meio do pregão.

    O estado vive no banco (`fecha_em` é data/hora absoluta), então o cronômetro
    é retomado no ponto certo — mas se o reinício demorar mais do que faltava, o
    laço central sobe com o prazo vencido e fecha o lote na hora. Está
    documentado em `docs/DEPLOY_LEILAO.md`; aqui fica fixado em teste.
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

    def test_lote_aberto_continua_aberto_e_com_o_prazo_gravado(self):
        prazo = self.lote.fecha_em
        # Nada de estado em memória: só o que está no banco.
        servicos.limpar_limites()
        de_novo = Lote.objects.get(pk=self.lote.pk)
        self.assertEqual(de_novo.status, "aberto")
        self.assertEqual(de_novo.fecha_em, prazo)
        self.assertEqual(de_novo.lider_id, self.ana.id)

    def test_reinicio_demorado_fecha_o_lote_na_primeira_volta(self):
        Lote.objects.filter(pk=self.lote.pk).update(
            fecha_em=timezone.now() - timedelta(seconds=30)
        )
        servicos.verificar_prazos()
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "vendido")
        self.assertEqual(Arremate.objects.filter(lote=self.lote).count(), 1)


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
