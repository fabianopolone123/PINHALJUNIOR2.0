"""
Cliente da IA (API do GPT / OpenAI).

Só usa a biblioteca-padrão (`urllib`), sem dependências novas — mesmo padrão do
`core/mercadopago.py` e do envio da W-API. Fala com a API de Chat Completions
(`POST {base_url}/chat/completions`).

Ponto de entrada reaproveitável: `conversar(config, mensagens, ...)` recebe uma
lista de mensagens no formato da OpenAI e devolve `(ok, texto|erro)`. O atalho
`enviar_prompt(config, prompt)` monta a lista para o caso simples (um texto do
usuário) — usado hoje pelo botão "Enviar teste" da tela Configurações IA e pronto
para os usos que virão depois de configurado.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 30  # segundos


def conversar(config, mensagens, temperatura=0.7, max_tokens=None):
    """Faz um POST em /chat/completions e devolve `(ok: bool, detalhe: str)`.

    `detalhe` é a resposta em texto do modelo (sucesso) ou uma mensagem de erro
    amigável (falha). `mensagens` é a lista no formato da OpenAI, ex.:
    `[{"role": "user", "content": "Olá"}]`."""
    if not getattr(config, "api_key", ""):
        return False, "Configure a chave da API antes de enviar."

    base = (config.base_url or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    corpo = {"model": config.modelo_efetivo, "messages": mensagens, "temperature": temperatura}
    if max_tokens:
        corpo["max_tokens"] = max_tokens
    dados = json.dumps(corpo).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=dados,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            bruto = resp.read().decode("utf-8", "replace")
        resposta = json.loads(bruto) if bruto else {}
        escolhas = resposta.get("choices") or []
        if not escolhas:
            return False, "A IA respondeu, mas sem conteúdo."
        texto = (escolhas[0].get("message") or {}).get("content", "")
        return True, (texto or "").strip()
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace") if e.fp else ""
        try:
            j = json.loads(detalhe)
            detalhe = (j.get("error") or {}).get("message") or detalhe
        except (ValueError, TypeError):
            pass
        return False, f"Erro {e.code}: {detalhe or e.reason}"
    except urllib.error.URLError as e:
        return False, f"Falha de conexão: {e.reason}"
    except Exception as e:  # noqa: BLE001 — qualquer imprevisto vira mensagem amigável
        return False, f"Erro inesperado: {e}"


def enviar_prompt(config, prompt):
    """Atalho para o caso simples: um único texto do usuário."""
    return conversar(config, [{"role": "user", "content": prompt}])
