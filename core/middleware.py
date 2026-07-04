"""Middlewares do app core."""

from django.shortcuts import redirect
from django.urls import reverse

from .models import PerfilUsuario


class TrocaSenhaObrigatoriaMiddleware:
    """Enquanto o usuário tiver `precisa_trocar_senha` (contas temporárias de
    ajudantes no 1º login), redireciona tudo para a tela de trocar senha."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            perfil = (
                PerfilUsuario.objects
                .filter(usuario=user)
                .only("precisa_trocar_senha")
                .first()
            )
            if perfil is not None and perfil.precisa_trocar_senha:
                permitidos = {reverse("core:trocar_senha"), reverse("core:sair")}
                caminho = request.path
                if (
                    caminho not in permitidos
                    and not caminho.startswith("/static")
                    and not caminho.startswith("/media")
                ):
                    return redirect("core:trocar_senha")
        return self.get_response(request)
