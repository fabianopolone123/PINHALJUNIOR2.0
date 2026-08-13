import datetime
import hashlib
import json
import hmac
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from . import email_envio
from . import mercadopago as mp
from . import views
from . import wapi_parser
from .models import (
    Aventureiro,
    CobrancaEnviada,
    CompraLoja,
    ContatoEmail,
    ContatoWhatsapp,
    CustoClube,
    EmailConfig,
    EnvioAniversario,
    Evento,
    LogEmail,
    MembroDiretoria,
    MensagemWhatsapp,
    MSG_WA_ACEITA,
    MSG_WA_ENTREGUE,
    MSG_WA_ENVIADA,
    MSG_WA_FALHOU,
    MSG_WA_LIDA,
    MSG_WA_NAO_ENTREGUE,
    WhatsappWebhookEvent,
    TemplateAniversario,
    TemplateNotificacao,
    FaixaEtariaPreco,
    GrupoLoja,
    Inscricao,
    Mensalidade,
    MercadoPagoConfig,
    Pagamento,
    PedidoLoja,
    PerfilUsuario,
    ProdutoEvento,
    ProdutoLoja,
    VariacaoLoja,
    VariacaoProduto,
    WhatsappConfig,
)
from .views import whatsapp_config_view


class WhatsappConfigTests(TestCase):
    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.user = User.objects.create_user(username="diretor", password="123456")
        self.user.groups.add(grupo)
        self.factory = RequestFactory()

    def test_configuracao_persiste_quando_campos_sensiveis_vem_vazios(self):
        config = WhatsappConfig.get_solo()
        config.instance_id = "INSTANCIA-SALVA"
        config.token = "TOKEN-SALVO"
        config.base_url = "https://api.w-api.app/v1"
        config.save()

        request = self.factory.post(
            "/whatsapp/config/",
            {
                "instance_id": "",
                "token": "",
                "base_url": "https://api.w-api.app/v1",
            },
        )
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)

        response = whatsapp_config_view(request)

        self.assertEqual(response.status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.instance_id, "INSTANCIA-SALVA")
        self.assertEqual(config.token, "TOKEN-SALVO")


class MercadoPagoClienteTests(TestCase):
    """Unidades do cliente: assinatura do webhook e extracao da TAXA real."""

    def test_validar_assinatura_confere_hmac(self):
        config = MercadoPagoConfig.get_solo()
        config.modo = "teste"
        config.webhook_secret_teste = "segredo-super"
        config.save()

        data_id = "123456"
        request_id = "req-abc"
        ts = "1700000000"
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac.new(b"segredo-super", manifest.encode(), hashlib.sha256).hexdigest()
        header = f"ts={ts},v1={v1}"

        self.assertTrue(mp.validar_assinatura(
            config, x_signature=header, x_request_id=request_id, data_id=data_id
        ))
        # Assinatura adulterada nao passa.
        self.assertFalse(mp.validar_assinatura(
            config, x_signature=f"ts={ts},v1=deadbeef",
            x_request_id=request_id, data_id=data_id,
        ))

    def test_consultar_pagamento_extrai_taxa_e_liquido(self):
        config = MercadoPagoConfig.get_solo()
        config.access_token_teste = "TEST-abc"
        config.save()

        fake = {
            "status": "approved",
            "transaction_amount": 100.0,
            "fee_details": [{"type": "mercadopago_fee", "amount": 0.99}],
            "transaction_details": {"net_received_amount": 99.01},
            "external_reference": "ref-1",
            "payment_type_id": "bank_transfer",
        }
        with mock.patch.object(mp, "_request", return_value=(True, fake)):
            info = mp.consultar_pagamento(config, "123")
        self.assertTrue(info["ok"])
        self.assertEqual(info["status"], "aprovado")
        self.assertEqual(info["taxa"], Decimal("0.99"))
        self.assertEqual(info["liquido"], Decimal("99.01"))
        self.assertEqual(info["external_reference"], "ref-1")


class PagamentoLojinhaTests(TestCase):
    """Fluxo Pix da lojinha de evento: engine + webhook + simulacao."""

    def setUp(self):
        self.evento = Evento.objects.create(
            tipo="inscricao",
            nome="Festa Junina",
            data=timezone.localdate() + datetime.timedelta(days=7),
            inscricao_aberta_publico=True,
        )
        self.produto = ProdutoEvento.objects.create(evento=self.evento, nome="Camiseta")
        self.var = VariacaoProduto.objects.create(
            produto=self.produto, nome="M", valor=Decimal("100.00")
        )

    def _config_mp(self, modo="teste"):
        config = MercadoPagoConfig.get_solo()
        config.modo = modo
        config.access_token_teste = "TEST-abc"
        config.webhook_secret_teste = "segredo"
        config.access_token_prod = "APP_USR-xyz"
        config.webhook_secret_prod = "segredo-prod"
        config.save()
        return config

    def _iniciar_checkout(self):
        """POST na lojinha (define a sessao) e GET na tela de pagamento (cria o
        Pagamento pendente com o QR mockado). Retorna o Pagamento pendente."""
        loja_url = reverse("core:evento_loja", args=[self.evento.id])
        self.client.post(loja_url, {
            "comprador_nome": "Fulano",
            "comprador_whatsapp": "47999990000",
            "comprador_email": "f@x.com",
            "forma_pagamento": "pix",
            f"qtd_{self.var.id}": "1",
        })
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-1", "status": "pendente",
            "qr_code": "PIXCOPIACOLA", "qr_code_base64": "QkFTRTY0", "ticket_url": "http://mp/t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            self.client.get(reverse("core:evento_pagamento", args=[self.evento.id]))
        return Pagamento.objects.get(tipo="loja_evento")

    def test_pagamento_pendente_nao_cria_pedido(self):
        self._config_mp()
        pagamento = self._iniciar_checkout()
        self.assertEqual(pagamento.status, "pendente")
        self.assertEqual(pagamento.mp_payment_id, "MP-1")
        self.assertEqual(pagamento.valor_bruto, Decimal("100.00"))
        self.assertEqual(PedidoLoja.objects.count(), 0)  # nada criado ainda

    def test_simular_aprovacao_cria_pedido_com_taxa_1pct(self):
        self._config_mp(modo="teste")
        pagamento = self._iniciar_checkout()
        url = reverse("core:pagamento_simular", args=[pagamento.referencia])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("redirect", resp.json())

        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, "aprovado")
        self.assertTrue(pagamento.finalizado)
        self.assertEqual(pagamento.taxa, Decimal("1.00"))       # 1% de 100
        self.assertEqual(pagamento.valor_liquido, Decimal("99.00"))

        pedido = PedidoLoja.objects.get()
        self.assertEqual(pedido.forma_pagamento, "pix")
        self.assertEqual(pedido.valor_total, Decimal("100.00"))
        self.assertEqual(pedido.pagamento_id, pagamento.id)

    def test_simular_bloqueado_em_producao(self):
        self._config_mp(modo="producao")
        # Em producao o checkout usa as credenciais de producao (configurado=True).
        pagamento = self._iniciar_checkout()
        url = reverse("core:pagamento_simular", args=[pagamento.referencia])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(PedidoLoja.objects.count(), 0)

    def test_webhook_aprova_com_taxa_real_do_mp(self):
        self._config_mp()
        pagamento = self._iniciar_checkout()

        info = {
            "ok": True, "status": "aprovado",
            "valor": Decimal("100.00"), "taxa": Decimal("1.50"),
            "liquido": Decimal("98.50"), "external_reference": pagamento.referencia,
            "forma": "bank_transfer", "raw": {},
        }
        data_id = "987654"
        request_id = "req-1"
        ts = "1700000000"
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac.new(b"segredo", manifest.encode(), hashlib.sha256).hexdigest()

        url = reverse("core:mercadopago_webhook") + f"?data.id={data_id}&type=payment"
        with mock.patch.object(mp, "consultar_pagamento", return_value=info):
            resp = self.client.post(
                url, data="{}", content_type="application/json",
                HTTP_X_SIGNATURE=f"ts={ts},v1={v1}",
                HTTP_X_REQUEST_ID=request_id,
            )
        self.assertEqual(resp.status_code, 200)

        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, "aprovado")
        self.assertTrue(pagamento.finalizado)
        self.assertEqual(pagamento.taxa, Decimal("1.50"))          # taxa REAL do MP
        self.assertEqual(pagamento.valor_liquido, Decimal("98.50"))
        self.assertEqual(PedidoLoja.objects.count(), 1)

    def test_cartao_gera_preferencia_e_confirma_com_taxa_repassada(self):
        self._config_mp()
        loja_url = reverse("core:evento_loja", args=[self.evento.id])
        self.client.post(loja_url, {
            "comprador_nome": "Fulano", "comprador_whatsapp": "47999990000",
            "comprador_email": "f@x.com", "forma_pagamento": "cartao",
            f"qtd_{self.var.id}": "1",
        })
        fake_pref = {"ok": True, "preference_id": "PREF1",
                     "init_point": "https://mp/checkout/PREF1"}
        with mock.patch.object(mp, "criar_preferencia", return_value=fake_pref):
            resp = self.client.get(reverse("core:evento_pagamento", args=[self.evento.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "https://mp/checkout/PREF1")
        pag = Pagamento.objects.get(tipo="loja_evento", forma="cartao")
        self.assertEqual(pag.valor_bruto, Decimal("100.00"))
        self.assertEqual(PedidoLoja.objects.count(), 0)  # nada antes de aprovar

        # Webhook aprova: líquido = bruto (o repasse cobriu a taxa) → clube arca 0.
        info = {
            "ok": True, "status": "aprovado", "valor": Decimal("105.24"),
            "taxa": Decimal("5.24"), "liquido": Decimal("100.00"),
            "external_reference": pag.referencia, "forma": "credit_card", "raw": {},
        }
        data_id, request_id, ts = "555777", "req-c", "1700000000"
        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        v1 = hmac.new(b"segredo", manifest.encode(), hashlib.sha256).hexdigest()
        url = reverse("core:mercadopago_webhook") + f"?data.id={data_id}&type=payment"
        with mock.patch.object(mp, "consultar_pagamento", return_value=info):
            self.client.post(url, data="{}", content_type="application/json",
                             HTTP_X_SIGNATURE=f"ts={ts},v1={v1}", HTTP_X_REQUEST_ID=request_id)
        pag.refresh_from_db()
        self.assertEqual(pag.status, "aprovado")
        self.assertEqual(pag.taxa, Decimal("0.00"))          # repasse cobriu a taxa
        self.assertEqual(pag.valor_liquido, Decimal("100.00"))
        pedido = PedidoLoja.objects.get()
        self.assertEqual(pedido.forma_pagamento, "cartao")

    def test_simular_cartao_nao_cobra_taxa_do_clube(self):
        from .views import _aprovar_pagamento
        self._config_mp()
        p = Pagamento.objects.create(
            tipo="loja_clube", forma="cartao", referencia="cartsim1",
            valor_bruto=Decimal("50.00"),
        )
        _aprovar_pagamento(p)  # sem líquido = simulação de teste
        p.refresh_from_db()
        self.assertEqual(p.taxa, Decimal("0.00"))          # cartão: repassado ao cliente
        self.assertEqual(p.valor_liquido, Decimal("50.00"))

    def test_grossar_cartao(self):
        from .views import _grossar_cartao
        cfg = MercadoPagoConfig.get_solo()
        cfg.taxa_cartao_pct = Decimal("4.98")
        # 100 / (1 - 0,0498) = 105,24
        self.assertEqual(_grossar_cartao(cfg, Decimal("100")), Decimal("105.24"))

    def test_pagamento_rejeitado_mostra_recusa_sem_redirecionar(self):
        # Cartão recusado: o status não redireciona e a página mostra o aviso de
        # recusa (em vez de ficar girando para sempre).
        p = Pagamento.objects.create(
            tipo="mensalidade", forma="cartao",
            referencia=Pagamento.gerar_referencia(), modo="teste",
            valor_bruto=Decimal("30"), status="rejeitado", payload={},
        )
        dados = self.client.get(
            reverse("core:pagamento_status", args=[p.referencia])
        ).json()
        self.assertEqual(dados["status"], "rejeitado")
        self.assertNotIn("redirect", dados)
        resp = self.client.get(reverse("core:pagamento", args=[p.referencia]))
        self.assertContains(resp, "pixRejeitado")

    def test_painel_evento_desconta_taxa_no_resultado(self):
        self._config_mp()
        pagamento = self._iniciar_checkout()
        self.client.post(reverse("core:pagamento_simular", args=[pagamento.referencia]))
        grupo = Group.objects.get_or_create(name="Diretor")[0]
        diretor = User.objects.create_user("dir3", password="x")
        diretor.groups.add(grupo)
        self.client.force_login(diretor)
        resp = self.client.get(reverse("core:evento_painel", args=[self.evento.id]))
        self.assertEqual(resp.status_code, 200)
        fin = resp.context["financeiro"]
        self.assertEqual(fin["taxa"], Decimal("1.00"))            # 1% de 100
        self.assertEqual(fin["saidas_total"], Decimal("1.00"))    # 0 custos + 1 taxa
        self.assertEqual(resp.context["resumo"]["resultado"], Decimal("99.00"))

    def test_webhook_assinatura_invalida_rejeitada(self):
        self._config_mp()
        pagamento = self._iniciar_checkout()
        url = reverse("core:mercadopago_webhook") + "?data.id=1&type=payment"
        resp = self.client.post(
            url, data="{}", content_type="application/json",
            HTTP_X_SIGNATURE="ts=1,v1=errado", HTTP_X_REQUEST_ID="r",
        )
        self.assertEqual(resp.status_code, 401)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, "pendente")  # nada mudou

    def test_sem_mp_configurado_mantem_fluxo_simulado(self):
        # Sem credenciais -> o comportamento antigo (simulado) e preservado.
        loja_url = reverse("core:evento_loja", args=[self.evento.id])
        self.client.post(loja_url, {
            "comprador_nome": "Fulano",
            "comprador_whatsapp": "47999990000",
            "forma_pagamento": "pix",
            f"qtd_{self.var.id}": "1",
        })
        pag_url = reverse("core:evento_pagamento", args=[self.evento.id])
        self.client.get(pag_url)
        self.assertEqual(Pagamento.objects.count(), 0)  # nao usa a engine

        resp = self.client.post(pag_url)  # "simular aprovado" antigo cria o pedido
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(PedidoLoja.objects.count(), 1)


class MensalidadePixTests(TestCase):
    """Etapa 2: cobrar varias mensalidades numa cobranca Pix so; baixa multipla."""

    def setUp(self):
        from django.contrib.auth.models import Group
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir2", password="123456")
        self.diretor.groups.add(grupo)
        self.client.force_login(self.diretor)
        self.av = Aventureiro.objects.create(
            usuario=self.diretor, nome_completo="Aventureiro Teste", sexo="M",
            data_nascimento=datetime.date(2015, 1, 1), cpf="000",
            resp_nome="Resp", resp_cpf="111", resp_whatsapp="4799", resp_email="r@x.com",
        )
        self.m1 = Mensalidade.objects.create(
            aventureiro=self.av, ano=2026, mes=7, tipo="mensalidade",
            valor=Decimal("30.00"), status="aberta",
        )
        self.m2 = Mensalidade.objects.create(
            aventureiro=self.av, ano=2026, mes=8, tipo="mensalidade",
            valor=Decimal("30.00"), status="aberta",
        )
        cfg = MercadoPagoConfig.get_solo()
        cfg.modo = "teste"
        cfg.access_token_teste = "TEST-abc"
        cfg.webhook_secret_teste = "s"
        cfg.save()

    def test_tela_mensalidades_renderiza_botao_cobrar(self):
        resp = self.client.get(reverse("core:mensalidades") + "?ano=2026&aba=aventureiros")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cobrar em aberto via Pix")
        self.assertContains(resp, "modalCobrarPix")

    def test_cobrar_gera_um_pix_e_simular_baixa_todas(self):
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-9", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            resp = self.client.post(
                reverse("core:mensalidade_cobrar"),
                {"mensalidade_ids": [self.m1.id, self.m2.id]},
            )
        self.assertEqual(resp.status_code, 302)
        pag = Pagamento.objects.get(tipo="mensalidade")
        self.assertEqual(pag.valor_bruto, Decimal("60.00"))
        # Antes de pagar, as mensalidades continuam em aberto.
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.status, "aberta")

        # Simula a aprovacao (mesmo caminho do webhook).
        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))
        pag.refresh_from_db()
        self.assertEqual(pag.status, "aprovado")
        self.assertTrue(pag.finalizado)
        self.assertEqual(pag.taxa, Decimal("0.60"))  # 1% de 60

        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.assertEqual(self.m1.status, "paga")
        self.assertEqual(self.m2.status, "paga")
        self.assertEqual(self.m1.forma_pagamento, "pix")
        self.assertEqual(self.m1.pagamento_id, pag.id)
        self.assertEqual(self.m1.valor_pago, Decimal("30.00"))

    def test_financeiro_desconta_taxa_do_liquido(self):
        # Um custo do clube (data = date) exercita o render do extrato com data+hora.
        CustoClube.objects.create(
            nome="Hospedagem", valor=Decimal("100"),
            data=datetime.date(2026, 3, 1), destino="geral",
        )
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-f", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            self.client.post(reverse("core:mensalidade_cobrar"),
                             {"mensalidade_ids": [self.m1.id]})
        pag = Pagamento.objects.get(tipo="mensalidade")
        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))

        resp = self.client.get(reverse("core:financeiro"))
        self.assertEqual(resp.status_code, 200)
        mens = resp.context["resumo"]["mensalidades"]
        self.assertEqual(mens["taxa"], Decimal("0.30"))        # 1% de 30
        self.assertEqual(mens["liquido"], Decimal("29.70"))    # 30 - 0,30
        # A taxa entra nas saídas e reduz o resultado líquido.
        self.assertEqual(resp.context["resumo"]["taxas"]["total"], Decimal("0.30"))
        # E aparece como linha no extrato consolidado.
        taxas_extrato = [e for e in resp.context["extrato"] if e["tipo"] == "Taxa Mercado Pago"]
        self.assertEqual(len(taxas_extrato), 1)
        self.assertEqual(taxas_extrato[0]["valor"], Decimal("0.30"))

    def test_cobrar_cartao_gera_preferencia(self):
        fake_pref = {"ok": True, "preference_id": "P", "init_point": "https://mp/co/P"}
        with mock.patch.object(mp, "criar_preferencia", return_value=fake_pref):
            resp = self.client.post(
                reverse("core:mensalidade_cobrar"),
                {"mensalidade_ids": [self.m1.id], "forma_pagamento": "cartao"},
            )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "https://mp/co/P")
        pag = Pagamento.objects.get(tipo="mensalidade")
        self.assertEqual(pag.forma, "cartao")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.status, "aberta")  # só quita quando aprovar

    def test_desfazer_mensalidade_paga_via_pix(self):
        # Paga via Pix (simular) e depois "Desfazer" — deve voltar para em aberto.
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-x", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            self.client.post(reverse("core:mensalidade_cobrar"),
                             {"mensalidade_ids": [self.m1.id]})
        pag = Pagamento.objects.get(tipo="mensalidade")
        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.status, "paga")

        # Desfazer (mesmo endpoint do botão).
        resp = self.client.post(reverse("core:mensalidade_pagar"), {
            "mensalidade_id": self.m1.id, "pagar": "0",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "aberta")
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.status, "aberta")
        self.assertEqual(self.m1.valor_pago, None)


