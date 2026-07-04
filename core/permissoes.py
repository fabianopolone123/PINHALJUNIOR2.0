"""
Helpers de permissão por perfil de acesso.

Os perfis são grupos nativos do Django (ver comando `configurar_perfis`):
Diretor, Responsável, Professor, Tesoureiro, Secretário. Por enquanto, só o
Diretor recebe permissões nas telas; os demais serão liberados no futuro.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

PERFIL_DIRETOR = "Diretor"


def eh_diretor(user):
    """True se o usuário está autenticado e pertence ao perfil Diretor."""
    return (
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name=PERFIL_DIRETOR).exists()
    )


def diretor_required(view_func):
    """Restringe a view ao perfil Diretor.

    Sem login → vai para o login (via `login_required`). Logado mas sem o perfil
    Diretor → volta para "Meus Dados" com uma mensagem de acesso restrito.
    """

    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not eh_diretor(request.user):
            messages.error(request, "Acesso restrito ao perfil Diretor.")
            return redirect("core:inicio")
        return view_func(request, *args, **kwargs)

    return _wrapped


def pode_operar_evento(user, evento):
    """True se o usuário pode operar o PDV do evento: Diretor ou operador dele."""
    if not getattr(user, "is_authenticated", False):
        return False
    if eh_diretor(user):
        return True
    return evento.operadores.filter(usuario=user).exists()


def operador_required(view_func):
    """Restringe a view (que recebe `pk` do evento) ao Diretor ou a um operador
    daquele evento. Sem acesso, volta para a área inicial."""

    @login_required
    @wraps(view_func)
    def _wrapped(request, pk, *args, **kwargs):
        from .models import Evento

        evento = get_object_or_404(Evento, pk=pk)
        if not pode_operar_evento(request.user, evento):
            messages.error(request, "Você não tem acesso ao PDV deste evento.")
            return redirect("core:inicio")
        return view_func(request, pk, *args, **kwargs)

    return _wrapped
