"""Entrada ASGI do **serviço do leilão**.

    uvicorn config.asgi_leilao:application --host 127.0.0.1 --port 8011 --workers 1

**Um worker só, sempre.** O hub de eventos e o relógio do leilão vivem na
memória deste processo; dois processos seriam dois leilões paralelos, cada um
com o seu cronômetro. Ver `config/settings_leilao.py`.

O wrapper de `lifespan` existe porque o Django não trata esse protocolo: é ele
que liga o laço central quando o servidor sobe (e desliga quando cai). Se por
algum motivo o servidor subir sem `lifespan`, a primeira conexão SSE liga o laço
do mesmo jeito (`hub.garantir_laco`) — o leilão nunca fica sem relógio.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings_leilao")

from django.core.asgi import get_asgi_application  # noqa: E402

_django = get_asgi_application()


async def application(scope, receive, send):
    if scope["type"] == "lifespan":
        await _lifespan(scope, receive, send)
        return
    await _django(scope, receive, send)


async def _lifespan(scope, receive, send):
    from django.conf import settings

    from leilao.hub import garantir_laco, parar_laco

    while True:
        mensagem = await receive()
        if mensagem["type"] == "lifespan.startup":
            try:
                garantir_laco(getattr(settings, "LEILAO_TICK_SEGUNDOS", 1))
                await send({"type": "lifespan.startup.complete"})
            except Exception as e:  # noqa: BLE001
                await send({"type": "lifespan.startup.failed", "message": str(e)})
        elif mensagem["type"] == "lifespan.shutdown":
            parar_laco()
            await send({"type": "lifespan.shutdown.complete"})
            return
