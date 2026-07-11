import datetime
import hashlib
import hmac
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from . import mercadopago as mp
from .models import (
    Aventureiro,
    CobrancaEnviada,
    CompraLoja,
    CustoClube,
    Evento,
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