class LojaClubePixTests(TestCase):
    """Etapa 3: compra na Loja do Clube via Pix (cria a compra so na aprovacao)."""

    def setUp(self):
        self.user = User.objects.create_user("comprador", password="123456")
        self.client.force_login(self.user)
        self.produto = ProdutoLoja.objects.create(nome="Camiseta oficial")
        self.grupo = GrupoLoja.objects.create(produto=self.produto, nome="Tamanho", modo="unica")
        self.var = VariacaoLoja.objects.create(grupo=self.grupo, nome="M", valor=Decimal("40.00"))
        cfg = MercadoPagoConfig.get_solo()
        cfg.modo = "teste"
        cfg.access_token_teste = "TEST-abc"
        cfg.webhook_secret_teste = "s"
        cfg.save()

    def _por_no_carrinho(self):
        session = self.client.session
        session["loja_carrinho"] = [{
            "produto_id": self.produto.id,
            "aventureiro_id": None,
            "itens": [{"variacao_id": self.var.id, "qtd": 1}],
        }]
        session.save()

    def test_compra_loja_via_pix(self):
        self._por_no_carrinho()
        # Finaliza (define comprador/forma) e vai para o pagamento.
        self.client.post(reverse("core:loja_finalizar"), {
            "comprador_nome": "Fulano", "comprador_whatsapp": "4799", "forma_pagamento": "pix",
        })
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-L", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            resp = self.client.get(reverse("core:loja_pagamento"))
        self.assertEqual(resp.status_code, 302)  # redireciona para a pagina generica
        pag = Pagamento.objects.get(tipo="loja_clube")
        self.assertEqual(pag.valor_bruto, Decimal("40.00"))
        self.assertEqual(CompraLoja.objects.count(), 0)  # nada criado ainda

        # Simula a aprovacao.
        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))
        pag.refresh_from_db()
        self.assertEqual(pag.status, "aprovado")
        self.assertTrue(pag.finalizado)
        self.assertEqual(pag.taxa, Decimal("0.40"))

        compra = CompraLoja.objects.get()
        self.assertEqual(compra.forma_pagamento, "pix")
        self.assertEqual(compra.valor_total, Decimal("40.00"))
        self.assertEqual(compra.pagamento_id, pag.id)

    def test_vendas_loja_resultado_reflete_taxa(self):
        # Compra paga via Pix e, na aba Vendas, o resultado desconta a taxa.
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-v", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        self._por_no_carrinho()
        self.client.post(reverse("core:loja_finalizar"), {
            "comprador_nome": "Fulano", "comprador_whatsapp": "4799", "forma_pagamento": "pix",
        })
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            self.client.get(reverse("core:loja_pagamento"))
        pag = Pagamento.objects.get(tipo="loja_clube")
        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))

        diretor = User.objects.create_user("dir_loja", password="x")
        diretor.groups.add(Group.objects.get_or_create(name="Diretor")[0])
        self.client.force_login(diretor)
        resp = self.client.get(reverse("core:loja") + "?aba=vendas")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["taxa_loja"], Decimal("0.40"))       # 1% de 40
        self.assertEqual(resp.context["loja_resultado"], Decimal("39.60"))  # 40 - 0,40


class InscricaoPixTests(TestCase):
    """Etapa 4: inscricao online via Pix (paga) e criacao imediata (gratis)."""

    def _evento(self, com_faixa=True):
        ev = Evento.objects.create(
            tipo="inscricao", nome="Acampamento",
            data=timezone.localdate() + datetime.timedelta(days=10),
            inscricao_aberta_publico=True,
        )
        if com_faixa:
            FaixaEtariaPreco.objects.create(
                evento=ev, idade_min=1, idade_max=99, valor=Decimal("50.00")
            )
        return ev

    def _config_mp(self):
        cfg = MercadoPagoConfig.get_solo()
        cfg.modo = "teste"
        cfg.access_token_teste = "TEST-abc"
        cfg.webhook_secret_teste = "s"
        cfg.save()

    def _post_inscricao(self, ev):
        return {
            "responsavel_nome": "Mae", "responsavel_whatsapp": "4799",
            "responsavel_email": "m@x.com", "responsavel_cpf": "111",
            "part_idx": ["0"], "part_nome_0": "Crianca", "part_idade_0": "10",
        }

    def test_inscricao_paga_gera_pix_e_confirma_na_aprovacao(self):
        self._config_mp()
        ev = self._evento(com_faixa=True)
        url = reverse("core:evento_inscrever", args=[ev.id])
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-I", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            resp = self.client.post(url, self._post_inscricao(ev))
        self.assertEqual(resp.status_code, 302)
        pag = Pagamento.objects.get(tipo="inscricao")
        self.assertEqual(pag.valor_bruto, Decimal("50.00"))
        self.assertEqual(Inscricao.objects.count(), 0)  # nao cria antes de pagar

        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))
        pag.refresh_from_db()
        self.assertEqual(pag.status, "aprovado")
        self.assertTrue(pag.finalizado)
        self.assertEqual(pag.taxa, Decimal("0.50"))

        insc = Inscricao.objects.get()
        self.assertEqual(insc.status, "confirmada")
        self.assertEqual(insc.forma_pagamento, "pix")
        self.assertEqual(insc.valor_total, Decimal("50.00"))
        self.assertEqual(insc.pagamento_id, pag.id)
        self.assertEqual(insc.participantes.count(), 1)

    def test_inscricao_cartao_gera_preferencia(self):
        self._config_mp()
        ev = self._evento(com_faixa=True)
        fake_pref = {"ok": True, "preference_id": "P", "init_point": "https://mp/co/I"}
        data = self._post_inscricao(ev)
        data["forma_pagamento"] = "cartao"
        with mock.patch.object(mp, "criar_preferencia", return_value=fake_pref):
            resp = self.client.post(reverse("core:evento_inscrever", args=[ev.id]), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "https://mp/co/I")
        pag = Pagamento.objects.get(tipo="inscricao")
        self.assertEqual(pag.forma, "cartao")
        self.assertEqual(Inscricao.objects.count(), 0)  # só cria ao aprovar

    def test_inscricao_gratis_cria_na_hora_sem_pix(self):
        self._config_mp()
        ev = self._evento(com_faixa=False)  # sem faixa -> valor 0
        url = reverse("core:evento_inscrever", args=[ev.id])
        resp = self.client.post(url, self._post_inscricao(ev))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Pagamento.objects.count(), 0)  # gratis nao gera Pix
        insc = Inscricao.objects.get()
        self.assertEqual(insc.status, "confirmada")
        self.assertEqual(insc.valor_total, Decimal("0.00"))


