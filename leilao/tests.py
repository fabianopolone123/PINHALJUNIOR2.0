"""Testes do módulo de leilão.

    DJANGO_SETTINGS_MODULE=config.settings_leilao python manage.py test leilao

O foco é o que **quebra ao vivo, na frente de 50 pessoas**: corrida de lances,
cronômetro, prazo de pagamento, vazamento de dado privado no broadcast e as
armadilhas de template que este projeto já pagou caro.
"""

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


def criar_pessoa(nome="Fulano de Teste", **extra):
    dados = {
        "nome": nome,
        "whatsapp": "5511900000000",
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


class ViewsLocutorTests(TestCase):
    def setUp(self):
        servicos.limpar_limites()
        self.leilao = criar_leilao()
        self.lote = criar_lote(self.leilao)
        User = get_user_model()
        self.user = User.objects.create_user("locutor_teste", password="segredo-ficticio")
        self.user.is_staff = True
        self.user.save()
        self.c = Client()

    def test_mesa_exige_login(self):
        r = self.c.get("/locutor/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/locutor/entrar/", r["Location"])

    def test_usuario_comum_nao_entra_na_mesa(self):
        User = get_user_model()
        User.objects.create_user("comum", password="segredo-ficticio")
        self.c.login(username="comum", password="segredo-ficticio")
        r = self.c.get("/locutor/")
        self.assertEqual(r.status_code, 302)

    def test_locutor_abre_a_mesa(self):
        self.c.login(username="locutor_teste", password="segredo-ficticio")
        self.assertEqual(self.c.get("/locutor/").status_code, 200)

    def test_acao_abrir_poe_o_lote_em_pregao(self):
        self.c.login(username="locutor_teste", password="segredo-ficticio")
        r = self.c.post(
            "/locutor/acao/",
            data='{"acao": "abrir", "lote": %d}' % self.lote.id,
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, "aberto")

    def test_acao_sem_login_e_barrada(self):
        r = self.c.post(
            "/locutor/acao/",
            data='{"acao": "abrir"}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 302)

    def test_colocar_no_ar_encerra_o_leilao_anterior(self):
        """Dois leilões ao vivo dariam duas telas de pregão."""
        self.c.login(username="locutor_teste", password="segredo-ficticio")
        outro = criar_leilao(nome="Outro leilão", status="rascunho")
        self.c.post(f"/locutor/leiloes/{outro.pk}/status/", {"status": "ao_vivo"})
        self.leilao.refresh_from_db()
        outro.refresh_from_db()
        self.assertEqual(outro.status, "ao_vivo")
        self.assertEqual(self.leilao.status, "encerrado")
        self.assertEqual(Leilao.objects.filter(status="ao_vivo").count(), 1)


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
