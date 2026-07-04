import unicodedata
from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    AutorizacaoImagemForm,
    AventureiroForm,
    ContaForm,
    FichaMedicaForm,
    ResponsavelLegalForm,
)
from .models import Aventureiro

# ---------------------------------------------------------------------------
# Identificação do usuário durante o cadastro.
#
# Com a autenticação real, o fluxo correto usa `request.user`. As chaves de
# sessão abaixo permanecem apenas como retaguarda (fallback) e para levar o
# nome do último aventureiro à tela de sucesso.
# ---------------------------------------------------------------------------
SESSAO_USUARIO_ID = "cadastro_usuario_id"
SESSAO_ULTIMO_NOME = "cadastro_ultimo_nome"

BACKEND_PADRAO = "django.contrib.auth.backends.ModelBackend"


def login_view(request):
    """Tela de login com autenticação real (username + senha)."""
    # Já autenticado? Vai direto para a área interna.
    if request.user.is_authenticated:
        return redirect("core:inicio")

    erro = None
    usuario_digitado = ""
    if request.method == "POST":
        usuario_digitado = request.POST.get("usuario", "").strip()
        senha = request.POST.get("senha", "")
        # Login sem diferenciar maiúsculas/minúsculas no usuário (consistente com
        # o cadastro, que já impede usernames duplicados por `iexact`). Resolve o
        # username real antes de autenticar.
        username_real = (
            User.objects.filter(username__iexact=usuario_digitado)
            .values_list("username", flat=True)
            .first()
        )
        usuario = authenticate(
            request, username=username_real or usuario_digitado, password=senha
        )
        if usuario is not None:
            login(request, usuario)
            destino = request.POST.get("next") or request.GET.get("next")
            if destino and url_has_allowed_host_and_scheme(
                destino, allowed_hosts={request.get_host()}
            ):
                return redirect(destino)
            return redirect("core:inicio")
        erro = "Usuário ou senha inválidos."

    contexto = {
        "erro": erro,
        "usuario_digitado": usuario_digitado,
        "next": request.GET.get("next", ""),
    }
    return render(request, "core/login.html", contexto)


@require_POST
def sair_view(request):
    """Encerra a sessão do usuário e volta para a tela de login."""
    logout(request)
    return redirect("core:login")


def _idade(nascimento):
    """Idade aproximada em anos completos a partir da data de nascimento."""
    if not nascimento:
        return None
    hoje = date.today()
    return hoje.year - nascimento.year - (
        (hoje.month, hoje.day) < (nascimento.month, nascimento.day)
    )


def _iniciais(nome):
    """Iniciais (até 2 letras) do nome, para o placeholder de foto."""
    partes = [p for p in (nome or "").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][0].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _foto_valida(av):
    """True apenas se o campo tem valor E o arquivo existe fisicamente."""
    if not av.foto:
        return False
    try:
        return av.foto.storage.exists(av.foto.name)
    except Exception:
        return False


def _classes_investidas(av):
    """Lista de rótulos das classes marcadas para o aventureiro."""
    mapa = [
        (av.classe_abelhinhas, "Abelhinhas"),
        (av.classe_luminares, "Luminares"),
        (av.classe_edificadores, "Edificadores"),
        (av.classe_maos_ajudadoras, "Mãos Ajudadoras"),
    ]
    return [rotulo for marcado, rotulo in mapa if marcado]


def _preparar_ficha(fm):
    """Anexa à ficha médica listas prontas para exibição (ou None)."""
    if fm is None:
        return None

    doencas = [
        (fm.catapora, "Catapora"), (fm.meningite, "Meningite"),
        (fm.hepatite, "Hepatite"), (fm.dengue, "Dengue"),
        (fm.pneumonia, "Pneumonia"), (fm.malaria, "Malária"),
        (fm.febre_amarela, "Febre amarela"), (fm.h1n1, "H1N1"),
        (fm.colera, "Cólera"), (fm.rubeola, "Rubéola"),
        (fm.sarampo, "Sarampo"), (fm.tetano, "Tétano"),
    ]
    fm.doencas_lista = [r for marcado, r in doencas if marcado]

    alergias = []
    if fm.alergia_pele:
        alergias.append("Cutânea/de pele" + (f": {fm.alergia_pele_qual}" if fm.alergia_pele_qual else ""))
    if fm.alergia_alimentar:
        alergias.append("Alimentar" + (f": {fm.alergia_alimentar_qual}" if fm.alergia_alimentar_qual else ""))
    if fm.alergia_medicamentos:
        alergias.append("Medicamentos" + (f": {fm.alergia_medicamentos_qual}" if fm.alergia_medicamentos_qual else ""))
    fm.alergias_lista = alergias

    condicoes = [
        (fm.cardiaco, "Cardíacos", fm.cardiaco_medicamentos),
        (fm.diabetico, "Diabetes", fm.diabetico_medicamentos),
        (fm.renais, "Renais", fm.renais_medicamentos),
        (fm.psicologicos, "Psicológicos", fm.psicologicos_medicamentos),
    ]
    fm.condicoes_lista = [
        r + (f" (medicamentos: {med})" if med else "")
        for marcado, r, med in condicoes if marcado
    ]

    historico = [
        (fm.problema_recente, "Problema de saúde recente", fm.problema_recente_qual),
        (fm.medicamento_recente, "Uso recente de medicamentos", fm.medicamento_recente_qual),
        (fm.ferimento_recente, "Ferimento/fratura recente", fm.ferimento_recente_qual),
        (fm.cirurgia, "Cirurgia", fm.cirurgia_qual),
        (fm.internado_5anos, "Internação nos últimos 5 anos", fm.internado_5anos_motivo),
    ]
    fm.historico_lista = [
        r + (f": {det}" if det else "")
        for marcado, r, det in historico if marcado
    ]

    # Condição -> "Sim (medicamentos: X)" / "Não", para exibição direta.
    def _cond(marcado, med):
        if not marcado:
            return "Não"
        return "Sim" + (f" (medicamentos: {med})" if med else "")

    fm.cardiaco_txt = _cond(fm.cardiaco, fm.cardiaco_medicamentos)
    fm.diabetico_txt = _cond(fm.diabetico, fm.diabetico_medicamentos)
    fm.renais_txt = _cond(fm.renais, fm.renais_medicamentos)
    fm.psicologicos_txt = _cond(fm.psicologicos, fm.psicologicos_medicamentos)
    return fm