class AcertoPublicoTests(TestCase):
    """Página pública de acerto (link do WhatsApp): ver o que deve e pagar."""

    def setUp(self):
        self.user = User.objects.create_user("resp1", password="x")
        self.av = Aventureiro.objects.create(
            usuario=self.user, nome_completo="Ana Teste", sexo="F",
            data_nascimento=datetime.date(2015, 1, 1), cpf="1",
            resp_nome="Mae Teste", resp_cpf="2", resp_whatsapp="4799", resp_email="m@x.com",
        )
        hoje = timezone.localdate()
        self.m1 = Mensalidade.objects.create(
            aventureiro=self.av, ano=hoje.year, mes=hoje.month,
            valor=Decimal("30.00"), status="aberta",
        )
        self.perfil = PerfilUsuario.objects.create(usuario=self.user)
        self.token = self.perfil.get_token_acerto()
        cfg = MercadoPagoConfig.get_solo()
        cfg.modo = "teste"; cfg.access_token_teste = "T"; cfg.webhook_secret_teste = "s"
        cfg.save()

    def test_pagina_mostra_em_aberto(self):
        r = self.client.get(reverse("core:acerto", args=[self.token]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Ana Teste")
        self.assertContains(r, "Acerto de mensalidades")

    def test_token_invalido(self):
        r = self.client.get(reverse("core:acerto", args=["naoexiste"]))
        self.assertContains(r, "Link inválido")

    def test_acerto_ignora_meses_futuros(self):
        # Mês do ano que vem = ainda não venceu → não deve entrar no acerto.
        futura = Mensalidade.objects.create(
            aventureiro=self.av, ano=timezone.localdate().year + 1, mes=1,
            valor=Decimal("30.00"), status="aberta",
        )
        from .views import _mensalidades_abertas_familia
        abertas = _mensalidades_abertas_familia(self.user)
        self.assertIn(self.m1, abertas)          # mês atual (vencido) entra
        self.assertNotIn(futura, abertas)         # mês futuro NÃO entra

    def test_acerto_ignora_aventureiro_inativo(self):
        """Regra do clube: **inativo não é cobrado**, mesmo tendo mês em aberto.
        A cobrança e os relatórios já respeitavam; esta página pública não."""
        inativo = Aventureiro.objects.create(
            usuario=self.user, nome_completo="Saiu do Clube", sexo="M",
            data_nascimento=datetime.date(2014, 1, 1), cpf="INAT1", ativo=False,
            resp_nome="Mae Teste", resp_cpf="2", resp_whatsapp="4799",
        )
        hoje = timezone.localdate()
        divida = Mensalidade.objects.create(
            aventureiro=inativo, ano=hoje.year, mes=hoje.month,
            valor=Decimal("30.00"), status="aberta",
        )
        from .views import _mensalidades_abertas_familia
        abertas = _mensalidades_abertas_familia(self.user)
        self.assertIn(self.m1, abertas)           # o ativo continua
        self.assertNotIn(divida, abertas)         # o inativo NÃO é cobrado

        r = self.client.get(reverse("core:acerto", args=[self.token]))
        self.assertContains(r, "Ana Teste")
        self.assertNotContains(r, "Saiu do Clube")

    def test_acerto_de_familia_so_com_inativo_nao_cobra_nada(self):
        self.av.ativo = False
        self.av.save()
        r = self.client.get(reverse("core:acerto", args=[self.token]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Tudo em dia")     # nada a cobrar

    def test_cobrar_pix_e_simular_quita_familia(self):
        fake = {"ok": True, "mp_payment_id": "MP", "status": "pendente",
                "qr_code": "P", "qr_code_base64": "B", "ticket_url": "http://t"}
        with mock.patch.object(mp, "criar_pix", return_value=fake):
            r = self.client.post(reverse("core:acerto_cobrar", args=[self.token]),
                                 {"forma_pagamento": "pix"})
        self.assertEqual(r.status_code, 302)
        pag = Pagamento.objects.get(tipo="mensalidade")
        self.assertEqual(pag.valor_bruto, Decimal("30.00"))
        self.assertEqual(pag.usuario_id, self.user.id)   # ligado à família
        self.client.post(reverse("core:pagamento_simular", args=[pag.referencia]))
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.status, "paga")


class CobrancaWhatsappTests(TestCase):
    """Aba Cobranças: envio por WhatsApp registra o histórico do mês."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_cob", password="x")
        self.diretor.groups.add(grupo)
        self.user = User.objects.create_user("fam1", password="x")
        self.av = Aventureiro.objects.create(
            usuario=self.user, nome_completo="Ana", sexo="F",
            data_nascimento=datetime.date(2015, 1, 1), cpf="1",
            resp_nome="Mae Ana", resp_cpf="2", resp_whatsapp="47999990000", resp_email="m@x.com",
        )
        hoje = timezone.localdate()
        Mensalidade.objects.create(
            aventureiro=self.av, ano=hoje.year, mes=hoje.month,
            valor=Decimal("30.00"), status="aberta",
        )
        wa = WhatsappConfig.get_solo()
        wa.instance_id = "I"; wa.token = "T"; wa.save()
        self.client.force_login(self.diretor)

    def test_enviar_cobranca_registra_historico(self):
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "msgid")):
            r = self.client.post(reverse("core:mensalidade_cobranca_enviar"),
                                 {"usuario_id": self.user.id, "so_nao_enviados": "0"})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual(d["enviados"], 1)
        hoje = timezone.localdate()
        self.assertEqual(
            CobrancaEnviada.objects.filter(
                usuario=self.user, ano=hoje.year, mes=hoje.month
            ).count(),
            1,
        )

    def test_tela_cobrancas_renderiza(self):
        r = self.client.get(reverse("core:mensalidades") + "?aba=cobrancas")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Mae Ana")
        self.assertContains(r, "Enviar a todos")

    def test_salva_mensagem_apelo(self):
        from .models import ConfigMensalidade
        self.client.post(reverse("core:mensalidade_cobranca_config"), {
            "mensagem_cobranca": "Oi {nome}", "mensagem_apelo": "Contribua! 💚",
        })
        self.assertEqual(ConfigMensalidade.get_solo().mensagem_apelo, "Contribua! 💚")


class PerfilResponsavelTests(TestCase):
    """Perfil Responsável: menu por perfil + telas próprias de Loja, Mensalidades
    e Presença (só-leitura), separadas das do Diretor."""

    def setUp(self):
        self.grupo_dir = Group.objects.create(name="Diretor")
        self.grupo_resp = Group.objects.create(name="Responsável")
        self.diretor = User.objects.create_user("dir", password="x")
        self.diretor.groups.add(self.grupo_dir, self.grupo_resp)   # pode trocar de perfil

        self.resp = User.objects.create_user("resp", password="x")
        self.av = Aventureiro.objects.create(
            usuario=self.resp, nome_completo="Ana Souza", sexo="F",
            data_nascimento=datetime.date(2015, 1, 1), cpf="1",
            resp_nome="Mae Souza", resp_cpf="2", resp_whatsapp="4799", resp_email="m@x.com",
        )
        hoje = timezone.localdate()
        self.m_atual = Mensalidade.objects.create(
            aventureiro=self.av, ano=hoje.year, mes=hoje.month,
            valor=Decimal("30.00"), status="aberta",
        )
        self.m_futura = Mensalidade.objects.create(
            aventureiro=self.av, ano=hoje.year + 1, mes=1,
            valor=Decimal("30.00"), status="aberta",
        )
        cfg = MercadoPagoConfig.get_solo()
        cfg.modo = "teste"; cfg.access_token_teste = "T"; cfg.webhook_secret_teste = "s"
        cfg.save()

    # --- Menu por perfil (registro central) ---
    def test_menu_por_perfil(self):
        from .menus import itens_menu_para
        ids_dir = {i["id"] for i in itens_menu_para(self.diretor)}
        ids_resp = {i["id"] for i in itens_menu_para(self.resp)}
        self.assertIn("financeiro", ids_dir)
        self.assertIn("usuarios", ids_dir)
        self.assertEqual(ids_resp, {"inicio", "mensalidades", "loja", "presenca"})
        self.assertNotIn("financeiro", ids_resp)
        self.assertNotIn("usuarios", ids_resp)

    # --- Loja ---
    def test_loja_responsavel_sem_gerenciar_nem_vendas(self):
        self.client.force_login(self.resp)
        r = self.client.get(reverse("core:loja"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/loja_responsavel.html")
        self.assertContains(r, "Meus pedidos")
        self.assertNotContains(r, "Cadastrar produto")   # Gerenciar é do Diretor

    def test_loja_diretor_mantem_painel(self):
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:loja"))
        self.assertTemplateUsed(r, "core/loja.html")

    # --- Mensalidades ---
    def test_mensalidades_responsavel_mostra_apelo_e_ignora_futuro(self):
        self.client.force_login(self.resp)
        r = self.client.get(reverse("core:mensalidades"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/mensalidades_responsavel.html")
        self.assertContains(r, "Ana Souza")
        # Só o vencido entra por padrão; o futuro fica de fora.
        self.assertEqual(r.context["n_abertas"], 1)
        self.assertTrue(r.context["tem_futuras"])
        self.assertTrue(r.context["mensagem_apelo"])

    def test_mensalidades_responsavel_adiantar_inclui_futuro(self):
        self.client.force_login(self.resp)
        r = self.client.get(reverse("core:mensalidades") + "?frente=1")
        self.assertEqual(r.context["n_abertas"], 2)

    def test_pagar_selecionadas_gera_um_pagamento_da_familia(self):
        self.client.force_login(self.resp)
        fake = {"ok": True, "mp_payment_id": "MP", "status": "pendente",
                "qr_code": "P", "qr_code_base64": "B", "ticket_url": "http://t"}
        with mock.patch.object(mp, "criar_pix", return_value=fake):
            r = self.client.post(reverse("core:minhas_mensalidades_pagar"),
                                 {"mensalidade_ids": [self.m_atual.id], "forma_pagamento": "pix"})
        self.assertEqual(r.status_code, 302)
        pag = Pagamento.objects.get(tipo="mensalidade")
        self.assertEqual(pag.valor_bruto, Decimal("30.00"))
        self.assertEqual(pag.usuario_id, self.resp.id)

    def test_nao_paga_mensalidade_de_outra_familia(self):
        outro = User.objects.create_user("outro", password="x")
        av2 = Aventureiro.objects.create(
            usuario=outro, nome_completo="Beto", sexo="M",
            data_nascimento=datetime.date(2014, 1, 1), cpf="9",
            resp_nome="Pai Beto", resp_cpf="8", resp_whatsapp="47", resp_email="p@x.com",
        )
        m_outro = Mensalidade.objects.create(
            aventureiro=av2, ano=timezone.localdate().year, mes=timezone.localdate().month,
            valor=Decimal("30.00"), status="aberta",
        )
        self.client.force_login(self.resp)
        r = self.client.post(reverse("core:minhas_mensalidades_pagar"),
                             {"mensalidade_ids": [m_outro.id], "forma_pagamento": "pix"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Pagamento.objects.count(), 0)   # nada foi cobrado

    # --- Presença ---
    def test_presenca_responsavel_relatorio(self):
        ev = Evento.objects.create(nome="Reunião", tipo="simples", data=datetime.date(2026, 1, 10))
        from .models import PresencaEvento
        PresencaEvento.objects.create(evento=ev, aventureiro=self.av)
        self.client.force_login(self.resp)
        r = self.client.get(reverse("core:presenca"))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "core/presenca_responsavel.html")
        self.assertEqual(r.context["relatorio"][0]["n_foi"], 1)

    def test_responsavel_nao_marca_presenca(self):
        ev = Evento.objects.create(nome="Reunião", tipo="simples", data=datetime.date(2026, 1, 10))
        self.client.force_login(self.resp)
        r = self.client.post(reverse("core:presenca_marcar", args=[ev.id]),
                             {"aventureiro": self.av.id, "presente": "1"})
        self.assertEqual(r.status_code, 302)   # bloqueado (diretor_required → redireciona)
        from .models import PresencaEvento
        self.assertFalse(PresencaEvento.objects.filter(evento=ev, aventureiro=self.av).exists())

    # --- Seletor de perfil ("Ver como") ---
    def test_switcher_troca_para_responsavel_e_volta(self):
        self.client.force_login(self.diretor)
        # Sem trocar: Diretor vê o painel.
        self.assertTemplateUsed(self.client.get(reverse("core:loja")), "core/loja.html")
        # Troca para Responsável.
        self.client.post(reverse("core:trocar_perfil"), {"perfil": "Responsável"})
        self.assertTemplateUsed(self.client.get(reverse("core:loja")), "core/loja_responsavel.html")
        self.assertTemplateUsed(
            self.client.get(reverse("core:mensalidades")), "core/mensalidades_responsavel.html"
        )
        self.assertTemplateUsed(
            self.client.get(reverse("core:presenca")), "core/presenca_responsavel.html"
        )
        # Volta ao Diretor.
        self.client.post(reverse("core:trocar_perfil"), {"perfil": "Diretor"})
        self.assertTemplateUsed(self.client.get(reverse("core:loja")), "core/loja.html")

    def test_switcher_recusa_perfil_que_o_usuario_nao_tem(self):
        self.client.force_login(self.resp)   # só Responsável (sem grupo)
        self.client.post(reverse("core:trocar_perfil"), {"perfil": "Diretor"})
        # Não virou Diretor: continua na visão de responsável.
        self.assertNotEqual(self.client.session.get("perfil_ativo"), "Diretor")
        self.assertTemplateUsed(
            self.client.get(reverse("core:mensalidades")), "core/mensalidades_responsavel.html"
        )


class DemoIsolamentoTests(TestCase):
    """Aventureiros/eventos FICTÍCIOS (demo) não entram nas contagens do clube."""

    def setUp(self):
        self.grupo_dir = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir3", password="x")
        self.diretor.groups.add(self.grupo_dir)
        hoje = timezone.localdate()
        # Aventureiro REAL (de uma família real) com 1 mensalidade em aberto.
        self.real_user = User.objects.create_user("familia_real", password="x")
        self.real = Aventureiro.objects.create(
            usuario=self.real_user, nome_completo="Joao Real", sexo="M",
            data_nascimento=datetime.date(2015, 1, 1), cpf="R1",
            resp_nome="Mae Real", resp_cpf="R2", resp_whatsapp="47", resp_email="r@x.com",
        )
        Mensalidade.objects.create(
            aventureiro=self.real, ano=hoje.year, mes=hoje.month,
            valor=Decimal("30.00"), status="aberta",
        )
        # Aventureiro FICTÍCIO (demo) com 1 mensalidade PAGA (não pode contar).
        self.demo = Aventureiro.objects.create(
            usuario=self.diretor, nome_completo="Fantasma Demo", sexo="M",
            data_nascimento=datetime.date(2016, 1, 1), cpf="D1", demo=True,
            resp_nome="Fabiano Demo", resp_cpf="D2", resp_whatsapp="47", resp_email="d@x.com",
        )
        Mensalidade.objects.create(
            aventureiro=self.demo, ano=hoje.year, mes=hoje.month,
            valor=Decimal("30.00"), status="paga", valor_pago=Decimal("30.00"),
        )
        self.client.force_login(self.diretor)

    def test_demo_fora_de_usuarios(self):
        r = self.client.get(reverse("core:usuarios"))
        self.assertContains(r, "Joao Real")
        self.assertNotContains(r, "Fantasma Demo")

    def test_demo_fora_de_mensalidades_do_diretor(self):
        r = self.client.get(reverse("core:mensalidades") + "?aba=aventureiros")
        self.assertContains(r, "Joao Real")
        self.assertNotContains(r, "Fantasma Demo")
        # Totais: recebido ignora a paga fictícia; aberto conta só a real.
        self.assertEqual(r.context["totais"]["recebido"], Decimal("0"))
        self.assertEqual(r.context["totais"]["aberto"], Decimal("30.00"))

    def test_demo_fora_da_presenca_do_diretor(self):
        ev = Evento.objects.create(nome="Reunião", tipo="simples", data=datetime.date(2026, 1, 10))
        r = self.client.get(reverse("core:presenca_evento", args=[ev.id]))
        nomes = [a.nome_completo for a in r.context["aventureiros"]]
        self.assertIn("Joao Real", nomes)
        self.assertNotIn("Fantasma Demo", nomes)


class EmailConfigTests(TestCase):
    """Base do canal de e-mail: configuração, mascaramento e envio de teste."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_email", password="x")
        self.diretor.groups.add(grupo)
        self.client.force_login(self.diretor)

    def test_tela_exige_diretor(self):
        outro = User.objects.create_user("resp_email", password="x")
        self.client.force_login(outro)
        r = self.client.get(reverse("core:email"))
        self.assertNotEqual(r.status_code, 200)

    def test_salva_config_e_normaliza_senha_de_app(self):
        r = self.client.post(reverse("core:email_config"), {
            "usuario": "clube@gmail.com",
            "senha": "abcd efgh ijkl mnop",   # o Gmail exibe com espaços
            "remetente_nome": "Clube Pinhal",
            "host": "smtp.gmail.com",
            "porta": "587",
            "seguranca": "tls",
        })
        self.assertEqual(r.status_code, 302)
        cfg = EmailConfig.get_solo()
        # Os espaços são removidos — o servidor SMTP não os aceita.
        self.assertEqual(cfg.senha, "abcdefghijklmnop")
        self.assertTrue(cfg.configurado)
        self.assertEqual(cfg.remetente, "Clube Pinhal <clube@gmail.com>")

    def test_senha_persiste_quando_campo_vem_vazio(self):
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "SENHA-SALVA"
        cfg.save()

        self.client.post(reverse("core:email_config"), {
            "usuario": "clube@gmail.com", "senha": "",
            "host": "smtp.gmail.com", "porta": "587", "seguranca": "tls",
        })
        cfg.refresh_from_db()
        self.assertEqual(cfg.senha, "SENHA-SALVA")

    def test_senha_mascarada_nao_vaza(self):
        cfg = EmailConfig.get_solo()
        cfg.senha = "abcdefghijklmnop"
        cfg.save()
        self.assertNotIn("abcd", cfg.senha_mascarada)
        self.assertTrue(cfg.senha_mascarada.endswith("mnop"))

    def test_porta_invalida_mantem_a_anterior(self):
        self.client.post(reverse("core:email_config"), {
            "usuario": "clube@gmail.com", "senha": "x",
            "host": "smtp.gmail.com", "porta": "abc", "seguranca": "tls",
        })
        self.assertEqual(EmailConfig.get_solo().porta, 587)

    def test_testar_sem_configurar_devolve_400(self):
        r = self.client.post(reverse("core:email_testar"), {"destino": "a@b.com"})
        self.assertEqual(r.status_code, 400)

    def test_envio_de_teste_usa_o_cliente_e_conta_o_envio(self):
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.save()

        with mock.patch("core.views.email_envio.enviar", return_value=(True, "enviado")) as env:
            r = self.client.post(reverse("core:email_testar"), {"destino": "pai@exemplo.com"})

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(env.call_args[0][1], "pai@exemplo.com")

    def test_falha_de_envio_devolve_502_com_motivo(self):
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.save()

        with mock.patch("core.views.email_envio.enviar", return_value=(False, "Senha recusada.")):
            r = self.client.post(reverse("core:email_testar"), {"destino": "pai@exemplo.com"})

        self.assertEqual(r.status_code, 502)
        self.assertIn("Senha recusada.", r.json()["erro"])

    def test_contadores_registram_envio_e_falha(self):
        cfg = EmailConfig.get_solo()
        cfg.registrar_envio()
        cfg.registrar_falha("erro qualquer")
        cfg.refresh_from_db()
        self.assertEqual(cfg.enviados, 1)
        self.assertEqual(cfg.falhas, 1)
        self.assertIn("erro qualquer", cfg.ultimo_erro)

    def test_menu_do_diretor_tem_o_item_email(self):
        r = self.client.get(reverse("core:email"))
        self.assertEqual(r.status_code, 200)
        ids = [i["id"] for i in r.context["menu_itens"]]
        self.assertIn("email", ids)

    def test_cliente_recusa_destino_invalido_sem_abrir_conexao(self):
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.save()
        ok, detalhe = email_envio.enviar(cfg, "sem-arroba", "Assunto", "Corpo")
        self.assertFalse(ok)
        self.assertIn("inválido", detalhe)


class ConsentimentoEmailTests(TestCase):
    """Camada anti-spam: descadastro, bounce, gate e cabeçalhos."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_cons", password="x")
        self.diretor.groups.add(grupo)
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.site_url = "https://pinhaljunior.com.br"
        cfg.save()
        self.cfg = cfg

    # ---- Gate ----
    def test_gate_libera_endereco_novo_e_cria_contato(self):
        pode, contato, motivo = views._pode_enviar_email("novo@exemplo.com")
        self.assertTrue(pode)
        self.assertEqual(motivo, "ok")
        self.assertTrue(ContatoEmail.objects.filter(endereco="novo@exemplo.com").exists())
        self.assertTrue(contato.token)

    def test_gate_normaliza_caixa_e_espacos(self):
        views._pode_enviar_email("  Maiuscula@Exemplo.COM ")
        self.assertTrue(ContatoEmail.objects.filter(endereco="maiuscula@exemplo.com").exists())

    def test_descadastrado_barra_aviso_mas_nao_comprovante(self):
        c = ContatoEmail.para("saiu@exemplo.com")
        c.descadastrar()
        pode, _, motivo = views._pode_enviar_email("saiu@exemplo.com")
        self.assertFalse(pode)
        self.assertEqual(motivo, "descadastrado")
        # Transacional (comprovante do que a propria pessoa fez) continua passando.
        pode_t, _, _ = views._pode_enviar_email("saiu@exemplo.com", transacional=True)
        self.assertTrue(pode_t)

    def test_bounce_barra_ate_o_transacional(self):
        c = ContatoEmail.para("morto@exemplo.com")
        c.registrar_bounce("550 no such user")
        for transacional in (False, True):
            pode, _, motivo = views._pode_enviar_email("morto@exemplo.com",
                                                       transacional=transacional)
            self.assertFalse(pode)
            self.assertEqual(motivo, "endereco_recusado")

    def test_forcar_fura_descadastro_mas_nao_bounce(self):
        ContatoEmail.para("a@x.com").descadastrar()
        ContatoEmail.para("b@x.com").registrar_bounce("550")
        with mock.patch("core.views.email_envio.enviar", return_value=(True, "enviado")):
            ok_a, _ = views._enviar_email("a@x.com", "s", "c", forcar=True)
        ok_b, motivo_b = views._enviar_email("b@x.com", "s", "c", forcar=True)
        self.assertTrue(ok_a)
        self.assertFalse(ok_b)
        self.assertEqual(motivo_b, "endereco_recusado")

    # ---- Cabecalhos e corpo ----
    def test_aviso_leva_list_unsubscribe_e_link(self):
        contato = ContatoEmail.para("pai@exemplo.com")
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.return_value = 1
            email_envio.enviar(self.cfg, "pai@exemplo.com", "Cobranca", "Corpo",
                               contato=contato, transacional=False)
        kw = EM.call_args.kwargs
        self.assertIn("List-Unsubscribe", kw["headers"])
        self.assertIn(contato.token, kw["headers"]["List-Unsubscribe"])
        self.assertEqual(kw["headers"]["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.assertIn("Para não receber mais estes avisos", kw["body"])

    def test_transacional_nao_leva_descadastro(self):
        contato = ContatoEmail.para("pai@exemplo.com")
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.return_value = 1
            email_envio.enviar(self.cfg, "pai@exemplo.com", "Compra", "Corpo",
                               contato=contato, transacional=True)
        kw = EM.call_args.kwargs
        self.assertIsNone(kw["headers"])
        self.assertNotIn("Para não receber mais estes avisos", kw["body"])
        # O rodape de identificacao continua em todo e-mail.
        self.assertIn("Clube de Aventureiros Pinhal Júnior", kw["body"])

    def test_reply_to_vai_quando_configurado(self):
        self.cfg.reply_to = "contato@pinhaljunior.com.br"
        self.cfg.save()
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.return_value = 1
            email_envio.enviar(self.cfg, "a@x.com", "s", "c")
        self.assertEqual(EM.call_args.kwargs["reply_to"], ["contato@pinhaljunior.com.br"])

    # ---- Bounce automatico ----
    def test_recusa_do_servidor_marca_bounce(self):
        import smtplib
        contato = ContatoEmail.para("recusa@exemplo.com")
        erro = smtplib.SMTPRecipientsRefused({"recusa@exemplo.com": (550, b"No such user")})
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.side_effect = erro
            ok, _ = email_envio.enviar(self.cfg, "recusa@exemplo.com", "s", "c", contato=contato)
        contato.refresh_from_db()
        self.assertFalse(ok)
        self.assertTrue(contato.bloqueado)

    def test_falha_de_conexao_nao_marca_bounce(self):
        """Problema nosso (rede/senha) nao pode suprimir o endereco da pessoa."""
        contato = ContatoEmail.para("ok@exemplo.com")
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.side_effect = TimeoutError("timeout")
            email_envio.enviar(self.cfg, "ok@exemplo.com", "s", "c", contato=contato)
        contato.refresh_from_db()
        self.assertFalse(contato.bloqueado)

    # ---- Pagina publica de descadastro ----
    def test_pagina_descadastro_funciona_e_e_reversivel(self):
        contato = ContatoEmail.para("saida@exemplo.com")
        url = reverse("core:descadastrar", args=[contato.token])

        self.assertEqual(self.client.get(url).status_code, 200)   # publica, sem login

        self.client.post(url)
        contato.refresh_from_db()
        self.assertTrue(contato.descadastrado)

        self.client.post(url, {"acao": "reinscrever"})
        contato.refresh_from_db()
        self.assertFalse(contato.descadastrado)

    def test_descadastro_com_token_invalido_da_404(self):
        r = self.client.get(reverse("core:descadastrar", args=["naoexiste"]))
        self.assertEqual(r.status_code, 404)

    def test_descadastro_e_idempotente(self):
        contato = ContatoEmail.para("dup@exemplo.com")
        contato.descadastrar()
        contato.refresh_from_db()
        primeira = contato.descadastrado_em
        contato.descadastrar()
        contato.refresh_from_db()
        self.assertEqual(contato.descadastrado_em, primeira)

    # ---- Canal por notificacao ----
    def test_template_nasce_com_whatsapp_ligado_e_email_desligado(self):
        tpl = TemplateNotificacao.get_tipo("cadastro_novo")
        self.assertTrue(tpl.enviar_whatsapp)
        self.assertFalse(tpl.enviar_email)
        self.assertTrue(tpl.assunto)   # assunto padrao preenchido

    def test_salvar_template_grava_os_canais(self):
        self.client.force_login(self.diretor)
        self.client.post(reverse("core:whatsapp_templates"), {
            "tipo": "cadastro_novo", "ativo": "1", "enviar_email": "1",
            "mensagem": "Oi {nome}", "prompt_ia": "", "assunto": "Bem-vindo!",
        })
        tpl = TemplateNotificacao.get_tipo("cadastro_novo")
        self.assertTrue(tpl.enviar_email)
        self.assertFalse(tpl.enviar_whatsapp)   # nao veio no POST = desmarcado
        self.assertEqual(tpl.assunto, "Bem-vindo!")

    def test_assunto_vazio_cai_no_padrao(self):
        self.client.force_login(self.diretor)
        self.client.post(reverse("core:whatsapp_templates"), {
            "tipo": "cadastro_novo", "ativo": "1", "assunto": "",
            "mensagem": "Oi", "prompt_ia": "",
        })
        self.assertEqual(
            TemplateNotificacao.get_tipo("cadastro_novo").assunto,
            TemplateNotificacao.assunto_padrao("cadastro_novo"),
        )


class FanOutNotificacaoTests(TestCase):
    """Etapa 3: `_notificar` despacha para os canais marcados no template."""

    def setUp(self):
        wa = WhatsappConfig.get_solo()
        wa.instance_id = "X"
        wa.token = "Y"
        wa.base_url = "https://api.w-api.app/v1"
        wa.save()
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.save()
        self.tpl = TemplateNotificacao.get_tipo("cadastro_novo")
        self.tpl.ativo = True
        self.tpl.mensagem = "Ola {nome}, seu usuario e *{usuario}*"
        self.tpl.assunto = "Bem-vindo, {nome}"
        self.tpl.save()
        self.ctx = {"nome": "Ana", "usuario": "ana123"}

    def _chamar(self, **kw):
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")) as wa, \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")) as em:
            enviado, motivo = views._notificar("cadastro_novo", "5516999999999",
                                               self.ctx, **kw)
        return enviado, motivo, wa, em

    def test_so_whatsapp_por_padrao(self):
        enviado, _, wa, em = self._chamar(email="pai@exemplo.com")
        self.assertTrue(enviado)
        self.assertTrue(wa.called)
        self.assertFalse(em.called)   # enviar_email nasce desligado

    def test_os_dois_canais_quando_marcados(self):
        self.tpl.enviar_email = True
        self.tpl.save()
        enviado, motivo, wa, em = self._chamar(email="pai@exemplo.com")
        self.assertTrue(enviado)
        self.assertTrue(wa.called)
        self.assertTrue(em.called)
        self.assertIn("whatsapp:", motivo)
        self.assertIn("email:", motivo)

    def test_so_email_quando_whatsapp_desmarcado(self):
        self.tpl.enviar_whatsapp = False
        self.tpl.enviar_email = True
        self.tpl.save()
        _, _, wa, em = self._chamar(email="pai@exemplo.com")
        self.assertFalse(wa.called)
        self.assertTrue(em.called)

    def test_email_recebe_texto_sem_marcacao_do_whatsapp(self):
        self.tpl.enviar_email = True
        self.tpl.save()
        _, _, _, em = self._chamar(email="pai@exemplo.com")
        corpo = em.call_args[0][2]
        self.assertIn("ana123", corpo)
        self.assertNotIn("*", corpo)     # o *negrito* do WhatsApp foi removido

    def test_assunto_interpola_marcadores(self):
        self.tpl.enviar_email = True
        self.tpl.save()
        _, _, _, em = self._chamar(email="pai@exemplo.com")
        self.assertEqual(em.call_args[0][1], "Bem-vindo, Ana")

    def test_transacional_marcado_no_envio_de_email(self):
        self.tpl.enviar_email = True
        self.tpl.save()
        _, _, _, em = self._chamar(email="pai@exemplo.com")
        self.assertTrue(em.call_args.kwargs["transacional"])

    def test_sem_canal_util_nao_renderiza(self):
        """Sem número e sem e-mail não chega a chamar a IA nem montar texto."""
        with mock.patch("core.views._render_notificacao") as render:
            enviado, motivo = views._notificar("cadastro_novo", "", self.ctx)
        self.assertFalse(enviado)
        self.assertEqual(motivo, "sem_canal")
        self.assertFalse(render.called)

    def test_template_inativo_nao_envia_por_nenhum_canal(self):
        self.tpl.ativo = False
        self.tpl.enviar_email = True
        self.tpl.save()
        enviado, motivo, wa, em = self._chamar(email="pai@exemplo.com")
        self.assertFalse(enviado)
        self.assertEqual(motivo, "template_inativo")
        self.assertFalse(wa.called)
        self.assertFalse(em.called)

    def test_texto_renderizado_uma_vez_para_os_dois_canais(self):
        """A IA (quando ligada) não pode ser chamada duas vezes por notificação."""
        self.tpl.enviar_email = True
        self.tpl.save()
        with mock.patch("core.views._render_notificacao", return_value="txt") as render, \
             mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")), \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")):
            views._notificar("cadastro_novo", "5516999999999", self.ctx,
                             email="pai@exemplo.com")
        self.assertEqual(render.call_count, 1)

    def test_limpeza_da_marcacao(self):
        self.assertEqual(views.texto_para_email("Total: *R$ 10,00* hoje"),
                         "Total: R$ 10,00 hoje")
        # Underscore e til não são tocados (aparecem em e-mails e arquivos).
        self.assertEqual(views.texto_para_email("a_b ~c~"), "a_b ~c~")


class CobrancaPorEmailTests(TestCase):
    """Etapa 4: cobrança por e-mail, com contagem e filtro POR CANAL."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_cob", password="x")
        self.diretor.groups.add(grupo)
        self.client.force_login(self.diretor)

        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.save()
        wa = WhatsappConfig.get_solo()
        wa.instance_id = "X"
        wa.token = "Y"
        wa.base_url = "https://api.w-api.app/v1"
        wa.save()

        self.familia = User.objects.create_user("familia_cob", password="x")
        hoje = timezone.localdate()
        self.av = Aventureiro.objects.create(
            usuario=self.familia, nome_completo="Filho Um", sexo="M",
            data_nascimento=datetime.date(2015, 5, 5), cpf="C1",
            resp_nome="Mae Cobranca", resp_cpf="C2",
            resp_whatsapp="5516988887777", resp_email="mae@exemplo.com",
        )
        Mensalidade.objects.create(
            aventureiro=self.av, ano=hoje.year, mes=hoje.month,
            valor=Decimal("50.00"), status="aberta",
        )

    def test_familia_traz_email_e_contagem_por_canal(self):
        f = views._cobrancas_familias()[0]
        self.assertEqual(f["email"], "mae@exemplo.com")
        self.assertTrue(f["tem_email"])
        self.assertEqual(f["cobrado_mes_whatsapp"], 0)
        self.assertEqual(f["cobrado_mes_email"], 0)

    def test_envio_por_email_registra_o_canal(self):
        with mock.patch("core.views._enviar_email", return_value=(True, "enviado")) as em:
            r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), {
                "canal": "email", "usuario_id": self.familia.id,
            })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["enviados"], 1)
        reg = CobrancaEnviada.objects.get()
        self.assertEqual(reg.canal, "email")
        # Cobrança NÃO é transacional: respeita descadastro e leva List-Unsubscribe.
        self.assertFalse(em.call_args.kwargs["transacional"])

    def test_cobranca_por_email_nao_marca_o_whatsapp_como_enviado(self):
        """O bug que o campo `canal` existe para evitar."""
        with mock.patch("core.views._enviar_email", return_value=(True, "enviado")):
            self.client.post(reverse("core:mensalidade_cobranca_enviar"), {
                "canal": "email", "usuario_id": self.familia.id,
            })
        f = views._cobrancas_familias()[0]
        self.assertEqual(f["cobrado_mes_email"], 1)
        self.assertEqual(f["cobrado_mes_whatsapp"], 0)   # WhatsApp segue pendente

    def test_filtro_so_nao_enviados_e_por_canal(self):
        CobrancaEnviada.objects.create(
            usuario=self.familia, canal="email",
            ano=timezone.localdate().year, mes=timezone.localdate().month,
        )
        # Já cobrado por e-mail, mas o WhatsApp ainda deve sair.
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")):
            r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), {
                "canal": "whatsapp", "so_nao_enviados": "1",
            })
        self.assertEqual(r.json()["enviados"], 1)

    def test_descadastrado_nao_recebe_cobranca(self):
        ContatoEmail.para("mae@exemplo.com").descadastrar()
        r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), {
            "canal": "email", "usuario_id": self.familia.id,
        })
        d = r.json()
        self.assertEqual(d["enviados"], 0)
        self.assertIn("descadastrou-se", d["falhas"][0])
        self.assertFalse(CobrancaEnviada.objects.exists())

    def test_sem_email_configurado_recusa(self):
        cfg = EmailConfig.get_solo()
        cfg.senha = ""
        cfg.save()
        r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), {"canal": "email"})
        self.assertEqual(r.status_code, 400)

    def test_canal_invalido_recusa(self):
        r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), {"canal": "pombo"})
        self.assertEqual(r.status_code, 400)

    # ---- Canal "ambos" ----
    def _enviar_ambos(self, **extra):
        dados = {"canal": "ambos", "usuario_id": self.familia.id}
        dados.update(extra)
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")) as wa, \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")) as em:
            r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), dados)
        return r, wa, em

    def test_ambos_envia_pelos_dois_e_grava_dois_registros(self):
        r, wa, em = self._enviar_ambos()
        d = r.json()
        self.assertEqual(d["enviados"], 2)
        self.assertEqual(d["por_canal"], {"whatsapp": 1, "email": 1})
        self.assertTrue(wa.called)
        self.assertTrue(em.called)
        canais = sorted(CobrancaEnviada.objects.values_list("canal", flat=True))
        self.assertEqual(canais, ["email", "whatsapp"])

    def test_ambos_gera_a_mensagem_uma_vez_so(self):
        """Com a IA ligada, gerar por canal dobraria o custo e mandaria textos
        diferentes para a mesma pessoa."""
        with mock.patch("core.views._montar_mensagem_cobranca", return_value="msg") as m, \
             mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")), \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")):
            self.client.post(reverse("core:mensalidade_cobranca_enviar"),
                             {"canal": "ambos", "usuario_id": self.familia.id})
        self.assertEqual(m.call_count, 1)

    def test_ambos_com_filtro_manda_so_pelo_canal_que_falta(self):
        """Já cobrada por WhatsApp: em 'ambos' com o filtro, sai só o e-mail."""
        CobrancaEnviada.objects.create(
            usuario=self.familia, canal="whatsapp",
            ano=timezone.localdate().year, mes=timezone.localdate().month,
        )
        r, wa, em = self._enviar_ambos(so_nao_enviados="1")
        d = r.json()
        self.assertEqual(d["por_canal"], {"whatsapp": 0, "email": 1})
        self.assertFalse(wa.called)      # não duplica o WhatsApp
        self.assertTrue(em.called)

    def test_ambos_sem_filtro_manda_pelos_dois_mesmo_ja_cobrado(self):
        CobrancaEnviada.objects.create(
            usuario=self.familia, canal="whatsapp",
            ano=timezone.localdate().year, mes=timezone.localdate().month,
        )
        r, wa, em = self._enviar_ambos()
        self.assertEqual(r.json()["enviados"], 2)
        self.assertTrue(wa.called)

    def test_ambos_respeita_descadastro_no_email_e_manda_o_whatsapp(self):
        ContatoEmail.para("mae@exemplo.com").descadastrar()
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")) as wa:
            r = self.client.post(reverse("core:mensalidade_cobranca_enviar"),
                                 {"canal": "ambos", "usuario_id": self.familia.id})
        d = r.json()
        self.assertEqual(d["por_canal"], {"whatsapp": 1, "email": 0})
        self.assertTrue(wa.called)
        self.assertTrue(any("descadastrou-se" in x for x in d["falhas"]))

    def test_ambos_continua_se_um_canal_nao_esta_configurado(self):
        """E-mail desconfigurado não pode abortar o lote inteiro."""
        cfg = EmailConfig.get_solo()
        cfg.senha = ""
        cfg.save()
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")) as wa:
            r = self.client.post(reverse("core:mensalidade_cobranca_enviar"),
                                 {"canal": "ambos", "usuario_id": self.familia.id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["por_canal"], {"whatsapp": 1, "email": 0})
        self.assertTrue(wa.called)

    def test_ambos_recusa_se_nenhum_canal_configurado(self):
        cfg = EmailConfig.get_solo()
        cfg.senha = ""
        cfg.save()
        wa = WhatsappConfig.get_solo()
        wa.token = ""
        wa.save()
        r = self.client.post(reverse("core:mensalidade_cobranca_enviar"), {"canal": "ambos"})
        self.assertEqual(r.status_code, 400)

    def test_seletor_tem_a_opcao_ambos(self):
        html = self.client.get(reverse("core:mensalidades") + "?aba=cobrancas").content.decode()
        self.assertIn('<option value="ambos"', html)

    def test_seletor_de_canal_nao_usa_a_classe_do_seletor_de_telefone(self):
        """Regressão: o seletor de canal chegou a nascer com a classe
        `mens-cob-tel-sel`, o que fazia trocar o canal disparar o POST que muda o
        telefone de cobrança da família."""
        html = self.client.get(reverse("core:mensalidades") + "?aba=cobrancas").content.decode()
        i = html.index('id="cobrancaCanal"')
        tag = html[html.rindex("<select", 0, i):html.index(">", i) + 1]
        self.assertIn("mens-cob-canal-sel", tag)
        self.assertNotIn("mens-cob-tel-sel", tag)

    def test_registro_antigo_conta_como_whatsapp(self):
        """Compatibilidade: cobranças gravadas antes do campo `canal`."""
        reg = CobrancaEnviada.objects.create(
            usuario=self.familia,
            ano=timezone.localdate().year, mes=timezone.localdate().month,
        )
        self.assertEqual(reg.canal, "whatsapp")


class ConfirmacaoAutorizacaoTests(TestCase):
    """Resposta automática da autorização: idempotente, com retry e com log."""

    def setUp(self):
        cfg = WhatsappConfig.get_solo()
        cfg.instance_id = "X"
        cfg.token = "Y"
        cfg.base_url = "https://api.w-api.app/v1"
        cfg.mensagem_autorizacao = "Autorizo o clube a me enviar mensagens"
        cfg.resposta_autorizacao = "Obrigado! Voce foi liberado."
        cfg.save()
        self.cfg = cfg

        self.user = User.objects.create_user("resp_auth", password="x")
        Aventureiro.objects.create(
            usuario=self.user, nome_completo="Filho Auth", sexo="M",
            data_nascimento=datetime.date(2015, 2, 2), cpf="AUTH1",
            resp_nome="Resp Auth", resp_cpf="AUTH2",
            resp_whatsapp="5516991112222", resp_email="auth@exemplo.com",
        )
        self.numero = "5516991112222"

    def _mensagem(self, texto, envio=(True, "ok")):
        with mock.patch("core.views._enviar_whatsapp", return_value=envio) as env:
            views._registrar_contato_whatsapp(self.numero, texto)
        return env

    def _perfil(self):
        return PerfilUsuario.objects.get(usuario=self.user)

    def test_autorizacao_envia_confirmacao_e_marca(self):
        env = self._mensagem(self.cfg.mensagem_autorizacao)
        p = self._perfil()
        self.assertIsNotNone(p.autorizacao_recebida_em)
        self.assertIsNotNone(p.confirmacao_autorizacao_em)
        self.assertTrue(env.called)

    def test_nao_reenvia_em_mensagens_seguintes(self):
        self._mensagem(self.cfg.mensagem_autorizacao)
        env = self._mensagem("oi, tudo bem?")
        self.assertFalse(env.called)      # ja confirmado, nao repete

    def test_falha_no_envio_deixa_pendente_e_nao_marca(self):
        """O bug que motivou a mudança: falha transitória sumia em silêncio."""
        self._mensagem(self.cfg.mensagem_autorizacao, envio=(False, "timeout"))
        p = self._perfil()
        self.assertIsNotNone(p.autorizacao_recebida_em)   # autorizou
        self.assertIsNone(p.confirmacao_autorizacao_em)   # mas nao confirmou

    def test_retry_na_proxima_mensagem_apos_falha(self):
        self._mensagem(self.cfg.mensagem_autorizacao, envio=(False, "timeout"))
        env = self._mensagem("oi")                        # qualquer mensagem
        self.assertTrue(env.called)                       # tentou de novo
        self.assertIsNotNone(self._perfil().confirmacao_autorizacao_em)

    def test_excecao_no_envio_nao_derruba_o_webhook(self):
        with mock.patch("core.views._enviar_whatsapp", side_effect=RuntimeError("boom")):
            views._registrar_contato_whatsapp(self.numero, self.cfg.mensagem_autorizacao)
        p = self._perfil()
        self.assertIsNotNone(p.autorizacao_recebida_em)
        self.assertIsNone(p.confirmacao_autorizacao_em)   # segue pendente

    def test_sem_resposta_configurada_nao_envia(self):
        self.cfg.resposta_autorizacao = ""
        self.cfg.save()
        env = self._mensagem(self.cfg.mensagem_autorizacao)
        self.assertFalse(env.called)

    def test_mensagem_qualquer_nao_autoriza(self):
        env = self._mensagem("bom dia")
        self.assertIsNone(self._perfil().autorizacao_recebida_em)
        self.assertFalse(env.called)

    def test_marcar_autorizado_manualmente_nao_gera_resposta_depois(self):
        """Quem foi liberado à mão autorizou por fora — não pode receber a
        confirmação automática do nada na próxima mensagem."""
        grupo = Group.objects.create(name="Diretor")
        diretor = User.objects.create_user("dir_auth", password="x")
        diretor.groups.add(grupo)
        self.client.force_login(diretor)

        self.client.post(reverse("core:whatsapp_liberar"), {"usuario_id": self.user.id})
        p = self._perfil()
        self.assertIsNotNone(p.autorizacao_recebida_em)
        self.assertIsNotNone(p.confirmacao_autorizacao_em)

        env = self._mensagem("oi")
        self.assertFalse(env.called)

    def test_migration_fecha_o_passado(self):
        """Quem já estava autorizado antes do campo não pode receber 2ª resposta."""
        p = PerfilUsuario.objects.create(
            usuario=User.objects.create_user("antigo", password="x"),
            autorizacao_recebida_em=timezone.now(),
        )
        # Simula o estado pós-migration (o backfill roda no deploy).
        PerfilUsuario.objects.filter(pk=p.pk).update(
            confirmacao_autorizacao_em=p.autorizacao_recebida_em
        )
        p.refresh_from_db()
        enviou, motivo = views._confirmar_autorizacao(p, "5516999999999")
        self.assertFalse(enviou)
        self.assertEqual(motivo, "ja_confirmado")


class AniversariantesTests(TestCase):
    """Lista unificada dos três perfis, com deduplicação de quem tem mais de um."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_aniv", password="x")
        self.diretor.groups.add(grupo)
        self.client.force_login(self.diretor)

        self.conta = User.objects.create_user("familia_aniv", password="x")
        self.av = Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Crianca Um", sexo="M",
            data_nascimento=datetime.date(2015, 3, 10), cpf="11111111111",
            resp_nome="Mae Um", resp_cpf="22222222222",
            resp_whatsapp="5516991110001", resp_email="mae@exemplo.com",
            resp_data_nascimento=datetime.date(1985, 7, 20),
        )

    def _nomes(self):
        return [x["nome"] for x in views._aniversariantes()]

    def test_junta_aventureiro_e_responsavel(self):
        nomes = self._nomes()
        self.assertIn("Crianca Um", nomes)
        self.assertIn("Mae Um", nomes)

    def test_responsavel_sem_data_fica_de_fora(self):
        self.av.resp_data_nascimento = None
        self.av.save()
        self.assertNotIn("Mae Um", self._nomes())

    def test_inativo_e_demo_nao_entram(self):
        self.av.ativo = False
        self.av.save()
        nomes = self._nomes()
        self.assertNotIn("Crianca Um", nomes)
        self.assertNotIn("Mae Um", nomes)   # responsável do inativo também sai

    def test_mesma_pessoa_em_duas_criancas_aparece_uma_vez(self):
        """Mãe de dois filhos não pode receber duas mensagens."""
        Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Crianca Dois", sexo="F",
            data_nascimento=datetime.date(2017, 5, 5), cpf="33333333333",
            resp_nome="Mae Um", resp_cpf="22222222222",
            resp_whatsapp="5516991110001", resp_email="mae@exemplo.com",
            resp_data_nascimento=datetime.date(1985, 7, 20),
        )
        self.assertEqual(self._nomes().count("Mae Um"), 1)

    def test_diretoria_vence_responsavel_quando_e_a_mesma_pessoa(self):
        """Mesmo CPF nos dois perfis: entra como diretoria, e a tela avisa."""
        u = User.objects.create_user("dupla", password="x")
        MembroDiretoria.objects.create(
            usuario=u, nome_completo="Mae Um", cpf="22222222222",
            whatsapp="5516991110001", email="mae@exemplo.com",
            data_nascimento=datetime.date(1985, 7, 20),
        )
        itens = [x for x in views._aniversariantes() if x["nome"] == "Mae Um"]
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["perfil"], "diretoria")
        # A tela mostra o rótulo, não a chave técnica ("responsavel", sem acento).
        self.assertIn("Responsável", itens[0]["tambem_em"])

    def test_crianca_nao_e_engolida_pelo_responsavel(self):
        """Regressão: a criança usa o WhatsApp do responsável, então uma chave de
        identidade baseada em telefone fazia mãe e filho colidirem — e o filho
        sumia da lista, absorvido pela mãe."""
        av2 = Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Sem Cpf Proprio", sexo="F",
            data_nascimento=datetime.date(2018, 9, 9), cpf="",   # sem CPF
            resp_nome="Mae Um", resp_cpf="22222222222",
            resp_whatsapp="5516991110001",                        # MESMO da mãe
            resp_data_nascimento=datetime.date(1985, 7, 20),
        )
        nomes = self._nomes()
        self.assertIn("Sem Cpf Proprio", nomes)
        self.assertIn("Mae Um", nomes)
        self.assertEqual(nomes.count("Mae Um"), 1)
        item = [x for x in views._aniversariantes() if x["nome"] == av2.nome_completo][0]
        self.assertEqual(item["perfil"], "aventureiro")

    def test_dois_irmaos_com_cpf_vazio_aparecem_os_dois(self):
        for i, nome in enumerate(("Irmao A", "Irmao B")):
            Aventureiro.objects.create(
                usuario=self.conta, nome_completo=nome, sexo="M",
                data_nascimento=datetime.date(2016, 4, 1 + i), cpf="",
                resp_nome="Mae Um", resp_cpf="22222222222",
                resp_whatsapp="5516991110001",
            )
        nomes = self._nomes()
        self.assertIn("Irmao A", nomes)
        self.assertIn("Irmao B", nomes)

    def test_idade_e_calculada_na_data_de_hoje(self):
        hoje = timezone.localdate()
        Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Faz Hoje", sexo="M",
            data_nascimento=datetime.date(hoje.year - 9, hoje.month, hoje.day),
            cpf="44444444444", resp_nome="Pai X", resp_cpf="55555555555",
            resp_whatsapp="5516991110002",
        )
        item = [x for x in views._aniversariantes() if x["nome"] == "Faz Hoje"][0]
        self.assertEqual(item["idade"], 9)
        self.assertTrue(item["faz_hoje"])

    def test_29_de_fevereiro_cai_em_28(self):
        Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Bissexto", sexo="F",
            data_nascimento=datetime.date(2016, 2, 29), cpf="66666666666",
            resp_nome="Pai Y", resp_cpf="77777777777", resp_whatsapp="5516991110003",
        )
        item = [x for x in views._aniversariantes() if x["nome"] == "Bissexto"][0]
        self.assertEqual((item["mes"], item["dia"]), (2, 28))

    def test_ordenado_por_mes_e_dia(self):
        lista = views._aniversariantes()
        chaves = [(x["mes"], x["dia"]) for x in lista]
        self.assertEqual(chaves, sorted(chaves))

    # ---- Tela ----
    def test_tela_exige_diretor(self):
        self.client.force_login(self.conta)
        r = self.client.get(reverse("core:aniversarios"))
        self.assertNotEqual(r.status_code, 200)

    def test_tela_lista_filtra_por_mes(self):
        r = self.client.get(reverse("core:aniversarios") + "?mes=3")
        self.assertContains(r, "Crianca Um")
        self.assertNotContains(r, "Mae Um")      # julho, não março
        r2 = self.client.get(reverse("core:aniversarios") + "?mes=7")
        self.assertContains(r2, "Mae Um")

    def test_mes_zero_mostra_o_ano_todo(self):
        r = self.client.get(reverse("core:aniversarios") + "?mes=0")
        self.assertContains(r, "Crianca Um")
        self.assertContains(r, "Mae Um")

    def test_mes_invalido_nao_quebra(self):
        for v in ("abc", "99", "-1"):
            self.assertEqual(
                self.client.get(reverse("core:aniversarios") + f"?mes={v}").status_code, 200
            )

    def test_nenhum_comentario_de_template_vaza_na_tela(self):
        """Regressão: `{# ... #}` do Django é de UMA linha. Escrito em várias, o
        texto vira conteúdo visível — aconteceu no bloco de ações da lista e no
        seletor de canal da cobrança."""
        for url in (reverse("core:aniversarios"),
                    reverse("core:aniversarios") + "?aba=mensagens",
                    reverse("core:mensalidades") + "?aba=cobrancas"):
            html = self.client.get(url).content.decode()
            self.assertNotIn("{#", html, f"comentário vazando em {url}")
            self.assertNotIn("#}", html, f"comentário vazando em {url}")

    def test_classes_das_abas_existem_no_css(self):
        """Regressão: as abas nasceram com as classes `abas`/`aba`, que não
        existiam em CSS nenhum — renderizavam como links sublinhados."""
        from pathlib import Path
        from django.conf import settings

        css = (Path(settings.BASE_DIR) / "static" / "css" / "aniversarios.css").read_text(
            encoding="utf-8"
        )
        html = self.client.get(reverse("core:aniversarios")).content.decode()
        for classe in ("aniv-abas", "aniv-aba", "aniv-aba-badge", "aniv-largo"):
            self.assertIn(classe, html, f"{classe} não está no HTML")
            self.assertIn(f".{classe}", css, f"{classe} usada no HTML mas ausente do CSS")

    def test_abas_marcam_a_ativa(self):
        for aba, esperado in (("", "🎈"), ("mensagens", "✏️"), ("envios", "📬")):
            html = self.client.get(
                reverse("core:aniversarios") + (f"?aba={aba}" if aba else "")
            ).content.decode()
            # A aba ativa é a única com aria-current.
            self.assertEqual(html.count('aria-current="page"'), 1)
            self.assertIn(esperado, html)

    def test_menu_tem_o_item(self):
        r = self.client.get(reverse("core:aniversarios"))
        self.assertIn("aniversarios", [i["id"] for i in r.context["menu_itens"]])

    def test_aviso_de_cobertura_conta_quem_falta(self):
        Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Sem Data", sexo="M",
            data_nascimento=datetime.date(2016, 1, 1), cpf="88888888888",
            resp_nome="Resp Sem Data", resp_cpf="99999999999",
            resp_whatsapp="5516991110009",
        )
        r = self.client.get(reverse("core:aniversarios"))
        self.assertGreaterEqual(r.context["cobertura"]["responsaveis_sem_data"], 1)

    # ---- Mensagens ----
    def test_templates_nascem_com_texto_padrao(self):
        r = self.client.get(reverse("core:aniversarios") + "?aba=mensagens")
        tipos = [t.tipo for t in r.context["templates"]]
        self.assertEqual(tipos, ["aventureiro", "responsavel", "diretoria"])
        for t in r.context["templates"]:
            self.assertTrue(t.mensagem)
            self.assertTrue(t.assunto)
            self.assertFalse(t.ativo)     # nasce desligado

    def test_salvar_mensagem(self):
        r = self.client.post(reverse("core:aniversario_template"), {
            "tipo": "aventureiro", "ativo": "1",
            "mensagem": "Parabens {nome}, {idade} anos!", "assunto": "Parabens!",
        })
        self.assertEqual(r.status_code, 302)
        t = TemplateAniversario.get_tipo("aventureiro")
        self.assertTrue(t.ativo)
        self.assertEqual(t.assunto, "Parabens!")

    def test_assunto_vazio_cai_no_padrao(self):
        self.client.post(reverse("core:aniversario_template"), {
            "tipo": "diretoria", "mensagem": "oi", "assunto": "",
        })
        self.assertTrue(TemplateAniversario.get_tipo("diretoria").assunto)

    def test_tipo_invalido_recusado(self):
        self.client.post(reverse("core:aniversario_template"), {
            "tipo": "inexistente", "mensagem": "x",
        })
        self.assertFalse(TemplateAniversario.objects.filter(tipo="inexistente").exists())


class EnvioAniversarioTests(TestCase):
    """Disparo da mensagem de aniversário: gates, trava anual e botão manual."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_env", password="x")
        self.diretor.groups.add(grupo)
        self.client.force_login(self.diretor)

        wa = WhatsappConfig.get_solo()
        wa.instance_id = "X"; wa.token = "Y"
        wa.base_url = "https://api.w-api.app/v1"; wa.save()
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"; cfg.senha = "x"; cfg.save()

        self.tpl = TemplateAniversario.get_tipo("aventureiro")
        self.tpl.ativo = True
        self.tpl.mensagem = "Parabens {nome}, {idade} anos!"
        self.tpl.save()

        hoje = timezone.localdate()
        self.conta = User.objects.create_user("fam_env", password="x")
        self.av = Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Nino Aniversario", sexo="M",
            data_nascimento=datetime.date(hoje.year - 10, hoje.month, hoje.day),
            cpf="ENV1", resp_nome="Mae Env", resp_cpf="ENV2",
            resp_whatsapp="5516991112233", resp_email="mae.env@exemplo.com",
        )
        # Liberado no gate do WhatsApp (escreveu ao clube).
        ContatoWhatsapp.objects.create(
            numero="5516991112233", ultima_msg_em=timezone.now(), total_msgs=1,
        )
        self.ano = hoje.year

    def _pessoa(self):
        return [p for p in views._aniversariantes() if p["nome"] == "Nino Aniversario"][0]

    def _enviar(self, **kw):
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")) as wa, \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")) as em:
            res = views._enviar_aniversario(self._pessoa(), **kw)
        return res, wa, em

    # ---- Canais e conteúdo ----
    def test_envia_pelos_dois_canais(self):
        res, wa, em = self._enviar()
        self.assertTrue(res["whatsapp"][0])
        self.assertTrue(res["email"][0])
        self.assertTrue(wa.called and em.called)
        self.assertEqual(EnvioAniversario.objects.filter(ok=True).count(), 2)

    def test_marcadores_sao_trocados(self):
        _, wa, _ = self._enviar()
        texto = wa.call_args[0][2]
        self.assertIn("Nino", texto)
        self.assertIn("10", texto)
        self.assertNotIn("{nome}", texto)

    def test_template_desligado_nao_envia(self):
        self.tpl.ativo = False
        self.tpl.save()
        res, wa, em = self._enviar()
        self.assertEqual(res, {"_": (False, "template_inativo")})
        self.assertFalse(wa.called or em.called)

    def test_canal_desmarcado_nao_envia(self):
        self.tpl.enviar_email = False
        self.tpl.save()
        res, wa, em = self._enviar()
        self.assertIn("whatsapp", res)
        self.assertNotIn("email", res)
        self.assertFalse(em.called)

    # ---- Trava anual ----
    def test_nao_envia_duas_vezes_no_mesmo_ano(self):
        self._enviar()
        res, wa, em = self._enviar()
        self.assertEqual(res["whatsapp"], (False, "ja_enviado"))
        self.assertEqual(res["email"], (False, "ja_enviado"))
        self.assertFalse(wa.called or em.called)
        self.assertEqual(EnvioAniversario.objects.filter(ok=True).count(), 2)

    def test_forcar_reenvia(self):
        self._enviar()
        res, wa, _ = self._enviar(forcar=True)
        self.assertTrue(res["whatsapp"][0])
        self.assertTrue(wa.called)

    def test_ano_seguinte_envia_de_novo(self):
        self._enviar()
        res, wa, _ = self._enviar(ano=self.ano + 1)
        self.assertTrue(res["whatsapp"][0])

    def test_falha_nao_queima_o_ano(self):
        """Erro de rede não pode impedir a pessoa de receber depois."""
        with mock.patch("core.views._enviar_whatsapp", return_value=(False, "timeout")), \
             mock.patch("core.views._enviar_email", return_value=(False, "timeout")):
            views._enviar_aniversario(self._pessoa())
        self.assertEqual(EnvioAniversario.objects.filter(ok=True).count(), 0)
        res, wa, _ = self._enviar()          # nova tentativa passa
        self.assertTrue(res["whatsapp"][0])

    # ---- Gates anti-spam ----
    def test_whatsapp_barrado_para_quem_nunca_escreveu(self):
        ContatoWhatsapp.objects.all().delete()
        res, wa, em = self._enviar()
        self.assertEqual(res["whatsapp"], (False, "nao_liberado"))
        self.assertFalse(wa.called)
        self.assertTrue(res["email"][0])     # o e-mail continua

    def test_email_vai_como_nao_transacional(self):
        """Aniversário não é comprovante: respeita descadastro e leva
        List-Unsubscribe."""
        _, _, em = self._enviar()
        self.assertFalse(em.call_args.kwargs["transacional"])
        self.assertEqual(em.call_args.kwargs["origem"], "aniversario")

    def test_forcar_nao_fura_o_gate_do_whatsapp(self):
        ContatoWhatsapp.objects.all().delete()
        res, wa, _ = self._enviar(forcar=True)
        self.assertEqual(res["whatsapp"], (False, "nao_liberado"))
        self.assertFalse(wa.called)

    def test_descadastrado_no_email_ainda_recebe_no_whatsapp(self):
        ContatoEmail.para("mae.env@exemplo.com").descadastrar()
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")) as wa:
            res = views._enviar_aniversario(self._pessoa())
        self.assertTrue(res["whatsapp"][0])
        self.assertFalse(res["email"][0])
        self.assertTrue(wa.called)

    # ---- Botão manual ----
    def test_botao_manual_envia_e_registra_quem_clicou(self):
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")), \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")):
            r = self.client.post(reverse("core:aniversario_enviar"),
                                 {"chave": self._pessoa()["chave"]})
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual(sorted(d["enviados"]), ["email", "whatsapp"])
        reg = EnvioAniversario.objects.filter(ok=True).first()
        self.assertTrue(reg.manual)
        self.assertEqual(reg.enviado_por, self.diretor)

    def test_botao_manual_com_chave_inexistente(self):
        r = self.client.post(reverse("core:aniversario_enviar"), {"chave": "nao-existe"})
        self.assertEqual(r.status_code, 404)

    def test_botao_manual_exige_diretor(self):
        self.client.force_login(self.conta)
        r = self.client.post(reverse("core:aniversario_enviar"), {"chave": "x"})
        self.assertNotEqual(r.status_code, 200)

    # ---- Tela ----
    def test_tela_marca_quem_ja_recebeu(self):
        self._enviar()
        r = self.client.get(reverse("core:aniversarios"))
        pessoa = [p for p in r.context["lista"] if p["nome"] == "Nino Aniversario"][0]
        self.assertTrue(pessoa["enviado_whatsapp"])
        self.assertTrue(pessoa["enviado_email"])

    def test_aba_envios_lista_o_historico(self):
        self._enviar()
        r = self.client.get(reverse("core:aniversarios") + "?aba=envios")
        self.assertContains(r, "Nino Aniversario")
        self.assertContains(r, "Últimos envios de aniversário")

    # ---- Comando de cron ----
    def test_comando_envia_so_quem_faz_hoje(self):
        Aventureiro.objects.create(
            usuario=self.conta, nome_completo="Outro Mes", sexo="F",
            data_nascimento=datetime.date(2015, 1, 1) if timezone.localdate().month != 1
            else datetime.date(2015, 6, 1),
            cpf="ENV9", resp_nome="Mae Env", resp_cpf="ENV2",
            resp_whatsapp="5516991112233",
        )
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")), \
             mock.patch("core.views._enviar_email", return_value=(True, "enviado")):
            call_command("enviar_aniversarios", "--pausa", "0", stdout=out)
        self.assertIn("Nino Aniversario", out.getvalue())
        self.assertNotIn("Outro Mes", out.getvalue())

    def test_comando_e_idempotente(self):
        from django.core.management import call_command
        from io import StringIO
        for _ in range(2):
            with mock.patch("core.views._enviar_whatsapp", return_value=(True, "ok")), \
                 mock.patch("core.views._enviar_email", return_value=(True, "enviado")):
                call_command("enviar_aniversarios", "--pausa", "0", stdout=StringIO())
        self.assertEqual(EnvioAniversario.objects.filter(ok=True).count(), 2)

    def test_dry_run_nao_envia(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("enviar_aniversarios", "--dry-run", stdout=out)
        self.assertIn("simulação", out.getvalue())
        self.assertEqual(EnvioAniversario.objects.count(), 0)


class LogEmailTests(TestCase):
    """Extrato de envios da tela /email/."""

    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.diretor = User.objects.create_user("dir_log", password="x")
        self.diretor.groups.add(grupo)
        self.client.force_login(self.diretor)
        cfg = EmailConfig.get_solo()
        cfg.usuario = "clube@gmail.com"
        cfg.senha = "x"
        cfg.save()
        self.cfg = cfg

    def test_envio_bem_sucedido_vira_linha(self):
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.return_value = 1
            email_envio.enviar(self.cfg, "a@x.com", "Oi", "Corpo", origem="teste")
        log = LogEmail.objects.get()
        self.assertTrue(log.ok)
        self.assertEqual(log.para, "a@x.com")
        self.assertEqual(log.assunto, "Oi")
        self.assertEqual(log.rotulo_origem, "Teste")

    def test_falha_vira_linha_com_motivo(self):
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.side_effect = TimeoutError("estourou")
            email_envio.enviar(self.cfg, "a@x.com", "Oi", "Corpo", origem="cobranca")
        log = LogEmail.objects.get()
        self.assertFalse(log.ok)
        self.assertIn("tempo esgotado", log.detalhe)
        self.assertEqual(log.rotulo_origem, "Cobrança")

    def test_barrado_pelo_gate_tambem_aparece(self):
        """Descadastrado não some em silêncio — o Diretor precisa ver o motivo."""
        ContatoEmail.para("saiu@x.com").descadastrar()
        views._enviar_email("saiu@x.com", "Cobranca", "Corpo", origem="cobranca")
        log = LogEmail.objects.get()
        self.assertFalse(log.ok)
        self.assertIn("descadastrou-se", log.detalhe)

    def test_rotulo_de_notificacao_usa_o_nome_do_template(self):
        LogEmail.registrar("a@x.com", "s", True, "enviado", "cadastro_novo")
        self.assertEqual(LogEmail.objects.get().rotulo_origem,
                         "Boas-vindas de novo cadastro")

    def test_corpo_nao_e_gravado(self):
        with mock.patch("core.email_envio.EmailMessage") as EM:
            EM.return_value.send.return_value = 1
            email_envio.enviar(self.cfg, "a@x.com", "Oi", "SEGREDO NO CORPO")
        campos = " ".join(str(v) for v in LogEmail.objects.values()[0].values())
        self.assertNotIn("SEGREDO", campos)

    def test_apara_o_excedente(self):
        for i in range(LogEmail.LIMITE + 60):
            LogEmail.registrar(f"n{i}@x.com", "s", True)
        self.assertLessEqual(LogEmail.objects.count(), LogEmail.LIMITE + 50)

    def test_tela_mostra_o_extrato(self):
        LogEmail.registrar("pai@exemplo.com", "Assunto Visivel", True, "enviado", "teste")
        r = self.client.get(reverse("core:email"))
        self.assertContains(r, "Últimos envios")
        self.assertContains(r, "pai@exemplo.com")
        self.assertContains(r, "Assunto Visivel")

    def test_tela_sem_envios_mostra_aviso(self):
        r = self.client.get(reverse("core:email"))
        self.assertContains(r, "Nenhum e-mail enviado ainda")


class FormasPagamentoEventoTests(TestCase):
    """Cada evento escolhe o que aceita no site: so Pix, so cartao ou os dois."""

    def setUp(self):
        self.evento = Evento.objects.create(
            tipo="inscricao",
            nome="Acampamento",
            local="Sede",
            data=timezone.localdate() + datetime.timedelta(days=10),
            inscricao_aberta_publico=True,
        )
        self.produto = ProdutoEvento.objects.create(evento=self.evento, nome="Lanche")
        self.var = VariacaoProduto.objects.create(
            produto=self.produto, nome="Unidade", valor=Decimal("20.00")
        )
        self.loja_url = reverse("core:evento_loja", args=[self.evento.id])

    def _comprar(self, forma):
        return self.client.post(self.loja_url, {
            "comprador_nome": "Fulano",
            "comprador_whatsapp": "16999990000",
            "comprador_email": "f@exemplo.com",
            "forma_pagamento": forma,
            f"qtd_{self.var.id}": "1",
        })

    # --- o padrao nao muda o comportamento antigo ---

    def test_padrao_e_ambas_as_formas(self):
        self.assertEqual(self.evento.formas_pagamento_online, "ambos")
        self.assertEqual(
            [f[0] for f in self.evento.formas_online()], ["pix", "cartao"]
        )

    # --- filtragem por evento ---

    def test_somente_pix_esconde_o_cartao(self):
        self.evento.formas_pagamento_online = "pix"
        self.evento.save()
        self.assertEqual([f[0] for f in self.evento.formas_online()], ["pix"])
        self.assertTrue(self.evento.aceita_forma_online("pix"))
        self.assertFalse(self.evento.aceita_forma_online("cartao"))

    def test_somente_cartao_esconde_o_pix(self):
        self.evento.formas_pagamento_online = "cartao"
        self.evento.save()
        self.assertEqual([f[0] for f in self.evento.formas_online()], ["cartao"])
        self.assertFalse(self.evento.aceita_forma_online("pix"))

    # --- a tela reflete a escolha ---

    def test_lojinha_so_mostra_a_forma_liberada(self):
        self.evento.formas_pagamento_online = "pix"
        self.evento.save()
        r = self.client.get(self.loja_url)
        self.assertContains(r, 'value="pix"')
        self.assertNotContains(r, 'value="cartao"')

    def test_lojinha_com_ambos_mostra_as_duas(self):
        r = self.client.get(self.loja_url)
        self.assertContains(r, 'value="pix"')
        self.assertContains(r, 'value="cartao"')

    # --- o servidor nao confia no HTML ---

    def test_post_com_forma_bloqueada_nao_fecha_o_pedido(self):
        """Esconder o radio nao basta: o POST forjado tem que ser recusado."""
        self.evento.formas_pagamento_online = "pix"
        self.evento.save()
        resp = self._comprar("cartao")
        self.assertEqual(resp.status_code, 200)  # voltou para o formulario
        self.assertNotIn("loja_checkout", self.client.session)
        self.assertContains(resp, "apenas por Pix")

    def test_post_com_forma_liberada_segue_para_o_pagamento(self):
        self.evento.formas_pagamento_online = "pix"
        self.evento.save()
        resp = self._comprar("pix")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("loja_checkout", self.client.session)

    # --- configuracao pelo Diretor ---

    def test_config_do_evento_tem_o_campo(self):
        diretor = User.objects.create_user("diretor_formas", password="x")
        grupo, _ = Group.objects.get_or_create(name="Diretor")
        diretor.groups.add(grupo)
        self.client.force_login(diretor)
        r = self.client.get(reverse("core:evento_painel", args=[self.evento.id]))
        self.assertContains(r, "formas_pagamento_online")
        self.assertContains(r, "Somente Pix")


class PagamentoPorForaTests(TestCase):
    """Evento pago direto ao evento (ex.: Aventuri): a inscricao e confirmada sem
    cobrar, fica como pagamento pendente e o valor NAO entra em caixa nenhum."""

    def setUp(self):
        self.diretor = User.objects.create_user("dir_fora", password="x")
        self.diretor.groups.add(Group.objects.get_or_create(name="Diretor")[0])
        cfg = MercadoPagoConfig.get_solo()
        cfg.modo = "teste"
        cfg.access_token_teste = "TEST-abc"
        cfg.webhook_secret_teste = "s"
        cfg.save()
        self.ev = Evento.objects.create(
            tipo="inscricao", nome="Aventuri", local="Campo",
            data=timezone.localdate() + datetime.timedelta(days=10),
            inscricao_aberta_publico=True, formas_pagamento_online="pix",
        )
        FaixaEtariaPreco.objects.create(
            evento=self.ev, idade_min=1, idade_max=99, valor=Decimal("50.00")
        )

    def _ligar_por_fora(self, instrucoes="Pix direto para a organizacao."):
        self.ev.pagamento_por_fora = True
        self.ev.instrucoes_pagamento_fora = instrucoes
        self.ev.save(update_fields=["pagamento_por_fora", "instrucoes_pagamento_fora"])

    def _post(self):
        return {
            "responsavel_nome": "Mae", "responsavel_whatsapp": "4799",
            "responsavel_email": "m@exemplo.com", "responsavel_cpf": "111",
            "part_idx": ["0"], "part_nome_0": "Crianca", "part_idade_0": "10",
            "forma_pagamento": "pix",
        }

    def _inscrever(self):
        resp = self.client.post(
            reverse("core:evento_inscrever", args=[self.ev.id]), self._post()
        )
        self.assertEqual(resp.status_code, 302)
        return Inscricao.objects.get()

    def test_confirma_na_hora_sem_passar_pela_fatura(self):
        self._ligar_por_fora()
        insc = self._inscrever()
        self.assertEqual(insc.status, "confirmada")
        self.assertTrue(insc.pagamento_externo)
        self.assertIsNone(insc.pago_externo_em)      # nasce pendente
        self.assertEqual(insc.forma_pagamento, "pix")
        self.assertEqual(insc.valor_total, Decimal("50.00"))
        self.assertEqual(Pagamento.objects.count(), 0)   # nao passou pelo MP

    def test_sucesso_mostra_a_orientacao_cadastrada(self):
        self._ligar_por_fora("Pix para a chave do Aventuri.")
        self._inscrever()
        html = self.client.get(
            reverse("core:evento_inscricao_sucesso", args=[self.ev.id])
        ).content.decode()
        self.assertIn("Pix para a chave do Aventuri.", html)
        self.assertIn("Pagamento pendente", html)

    def test_pagina_de_inscricao_avisa_e_orienta(self):
        self._ligar_por_fora("Envie o comprovante no grupo.")
        html = self.client.get(
            reverse("core:evento_inscrever", args=[self.ev.id])
        ).content.decode()
        self.assertIn("pagamento é feito direto ao evento", html)
        self.assertIn("Envie o comprovante no grupo.", html)

    def test_fica_fora_do_caixa_do_evento_e_do_clube(self):
        self._ligar_por_fora()
        self._inscrever()
        self.client.force_login(self.diretor)

        painel = self.client.get(reverse("core:evento_painel", args=[self.ev.id]))
        self.assertEqual(painel.context["resumo"]["arrecadacao_inscricoes"], Decimal("0"))
        self.assertEqual(painel.context["resumo"]["receitas"], Decimal("0"))
        self.assertEqual(painel.context["resumo"]["inscritos"], 1)   # a pessoa conta
        self.assertEqual(painel.context["externo"]["pendente"], Decimal("50.00"))
        self.assertEqual(painel.context["externo"]["pago"], Decimal("0"))

        fin = self.client.get(reverse("core:financeiro"))
        self.assertEqual(fin.context["resumo"]["eventos"]["inscricoes"], Decimal("0"))

    def test_marcar_pago_nao_joga_o_valor_no_caixa(self):
        self._ligar_por_fora()
        insc = self._inscrever()
        self.client.force_login(self.diretor)
        url = reverse("core:evento_inscricao_pago", args=[self.ev.id, insc.id])

        self.client.post(url)
        insc.refresh_from_db()
        self.assertIsNotNone(insc.pago_externo_em)
        self.assertEqual(insc.pago_externo_por_id, self.diretor.id)

        painel = self.client.get(reverse("core:evento_painel", args=[self.ev.id]))
        self.assertEqual(painel.context["resumo"]["arrecadacao_inscricoes"], Decimal("0"))
        self.assertEqual(painel.context["externo"]["pago"], Decimal("50.00"))
        self.assertEqual(painel.context["externo"]["pendente"], Decimal("0"))

        # O mesmo botao desfaz a baixa.
        self.client.post(url)
        insc.refresh_from_db()
        self.assertIsNone(insc.pago_externo_em)
        self.assertIsNone(insc.pago_externo_por_id)

    def test_marcar_pago_recusa_inscricao_normal(self):
        """So inscricao paga por fora tem baixa manual — a normal ja foi cobrada."""
        insc = Inscricao.objects.create(
            evento=self.ev, responsavel_nome="Pai",
            codigo=Inscricao.gerar_codigo_unico(), valor_total=Decimal("50.00"),
        )
        self.client.force_login(self.diretor)
        self.client.post(
            reverse("core:evento_inscricao_pago", args=[self.ev.id, insc.id])
        )
        insc.refresh_from_db()
        self.assertIsNone(insc.pago_externo_em)

    def test_lojinha_junto_herda_o_fora_do_caixa(self):
        """Camiseta levada na inscricao por fora tambem nao foi cobrada."""
        self._ligar_por_fora()
        produto = ProdutoEvento.objects.create(evento=self.ev, nome="Camiseta")
        var = VariacaoProduto.objects.create(
            produto=produto, nome="M", valor=Decimal("30.00")
        )
        dados = self._post()
        dados[f"qtd_{var.id}"] = "1"
        self.client.post(reverse("core:evento_inscrever", args=[self.ev.id]), dados)
        pedido = PedidoLoja.objects.get()
        self.assertTrue(pedido.pagamento_externo)

        self.client.force_login(self.diretor)
        painel = self.client.get(reverse("core:evento_painel", args=[self.ev.id]))
        self.assertEqual(painel.context["resumo"]["vendas_loja"], Decimal("0"))
        self.assertEqual(painel.context["externo"]["total"], Decimal("80.00"))

    def test_forma_forjada_cai_na_liberada(self):
        """POST com forma que o evento nao aceita nao muda o registro."""
        self._ligar_por_fora()
        dados = self._post()
        dados["forma_pagamento"] = "cartao"     # evento e "somente Pix"
        self.client.post(reverse("core:evento_inscrever", args=[self.ev.id]), dados)
        insc = Inscricao.objects.get()
        self.assertTrue(insc.pagamento_externo)
        self.assertEqual(insc.forma_pagamento, "pix")
        self.assertEqual(Pagamento.objects.count(), 0)

    def test_evento_sem_a_opcao_continua_cobrando_pelo_site(self):
        """Regressao: quem nao ligar a chave segue cobrando pelo Mercado Pago."""
        fake_pix = {
            "ok": True, "mp_payment_id": "MP-X", "status": "pendente",
            "qr_code": "PIX", "qr_code_base64": "B64", "ticket_url": "http://t",
        }
        with mock.patch.object(mp, "criar_pix", return_value=fake_pix):
            self.client.post(
                reverse("core:evento_inscrever", args=[self.ev.id]), self._post()
            )
        self.assertEqual(Pagamento.objects.count(), 1)
        self.assertEqual(Inscricao.objects.count(), 0)   # so cria ao aprovar

    def test_gratis_nao_vira_pagamento_pendente(self):
        """Sem valor nao ha o que pagar por fora — segue confirmando na hora."""
        self.ev.faixas_preco.all().delete()
        self._ligar_por_fora()
        insc = self._inscrever()
        self.assertFalse(insc.pagamento_externo)
        self.assertEqual(insc.valor_total, Decimal("0.00"))

    def test_config_do_evento_tem_os_campos(self):
        self.client.force_login(self.diretor)
        html = self.client.get(
            reverse("core:evento_painel", args=[self.ev.id])
        ).content.decode()
        self.assertIn("pagamento_por_fora", html)
        self.assertIn("instrucoes_pagamento_fora", html)

    def test_classes_novas_existem_no_css(self):
        """Regressao do defeito de Aniversarios: classe usada no HTML sem regra
        em CSS nenhum nao quebra teste — so renderiza feio."""
        from pathlib import Path

        from django.conf import settings

        css = (Path(settings.BASE_DIR) / "static" / "css" / "eventos.css").read_text(
            encoding="utf-8"
        )
        self._ligar_por_fora()
        self._inscrever()
        self.client.force_login(self.diretor)
        paginas = {
            reverse("core:evento_inscrever", args=[self.ev.id]): (
                "insc-forma-pagamento", "insc-forma-titulo", "insc-forma-opt",
                "insc-forma-instrucoes",
            ),
            reverse("core:evento_painel", args=[self.ev.id]): (
                "inscrito-acoes", "btn-marcar-pago", "pill-pendente",
                "fin-card-fora", "fin-card-acao", "lanc-fora", "lanc-selo-fora",
            ),
        }
        for url, classes in paginas.items():
            html = self.client.get(url).content.decode()
            for classe in classes:
                self.assertIn(classe, html, f"{classe} nao esta no HTML de {url}")
                self.assertIn(f".{classe}", css, f"{classe} ausente do CSS")


class ExtratoWhatsappTests(TestCase):
    """Extrato de saida do WhatsApp: quem recebeu e quem nao (aba 📨 Envios).

    A resposta do envio so diz que a W-API ACEITOU a mensagem; quem conta se ela
    chegou e o webhook de entrega, casado pelo messageId."""

    def setUp(self):
        grupo_dir, _ = Group.objects.get_or_create(name="Diretor")
        self.diretor = User.objects.create_user("dir_envios", password="x")
        self.diretor.groups.add(grupo_dir)
        cfg = WhatsappConfig.get_solo()
        cfg.instance_id = "INST"; cfg.token = "TOK"; cfg.save()
        self.cfg = cfg
        self.webhook_url = reverse("core:whatsapp_webhook")

    def _envio(self, message_id="MSG1", status=MSG_WA_ACEITA, numero="5516999990000"):
        return MensagemWhatsapp.objects.create(
            numero=numero, message_id=message_id, status=status, origem="cobranca",
            nome="Fulano de Tal",
        )

    def _status_payload(self, message_id, status, **extra):
        payload = {"event": "webhookDelivery", "messageId": message_id, "status": status}
        payload.update(extra)
        return payload

    def _postar(self, payload):
        return self.client.post(
            self.webhook_url, data=json.dumps(payload), content_type="application/json"
        )

    # --- registro no envio (ponto unico) ---

    def test_envio_com_sucesso_vira_linha_aceita_com_message_id(self):
        with mock.patch.object(views, "_wapi_post_texto", return_value=(True, "WAMID1")):
            ok, detalhe = views._enviar_whatsapp(self.cfg, "5516999990000", "oi", origem="teste")
        self.assertTrue(ok)
        linha = MensagemWhatsapp.objects.get()
        self.assertEqual(linha.status, MSG_WA_ACEITA)
        self.assertEqual(linha.message_id, "WAMID1")
        self.assertEqual(linha.origem, "teste")

    def test_falha_da_api_vira_linha_com_o_motivo(self):
        with mock.patch.object(
            views, "_wapi_post_texto", return_value=(False, "Erro 401: Whatsapp não conectado")
        ):
            ok, _ = views._enviar_whatsapp(self.cfg, "5516999990000", "oi", origem="cobranca")
        self.assertFalse(ok)
        linha = MensagemWhatsapp.objects.get()
        self.assertEqual(linha.status, MSG_WA_FALHOU)
        self.assertIn("401", linha.detalhe)
        self.assertTrue(linha.problema)

    def test_texto_da_mensagem_nunca_e_gravado(self):
        """Mesma regra do LogEmail: nao acumular dado pessoal a toa."""
        with mock.patch.object(views, "_wapi_post_texto", return_value=(True, "WAMID2")):
            views._enviar_whatsapp(self.cfg, "5516999990000", "segredo do aventureiro")
        campos = " ".join(
            str(v) for v in MensagemWhatsapp.objects.values().first().values()
        )
        self.assertNotIn("segredo", campos)

    # --- webhook de entrega ---

    def test_webhook_marca_entregue_e_depois_lida(self):
        self._envio("WAMID3")
        self._postar(self._status_payload("WAMID3", "RECEIVED"))
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_ENTREGUE)
        self._postar(self._status_payload("WAMID3", "READ"))
        linha = MensagemWhatsapp.objects.get()
        self.assertEqual(linha.status, MSG_WA_LIDA)
        self.assertTrue(linha.chegou)
        self.assertIsNotNone(linha.status_em)

    def test_status_nao_retrocede(self):
        """O WhatsApp manda os avisos fora de ordem; 'lida' nao pode virar 'entregue'."""
        self._envio("WAMID4", status=MSG_WA_LIDA)
        self._postar(self._status_payload("WAMID4", "DELIVERY_ACK"))
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_LIDA)

    def test_falha_do_whatsapp_vale_mesmo_depois(self):
        self._envio("WAMID5", status=MSG_WA_ENVIADA)
        self._postar(self._status_payload("WAMID5", "FAILED", reason="numero inexistente"))
        linha = MensagemWhatsapp.objects.get()
        self.assertEqual(linha.status, MSG_WA_NAO_ENTREGUE)
        self.assertIn("inexistente", linha.detalhe)

    def test_um_aviso_pode_atualizar_varias_mensagens(self):
        """O 'READ' costuma vir com uma lista de ids."""
        self._envio("A1"); self._envio("A2")
        self._postar({"event": "webhookDelivery", "ids": ["A1", "A2"], "status": "READ"})
        self.assertEqual(
            list(MensagemWhatsapp.objects.values_list("status", flat=True)),
            [MSG_WA_LIDA, MSG_WA_LIDA],
        )

    def test_status_de_mensagem_desconhecida_nao_quebra(self):
        r = self._postar(self._status_payload("NAO-EXISTE", "READ"))
        self.assertEqual(r.status_code, 200)

    # --- o ponto perigoso: status NAO pode virar "mensagem recebida" ---

    def test_aviso_de_status_nao_marca_contato_nem_autorizacao(self):
        """Se um payload de status entrasse como conversa, o termometro ficaria
        verde e a pessoa seria dada como autorizada sem ter escrito nada."""
        self._envio("WAMID6", numero="5516991112222")
        self._postar({
            "event": "webhookDelivery", "messageId": "WAMID6", "status": "READ",
            "phone": "5516991112222", "chat": {"id": "5516991112222"},
        })
        self.assertEqual(WhatsappWebhookEvent.objects.count(), 0)
        self.assertEqual(ContatoWhatsapp.objects.count(), 0)

    def test_mensagem_recebida_normal_continua_funcionando(self):
        """Regressao: o payload de conversa nao pode ser confundido com status."""
        self._postar({
            "event": "webhookReceived", "messageId": "R1", "fromMe": False,
            "isGroup": False, "chat": {"id": "5516993334444"},
            "sender": {"id": "5516993334444", "pushName": "Alguem"},
            "msgContent": {"conversation": "oi"},
        })
        self.assertEqual(WhatsappWebhookEvent.objects.count(), 1)

    # --- parser ---

    def test_parser_ignora_payload_sem_id_de_mensagem(self):
        ids, status, _ = wapi_parser.extrair_status({"event": "webhookDelivery", "status": "READ"})
        self.assertEqual((ids, status), ([], ""))

    # --- formato REAL da instancia (visto no webhook em producao) ---
    # A W-API manda DOIS eventos: `webhookDelivery` (eco da saida, SEM campo de
    # status) e `webhookStatus` (com status SERVER/DELIVERY/READ). Numeros aqui
    # sao ficticios de proposito — o repositorio e publico.

    def test_payload_real_webhook_status_server(self):
        self._envio("3EB0REAL1")
        self._postar({
            "event": "webhookStatus", "instanceId": "LITE-XXXX", "status": "SERVER",
            "messageId": "3EB0REAL1", "fromMe": True, "moment": 1786568130,
            "chat": {"id": "5599999999999"}, "isGroup": False,
        })
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_ENVIADA)
        self.assertEqual(WhatsappWebhookEvent.objects.count(), 0)

    def test_payload_real_webhook_status_delivery_e_read(self):
        self._envio("3EB0REAL2")
        base = {"event": "webhookStatus", "messageId": "3EB0REAL2", "fromMe": True}
        self._postar({**base, "status": "DELIVERY"})
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_ENTREGUE)
        self._postar({**base, "status": "READ"})
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_LIDA)

    def test_payload_real_webhook_delivery_sem_campo_de_status(self):
        """`webhookDelivery` chega sem `status`: vale como ENVIADA (saiu), nunca
        como entregue — quem confirma a chegada e o `webhookStatus` DELIVERY."""
        self._envio("3EB0REAL3")
        self._postar({
            "event": "webhookDelivery", "instanceId": "LITE-XXXX", "isGroup": False,
            "messageId": "3EB0REAL3", "fromMe": True,
            "chat": {"id": "5599999999999"}, "sender": {"id": "5599999999999"},
        })
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_ENVIADA)
        self.assertEqual(WhatsappWebhookEvent.objects.count(), 0)

    def test_evento_sem_status_e_sem_fromMe_nao_e_tratado_como_status(self):
        """Trava contra o pior caso: engolir uma mensagem RECEBIDA como se fosse
        aviso de entrega faria o clube perder a mensagem (e a autorizacao nela)."""
        ids, status, _ = wapi_parser.extrair_status({
            "event": "webhookDelivery", "messageId": "X1", "fromMe": False,
        })
        self.assertEqual((ids, status), ([], ""))

    def test_status_pendente_e_reconhecido_mas_nao_muda_nada(self):
        self._envio("3EB0REAL4")
        self._postar({"event": "webhookStatus", "messageId": "3EB0REAL4", "status": "PENDING"})
        self.assertEqual(MensagemWhatsapp.objects.get().status, MSG_WA_ACEITA)
        self.assertEqual(WhatsappWebhookEvent.objects.count(), 0)

    def test_parser_entende_ack_numerico(self):
        ids, status, _ = wapi_parser.extrair_status({"messageId": "X", "ack": 3})
        self.assertEqual((ids, status), (["X"], wapi_parser.STATUS_LIDA))

    # --- tela ---

    def test_aba_envios_mostra_quem_recebeu_e_quem_nao(self):
        self._envio("OK1", status=MSG_WA_ENTREGUE)
        MensagemWhatsapp.objects.create(
            numero="5516988887777", status=MSG_WA_FALHOU, origem="cobranca",
            nome="Sem Whats", detalhe="Erro 400: número inválido",
        )
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:whatsapp") + "?aba=envios")
        self.assertContains(r, "quem recebeu e quem não")
        self.assertContains(r, "Entregue")
        self.assertContains(r, "Falhou")
        self.assertContains(r, "número inválido")

    def test_filtro_mostra_so_quem_nao_recebeu(self):
        self._envio("OK2", status=MSG_WA_ENTREGUE, numero="5516900000001")
        MensagemWhatsapp.objects.create(numero="5516900000002", status=MSG_WA_NAO_ENTREGUE)
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:whatsapp") + "?aba=envios&filtro=problema")
        self.assertContains(r, "5516900000002")
        self.assertNotContains(r, "5516900000001")

    def test_avisa_quando_o_webhook_de_entrega_nao_confirma_nada(self):
        self._envio("SEM1")
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:whatsapp") + "?aba=envios")
        self.assertContains(r, "webhook de entrega ainda não está confirmando")

    def test_poda_mantem_o_limite(self):
        for i in range(MensagemWhatsapp.LIMITE + 60):
            MensagemWhatsapp.registrar(f"55169000{i:05d}", True, f"ID{i}")
        self.assertLessEqual(MensagemWhatsapp.objects.count(), MensagemWhatsapp.LIMITE + 50)


