"""
Cliente da IA (API do GPT / OpenAI).

Só usa a biblioteca-padrão (`urllib`), sem dependências novas — mesmo padrão do
`core/mercadopago.py` e do envio da W-API. Fala com a API de Chat Completions
(`POST {BASE_URL}/chat/completions`).

O **modelo é fixo** (`MODELO`, o mais barato) e a URL base **não é configurável**
(`BASE_URL`) — só a chave da API vem da tela. Ponto de entrada reaproveitável:
`conversar(config, mensagens, ...)` recebe a lista de mensagens no formato da OpenAI
e devolve `(ok, texto|erro, uso)`, onde `uso` é o dict de tokens consumidos (ou
None em falha). O atalho `enviar_prompt(config, prompt)` monta a lista para o caso
simples (um texto do usuário) — usado hoje pelo botão "Enviar teste" e pronto para
os usos que virão depois.
"""

import json
import urllib.error
import urllib.request

# Modelo fixo: o mais barato disponível (o Diretor não escolhe na tela).
MODELO = "gpt-4.1-nano"
# URL base da API (não configurável).
BASE_URL = "https://api.openai.com/v1"
TIMEOUT = 30  # segundos


def _extrair_uso(resposta):
    """Monta o dict de consumo a partir do bloco `usage` da resposta da OpenAI.
    `cache` é o subconjunto da entrada que veio do cache (mais barato)."""
    uso = resposta.get("usage") or {}
    detalhes = uso.get("prompt_tokens_details") or {}
    return {
        "prompt": uso.get("prompt_tokens", 0) or 0,
        "cache": detalhes.get("cached_tokens", 0) or 0,
        "completion": uso.get("completion_tokens", 0) or 0,
        "total": uso.get("total_tokens", 0) or 0,
    }


def conversar(config, mensagens, temperatura=0.7, max_tokens=None):
    """Faz um POST em /chat/completions e devolve `(ok: bool, detalhe: str, uso: dict|None)`.

    `detalhe` é a resposta em texto do modelo (sucesso) ou uma mensagem de erro
    amigável (falha). `uso` traz os tokens consumidos (None se não houve chamada
    bem-sucedida). `mensagens` é a lista no formato da OpenAI, ex.:
    `[{"role": "user", "content": "Olá"}]`."""
    if not getattr(config, "api_key", ""):
        return False, "Configure a chave da API antes de enviar.", None

    url = f"{BASE_URL}/chat/completions"
    corpo = {"model": MODELO, "messages": mensagens, "temperature": temperatura}
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
            return False, "A IA respondeu, mas sem conteúdo.", None
        texto = (escolhas[0].get("message") or {}).get("content", "")
        return True, (texto or "").strip(), _extrair_uso(resposta)
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace") if e.fp else ""
        try:
            j = json.loads(detalhe)
            detalhe = (j.get("error") or {}).get("message") or detalhe
        except (ValueError, TypeError):
            pass
        return False, f"Erro {e.code}: {detalhe or e.reason}", None
    except urllib.error.URLError as e:
        return False, f"Falha de conexão: {e.reason}", None
    except Exception as e:  # noqa: BLE001 — qualquer imprevisto vira mensagem amigável
        return False, f"Erro inesperado: {e}", None


def enviar_prompt(config, prompt):
    """Atalho para o caso simples: um único texto do usuário."""
    return conversar(config, [{"role": "user", "content": prompt}])
