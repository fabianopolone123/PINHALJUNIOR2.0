"""Hub de eventos em memória + laço central do leilão.

É o que faz o leilão ser "ao vivo". Duas peças:

- **`HUB`** — um publicador/assinante em memória. Quem dá um lance publica um
  evento; todas as conexões SSE abertas recebem. Sem Redis, sem fila, sem peça
  nova: cabe na memória do processo porque **o serviço roda com um worker só**
  (ver `config/settings_leilao.py`).
- **`laco_central`** — uma corrotina única que bate a cada segundo e é o **ponto
  único onde o tempo decidiria alguma coisa**. Hoje ela não tem o que fazer: as
  duas regras que aplicava (o prazo de pagamento e o fim do chat) saíram a
  pedido do clube, e cronômetro nunca houve — quem fecha o item é o locutor.
  Ela fica de pé porque regra de tempo nova entra **ali**, e não num caminho
  paralelo. O `laco_reacoes` é separado, e o porquê está nele.

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
        # fila -> é do PÚBLICO? As telas da equipe (mesa do locutor, caixa)
        # também ficam conectadas, e contá-las estragaria o único número que o
        # locutor usa para decidir a hora de começar: "quantas pessoas já
        # chegaram". Três voluntários com a tela aberta viravam três
        # participantes.
        self._assinantes = {}
        self._loop = None
        self._seq = 0
        self._lock = threading.Lock()

    # -- ciclo de vida -----------------------------------------------------
    def registrar_loop(self, loop):
        """Guarda o loop de eventos (chamado no startup do ASGI)."""
        self._loop = loop

    @property
    def conectados(self):
        """Quantas PESSOAS estão no leilão (a equipe não conta)."""
        return sum(1 for publico in self._assinantes.values() if publico)

    @property
    def total(self):
        """Todas as conexões abertas — é o que o teto do serviço limita."""
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
    def assinar(self, publico=True):
        """Devolve uma fila nova já inscrita. Lembre de `cancelar()` no fim.

        `publico=False` para as telas da equipe: elas recebem tudo, mas não
        entram na contagem de gente no leilão.
        """
        fila = asyncio.Queue(maxsize=FILA_MAX)
        self._assinantes[fila] = bool(publico)
        return fila

    def cancelar(self, fila):
        self._assinantes.pop(fila, None)


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
    """Bate a cada `intervalo` segundos e chama `servicos.verificar_prazos()`.

    **Hoje não há o que vencer** (ver o docstring daquela função). O laço
    continua porque é o lugar único do tempo neste módulo. Qualquer erro é
    **logado e engolido** — um tropeço numa volta não pode matar o relógio do
    leilão inteiro.
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


async def laco_reacoes(intervalo=0.5):
    """Despeja as reações acumuladas — **sem tocar no banco**.

    Laço próprio porque é rápido (meio segundo) e barato: o laço central faz
    consultas a cada volta, e rodá-lo nesse ritmo custaria caro à toa. Aqui só
    se lê um dicionário em memória.
    """
    from . import reacoes

    while True:
        try:
            acumulado = reacoes.drenar()
            if acumulado:
                HUB.publicar("reacoes", acumulado)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — enfeite não derruba o pregão
            logger.exception("Falha ao despejar reações")
        await asyncio.sleep(intervalo)


# ---------------------------------------------------------------------------
# Partida do laço
# ---------------------------------------------------------------------------
_tarefa = None
_tarefa_reacoes = None


def garantir_laco(intervalo=1.0):
    """Garante que o laço central esteja rodando neste loop de eventos.

    Chamado no *startup* do ASGI e, por segurança, na primeira conexão SSE — se
    o servidor for subido sem suporte a `lifespan`, o leilão continua com
    cronômetro. Idempotente: chamar dez vezes não cria dez laços.
    """
    global _tarefa, _tarefa_reacoes
    loop = asyncio.get_running_loop()
    HUB.registrar_loop(loop)
    if _tarefa is None or _tarefa.done():
        _tarefa = loop.create_task(laco_central(intervalo))
    if _tarefa_reacoes is None or _tarefa_reacoes.done():
        _tarefa_reacoes = loop.create_task(laco_reacoes())
    return _tarefa


def parar_laco():
    global _tarefa, _tarefa_reacoes
    for t in (_tarefa, _tarefa_reacoes):
        if t is not None and not t.done():
            t.cancel()
    _tarefa = None
    _tarefa_reacoes = None