class TopDevedoresTests(TestCase):
    """Aba Resumo de Mensalidades: os 10 aventureiros que mais devem."""

    def setUp(self):
        grupo_dir, _ = Group.objects.get_or_create(name="Diretor")
        self.diretor = User.objects.create_user("dir_devedores", password="x")
        self.diretor.groups.add(grupo_dir)
        self.ano = timezone.localdate().year
        self.resp = User.objects.create_user("resp_devedores", password="x")

    def _aventureiro(self, nome, cpf, ativo=True, demo=False):
        return Aventureiro.objects.create(
            usuario=self.resp, nome_completo=nome, sexo="M",
            data_nascimento=datetime.date(2015, 1, 1), cpf=cpf,
            resp_nome="Mae " + nome, resp_cpf="r" + cpf, resp_whatsapp="4799",
            resp_email="m@exemplo.com", ativo=ativo, demo=demo,
        )

    def _deve(self, av, meses, valor="30.00", ano=None, isento=False, status="aberta"):
        for mes in meses:
            Mensalidade.objects.create(
                aventureiro=av, ano=ano or self.ano, mes=mes,
                valor=Decimal(valor), isento=isento, status=status,
            )

    # --- ranking ---

    def test_ordena_do_maior_para_o_menor(self):
        pouco = self._aventureiro("Ana Pouco", "1")
        muito = self._aventureiro("Bruno Muito", "2")
        self._deve(pouco, [1])
        self._deve(muito, [1, 2, 3])
        top = views._top_devedores(self.ano)
        self.assertEqual([d["nome"] for d in top], ["Bruno Muito", "Ana Pouco"])
        self.assertEqual(top[0]["total"], Decimal("90.00"))
        self.assertEqual(top[0]["meses"], 3)
        # A barra é relativa a quem deve mais.
        self.assertEqual(top[0]["pct"], 100)
        self.assertEqual(top[1]["pct"], 33)

    def test_limita_a_dez(self):
        for i in range(12):
            av = self._aventureiro(f"Aventureiro {i}", str(100 + i))
            self._deve(av, range(1, i + 2))
        self.assertEqual(len(views._top_devedores(self.ano)), 10)

    # --- regras do clube ---

    def test_inativo_nao_entra(self):
        """Regra do clube: aventureiro inativo nao e cobrado."""
        inativo = self._aventureiro("Carla Saiu", "3", ativo=False)
        self._deve(inativo, [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(views._top_devedores(self.ano), [])

    def test_demo_nao_entra(self):
        demo = self._aventureiro("Fake Demo", "4", demo=True)
        self._deve(demo, [1, 2, 3])
        self.assertEqual(views._top_devedores(self.ano), [])

    def test_isento_e_paga_nao_contam(self):
        av = self._aventureiro("Davi Isento", "5")
        self._deve(av, [1], isento=True)
        self._deve(av, [2], status="paga")
        self._deve(av, [3])
        top = views._top_devedores(self.ano)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0]["total"], Decimal("30.00"))
        self.assertEqual(top[0]["meses"], 1)

    # --- divida de outros anos ---

    def test_soma_outros_anos_e_separa_no_detalhe(self):
        """Quem deve mais e quem deve mais NO TOTAL — ignorar o ano anterior daria
        um ranking errado —, mas a linha separa o que e de outro ano."""
        av = self._aventureiro("Elisa Atrasada", "6")
        self._deve(av, [11, 12], ano=self.ano - 1)
        self._deve(av, [1])
        top = views._top_devedores(self.ano)
        self.assertEqual(top[0]["total"], Decimal("90.00"))
        self.assertEqual(top[0]["no_ano"], Decimal("30.00"))
        self.assertEqual(top[0]["outros_anos"], Decimal("60.00"))

    # --- tela ---

    def test_resumo_mostra_o_bloco(self):
        av = self._aventureiro("Fabio Devedor", "7")
        self._deve(av, [1, 2])
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:mensalidades"))
        self.assertContains(r, "quem está devendo mais")
        self.assertContains(r, "Fabio Devedor")
        self.assertContains(r, "2 meses em aberto")

    def test_sem_devedor_mostra_mensagem_boa(self):
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:mensalidades"))
        self.assertContains(r, "Ninguém com mensalidade em aberto")


