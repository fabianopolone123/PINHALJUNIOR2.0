from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import (
    AutorizacaoImagemForm,
    AventureiroForm,
    ContaForm,
    FichaMedicaForm,
)


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


def _instanciar_forms(request):
    """Cria os quatro formulários (com prefixos) para GET ou POST."""
    if request.method == "POST":
        conta = ContaForm(request.POST, prefix="conta")
        aventureiro = AventureiroForm(request.POST, request.FILES, prefix="av")
        medica = FichaMedicaForm(request.POST, prefix="med")
        imagem = AutorizacaoImagemForm(request.POST, prefix="img")
    else:
        conta = ContaForm(prefix="conta")
        aventureiro = AventureiroForm(prefix="av")
        medica = FichaMedicaForm(prefix="med")
        imagem = AutorizacaoImagemForm(prefix="img")
    return conta, aventureiro, medica, imagem


def cadastro_view(request):
    """
    Cadastro de conta + aventureiro (ficha, médica e autorização de imagem).

    Fluxo visual em etapas (wizard) no front-end; no servidor tudo é
    enviado de uma vez e validado em conjunto. NÃO faz login automático.
    """
    conta, aventureiro, medica, imagem = _instanciar_forms(request)
    erro_aceites = []

    if request.method == "POST":
        formularios_ok = all(
            [
                conta.is_valid(),
                aventureiro.is_valid(),
                medica.is_valid(),
                imagem.is_valid(),
            ]
        )

        # Aceites obrigatórios (declaração médica e autorização de imagem).
        declaracao_ok = bool(
            aventureiro.data.get("av-declaracao_medica_aceita")
        )
        autorizacao_ok = bool(
            aventureiro.data.get("av-autorizacao_imagem_aceita")
        )
        if not declaracao_ok:
            erro_aceites.append("É necessário aceitar a declaração médica.")
        if not autorizacao_ok:
            erro_aceites.append("É necessário aceitar a autorização de uso de imagem.")

        if formularios_ok and declaracao_ok and autorizacao_ok:
            with transaction.atomic():
                # 1) Cria o usuário de acesso.
                usuario = User.objects.create_user(
                    username=conta.cleaned_data["username"],
                    password=conta.cleaned_data["senha"],
                )

                # 2) Salva o aventureiro (ficha de inscrição + responsáveis).
                aventureiro_obj = aventureiro.save(commit=False)
                aventureiro_obj.usuario = usuario
                aventureiro_obj.declaracao_medica_aceita = True
                aventureiro_obj.autorizacao_imagem_aceita = True
                aventureiro_obj.save()

                # 3) Salva a ficha médica.
                ficha = medica.save(commit=False)
                ficha.aventureiro = aventureiro_obj
                ficha.save()

                # 4) Salva a autorização de imagem.
                autorizacao = imagem.save(commit=False)
                autorizacao.aventureiro = aventureiro_obj
                autorizacao.save()

            return redirect("core:cadastro_sucesso")

    contexto = {
        "conta_form": conta,
        "aventureiro_form": aventureiro,
        "medica_form": medica,
        "imagem_form": imagem,
        "erro_aceites": erro_aceites,
    }
    return render(request, "core/cadastro.html", contexto)


def cadastro_sucesso_view(request):
    """Tela simples de confirmação após o cadastro."""
    return render(request, "core/cadastro_sucesso.html")
