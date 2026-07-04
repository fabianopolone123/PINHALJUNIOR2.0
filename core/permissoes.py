"""
Helpers de permissão por perfil de acesso.

Os perfis são grupos nativos do Django (ver comando `configurar_perfis`):
Diretor, Responsável, Professor, Tesoureiro, Secretário. Por enquanto, só o
Diretor recebe permissões nas telas; os demais serão liberados no futuro.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

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
