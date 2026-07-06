"""Cliente do Mercado Pago (engine de pagamentos Pix).

Só usa a biblioteca-padrão (`urllib`), sem dependências novas — mesmo padrão do
módulo WhatsApp (W-API). Concentra aqui toda a conversa HTTP com o Mercado Pago:

- `criar_pix`         → cria a cobrança Pix e devolve o QR (imagem + copia e cola);
- `consultar_pagamento` → lê o pagamento no MP (status + **taxa real** + líquido);
- `validar_assinatura`  → confere o `x-signature` do webhook (HMAC-SHA256);
- `mapear_status`       → traduz o status do MP para o nosso.

As credenciais e o modo (teste/produção) vêm do singleton `MercadoPagoConfig`.
Usamos a **API clássica de pagamentos** (`/v1/payments`), que devolve o QR em
`point_of_interaction.transaction_data` e a taxa em `fee_details` /
`transaction_details.net_received_amount`.
"""

import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

API_BASE = "https://api.mercadopago.com"
TIMEOUT = 20

# Mapa: status do Mercado Pago → nosso STATUS_PAGAMENTO_CHOICES.
_STATUS_MP = {
    "approved": "aprovado",
    "authorized": "aprovado",
    "pending": "pendente",
    "in_process": "pendente",
    "in_mediation": "pendente",
    "rejected": "rejeitado",
    "cancelled": "cancelado",
    "refunded": "estornado",
    "charged_back": "estornado",
}


def mapear_status(mp_status):
    """Traduz o status textual do MP para o nosso (default: 'pendente')."""
    return _STATUS_MP.get((mp_status or "").lower(), "pendente")


def _request(config, method, path, body=None, idempotency_key=None):
    """Chamada HTTP autenticada ao Mercado Pago. Retorna (ok, dados|erro)."""
    token = config.access_token
    if not token:
        return False, "Mercado Pago não configurado (falta o Access Token)."
    url = f"{API_BASE}{path}"
    dados = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    req = urllib.request.Request(url, data=dados, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            bruto = resp.read().decode("utf-8", "replace")
        return True, (json.loads(bruto) if bruto else {})
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace") if e.fp else ""
        try:
            j = json.loads(detalhe)
            detalhe = j.get("message") or j.get("error") or detalhe
        except (ValueError, TypeError):
            pass
        return False, f"Erro {e.code}: {detalhe or e.reason}"
    except urllib.error.URLError as e:
        return False, f"Falha de conexão com o Mercado Pago: {e.reason}"
    except Exception as e:  # noqa: BLE001 — vira mensagem amigável
        return False, f"Erro inesperado no Mercado Pago: {e}"


def criar_pix(config, *, referencia, valor, descricao, payer_email="",
              payer_nome="", notification_url="", expira_minutos=30):
    """Cria uma cobrança Pix. Retorna dict:
    {ok, mp_payment_id, status, qr_code, qr_code_base64, ticket_url, erro, raw}.

    `valor` é Decimal/float (R$). `referencia` é a nossa external_reference (casa o
    webhook). `expira_minutos` define a validade do QR (Pix dinâmico de uso único).
    """
    expira = timezone.localtime() + timedelta(minutes=expira_minutos)
    corpo = {
        "transaction_amount": round(float(valor), 2),
        "description": descricao or "Clube de Aventureiros Pinhal Júnior",
        "payment_method_id": "pix",
        "external_reference": referencia,
        "date_of_expiration": expira.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
        "payer": {"email": payer_email or "sem-email@pinhaljunior.com.br"},
    }
    if payer_nome:
        partes = payer_nome.strip().split(" ", 1)
        corpo["payer"]["first_name"] = partes[0]
        if len(partes) > 1:
            corpo["payer"]["last_name"] = partes[1]
    if notification_url:
        corpo["notification_url"] = notification_url

    ok, dados = _request(config, "POST", "/v1/payments", corpo, idempotency_key=referencia)
    if not ok:
        return {"ok": False, "erro": dados}
    tx = (dados.get("point_of_interaction") or {}).get("transaction_data") or {}
    return {
        "ok": True,
        "mp_payment_id": str(dados.get("id") or ""),
        "status": mapear_status(dados.get("status")),
        "qr_code": tx.get("qr_code") or "",
        "qr_code_base64": tx.get("qr_code_base64") or "",
        "ticket_url": tx.get("ticket_url") or "",
        "raw": dados,
    }


def consultar_pagamento(config, payment_id):
    """Lê um pagamento no MP. Retorna dict com status + **taxa real** + líquido:
    {ok, status, valor, taxa, liquido, external_reference, forma, erro, raw}.

    `taxa` = soma de `fee_details`; `liquido` = `net_received_amount` (ou bruto − taxa).
    """
    ok, dados = _request(config, "GET", f"/v1/payments/{payment_id}")
    if not ok:
        return {"ok": False, "erro": dados}
    bruto = Decimal(str(dados.get("transaction_amount") or "0"))
    taxa = sum(
        (Decimal(str(fd.get("amount") or "0")) for fd in (dados.get("fee_details") or [])),
        Decimal("0"),
    )
    detalhes = dados.get("transaction_details") or {}
    liquido_mp = detalhes.get("net_received_amount")
    liquido = Decimal(str(liquido_mp)) if liquido_mp is not None else (bruto - taxa)
    return {
        "ok": True,
        "status": mapear_status(dados.get("status")),
        "valor": bruto,
        "taxa": taxa,
        "liquido": liquido,
        "external_reference": dados.get("external_reference") or "",
        "forma": dados.get("payment_type_id") or "",
        "raw": dados,
    }


def validar_assinatura(config, *, x_signature, x_request_id, data_id):
    """Confere o cabeçalho `x-signature` do webhook (HMAC-SHA256).

    Monta o *manifest* `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`, calcula o
    HMAC com a `webhook_secret` e compara com o `v1` do cabeçalho. Sem secret
    configurada, não dá para validar → retorna False (o chamador decide o que fazer).
    """
    secret = config.webhook_secret
    if not secret or not x_signature:
        return False
    ts = v1 = ""
    for parte in x_signature.split(","):
        chave, _, valor = parte.strip().partition("=")
        chave = chave.strip()
        if chave == "ts":
            ts = valor.strip()
        elif chave == "v1":
            v1 = valor.strip()
    if not ts or not v1:
        return False
    # O MP recomenda o data.id em minúsculas quando for alfanumérico.
    did = str(data_id or "")
    if did and not did.isdigit():
        did = did.lower()
    manifest = f"id:{did};"
    if x_request_id:
        manifest += f"request-id:{x_request_id};"
    manifest += f"ts:{ts};"
    esperado = hmac.new(
        secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperado, v1)
