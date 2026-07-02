from django.shortcuts import render


def login_view(request):
    """
    Exibe a tela de login.

    Por enquanto apenas renderiza o template — a autenticação real
    ainda não está implementada.
    """
    return render(request, "core/login.html")


def inicio_view(request):
    """
    Exibe a tela inicial interna (área logada).

    Nesta etapa é apenas visual: NÃO há autenticação, permissões nem
    controle de sessão. Será exibida futuramente após o login.
    """
    return render(request, "core/inicio.html")
