"""
Cliente da W-API (WhatsApp) — chamadas que não são o simples envio de texto já
existente em views (`_enviar_whatsapp`). Só usa a biblioteca-padrão (`urllib`),
sem dependências novas, no mesmo padrão de `core/mercadopago.py`/`core/openai_ia.py`.

Endpoints usados (base = `config.base_url`, padrão `https://api.w-api.app/v1`):
- Listar grupos:      GET  /group/get-all-groups?instanceId=...
- Metadados do grupo: GET  /group/group-metadata?instanceId=...&groupId=...
- Config do webhook:  PUT  /webhook/update-webhook-received?instanceId=...  body {"value": url}
- Enviar texto:       POST /message/send-text?instanceId=...  body {"phone": destino, "message": txt}
  (destino pode ser um número OU um ID de grupo `...@g.us`.)

Todas devolvem `(ok: bool, dados|erro)`.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 20


def _base(config):
    return (config.base_url or "https://api.w-api.app/v1").rstrip("/")


def _requisitar(config, metodo, caminho, params=None, corpo=None):
    """Faz a requisição e devolve `(ok, dados_dict|mensagem_erro)`."""
    params = dict(params or {})
    params["instanceId"] = config.instance_id
    url = f"{_base(config)}{caminho}?{urllib.parse.urlencode(params)}"
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(
        url, data=dados, method=metodo,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.token}",
        },
    )
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
        return False, f"Falha de conexão: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return False, f"Erro inesperado: {e}"


def listar_grupos(config):
    """Lista os grupos da instância. Devolve `(ok, lista|erro)`, onde cada item é
    `{"group_id", "nome", "tamanho"}`. Faz parsing defensivo do payload (o formato
    exato do item de grupo não está detalhado na doc)."""
    ok, dados = _requisitar(config, "GET", "/group/get-all-groups")
    if not ok:
        return False, dados
    if isinstance(dados, dict) and dados.get("error"):
        return False, dados.get("message") or "A W-API retornou erro ao listar grupos."
    brutos = []
    if isinstance(dados, dict):
        brutos = dados.get("groups") or dados.get("data") or []
    elif isinstance(dados, list):
        brutos = dados
    grupos = []
    for g in brutos:
        if isinstance(g, str):  # veio só o ID
            grupos.append({"group_id": g, "nome": "", "tamanho": 0})
            continue
        if not isinstance(g, dict):
            continue
        gid = g.get("id") or g.get("groupId") or g.get("jid") or ""
        if not gid:
            continue
        nome = g.get("subject") or g.get("name") or g.get("nome") or ""
        tamanho = g.get("size") or g.get("participantsCount") or len(g.get("participants") or []) or 0
        grupos.append({"group_id": gid, "nome": nome, "tamanho": int(tamanho or 0)})
    return True, grupos


def dados_grupo(config, group_id):
    """Metadados de um grupo específico (nome/subject etc.). `(ok, dict|erro)`."""
    ok, dados = _requisitar(config, "GET", "/group/group-metadata", params={"groupId": group_id})
    if not ok:
        return False, dados
    return True, (dados.get("group") if isinstance(dados, dict) else dados) or {}


def configurar_webhook_recebido(config, url):
    """Aponta o webhook de mensagens recebidas para `url`. `(ok, dict|erro)`."""
    return _requisitar(
        config, "PUT", "/webhook/update-webhook-received", corpo={"value": url}
    )


# Nomes candidatos do endpoint que aponta o **webhook de entrega/status**. A doc
# pública não abre o nome, e sondar por GET não resolve: a W-API responde
# `Cannot GET /v1/webhook/...` para TODA rota de webhook, inclusive a que
# funciona com PUT. Então tenta-se um a um, e um 404 só descarta aquele nome.
# Todos os candidatos têm semântica de entrega/status — se um deles pegar, o valor
# gravado é a nossa URL, que é exatamente o que se quer.
CAMINHOS_WEBHOOK_ENTREGA = (
    "/webhook/update-webhook-delivery",
    "/webhook/update-webhook-message-status",
    "/webhook/update-webhook-status",
    "/webhook/update-delivery-webhook",
)


def configurar_webhook_entrega(config, url):
    """Aponta o webhook de **entrega/status** para `url`.

    Devolve `(ok, caminho_que_funcionou|erro)`. Quando nenhum candidato pega, o
    erro já vem pronto para a tela: a configuração tem de ser feita à mão no
    painel da W-API (o receptor do sistema funciona igual — só a configuração
    é que muda de lugar)."""
    erros = []
    for caminho in CAMINHOS_WEBHOOK_ENTREGA:
        ok, dados = _requisitar(config, "PUT", caminho, corpo={"value": url})
        if ok and not (isinstance(dados, dict) and dados.get("error")):
            return True, caminho
        erros.append(f"{caminho.rsplit('/', 1)[-1]}: {dados}")
    return False, (
        "A W-API não aceitou nenhum dos nomes de endpoint conhecidos para o webhook "
        "de entrega. Configure a URL à mão no painel da W-API (campo de webhook de "
        "entrega/status) — o resto do sistema já está pronto para receber. "
        "Detalhe: " + " | ".join(erros)
    )


def enviar_texto(config, destino, mensagem):
    """Envia texto para um número OU grupo (`...@g.us`). `(ok, message_id|erro)`."""
    ok, dados = _requisitar(
        config, "POST", "/message/send-text",
        corpo={"phone": destino, "message": mensagem},
    )
    if not ok:
        return False, dados
    msg_id = ""
    if isinstance(dados, dict):
        msg_id = dados.get("messageId") or dados.get("insertedId") or ""
    return True, msg_id