@login_required
def inicio_view(request):
    """Área interna "Meus Dados": dados da conta + aventureiros do usuário."""
    usuario = request.user
    aventureiros = list(
        usuario.aventureiros
        .select_related("ficha_medica", "autorizacao_imagem")
        .all()
    )

    for av in aventureiros:
        av.idade = _idade(av.data_nascimento)
        av.classes = _classes_investidas(av)
        av.foto_ok = _foto_valida(av)
        av.iniciais = _iniciais(av.nome_completo)
        # Reverse OneToOne pode não existir; getattr evita exceção.
        _preparar_ficha(getattr(av, "ficha_medica", None))

    # Responsável principal: dados do responsável legal do aventureiro mais recente.
    ultimo = max(aventureiros, key=lambda a: a.criado_em) if aventureiros else None
    responsavel = None
    if ultimo is not None:
        autorizacao = getattr(ultimo, "autorizacao_imagem", None)
        responsavel = {
            "nome": ultimo.resp_nome,
            "parentesco": ultimo.resp_parentesco,
            "cpf": ultimo.resp_cpf,
            "email": ultimo.resp_email,
            "whatsapp": ultimo.resp_whatsapp,
            "cidade": autorizacao.resp_cidade if autorizacao else "",
            "estado": autorizacao.resp_estado if autorizacao else "",
        }

    contexto = {
        "aventureiros": aventureiros,
        "total_aventureiros": len(aventureiros),
        "responsavel": responsavel,
    }
    return render(request, "core/inicio.html", contexto)


@login_required
def editar_responsavel_view(request):
    """
    Edita os dados do responsável legal do usuário logado.

    Como o responsável é gravado em cada `Aventureiro`, a alteração é aplicada a
    todos os aventureiros do usuário que compartilham o mesmo CPF de responsável
    (base: o aventureiro mais recente). Se nenhum tiver o mesmo CPF, altera apenas
    o mais recente. Nunca toca em dados de outros usuários.
    """
    usuario = request.user
    base = usuario.aventureiros.order_by("-criado_em").first()
    if base is None:
        messages.error(
            request, "Você ainda não tem aventureiros cadastrados para editar o responsável."
        )
        return redirect("core:inicio")

    if request.method == "POST":
        form = ResponsavelLegalForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            cpf_base = (base.resp_cpf or "").strip()
            # Materializa os alvos ANTES de alterar o CPF.
            if cpf_base:
                alvos = list(usuario.aventureiros.filter(resp_cpf=cpf_base))
            else:
                alvos = []
            if not alvos:
                alvos = [base]

            campos = [
                "resp_nome", "resp_parentesco", "resp_cpf", "resp_email", "resp_whatsapp",
            ]
            for av in alvos:
                for campo in campos:
                    setattr(av, campo, dados[campo])
                av.save(update_fields=campos)

            messages.success(request, "Dados do responsável atualizados com sucesso.")
            return redirect("core:inicio")
        messages.error(request, "Não foi possível salvar. Verifique os campos destacados.")
    else:
        form = ResponsavelLegalForm(
            initial={
                "resp_nome": base.resp_nome,
                "resp_parentesco": base.resp_parentesco,
                "resp_cpf": base.resp_cpf,
                "resp_email": base.resp_email,
                "resp_whatsapp": base.resp_whatsapp,
            }
        )

    return render(request, "core/editar_responsavel.html", {"form": form})


