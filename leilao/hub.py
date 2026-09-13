"""Hub de eventos em memória + laço central do leilão.

É o que faz o leilão ser "ao vivo". Duas peças:

- **`HUB`** — um publicador/assinante em memória. Quem dá um lance publica um
  evento; todas as conexões SSE abertas recebem. Sem Redis, sem fila, sem peça
  nova: cabe na memória do processo porque **o serviço roda com um worker só**
  (ver `config/settings_leilao.py`).
- **`laco_central`** — uma corrotina única que, a cada segundo, fecha o lote cujo
  cronômetro zerou, expira o arremate não pago e devolve o item à fila. É o
  relógio do módulo: **um lugar só** decide o tempo de tudo.

Detalhe que importa: o `POST` de lance roda em **thread** (view síncrona), e o
SSE roda no **loop de eventos**. Por isso `publicar()` é seguro para chamar de
qualquer thread — ele agenda a entrega no loop com `call_soon_threadsafe`.
"""

import asyncio
import json
import logging
import threading

logger = logging.getLogger(__name__)

# Quantos eventos podem ficar represados por conexão antes de a gente desistir
# de "contar a história" para aquele cliente. Celular em rede ruim não pode
# segurar o pregão dos outros: estourando, mandamos um "ressincronize" e ele
# volta pedindo o estado inteiro.
FILA_MAX = 64


class Hub:
    """Publicador/assinante em memória para os eventos do leilão."""

    def __init__(self):
        self._assinantes = set()
        self._loop = None
        self._seq = 0
        self._lock = threading.Lock()

    # -- ciclo de vida -----------------------------------------------------
    def registrar_loop(self, loop):
        """Guarda o loop de eventos (chamado no startup do ASGI)."""
        self._loop = loop

    @property
    def conectados(self):
        return len(self._assinantes)

    # -- publicação --------------------------------------------------------
    def publicar(self, tipo, dados=None):
        """Manda um evento para todo mundo. **Seguro em qualquer thread.**

        O lance chega por uma view síncrona (threadpool) e precisa acordar
        conexões que vivem no loop de eventos — daí o `call_soon_threadsafe`.
        """
        with self._lock:
            self._seq += 1
            seq = self._seq
        evento = {"seq": seq, "tipo": tipo, "dados": dados or {}}
        loop = self._loop
        if loop is None:
            # Sem loop (ex.: comando de gerenciamento, teste síncrono): não há
            # ninguém ouvindo. Publicar vira no-op em vez de estourar.
            return seq
        try:
            loop.call_soon_threadsafe(self._entregar, evento)
        except RuntimeError:  # loop já fechado (desligando o serviço)
            pass
        return seq

    def _entregar(self, evento):
        """Roda no loop de eventos: empurra para cada assinante."""
        for fila in list(self._assinantes):
            try:
                fila.put_nowait(evento)
            except asyncio.QueueFull:
                # Cliente lento. Esvazia e pede ressincronização — é mais barato
                # (e mais correto) do que tentar entregar um histórico atrasado.
                _esvaziar(fila)
                try:
                    fila.put_nowait({"seq": evento["seq"], "tipo": "resync", "dados": {}})
                except asyncio.QueueFull:  # pragma: no cover — acabou de esvaziar
                    pass

    # -- assinatura --------------------------------------------------------
    def assinar(self):
        """Devolve uma fila nova já inscrita. Lembre de `cancelar()` no fim."""
        fila = asyncio.Queue(maxsize=FILA_MAX)
        self._assinantes.add(fila)
        return fila

    def cancelar(self, fila):
        self._assinantes.discard(fila)


def _esvaziar(fila):
    while True:
        try:
            fila.get_nowait()
        except asyncio.QueueEmpty:
            return


# Instância única do processo.
HUB = Hub()


def sse(evento):
    """Formata um evento no protocolo do `text/event-stream`.

    O `id:` é o número de sequência — é ele que o navegador devolve em
    `Last-Event-ID` ao reconectar. Não usamos isso para repetir eventos (o
    servidor sempre remanda o **estado inteiro** na reconexão, que é mais
    simples e sempre correto), mas ajuda a depurar.
    """
    corpo = json.dumps(evento.get("dados") or {}, ensure_ascii=False, default=str)
    return f"id: {evento['seq']}\nevent: {evento['tipo']}\ndata: {corpo}\n\n"


# ---------------------------------------------------------------------------
# Laço central
# ---------------------------------------------------------------------------
async def laco_central(intervalo=1.0):
    """Confere, a cada `intervalo` segundos, o que venceu.

    Tudo que é "tempo" no leilão passa por aqui: o cronômetro do lote e o prazo
    de 15 minutos do arremate. Qualquer erro é **logado e engolido** — um
    tropeço numa volta não pode matar o relógio do leilão inteiro.
    """
    from asgiref.sync import sync_to_async

    from . import servicos

    verificar = sync_to_async(servicos.verificar_prazos, thread_sensitive=False)
    while True:
        try:
            await verificar()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — o laço não pode morrer
            logger.exception("Falha na volta do laço central do leilão")
        await asyncio.sleep(intervalo)


# ---------------------------------------------------------------------------
# Partida do laço
# ---------------------------------------------------------------------------
_tarefa = None


def garantir_laco(intervalo=1.0):
    """Garante que o laço central esteja rodando neste loop de eventos.

    Chamado no *startup* do ASGI e, por segurança, na primeira conexão SSE — se
    o servidor for subido sem suporte a `lifespan`, o leilão continua com
    cronômetro. Idempotente: chamar dez vezes não cria dez laços.
    """
    global _tarefa
    loop = asyncio.get_running_loop()
    HUB.registrar_loop(loop)
    if _tarefa is None or _tarefa.done():
        _tarefa = loop.create_task(laco_central(intervalo))
    return _tarefa


def parar_laco():
    global _tarefa
    if _tarefa is not None and not _tarefa.done():
        _tarefa.cancel()
    _tarefa = None
