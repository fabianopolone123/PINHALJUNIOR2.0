from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import (
    AutorizacaoImagemForm,
    AventureiroForm,
    ContaForm,
    FichaMedicaForm,
)

# ---------------------------------------------------------------------------
# Identificação temporária do usuário durante o fluxo de cadastro.
#
# ATENÇÃO (temporário): enquanto a autenticação real (login/logout) não é
# implementada, guardamos o id do usuário recém-criado na sessão para permitir
# cadastrar mais de um aventureiro na mesma conta. Quando o login real existir,
# basta trocar `request.session[SESSAO_USUARIO_ID]` por `request.user`.
# ---------------------------------------------------------------------------
SESSAO_USUARIO_ID = "cadastro_usuario_id"
SESSAO_ULTIMO_NOME = "cadastro_ultimo_nome"


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


def _instanciar_forms_aventureiro(request):
    """Cria os três formulários da ficha (com prefixos) para GET ou POST.

    Usado tanto no cadastro inicial quanto no cadastro de um novo aventureiro
    na mesma conta (que não tem a etapa de criação de conta).
    """
    if request.method == "POST":
        aventureiro = AventureiroForm(request.POST, request.FILES, prefix="av")
        medica = FichaMedicaForm(request.POST, prefix="med")
        imagem = AutorizacaoImagemForm(request.POST, prefix="img")
    else:
        aventureiro = AventureiroForm(prefix="av")
        medica = FichaMedicaForm(prefix="med")
        imagem = AutorizacaoImagemForm(prefix="img")
    return aventureiro, medica, imagem


def _validar_aceites(aventureiro):
    """Valida os aceites obrigatórios (declaração médica e uso de imagem)."""
    erros = []
    declaracao_ok = bool(aventureiro.data.get("av-declaracao_medica_aceita"))
    autorizacao_ok = bool(aventureiro.data.get("av-autorizacao_imagem_aceita"))
    if not declaracao_ok:
        erros.append("É necessário aceitar a declaração médica.")
    if not autorizacao_ok:
        erros.append("É necessário aceitar a autorização de uso de imagem.")
    return erros


def _salvar_aventureiro(usuario, aventureiro, medica, imagem):
    """Salva o aventureiro + ficha médica + autorização de imagem (transacional)."""
    with transaction.atomic():
        aventureiro_obj = aventureiro.save(commit=False)
        aventureiro_obj.usuario = usuario
        aventureiro_obj.declaracao_medica_aceita = True
        aventureiro_obj.autorizacao_imagem_aceita = True
        aventureiro_obj.save()

        ficha = medica.save(commit=False)
        ficha.aventureiro = aventureiro_obj
        ficha.save()

        autorizacao = imagem.save(commit=False)
        autorizacao.aventureiro = aventureiro_obj
        autorizacao.save()
    return aventureiro_obj


def _dados_responsaveis_anteriores(usuario):
    """Retorna os dados de pai/mãe/responsável legal do último aventureiro.

    Usado para oferecer o reaproveitamento no cadastro de um novo aventureiro
    da mesma conta. Retorna ``None`` quando o usuário ainda não tem aventureiros.
    """
    ultimo = usuario.aventureiros.order_by("-criado_em").first()
    if ultimo is None:
        return None
    campos = [
        "pai_nome", "pai_email", "pai_cpf", "pai_celular", "pai_whatsapp",
        "mae_nome", "mae_email", "mae_cpf", "mae_celular", "mae_whatsapp",
        "resp_nome", "resp_parentesco", "resp_cpf", "resp_email", "resp_whatsapp",
    ]
    return {campo: getattr(ultimo, campo) for campo in campos}


def cadastro_view(request):
    """
    Cadastro inicial: cria a conta de acesso + o primeiro aventureiro
    (ficha de inscrição, ficha médica e autorização de imagem).

    Fluxo visual em etapas (wizard) no front-end; no servidor tudo é
    enviado de uma vez e validado em conjunto. NÃO faz login automático,
    mas guarda o usuário na sessão para permitir cadastrar outros aventureiros.
    """
    conta = ContaForm(request.POST or None, prefix="conta")
    aventureiro, medica, imagem = _instanciar_forms_aventureiro(request)
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
        erro_aceites = _validar_aceites(aventureiro)

        if formularios_ok and not erro_aceites:
            usuario = User.objects.create_user(
                username=conta.cleaned_data["username"],
                password=conta.cleaned_data["senha"],
            )
            aventureiro_obj = _salvar_aventureiro(usuario, aventureiro, medica, imagem)
            # Mantém o usuário "atual" durante o fluxo (temporário, ver topo).
            request.session[SESSAO_USUARIO_ID] = usuario.pk
            request.session[SESSAO_ULTIMO_NOME] = aventureiro_obj.nome_completo
            return redirect("core:cadastro_sucesso")

    contexto = {
        "conta_form": conta,
        "aventureiro_form": aventureiro,
        "medica_form": medica,
        "imagem_form": imagem,
        "erro_aceites": erro_aceites,
        "modo_novo": False,
    }
    return render(request, "core/cadastro.html", contexto)


def cadastro_novo_aventureiro_view(request):
    """
    Cadastro de um NOVO aventureiro na mesma conta (sem etapa de conta).

    Exige que exista um usuário identificado na sessão (criado no cadastro
    inicial). Se não existir, redireciona para o cadastro inicial.
    """
    usuario_id = request.session.get(SESSAO_USUARIO_ID)
    usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
    if usuario is None:
        # Sem usuário identificado na sessão: volta para o cadastro inicial.
        request.session.pop(SESSAO_USUARIO_ID, None)
        return redirect("core:cadastro")

    aventureiro, medica, imagem = _instanciar_forms_aventureiro(request)
    erro_aceites = []

    if request.method == "POST":
        formularios_ok = all(
            [aventureiro.is_valid(), medica.is_valid(), imagem.is_valid()]
        )
        erro_aceites = _validar_aceites(aventureiro)

        if formularios_ok and not erro_aceites:
            aventureiro_obj = _salvar_aventureiro(usuario, aventureiro, medica, imagem)
            request.session[SESSAO_ULTIMO_NOME] = aventureiro_obj.nome_completo
            return redirect("core:cadastro_sucesso")

    contexto = {
        "aventureiro_form": aventureiro,
        "medica_form": medica,
        "imagem_form": imagem,
        "erro_aceites": erro_aceites,
        "modo_novo": True,
        "dados_anteriores": _dados_responsaveis_anteriores(usuario),
    }
    return render(request, "core/cadastro.html", contexto)


def cadastro_sucesso_view(request):
    """Tela de confirmação: mostra o nome cadastrado e as próximas opções."""
    contexto = {
        "nome_aventureiro": request.session.get(SESSAO_ULTIMO_NOME),
        # Só oferece "cadastrar outro" se houver um usuário identificado.
        "pode_cadastrar_outro": bool(request.session.get(SESSAO_USUARIO_ID)),
    }
    return render(request, "core/cadastro_sucesso.html", contexto)