def _instanciar_forms_aventureiro(request):
    """Cria os três formulários da ficha (com prefixos) para GET ou POST."""
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
    """Dados de pai/mãe/responsável legal do último aventureiro (ou None)."""
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
    Cadastro inicial: cria a conta de acesso + o primeiro aventureiro.

    Ao finalizar, o usuário é autenticado automaticamente (login real) e
    redirecionado para a tela de sucesso.
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
            # Login automático (autenticação real) + retaguarda por sessão.
            login(request, usuario, backend=BACKEND_PADRAO)
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

    Prioriza o usuário autenticado (`request.user`); como retaguarda, aceita o
    usuário guardado na sessão. Sem nenhum dos dois, redireciona para o login.
    """
    if request.user.is_authenticated:
        usuario = request.user
    else:
        usuario_id = request.session.get(SESSAO_USUARIO_ID)
        usuario = User.objects.filter(pk=usuario_id).first() if usuario_id else None
    if usuario is None:
        return redirect("core:login")

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


def _normaliza(texto):
    """Minúsculas + sem acentos + espaços colapsados (para chaves/pesquisa)."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


_ORDEM_PAPEIS = {"Pai": 0, "Mãe": 1, "Responsável legal": 2}


def _ordena_papeis(papeis):
    return sorted(papeis, key=lambda p: _ORDEM_PAPEIS.get(p, 99))


def _chave_responsavel(nome, cpf, whatsapp):
    """Chave para agrupar responsáveis: CPF > nome+WhatsApp > nome. Sem nome -> None."""
    nome_n = _normaliza(nome)
    if not nome_n:
        return None
    cpf = (cpf or "").strip()
    if cpf:
        return f"cpf:{cpf}"
    whats = (whatsapp or "").strip()
    if whats:
        return f"nw:{nome_n}|{_normaliza(whats)}"
    return f"n:{nome_n}"


@login_required
def usuarios_view(request):
    """
    Visão geral de responsáveis e aventureiros com o vínculo familiar.

    Considera pai, mãe e responsável legal de cada aventureiro, agrupa
    responsáveis únicos (por CPF, ou nome+WhatsApp, ou nome) e junta papéis e
    aventureiros vinculados. Exibe apenas dados resumidos (nada sensível).

    Acesso: qualquer usuário autenticado. FUTURO: poderá ser restrito por perfil.
    """
    aventureiros = list(Aventureiro.objects.all())

    responsaveis = {}   # chave -> {nome, papeis:set, vinculos: {av_id: {...}}}
    total_vinculos = 0
    resumo_aventureiros = []

    for av in aventureiros:
        idade = _idade(av.data_nascimento)
        resumo_aventureiros.append({
            "nome": av.nome_completo,
            "idade": idade,
            "pai": av.pai_nome or "",
            "mae": av.mae_nome or "",
            "resp": av.resp_nome or "",
        })

        candidatos = [
            ("Pai", av.pai_nome, av.pai_cpf, av.pai_whatsapp),
            ("Mãe", av.mae_nome, av.mae_cpf, av.mae_whatsapp),
            ("Responsável legal", av.resp_nome, av.resp_cpf, av.resp_whatsapp),
        ]
        for papel, nome, cpf, whats in candidatos:
            chave = _chave_responsavel(nome, cpf, whats)
            if chave is None:
                continue
            total_vinculos += 1
            resp = responsaveis.setdefault(
                chave, {"nome": nome.strip(), "papeis": set(), "vinculos": {}}
            )
            resp["papeis"].add(papel)
            vinc = resp["vinculos"].setdefault(
                av.id, {"nome": av.nome_completo, "idade": idade, "papeis": set()}
            )
            vinc["papeis"].add(papel)

    lista_responsaveis = []
    for resp in responsaveis.values():
        vinculos = [
            {"nome": v["nome"], "idade": v["idade"], "papeis": _ordena_papeis(v["papeis"])}
            for v in resp["vinculos"].values()
        ]
        vinculos.sort(key=lambda x: _normaliza(x["nome"]))
        lista_responsaveis.append({
            "nome": resp["nome"],
            "papeis": _ordena_papeis(resp["papeis"]),
            "vinculos": vinculos,
        })
    lista_responsaveis.sort(key=lambda x: _normaliza(x["nome"]))

    resumo_aventureiros.sort(key=lambda x: _normaliza(x["nome"]))

    contexto = {
        "responsaveis": lista_responsaveis,
        "resumo_aventureiros": resumo_aventureiros,
        "total_responsaveis": len(lista_responsaveis),
        "total_aventureiros": len(aventureiros),
        "total_vinculos": total_vinculos,
    }
    return render(request, "core/usuarios.html", contexto)


def cadastro_sucesso_view(request):
    """Tela de confirmação: mostra o nome cadastrado e as próximas opções."""
    pode_cadastrar_outro = (
        request.user.is_authenticated
        or bool(request.session.get(SESSAO_USUARIO_ID))
    )
    contexto = {
        "nome_aventureiro": request.session.get(SESSAO_ULTIMO_NOME),
        "pode_cadastrar_outro": pode_cadastrar_outro,
    }
    return render(request, "core/cadastro_sucesso.html", contexto)