class EventoInativoTests(TestCase):
    """Inativar um evento: sai do menu e fecha as telas publicas, mesmo dentro
    da data. O Diretor continua com painel/balco e nada do que ja aconteceu
    (inscricoes, pedidos, presenca, financeiro) e apagado."""

    def setUp(self):
        grupo_dir, _ = Group.objects.get_or_create(name="Diretor")
        self.diretor = User.objects.create_user("dir_inativo", password="x")
        self.diretor.groups.add(grupo_dir)

        self.resp = User.objects.create_user("resp_inativo", password="x")
        Aventureiro.objects.create(
            usuario=self.resp, nome_completo="Ana Souza", sexo="F",
            data_nascimento=datetime.date(2015, 1, 1), cpf="91",
            resp_nome="Mae Souza", resp_cpf="92", resp_whatsapp="4799",
            resp_email="mae@exemplo.com",
        )

        # Evento FUTURO e aberto ao publico: sem o campo `ativo`, tudo estaria aberto.
        self.evento = Evento.objects.create(
            tipo="inscricao",
            nome="Acampamento de Julho",
            local="Sede",
            data=timezone.localdate() + datetime.timedelta(days=10),
            inscricao_aberta_publico=True,
        )
        produto = ProdutoEvento.objects.create(evento=self.evento, nome="Lanche")
        self.var = VariacaoProduto.objects.create(
            produto=produto, nome="Unidade", valor=Decimal("20.00")
        )
        self.pagina_url = reverse("core:evento_pagina", args=[self.evento.id])
        self.inscrever_url = reverse("core:evento_inscrever", args=[self.evento.id])
        self.loja_url = reverse("core:evento_loja", args=[self.evento.id])
        self.ativar_url = reverse("core:evento_ativar", args=[self.evento.id])

    def _inativar(self):
        self.evento.ativo = False
        self.evento.save(update_fields=["ativo"])

    # --- o padrao nao muda o comportamento antigo ---

    def test_evento_nasce_ativo(self):
        self.assertTrue(self.evento.ativo)
        self.assertTrue(self.evento.inscricoes_abertas())
        self.assertTrue(self.evento.loja_aberta())

    # --- trava no model (vale para qualquer caminho, inclusive POST forjado) ---

    def test_inativo_fecha_inscricao_e_lojinha_mesmo_no_prazo(self):
        self._inativar()
        self.assertFalse(self.evento.inscricoes_abertas())
        self.assertFalse(self.evento.loja_aberta())

    # --- menu dos responsaveis ---

    def test_menu_esconde_o_evento_inativo(self):
        self.client.force_login(self.resp)
        r = self.client.get(reverse("core:inicio"))
        self.assertContains(r, "Acampamento de Julho")
        self._inativar()
        r = self.client.get(reverse("core:inicio"))
        self.assertNotContains(r, "Acampamento de Julho")

    def test_reativar_devolve_o_evento_ao_menu(self):
        self._inativar()
        self.evento.ativo = True
        self.evento.save(update_fields=["ativo"])
        self.client.force_login(self.resp)
        self.assertContains(self.client.get(reverse("core:inicio")), "Acampamento de Julho")

    # --- telas publicas ---

    def test_pagina_do_inativo_da_404_para_visitante(self):
        self._inativar()
        self.assertEqual(self.client.get(self.pagina_url).status_code, 404)

    def test_responsavel_com_link_antigo_volta_ao_inicio(self):
        self._inativar()
        self.client.force_login(self.resp)
        r = self.client.get(self.pagina_url)
        self.assertRedirects(r, reverse("core:inicio"))

    def test_diretor_continua_vendo_a_pagina_e_o_painel(self):
        self._inativar()
        self.client.force_login(self.diretor)
        self.assertEqual(self.client.get(self.pagina_url).status_code, 200)
        r = self.client.get(reverse("core:evento_painel", args=[self.evento.id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Evento inativo")

    # --- o servidor nao confia no HTML: POST forjado tambem e barrado ---

    def test_post_de_inscricao_em_evento_inativo_nao_cria_inscricao(self):
        self._inativar()
        self.client.post(self.inscrever_url, {
            "responsavel_nome": "Fulano", "responsavel_whatsapp": "16999990000",
            "part_idx": "0", "nome_0": "Fulano", "idade_0": "10",
        })
        self.assertEqual(Inscricao.objects.count(), 0)

    def test_post_na_lojinha_de_evento_inativo_nao_abre_checkout(self):
        self._inativar()
        self.client.post(self.loja_url, {
            "comprador_nome": "Fulano",
            "comprador_whatsapp": "16999990000",
            "comprador_email": "f@exemplo.com",
            "forma_pagamento": "pix",
            f"qtd_{self.var.id}": "1",
        })
        self.assertNotIn("loja_checkout", self.client.session)
        self.assertEqual(PedidoLoja.objects.count(), 0)

    # --- o botao do Diretor ---

    def test_diretor_alterna_o_evento(self):
        self.client.force_login(self.diretor)
        self.client.post(self.ativar_url)
        self.evento.refresh_from_db()
        self.assertFalse(self.evento.ativo)
        self.client.post(self.ativar_url)
        self.evento.refresh_from_db()
        self.assertTrue(self.evento.ativo)

    def test_responsavel_nao_pode_inativar(self):
        self.client.force_login(self.resp)
        self.client.post(self.ativar_url)
        self.evento.refresh_from_db()
        self.assertTrue(self.evento.ativo)

    def test_get_nao_alterna(self):
        """Alternar e acao de POST: link/prefetch nunca pode desligar um evento."""
        self.client.force_login(self.diretor)
        self.assertEqual(self.client.get(self.ativar_url).status_code, 405)
        self.evento.refresh_from_db()
        self.assertTrue(self.evento.ativo)

    # --- evento que ja passou nao tem o que desligar ---

    def _evento_passado(self, ativo=True):
        return Evento.objects.create(
            tipo="inscricao", nome="Acampamento do ano passado", local="Sede",
            data=timezone.localdate() - datetime.timedelta(days=30), ativo=ativo,
        )

    def test_evento_que_ja_passou_nao_oferece_inativar(self):
        """Ja saiu do menu e nao aceita inscricao: o botao nao faria nada."""
        passado = self._evento_passado()
        url_ativar = reverse("core:evento_ativar", args=[passado.id])
        self.client.force_login(self.diretor)
        self.assertNotContains(self.client.get(reverse("core:eventos")), url_ativar)
        r = self.client.get(reverse("core:evento_painel", args=[passado.id]))
        self.assertNotContains(r, url_ativar)

    def test_evento_passado_e_inativo_ainda_pode_ser_reativado(self):
        """Desfazer continua possivel — senao o selo 'Inativo' ficaria para sempre."""
        passado = self._evento_passado(ativo=False)
        url_ativar = reverse("core:evento_ativar", args=[passado.id])
        self.client.force_login(self.diretor)
        self.assertContains(self.client.get(reverse("core:eventos")), url_ativar)
        r = self.client.get(reverse("core:evento_painel", args=[passado.id]))
        self.assertContains(r, "Reativar evento")

    def test_lista_de_eventos_mostra_o_selo_e_o_botao(self):
        self.client.force_login(self.diretor)
        r = self.client.get(reverse("core:eventos"))
        self.assertContains(r, "Inativar")
        self._inativar()
        r = self.client.get(reverse("core:eventos"))
        self.assertContains(r, "Inativo")
        self.assertContains(r, "Reativar")


class SegurancaCookiesTests(TestCase):
    """Cookie de sessao e de CSRF so podem trafegar por HTTPS em producao.

    O 301 do Nginx NAO resolve isso: quando o redirecionamento chega, o cookie
    JA foi enviado em texto puro na requisicao http://. Estes testes travam a
    regressao (alguem fixar em False, ou o vinculo com o DEBUG se perder).
    """

    def test_nao_comparar_com_settings_debug_aqui(self):
        """Nota de manutenção — já custou um teste vermelho.

        NÃO escreva `assertEqual(settings.SESSION_COOKIE_SECURE, not
        settings.DEBUG)`: o test runner do Django força `DEBUG = False`
        **depois** que o `settings.py` foi importado. O cookie, porém, foi
        calculado no import, com o DEBUG de verdade — então os dois valores
        não batem e o teste falha sem haver defeito nenhum no código.

        Quem vale são os dois testes abaixo, que recarregam o módulo com o
        `DJANGO_DEBUG` explícito e conferem cada cenário de verdade.
        """
        from django.conf import settings
        self.assertFalse(settings.DEBUG)  # o runner sempre desliga

    def test_producao_exige_cookie_secure(self):
        """Recarrega o settings com DEBUG desligado — o caso do VPS."""
        import importlib
        import os

        from config import settings as s

        anterior = os.environ.get("DJANGO_DEBUG")
        os.environ["DJANGO_DEBUG"] = "0"
        try:
            importlib.reload(s)
            self.assertFalse(s.DEBUG)
            self.assertTrue(s.SESSION_COOKIE_SECURE)
            self.assertTrue(s.CSRF_COOKIE_SECURE)
        finally:
            # Devolve o ambiente e o modulo ao estado original, senao o proximo
            # teste da suite herda um settings recarregado.
            if anterior is None:
                os.environ.pop("DJANGO_DEBUG", None)
            else:
                os.environ["DJANGO_DEBUG"] = anterior
            importlib.reload(s)

    def test_desenvolvimento_local_nao_exige_https(self):
        """Em DEBUG o cookie precisa continuar simples: o navegador nao guarda
        cookie `Secure` em http://127.0.0.1 e o login pararia de funcionar."""
        import importlib
        import os

        from config import settings as s

        anterior = os.environ.get("DJANGO_DEBUG")
        os.environ["DJANGO_DEBUG"] = "1"
        try:
            importlib.reload(s)
            self.assertTrue(s.DEBUG)
            self.assertFalse(s.SESSION_COOKIE_SECURE)
            self.assertFalse(s.CSRF_COOKIE_SECURE)
        finally:
            if anterior is None:
                os.environ.pop("DJANGO_DEBUG", None)
            else:
                os.environ["DJANGO_DEBUG"] = anterior
            importlib.reload(s)

    def test_ssl_redirect_fica_com_o_nginx(self):
        """Nao ligar no Django: o proxy ja faz o 301, e duplicar arrisca laco.
        Mas o header de proxy PRECISA existir — sem ele o Django nao sabe que a
        requisicao chegou por HTTPS e nem mandaria o cookie `Secure`."""
        from django.conf import settings
        self.assertFalse(getattr(settings, "SECURE_SSL_REDIRECT", False))
        self.assertEqual(
            settings.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https")
        )
