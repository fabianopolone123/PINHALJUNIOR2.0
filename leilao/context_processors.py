"""Contexto comum das telas do leilão.

Injeta a configuração de áudio e o participante da sessão em todo template —
assim nenhuma view precisa lembrar de passar isso.
"""

from django.urls import get_script_prefix

from .models import ConfigLeilao
from .papeis import menu_do, papeis_do
from .sessao import participante_atual


def leilao_base(request):
    cfg = ConfigLeilao.get_solo()
    # O MediaMTX fica atrás do mesmo Nginx, em `<prefixo>/audio/`. Montar a URL
    # a partir do `script_prefix` faz a mesma página servir em `/leilao/` (VPS) e
    # na raiz (desenvolvimento) sem configuração extra.
    prefixo = get_script_prefix()
    caminho = (cfg.audio_caminho or "leilao").strip("/")
    return {
        "config_leilao": cfg,
        "audio_ativo": cfg.audio_ativo,
        "audio_externo": cfg.audio_externo_url,
        "audio_whep": f"{prefixo}audio/{caminho}/whep" if cfg.audio_ativo else "",
        "audio_whip": f"{prefixo}audio/{caminho}/whip" if cfg.audio_ativo else "",
        "participante": participante_atual(request),
        # Menu da equipe: só as áreas que a pessoa realmente abre. O template
        # itera isto em vez de chumbar `{% if %}` por papel — mesma ideia do
        # `core/menus.py` no sistema do clube.
        "menu_equipe": menu_do(request.user) if hasattr(request, "user") else [],
        "meus_papeis": papeis_do(request.user) if hasattr(request, "user") else set(),
    }
