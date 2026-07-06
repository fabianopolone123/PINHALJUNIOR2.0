import datetime
import hashlib
import json
from collections import defaultdict
import re
import secrets
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from .forms import (
    AutorizacaoImagemForm,
    AventureiroForm,
    CampoInscricaoForm,
    ContaForm,
    CustoEventoForm,
    EventoComplexoForm,
    EventoForm,
    EventoInscricaoConfigForm,
    FaixaEtariaPrecoForm,
    FichaMedicaForm,
    InscricaoForm,
    ProdutoEventoForm,
    ProdutoLojaForm,
    ResponsavelLegalForm,
)
from .models import (
    FORMA_PAGAMENTO_CHOICES,
    MESES_PT,
    Aventureiro,
    CompraLoja,
    ConfigMensalidade,
    CupomDesconto,
    Evento,
    FotoProdutoLoja,
    GrupoLoja,
    Inscricao,
    ItemCompraLoja,
    ItemPedidoLoja,
    Mensalidade,
    OperadorEvento,
    ParticipanteInscricao,
    PedidoLoja,
    PerfilUsuario,
    PresencaEvento,
    ProdutoEvento,
    ProdutoLoja,
    RespostaInscricao,
    VariacaoLoja,
    VariacaoProduto,
    WhatsappConfig,
)
from .permissoes import diretor_required, eh_diretor, operador_required, pode_operar_evento

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
            # Ajudante externo (conta temporária) vai direto para o evento dele.
            op = OperadorEvento.objects.filter(usuario=usuario, externo=True).first()
            if op is not None:
                url = reverse("core:evento_operar", args=[op.evento_id])
            else:
                destino = request.POST.get("next") or request.GET.get("next")
                if destino and url_has_allowed_host_and_scheme(
                    destino, allowed_hosts={request.get_host()}
                ):
                    url = destino
                else:
                    url = reverse("core:inicio")
            if _eh_ajax(request):
                return _ajax_redirect(url)
            return redirect(url)
        if _eh_ajax(request):
            return _ajax_toast("Usuário ou senha inválidos.")
        messages.error(request, "Usuário ou senha inválidos.")

    contexto = {
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
    # Ajudante externo não tem "Meus Dados": vai direto para o evento dele.
    op_externo = OperadorEvento.objects.filter(
        usuario=request.user, externo=True
    ).first()
    if op_externo is not None:
        return redirect("core:evento_operar", pk=op_externo.evento_id)

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
        # Gera as mensalidades do ano: o mês atual como inscrição e os
        # seguintes como mensalidade (valores/isenção conforme configuração).
        hoje = timezone.localdate()
        _gerar_mensalidades(aventureiro_obj, hoje.year, mes_inscricao=hoje.month)
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


# Conectores de nome (não ajudam a identificar a pessoa e atrapalham o casamento).
_CONECTORES_NOME = {"de", "da", "do", "das", "dos", "e"}


def _tokens_lista(nome):
    """Nomes significativos, em ordem (sem acento/caixa e sem conectores).
    Usado para casar nomes de participantes com aventureiros cadastrados."""
    return [t for t in _normaliza(nome).split() if t not in _CONECTORES_NOME]


def _cobre_token(p, a):
    """True se o token `p` (do participante) casa com `a` (do aventureiro):
    igualdade, ou uma **inicial** (token de 1 letra) que começa o outro
    (ex.: 'z' casa com 'zanatta')."""
    return p == a or (len(p) == 1 and a.startswith(p)) or (len(a) == 1 and p.startswith(a))


def _nome_casa(pt, at):
    """True se **todos** os tokens do participante (`pt`, lista) são cobertos por
    tokens **distintos** do aventureiro (`at`, lista) — igualdade ou inicial. Assim
    'Alice Z Moreira' casa com 'Alice Zanatta Moreira', e 'Beatriz Gonçalves' ainda
    casa com 'Beatriz Gonçalves Steinmeyer' (subconjunto)."""
    if not pt:
        return False
    resto = list(at)
    for p in pt:
        alvo = next((j for j, a in enumerate(resto) if a == p), None)  # exato primeiro
        if alvo is None:
            alvo = next((j for j, a in enumerate(resto) if _cobre_token(p, a)), None)
        if alvo is None:
            return False
        resto.pop(alvo)
    return True


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


@diretor_required
def usuarios_view(request):
    """
    Visão geral de responsáveis e aventureiros com o vínculo familiar.

    Restrito ao perfil **Diretor** (exibe dados completos ao clicar em um card,
    num modal). Considera pai, mãe e responsável legal de cada aventureiro,
    agrupa responsáveis únicos (por CPF, ou nome+WhatsApp, ou nome) e junta
    papéis, dados de contato e aventureiros vinculados.
    """
    aventureiros = list(
        Aventureiro.objects
        .select_related("ficha_medica", "autorizacao_imagem", "usuario")
        .all()
    )

    responsaveis = {}   # chave -> {nome, papeis, contato..., vinculos: {av_id: {...}}}

    for av in aventureiros:
        # Dados de exibição do aventureiro (usados no modal detalhado).
        av.idade = _idade(av.data_nascimento)
        av.classes = _classes_investidas(av)
        av.foto_ok = _foto_valida(av)
        av.iniciais = _iniciais(av.nome_completo)
        av.conta_ativa = bool(av.usuario and av.usuario.is_active)
        _preparar_ficha(getattr(av, "ficha_medica", None))

        candidatos = [
            ("Pai", av.pai_nome, av.pai_cpf, av.pai_email, av.pai_celular, av.pai_whatsapp),
            ("Mãe", av.mae_nome, av.mae_cpf, av.mae_email, av.mae_celular, av.mae_whatsapp),
            ("Responsável legal", av.resp_nome, av.resp_cpf, av.resp_email, "", av.resp_whatsapp),
        ]
        for papel, nome, cpf, email, celular, whats in candidatos:
            chave = _chave_responsavel(nome, cpf, whats)
            if chave is None:
                continue
            resp = responsaveis.setdefault(chave, {
                "nome": nome.strip(), "papeis": set(),
                "cpf": "", "email": "", "celular": "", "whatsapp": "",
                "vinculos": {},
            })
            resp["papeis"].add(papel)
            # Guarda o primeiro contato não-vazio encontrado para a pessoa.
            for campo, valor in (
                ("cpf", cpf), ("email", email), ("celular", celular), ("whatsapp", whats),
            ):
                if not resp[campo] and (valor or "").strip():
                    resp[campo] = valor.strip()
            vinc = resp["vinculos"].setdefault(
                av.id,
                {"nome": av.nome_completo, "idade": av.idade,
                 "papeis": set(), "ativo": av.ativo},
            )
            vinc["papeis"].add(papel)

    lista_responsaveis = []
    for resp in responsaveis.values():
        vinculos = [
            {"nome": v["nome"], "idade": v["idade"],
             "papeis": _ordena_papeis(v["papeis"]), "ativo": v["ativo"]}
            for v in resp["vinculos"].values()
        ]
        vinculos.sort(key=lambda x: _normaliza(x["nome"]))
        # Responsável é "ativo" enquanto tiver ao menos um aventureiro ativo
        # (mesma regra da conta). Todos inativos -> responsável inativo.
        resp_ativo = any(v["ativo"] for v in vinculos)
        lista_responsaveis.append({
            "nome": resp["nome"],
            "papeis": _ordena_papeis(resp["papeis"]),
            "cpf": resp["cpf"], "email": resp["email"],
            "celular": resp["celular"], "whatsapp": resp["whatsapp"],
            "vinculos": vinculos,
            "ativo": resp_ativo,
        })
    lista_responsaveis.sort(key=lambda x: _normaliza(x["nome"]))

    # Vincula cada responsável (por CPF) à conta em que ele é o responsável legal,
    # para o Diretor poder escolher o WhatsApp principal (recuperação de senha).
    # Só quando há exatamente uma conta para aquele CPF.
    cpf_para_contas = {}
    for av in aventureiros:
        if av.usuario_id:
            k = _so_digitos(av.resp_cpf)
            if k:
                cpf_para_contas.setdefault(k, set()).add(av.usuario_id)

    for i, resp in enumerate(lista_responsaveis):
        resp["id"] = f"resp-{i}"
        resp["conta_id"] = None
        resp["numeros_principal"] = []
        resp["principal_origem"] = ""
        k = _so_digitos(resp["cpf"])
        contas = cpf_para_contas.get(k) if k else None
        if contas and len(contas) == 1:
            uid = next(iter(contas))
            usuario = next((a.usuario for a in aventureiros if a.usuario_id == uid), None)
            if usuario is not None:
                resp["conta_id"] = uid
                resp["numeros_principal"] = _numeros_conta(usuario)
                perfil = getattr(usuario, "perfil", None)
                resp["principal_origem"] = perfil.whatsapp_principal_origem if perfil else ""

    aventureiros.sort(key=lambda a: _normaliza(a.nome_completo))

    contexto = {
        "responsaveis": lista_responsaveis,
        "aventureiros": aventureiros,
        "total_responsaveis": len(lista_responsaveis),
        "total_aventureiros": len(aventureiros),
        "total_ativos": sum(1 for a in aventureiros if a.ativo),
    }
    return render(request, "core/usuarios.html", contexto)


@diretor_required
@require_POST
def aventureiro_toggle_ativo_view(request, pk):
    """Marca um aventureiro como inativo (desligado) ou reativa (Diretor).

    Cascata na conta do responsável (`usuario`): se, após a mudança, o usuário
    não tiver **nenhum** aventureiro ativo, a conta é **desativada** (`is_active`
    = False); se tiver pelo menos um ativo, a conta fica/volta ativa. Contas de
    Diretor/staff nunca são desativadas por aqui (evita travar o acesso admin)."""
    av = get_object_or_404(Aventureiro, pk=pk)
    av.ativo = not av.ativo
    av.save(update_fields=["ativo"])

    user = av.usuario
    conta_desativada = False
    if user is not None:
        tem_ativo = user.aventureiros.filter(ativo=True).exists()
        protegido = (
            user.is_staff or user.is_superuser or eh_diretor(user)
        )
        novo_status = tem_ativo or protegido
        if user.is_active != novo_status:
            user.is_active = novo_status
            user.save(update_fields=["is_active"])
        conta_desativada = not novo_status and not tem_ativo

    if av.ativo:
        messages.success(request, f"“{av.nome_completo}” foi reativado.")
    else:
        msg = f"“{av.nome_completo}” marcado como inativo (desligado)."
        if conta_desativada:
            msg += " A conta do responsável também foi desativada (sem aventureiros ativos)."
        messages.success(request, msg)
    return redirect("core:usuarios")


@diretor_required
def eventos_view(request):
    """Lista os eventos do clube. Restrito ao perfil Diretor."""
    eventos = list(Evento.objects.all())
    # Um evento só pode ser excluído se estiver "vazio" (sem inscrições, pedidos
    # nem presença marcada) — protege dados de pessoas/vendas/presença. Ver
    # `evento_excluir_view`.
    for e in eventos:
        e.pode_excluir = not (
            e.inscricoes.exists() or e.pedidos.exists() or e.presencas.exists()
        )
    return render(request, "core/eventos.html", {"eventos": eventos})


@diretor_required
@require_POST
def evento_excluir_view(request, pk):
    """Exclui um evento (Diretor), **apenas se estiver vazio** — sem nenhuma
    inscrição, pedido da lojinha ou **presença marcada**. Assim é possível apagar
    eventos de teste/erro sem risco de destruir dados de pessoas, vendas ou
    presença. A exclusão remove em cascata os dados de configuração do evento
    (custos, produtos, faixas, campos e operadores)."""
    evento = get_object_or_404(Evento, pk=pk)
    if evento.inscricoes.exists() or evento.pedidos.exists() or evento.presencas.exists():
        messages.error(
            request,
            "Não é possível excluir: este evento já tem inscrições, pedidos ou "
            "presença marcada. Ele é mantido para preservar esses dados.",
        )
        return redirect("core:eventos")
    nome = evento.nome
    evento.delete()
    messages.success(request, f"Evento “{nome}” excluído.")
    return redirect("core:eventos")


@diretor_required
def evento_novo_view(request):
    """
    Cadastra um evento simples (restrito ao Diretor).

    Suporta `?duplicar=<id>`: pré-preenche o formulário com os dados de um evento
    existente (para recadastrar algo recorrente mudando só a data/horário).
    """
    if request.method == "POST":
        form = EventoForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.tipo = "simples"
            evento.criado_por = request.user
            evento.save()
            messages.success(request, "Evento cadastrado com sucesso.")
            return redirect("core:eventos")
        messages.error(request, "Não foi possível salvar. Verifique os campos destacados.")
    else:
        initial = {}
        duplicar_id = request.GET.get("duplicar")
        if duplicar_id:
            base = Evento.objects.filter(pk=duplicar_id).first()
            if base is not None:
                initial = {
                    "nome": base.nome,
                    "local": base.local,
                    "descricao": base.descricao,
                    "data": base.data,
                    "horario_inicio": base.horario_inicio,
                    "horario_fim": base.horario_fim,
                }
        form = EventoForm(initial=initial)

    duplicando = bool(request.GET.get("duplicar"))
    return render(
        request, "core/evento_form.html", {"form": form, "duplicando": duplicando}
    )


@diretor_required
def evento_complexo_novo_view(request):
    """Cria um evento complexo (com inscrição). Fase 1: dados básicos + painel."""
    if request.method == "POST":
        form = EventoComplexoForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.tipo = "inscricao"
            evento.criado_por = request.user
            evento.save()
            messages.success(
                request, "Evento criado! Configure os detalhes no painel do evento."
            )
            return redirect("core:evento_painel", pk=evento.pk)
        messages.error(request, "Não foi possível salvar. Verifique os campos destacados.")
    else:
        form = EventoComplexoForm()
    return render(request, "core/evento_complexo_form.html", {"form": form})


def _montar_financeiro(inscricoes, confirmadas, pedidos, pedidos_confirmados, custos,
                       arrecadacao_inscricoes, vendas_loja, total_custos):
    """Monta o extrato financeiro completo do evento (Fase 5).

    Consolida ENTRADAS (inscrições + lojinha confirmadas) e SAÍDAS (custos):
    resultado, agrupamentos (por fonte, por forma de pagamento e por canal) e um
    **extrato** cronológico com TODOS os lançamentos — inclusive os cancelados
    (mostrados para auditoria, mas **fora** dos totais). Só entra nos totais o que
    está confirmado. Cortesia soma R$ 0 (mas conta como transação)."""
    receitas = arrecadacao_inscricoes + vendas_loja
    resultado = receitas - total_custos
    formas_labels = dict(FORMA_PAGAMENTO_CHOICES)

    # --- Entradas por forma de pagamento (só confirmadas) ---
    formas = {}
    def _add_forma(forma, valor):
        b = formas.setdefault(forma, {"valor": Decimal("0"), "qtd": 0})
        b["valor"] += valor
        b["qtd"] += 1
    for i in confirmadas:
        _add_forma(i.forma_pagamento, i.valor_total)
    for p in pedidos_confirmados:
        _add_forma(p.forma_pagamento, p.valor_total)
    entradas_por_forma = [
        {"forma": formas_labels.get(k, k), "valor": v["valor"], "qtd": v["qtd"]}
        for k, v in sorted(formas.items(), key=lambda kv: kv[1]["valor"], reverse=True)
    ]

    # --- Entradas por canal (online × balcão), só confirmadas ---
    canal_online = Decimal("0")
    canal_pdv = Decimal("0")
    for reg in list(confirmadas) + list(pedidos_confirmados):
        if reg.origem == "pdv":
            canal_pdv += reg.valor_total
        else:
            canal_online += reg.valor_total

    # --- Extrato: todos os lançamentos (inclusive cancelados) ---
    extrato = []
    for i in inscricoes:
        extrato.append({
            "data": i.criado_em, "tipo": "Inscrição", "codigo": i.codigo,
            "descricao": i.responsavel_nome or "—",
            "forma": formas_labels.get(i.forma_pagamento, ""),
            "canal": "Balcão" if i.origem == "pdv" else "Online",
            "valor": i.valor_total, "entrada": True,
            "cancelado": i.status == "cancelada",
        })
    for p in pedidos:
        extrato.append({
            "data": p.criado_em, "tipo": "Lojinha", "codigo": p.codigo,
            "descricao": p.comprador_nome or "—",
            "forma": formas_labels.get(p.forma_pagamento, ""),
            "canal": "Balcão" if p.origem == "pdv" else "Online",
            "valor": p.valor_total, "entrada": True,
            "cancelado": p.status == "cancelado",
        })
    for c in custos:
        extrato.append({
            "data": c.criado_em, "tipo": "Custo", "codigo": "",
            "descricao": c.nome, "forma": "", "canal": "",
            "valor": c.valor, "entrada": False, "cancelado": False,
        })
    extrato.sort(key=lambda x: x["data"], reverse=True)

    return {
        "arrecadacao_inscricoes": arrecadacao_inscricoes,
        "vendas_loja": vendas_loja,
        "receitas": receitas,
        "custos": total_custos,
        "resultado": resultado,
        "entradas_por_forma": entradas_por_forma,
        "canal_online": canal_online,
        "canal_pdv": canal_pdv,
        "qtd_custos": len(custos),
        "extrato": extrato,
        "qtd_entradas": len(confirmadas) + len(pedidos_confirmados),
        "qtd_saidas": len(custos),
    }


def _montar_dashboard(confirmadas, pedidos_confirmados, custos, faixas, receitas,
                      total_custos, entradas_por_forma):
    """Dados visuais do Resumo (Fase 5.2): cobertura do clube + séries dos gráficos.

    **Cobertura**: tenta identificar quais aventureiros do clube estão inscritos
    comparando **conjuntos de nomes** (tokens, sem acento/caixa/conectores). Um
    participante casa com um aventureiro quando **todos os nomes digitados estão
    contidos** no nome cadastrado E isso aponta para **um único** aventureiro
    (senão fica "ambíguo" e não casa ninguém — evita falso positivo). Continua
    sendo **melhor esforço** (a inscrição guarda nome livre, sem vínculo rígido).
    Percentuais das barras já vêm prontos (o template só aplica a largura)."""
    # --- Cobertura: quais aventureiros do clube estão neste evento ---
    # Só aventureiros ATIVOS (os inativos/desligados não contam no total do clube).
    aventureiros = list(
        Aventureiro.objects.filter(ativo=True).order_by("nome_completo")
    )
    av_tokens = [(av, _tokens_lista(av.nome_completo)) for av in aventureiros]
    # Para cada participante, quais aventureiros seus nomes poderiam ser (casa por
    # igualdade/inicial). Vínculo manual (participante.aventureiro) tem prioridade.
    inscritos_ids = set()
    ambiguos_lista = []
    for i in confirmadas:
        for p in i.participantes.all():
            pt = _tokens_lista(p.nome)
            if not pt:
                continue
            candidatos = [av for av, at in av_tokens if _nome_casa(pt, at)]
            if len(candidatos) > 1:
                # Desambigua pelo sobrenome do responsável: ex. "Beatriz" +
                # responsável "...Staine" -> "Beatriz Gonçalves Staine".
                resp_tok = set(_tokens_lista(i.responsavel_nome))
                por_resp = [av for av, at in av_tokens
                            if av in candidatos and resp_tok & set(at)]
                if len(por_resp) == 1:
                    candidatos = por_resp
            if len(candidatos) == 1:
                inscritos_ids.add(candidatos[0].id)
            elif len(candidatos) > 1:
                # nome serve para mais de um -> "a conferir" (não casa sozinho)
                ambiguos_lista.append({
                    "participante": p.nome,
                    "responsavel": i.responsavel_nome,
                    "candidatos": [av.nome_completo for av in candidatos],
                })
    ambiguos = len(ambiguos_lista)
    inscritos_clube = []
    fora_clube = []
    for av in aventureiros:
        item = {"nome": av.nome_completo, "idade": _idade(av.data_nascimento)}
        (inscritos_clube if av.id in inscritos_ids else fora_clube).append(item)
    total_clube = len(inscritos_clube) + len(fora_clube)
    pct_cobertura = round(len(inscritos_clube) * 100 / total_clube) if total_clube else 0

    # --- Entradas por forma de pagamento (barras) ---
    max_forma = max((f["valor"] for f in entradas_por_forma), default=Decimal("0"))
    formas_chart = [
        dict(f, pct=(float(f["valor"] / max_forma * 100) if max_forma else 0))
        for f in entradas_por_forma
    ]

    # --- Inscritos por faixa etária (barras) ---
    faixa_por_id = {f.id: f for f in faixas}
    dist = {}
    for i in confirmadas:
        for p in i.participantes.all():
            if p.eh_diretoria:
                rot = "Diretoria"
            elif p.faixa_id and p.faixa_id in faixa_por_id:
                f = faixa_por_id[p.faixa_id]
                rot = f.rotulo or f"{f.idade_min}–{f.idade_max} anos"
            else:
                rot = "Sem faixa"
            dist[rot] = dist.get(rot, 0) + 1
    max_faixa = max(dist.values(), default=0)
    faixas_chart = [
        {"rotulo": k, "qtd": v, "pct": (v * 100 / max_faixa if max_faixa else 0)}
        for k, v in sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
    ]

    # --- Receitas × Custos (barras) ---
    max_rc = max(receitas, total_custos, Decimal("1"))
    rc = {
        "receitas": receitas, "custos": total_custos,
        "receitas_pct": float(receitas / max_rc * 100),
        "custos_pct": float(total_custos / max_rc * 100),
    }

    return {
        "cobertura": {
            "total_clube": total_clube,
            "inscritos_count": len(inscritos_clube),
            "fora_count": len(fora_clube),
            "pct": pct_cobertura,
            "inscritos": inscritos_clube,
            "fora": fora_clube,
            "ambiguos": ambiguos,
            "ambiguos_lista": ambiguos_lista,
        },
        "formas": formas_chart,
        "faixas": faixas_chart,
        "rc": rc,
        "tem_dados": bool(confirmadas) or total_custos > 0,
        # Listas simples exibidas ao clicar num card de KPI no Resumo (Etapa 4).
        "listas": {
            "inscritos": [
                {"resp": i.responsavel_nome,
                 "parts": [p.nome for p in i.participantes.all()]}
                for i in confirmadas
            ],
            "arrecadacao": [
                {"nome": i.responsavel_nome, "valor": i.valor_total} for i in confirmadas
            ],
            "vendas": [
                {"nome": p.comprador_nome, "valor": p.valor_total}
                for p in pedidos_confirmados
            ],
            "receitas": (
                [{"tipo": "Inscrição", "nome": i.responsavel_nome, "valor": i.valor_total}
                 for i in confirmadas]
                + [{"tipo": "Lojinha", "nome": p.comprador_nome, "valor": p.valor_total}
                   for p in pedidos_confirmados]
            ),
            "custos": [{"nome": c.nome, "valor": c.valor} for c in custos],
        },
    }


@diretor_required
def evento_painel_view(request, pk):
    """Painel (dashboard) de um evento complexo.

    Fase 1: resumo + custos. Parte 2.1: configuração de inscrição
    (visibilidade, prazo, faixas etárias de preço e valor da diretoria).
    Fase 5: aba Financeiro (extrato) + Resumo/dashboard (KPIs, gráficos, cobertura).
    """
    evento = Evento.objects.filter(pk=pk).first()
    if evento is None:
        # Link antigo de um evento já excluído: em vez de 404 cru, volta à lista.
        messages.info(request, "Esse evento não existe mais (pode ter sido excluído).")
        return redirect("core:eventos")
    custos = list(evento.custos.all())
    total_custos = sum((c.valor for c in custos), Decimal("0"))
    cupons = list(evento.cupons.select_related("inscricao").all())
    faixas = list(evento.faixas_preco.all())
    campos_inscricao = list(evento.campos_inscricao.all())
    produtos = list(evento.produtos.prefetch_related("variacoes").all())

    inscricoes = list(
        evento.inscricoes.prefetch_related(
            "participantes", "participantes__respostas", "respostas"
        ).all()
    )
    # Respostas da inscrição (não ligadas a um participante) vs. por participante.
    for i in inscricoes:
        i.respostas_gerais = [r for r in i.respostas.all() if r.participante_id is None]
    confirmadas = [i for i in inscricoes if i.status == "confirmada"]
    # "Inscritos" = pessoas (participantes) das inscrições confirmadas.
    inscritos = sum(len(i.participantes.all()) for i in confirmadas)
    arrecadacao_inscricoes = sum((i.valor_total for i in confirmadas), Decimal("0"))

    pedidos = list(evento.pedidos.prefetch_related("itens").all())
    pedidos_confirmados = [p for p in pedidos if p.status == "confirmado"]
    vendas_loja = sum((p.valor_total for p in pedidos_confirmados), Decimal("0"))
    receitas = arrecadacao_inscricoes + vendas_loja

    # Relatório "Vendidos por produto": Qtd conta tudo (inclusive cortesia),
    # Arrecadado é só o dinheiro (cortesia entra com valor 0).
    vendas_por_produto = {}
    for p in pedidos_confirmados:
        for item in p.itens.all():
            chave = (item.produto_nome, item.variacao_nome)
            linha = vendas_por_produto.setdefault(chave, {
                "produto": item.produto_nome, "variacao": item.variacao_nome,
                "qtd": 0, "total": Decimal("0"),
            })
            linha["qtd"] += item.quantidade
            linha["total"] += item.valor_total
    vendas_por_produto = sorted(
        vendas_por_produto.values(), key=lambda x: (x["produto"], x["variacao"])
    )

    # Casa os pedidos da lojinha com a inscrição da pessoa: vínculo direto (FK) ou
    # mesma conta logada (só quando o responsável tem UMA inscrição no evento — evita
    # atribuir errado). Os demais (avulsos/passantes) ficam só na aba Lojinha.
    insc_por_usuario = {}
    for i in inscricoes:
        if i.usuario_id:
            insc_por_usuario[i.usuario_id] = insc_por_usuario.get(i.usuario_id, 0) + 1
    compras_por_insc = {}
    for p in pedidos:
        alvo = None
        if p.inscricao_id:
            alvo = p.inscricao_id
        elif p.usuario_id and insc_por_usuario.get(p.usuario_id) == 1:
            alvo = next((i.id for i in inscricoes if i.usuario_id == p.usuario_id), None)
        if alvo:
            compras_por_insc.setdefault(alvo, []).append(p)
    cupons_por_insc = {}
    for c in cupons:
        if c.inscricao_id:
            cupons_por_insc.setdefault(c.inscricao_id, []).append(c)
    for i in inscricoes:
        i.compras = compras_por_insc.get(i.id, [])
        i.total_compras = sum(
            (p.valor_total for p in i.compras if p.status == "confirmado"), Decimal("0")
        )
        i.total_geral = i.valor_total + i.total_compras
        i.cupons_aplicados = cupons_por_insc.get(i.id, [])

    financeiro = _montar_financeiro(
        inscricoes, confirmadas, pedidos, pedidos_confirmados, custos,
        arrecadacao_inscricoes, vendas_loja, total_custos,
    )
    dashboard = _montar_dashboard(
        confirmadas, pedidos_confirmados, custos, faixas, receitas, total_custos,
        financeiro["entradas_por_forma"],
    )

    contexto = {
        "evento": evento,
        "custos": custos,
        "cupons": cupons,
        "form_custo": CustoEventoForm(),
        "faixas": faixas,
        "campos_inscricao": campos_inscricao,
        "produtos": produtos,
        "inscricoes": inscricoes,
        "pedidos": pedidos,
        "vendas_por_produto": vendas_por_produto,
        "config_form": EventoInscricaoConfigForm(instance=evento),
        # Prefixos evitam colisão de IDs entre os modais na mesma página.
        "faixa_form": FaixaEtariaPrecoForm(prefix="faixa"),
        "campo_form": CampoInscricaoForm(prefix="campo"),
        "inscricoes_abertas": evento.inscricoes_abertas(),
        "prazo_inscricao": evento.prazo_inscricao(),
        "resumo": {
            "inscritos": inscritos,
            "arrecadacao_inscricoes": arrecadacao_inscricoes,
            "vendas_loja": vendas_loja,
            "receitas": receitas,
            "custos": total_custos,
            "resultado": receitas - total_custos,
        },
        "financeiro": financeiro,
        "dashboard": dashboard,
        "dia": _resumo_dia(evento),
    }
    return render(request, "core/evento_painel.html", contexto)


@diretor_required
@require_POST
def evento_inscricao_config_view(request, pk):
    """Salva a configuração de inscrição do evento (Parte 2.1)."""
    evento = get_object_or_404(Evento, pk=pk)
    form = EventoInscricaoConfigForm(request.POST, instance=evento)
    if form.is_valid():
        form.save()
        messages.success(request, "Configuração de inscrição salva.")
    else:
        messages.error(
            request, "Não foi possível salvar a configuração. Verifique os campos."
        )
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


@diretor_required
@require_POST
def evento_faixa_nova_view(request, pk):
    """Adiciona uma faixa etária de preço ao evento."""
    evento = get_object_or_404(Evento, pk=pk)
    form = FaixaEtariaPrecoForm(request.POST, prefix="faixa")
    if form.is_valid():
        faixa = form.save(commit=False)
        faixa.evento = evento
        # A nova faixa entra no fim da ordem atual.
        ultima = evento.faixas_preco.order_by("-ordem").first()
        faixa.ordem = (ultima.ordem + 1) if ultima else 0
        faixa.save()
        messages.success(request, "Faixa etária adicionada.")
    else:
        messages.error(
            request, "Não foi possível adicionar a faixa. Verifique os campos."
        )
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


@diretor_required
@require_POST
def evento_faixa_excluir_view(request, pk, faixa_id):
    """Remove uma faixa etária de preço do evento."""
    evento = get_object_or_404(Evento, pk=pk)
    faixa = evento.faixas_preco.filter(pk=faixa_id).first()
    if faixa is not None:
        faixa.delete()
        messages.success(request, "Faixa etária removida.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


@diretor_required
@require_POST
def evento_campo_novo_view(request, pk):
    """Adiciona um campo personalizado ao formulário de inscrição (Fase 2.2)."""
    evento = get_object_or_404(Evento, pk=pk)
    form = CampoInscricaoForm(request.POST, prefix="campo")
    if form.is_valid():
        campo = form.save(commit=False)
        campo.evento = evento
        ultimo = evento.campos_inscricao.order_by("-ordem").first()
        campo.ordem = (ultimo.ordem + 1) if ultimo else 0
        campo.save()
        messages.success(request, "Campo adicionado ao formulário.")
    else:
        messages.error(
            request, "Não foi possível adicionar o campo. Verifique os dados."
        )
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


@diretor_required
@require_POST
def evento_campo_excluir_view(request, pk, campo_id):
    """Remove um campo do formulário de inscrição."""
    evento = get_object_or_404(Evento, pk=pk)
    campo = evento.campos_inscricao.filter(pk=campo_id).first()
    if campo is not None:
        campo.delete()
        messages.success(request, "Campo removido do formulário.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


@diretor_required
@require_POST
def evento_campo_mover_view(request, pk, campo_id):
    """Reordena um campo do formulário (mover para cima/baixo)."""
    evento = get_object_or_404(Evento, pk=pk)
    direcao = request.POST.get("direcao")
    campos = list(evento.campos_inscricao.all())
    idx = next((i for i, c in enumerate(campos) if c.id == campo_id), None)
    if idx is not None:
        alvo = idx - 1 if direcao == "cima" else idx + 1
        if 0 <= alvo < len(campos):
            campos[idx], campos[alvo] = campos[alvo], campos[idx]
            # Renumera a ordem sequencialmente (robusto a valores repetidos).
            for i, campo in enumerate(campos):
                if campo.ordem != i:
                    campo.ordem = i
                    campo.save(update_fields=["ordem"])
            messages.success(request, "Ordem dos campos atualizada.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


@diretor_required
@require_POST
def evento_cupom_novo_view(request, pk):
    """Gera cupons de desconto para inscrição (Fase 5.3). Só valem na inscrição.

    Aceita `percentual` (1–100), `quantidade` (1–5, gera vários de uma vez) e
    `faixa` (id de uma FaixaEtariaPreco do evento; vazio = qualquer faixa)."""
    evento = get_object_or_404(Evento, pk=pk)
    try:
        percentual = int(request.POST.get("percentual") or "")
    except (TypeError, ValueError):
        percentual = 0
    try:
        quantidade = int(request.POST.get("quantidade") or "1")
    except (TypeError, ValueError):
        quantidade = 1
    faixa_id = request.POST.get("faixa") or ""
    faixa = evento.faixas_preco.filter(pk=faixa_id).first() if faixa_id else None

    if not (1 <= percentual <= 100):
        messages.error(request, "Informe um percentual de desconto entre 1 e 100.")
    elif not (1 <= quantidade <= 5):
        messages.error(request, "A quantidade deve ser de 1 a 5 cupons por vez.")
    else:
        for _ in range(quantidade):
            CupomDesconto.objects.create(
                evento=evento, codigo=CupomDesconto.gerar_codigo_unico(),
                percentual=percentual, faixa=faixa, criado_por=request.user,
            )
        if faixa is not None:
            alvo = " · " + (faixa.rotulo or f"{faixa.idade_min}–{faixa.idade_max} anos")
        else:
            alvo = " · qualquer faixa"
        plural = "cupom" if quantidade == 1 else "cupons"
        messages.success(
            request, f"{quantidade} {plural} de {percentual}% gerado(s){alvo}."
        )
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#descontos")


@diretor_required
@require_POST
def evento_cupom_excluir_view(request, pk, cupom_id):
    """Remove um cupom de desconto (só se ainda não foi utilizado)."""
    evento = get_object_or_404(Evento, pk=pk)
    cupom = evento.cupons.filter(pk=cupom_id).first()
    if cupom is not None and cupom.usado:
        messages.error(request, "Não dá para remover um cupom já utilizado.")
    elif cupom is not None:
        codigo = cupom.codigo
        cupom.delete()
        messages.success(request, f"Cupom {codigo} removido.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#descontos")


def evento_pagina_view(request, pk):
    """
    Página do evento com inscrição (Fase 2.3).

    Aparece no menu de todos os perfis logados e serve de página do evento.
    Acesso: se o evento é **aberto ao público**, qualquer pessoa vê (sem login);
    se é **só para membros**, exige login. O envio da inscrição virá na Fase 2.4.
    """
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    if not evento.inscricao_aberta_publico and not request.user.is_authenticated:
        login_url = reverse("core:login")
        return redirect(f"{login_url}?next={request.path}")

    contexto = {
        "evento": evento,
        "faixas": list(evento.faixas_preco.all()),
        "campos": list(evento.campos_inscricao.all()),
        "inscricoes_abertas": evento.inscricoes_abertas(),
        "prazo_inscricao": evento.prazo_inscricao(),
        "tem_loja": evento.loja_aberta() and evento.produtos.filter(ativo=True).exists(),
    }
    return render(request, "core/evento_pagina.html", contexto)


def _ler_resposta_participante(request, campo, field_name):
    """(texto_legível, erro) de um campo 'por participante' lido do POST."""
    if campo.tipo == "escolha_multipla":
        escolhidos = [v for v in request.POST.getlist(field_name) if v in campo.opcoes_lista]
        if campo.obrigatorio and not escolhidos:
            return "", "obrigatório"
        return ", ".join(escolhidos), None
    valor = (request.POST.get(field_name) or "").strip()
    if campo.tipo == "sim_nao":
        return ("Sim" if valor else "Não"), None
    if campo.obrigatorio and not valor:
        return "", "obrigatório"
    if valor:
        if campo.tipo == "escolha_unica" and valor not in campo.opcoes_lista:
            return "", "opção inválida"
        if campo.tipo == "numero":
            try:
                float(valor.replace(",", "."))
            except ValueError:
                return "", "número inválido"
        if campo.tipo == "data":
            try:
                valor = datetime.datetime.strptime(
                    valor, "%Y-%m-%d"
                ).date().strftime("%d/%m/%Y")
            except ValueError:
                return "", "data inválida"
    return valor, None


def _linha_participante(request, idx, campos_part, tem_diretoria):
    """Monta o dict de uma linha de participante a partir do POST (com respostas)."""
    nome = (request.POST.get(f"part_nome_{idx}") or "").strip()
    try:
        idade = int(request.POST.get(f"part_idade_{idx}") or "")
    except (TypeError, ValueError):
        idade = None
    eh_dir = bool(tem_diretoria) and request.POST.get(f"part_diretoria_{idx}") == "1"
    campos = []
    for campo in campos_part:
        fname = f"part_campo{campo.id}_{idx}"
        texto, erro = _ler_resposta_participante(request, campo, fname)
        campos.append({
            "campo": campo,
            "valor": request.POST.get(fname, ""),
            "valores": request.POST.getlist(fname),
            "texto": texto,
            "erro": erro,
        })
    cupom = (request.POST.get(f"part_cupom_{idx}") or "").strip()
    return {"idx": str(idx), "nome": nome, "idade": idade, "diretoria": eh_dir,
            "campos": campos, "cupom": cupom}


def _linha_vazia(idx, campos_part):
    """Linha de participante em branco (para GET e para o modelo do JS)."""
    return {
        "idx": str(idx), "nome": "", "idade": None, "diretoria": False, "cupom": "",
        "campos": [
            {"campo": c, "valor": "", "valores": [], "texto": "", "erro": None}
            for c in campos_part
        ],
    }


def _buscar_cupom_valido(evento, codigo):
    """CupomDesconto disponível do evento para `codigo` (case-insensitive), ou None."""
    codigo = (codigo or "").strip()
    if not codigo:
        return None
    cupom = evento.cupons.filter(codigo__iexact=codigo).first()
    if cupom and cupom.ativo and not cupom.usado:
        return cupom
    return None


def _processar_cupons_participantes(evento, dados, cortesia=False):
    """Valida e aplica o cupom de CADA participante (o código digitado na linha
    dele). `dados` = lista de (participante, linha). Retorna (aplicados, erros):
    `aplicados` = [(cupom, participante, desconto)] para marcar após salvar; muta o
    `.valor` do participante com desconto. Regras: uso único; não repetir o mesmo
    código na inscrição; se o cupom tem faixa, a idade do participante deve casar."""
    aplicados = []
    erros = []
    usados = set()  # códigos já usados nesta submissão
    for p, linha in dados:
        codigo = (linha.get("cupom") or "").strip()
        if not codigo:
            continue
        if cortesia:
            continue  # inscrição cortesia já é grátis; o cupom não se aplica
        chave = codigo.lower()
        cupom = _buscar_cupom_valido(evento, codigo)
        if cupom is None or chave in usados:
            erros.append(f"Cupom “{codigo}” inválido ou já utilizado.")
            continue
        if cupom.faixa_id is not None:
            f = cupom.faixa
            if p.idade is None or not (f.idade_min <= p.idade <= f.idade_max):
                rot = f.rotulo or f"{f.idade_min}–{f.idade_max} anos"
                erros.append(
                    f"Cupom “{codigo}” é só para {rot} — "
                    f"“{p.nome}” não está nessa faixa etária."
                )
                continue
        usados.add(chave)
        if not p.valor or p.valor <= 0:
            continue  # nada a descontar (não consome o cupom)
        desconto = (p.valor * Decimal(cupom.percentual) / Decimal(100)).quantize(
            Decimal("0.01")
        )
        p.valor = p.valor - desconto
        aplicados.append((cupom, p, desconto))
    return aplicados, erros


def _marcar_cupons_usados(aplicados, inscricao):
    """Marca como usados os cupons aplicados (retorno de
    `_processar_cupons_participantes`), já com a inscrição/participante salvos.
    Cada cupom guarda em quem foi usado, o valor descontado e quando."""
    agora = timezone.now()
    for cupom, participante, desconto in aplicados:
        cupom.usado_em = agora
        cupom.inscricao = inscricao
        cupom.participante = participante
        cupom.usado_por = participante.nome or inscricao.responsavel_nome
        cupom.valor_desconto = desconto
        cupom.save(update_fields=[
            "usado_em", "inscricao", "participante", "usado_por", "valor_desconto"
        ])


def evento_cupom_validar_view(request, pk):
    """Validação AO VIVO de um cupom para um participante (JSON, sem gravar nada).
    Recebe (GET) `codigo`, `idade` e `diretoria` (1/0) e devolve se o cupom vale
    para aquele participante e o desconto em R$ que ele daria — usado pelo JS para
    o toast e para abater do total. A gravação/uso único só acontece ao confirmar."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    codigo = (request.GET.get("codigo") or "").strip()
    diretoria = (request.GET.get("diretoria") or "") in ("1", "true", "on")
    try:
        idade = int(request.GET.get("idade"))
    except (TypeError, ValueError):
        idade = None

    if not codigo:
        return JsonResponse({"valido": False, "mensagem": "Informe o código do cupom."})
    cupom = _buscar_cupom_valido(evento, codigo)
    if cupom is None:
        return JsonResponse({
            "valido": False,
            "mensagem": f"Cupom “{codigo}” inválido ou já utilizado.",
        })
    if cupom.faixa_id is not None:
        f = cupom.faixa
        if idade is None or not (f.idade_min <= idade <= f.idade_max):
            rot = f.rotulo or f"{f.idade_min}–{f.idade_max} anos"
            return JsonResponse({
                "valido": False,
                "mensagem": f"Cupom “{codigo}” é só para {rot}.",
            })

    faixas = list(evento.faixas_preco.all())
    valor, _faixa = evento.preco_participante(idade, diretoria, faixas)
    if valor and valor > 0:
        desconto = (valor * Decimal(cupom.percentual) / Decimal(100)).quantize(
            Decimal("0.01")
        )
    else:
        desconto = Decimal("0")
    if desconto > 0:
        desconto_txt = "−R$ " + f"{desconto:.2f}".replace(".", ",")
        mensagem = f"Cupom {cupom.codigo} aplicado ({cupom.percentual}%): {desconto_txt}"
    else:
        mensagem = f"Cupom {cupom.codigo} válido — sem valor a descontar."
    return JsonResponse({
        "valido": True,
        "percentual": cupom.percentual,
        "desconto": str(desconto),
        "codigo": cupom.codigo,
        "mensagem": mensagem,
    })


def evento_inscrever_view(request, pk):
    """Formulário de inscrição num evento (Fase 2.4). Pagamento simulado."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    if not evento.inscricao_aberta_publico and not request.user.is_authenticated:
        return redirect(f"{reverse('core:login')}?next={request.path}")
    if not evento.inscricoes_abertas():
        messages.error(request, "As inscrições para este evento estão encerradas.")
        return redirect("core:evento_pagina", pk=evento.pk)

    faixas = list(evento.faixas_preco.all())
    tem_diretoria = evento.valor_diretoria is not None
    campos_part = list(evento.campos_inscricao.filter(por_participante=True))
    produtos_loja = (
        list(evento.produtos.filter(ativo=True).prefetch_related("variacoes"))
        if evento.loja_aberta() else []
    )
    linhas = []
    erros_part = []
    desejados_loja = []
    erros_loja = []

    if request.method == "POST":
        form = InscricaoForm(request.POST, evento=evento)
        if produtos_loja:
            desejados_loja, erros_loja = _coletar_itens_loja(request, produtos_loja)
        for idx in request.POST.getlist("part_idx"):
            linha = _linha_participante(request, idx, campos_part, tem_diretoria)
            if not linha["nome"]:
                continue  # ignora linha em branco
            if linha["idade"] is None and not linha["diretoria"]:
                erros_part.append(f"Informe a idade de “{linha['nome']}”.")
            for c in linha["campos"]:
                if c["erro"]:
                    erros_part.append(f"“{linha['nome']}”: {c['campo'].rotulo} — {c['erro']}.")
            linhas.append(linha)
        if not linhas:
            erros_part.append("Adicione ao menos um participante.")

        # Monta os participantes com o preço da faixa/diretoria e aplica o cupom
        # digitado na linha de cada um (o desconto vale para AQUELE participante).
        dados = []  # (participante, linha)
        for linha in linhas:
            valor, faixa = evento.preco_participante(
                linha["idade"], linha["diretoria"], faixas
            )
            p = ParticipanteInscricao(
                nome=linha["nome"], idade=linha["idade"],
                eh_diretoria=linha["diretoria"], faixa=faixa, valor=valor,
            )
            dados.append((p, linha))
        aplicados, erros_cupom = _processar_cupons_participantes(evento, dados)
        erros_part.extend(erros_cupom)

        if form.is_valid() and not erros_part and not erros_loja:
            with transaction.atomic():
                inscricao = Inscricao(
                    evento=evento,
                    usuario=request.user if request.user.is_authenticated else None,
                    responsavel_nome=form.cleaned_data["responsavel_nome"],
                    responsavel_whatsapp=form.cleaned_data["responsavel_whatsapp"],
                    responsavel_email=form.cleaned_data["responsavel_email"],
                    responsavel_cpf=form.cleaned_data["responsavel_cpf"],
                    codigo=Inscricao.gerar_codigo_unico(),
                    status="confirmada",
                )
                inscricao.valor_total = sum((p.valor for p, _ in dados), Decimal("0"))
                inscricao.save()
                for p, linha in dados:
                    p.inscricao = inscricao
                    p.save()
                    for c in linha["campos"]:
                        RespostaInscricao.objects.create(
                            inscricao=inscricao, participante=p, campo=c["campo"],
                            campo_rotulo=c["campo"].rotulo, valor=c["texto"],
                        )
                for campo, nome in form.campos_extra:
                    RespostaInscricao.objects.create(
                        inscricao=inscricao, campo=campo, campo_rotulo=campo.rotulo,
                        valor=form.resposta_texto(campo, nome),
                    )
                # Itens da lojinha escolhidos junto da inscrição (opcional).
                _criar_pedido(
                    evento, desejados_loja,
                    {
                        "nome": inscricao.responsavel_nome,
                        "whatsapp": inscricao.responsavel_whatsapp,
                        "email": inscricao.responsavel_email,
                    },
                    usuario=request.user if request.user.is_authenticated else None,
                    inscricao=inscricao,
                )
                _marcar_cupons_usados(aplicados, inscricao)
            request.session["inscricao_codigo"] = inscricao.codigo
            return redirect("core:evento_inscricao_sucesso", pk=evento.pk)
        messages.error(request, "Verifique os campos destacados e os participantes.")
    else:
        inicial = {}
        if request.user.is_authenticated and request.user.email:
            inicial["responsavel_email"] = request.user.email
        form = InscricaoForm(evento=evento, initial=inicial)

    _marcar_quantidades(produtos_loja, desejados_loja)
    contexto = {
        "evento": evento,
        "form": form,
        "faixas": faixas,
        "tem_diretoria": tem_diretoria,
        "campos_participante": campos_part,
        "linhas": linhas or [_linha_vazia(0, campos_part)],
        "linha_modelo": _linha_vazia("__IDX__", campos_part),
        "erros_part": erros_part,
        "produtos_loja": produtos_loja,
        "erros_loja": erros_loja,
        "tem_cupons": evento.cupons.filter(ativo=True, usado_em__isnull=True).exists(),
        "faixas_json": [
            {"min": f.idade_min, "max": f.idade_max, "valor": str(f.valor)}
            for f in faixas
        ],
        "diretoria_json": (
            str(evento.valor_diretoria) if evento.valor_diretoria is not None else None
        ),
    }
    return render(request, "core/evento_inscrever.html", contexto)


def evento_inscricao_sucesso_view(request, pk):
    """Confirmação da inscrição (código + valor total). Pagamento simulado."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    codigo = request.session.get("inscricao_codigo")
    inscricao = evento.inscricoes.filter(codigo=codigo).first() if codigo else None
    if inscricao is None:
        return redirect("core:evento_pagina", pk=evento.pk)
    contexto = {
        "evento": evento,
        "inscricao": inscricao,
        "pedido": inscricao.pedidos.first(),
        "tem_loja": evento.loja_aberta() and evento.produtos.filter(ativo=True).exists(),
    }
    return render(request, "core/evento_inscricao_sucesso.html", contexto)


@diretor_required
@require_POST
def evento_inscricao_cancelar_view(request, pk, inscricao_id):
    """Cancela uma inscrição (Diretor). Sai da contagem/arrecadação do resumo."""
    evento = get_object_or_404(Evento, pk=pk)
    inscricao = evento.inscricoes.filter(pk=inscricao_id).first()
    if inscricao is not None and inscricao.status != "cancelada":
        inscricao.status = "cancelada"
        inscricao.save(update_fields=["status"])
        messages.success(request, f"Inscrição {inscricao.codigo} cancelada.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


# ---------------------------------------------------------------------------
# Lojinha — Fase 4.1: cadastro de produtos (com variações e estoque opcional)
# ---------------------------------------------------------------------------
def _variacao_vazia(idx):
    return {"idx": str(idx), "id": "", "nome": "", "valor_raw": "", "estoque_raw": ""}


def _parse_variacoes(request, controla):
    """Lê as linhas de variação do POST (indexadas) → (linhas, erros). Não salva."""
    linhas = []
    erros = []
    for idx in request.POST.getlist("var_idx"):
        nome = (request.POST.get(f"var_nome_{idx}") or "").strip()
        valor_raw = (request.POST.get(f"var_valor_{idx}") or "").strip()
        estoque_raw = (request.POST.get(f"var_estoque_{idx}") or "").strip()
        if not nome and not valor_raw:
            continue  # linha em branco
        valor = None
        try:
            valor = Decimal(valor_raw.replace(",", "."))
            if valor < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            erros.append(f"Preço inválido na variação “{nome or 'sem nome'}”.")
        try:
            estoque = int(estoque_raw) if (controla and estoque_raw) else 0
            estoque = max(estoque, 0)
        except ValueError:
            estoque = 0
        linhas.append({
            "idx": str(idx), "id": request.POST.get(f"var_id_{idx}") or "",
            "nome": nome, "valor": valor, "valor_raw": valor_raw,
            "estoque": estoque, "estoque_raw": estoque_raw,
        })
    if not linhas:
        erros.append("Adicione ao menos uma variação (com preço).")
    return linhas, erros


def _salvar_variacoes(produto, linhas):
    """Cria/atualiza as variações e remove as que não vieram."""
    vistos = []
    for i, ln in enumerate(linhas):
        var = None
        if ln["id"]:
            var = produto.variacoes.filter(pk=ln["id"]).first()
        if var is None:
            var = VariacaoProduto(produto=produto)
        var.nome = ln["nome"]
        var.valor = ln["valor"] or Decimal("0")
        var.estoque = ln["estoque"]
        var.ordem = i
        var.save()
        vistos.append(var.id)
    produto.variacoes.exclude(id__in=vistos).delete()


def _produto_form(request, evento, produto):
    """Cria ou edita um produto da lojinha (com variações)."""
    if request.method == "POST":
        form = ProdutoEventoForm(request.POST, request.FILES, instance=produto)
        controla = bool(request.POST.get("controla_estoque"))
        linhas, erros_var = _parse_variacoes(request, controla)
        if form.is_valid() and not erros_var:
            with transaction.atomic():
                prod = form.save(commit=False)
                prod.evento = evento
                if produto is None:
                    ultimo = evento.produtos.order_by("-ordem").first()
                    prod.ordem = (ultimo.ordem + 1) if ultimo else 0
                prod.save()
                _salvar_variacoes(prod, linhas)
            messages.success(request, "Produto salvo.")
            return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#lojinha")
        messages.error(request, "Verifique os dados do produto e as variações.")
    else:
        form = ProdutoEventoForm(instance=produto)
        if produto is not None:
            # `str()` (ponto decimal) — um Decimal/int cru seria localizado no
            # template (ex.: "12,00") e o <input type="number"> rejeitaria o valor,
            # deixando o campo vazio. Assim o preço/estoque atuais são reexibidos.
            linhas = [
                {"idx": str(i), "id": v.id, "nome": v.nome,
                 "valor_raw": str(v.valor), "estoque_raw": str(v.estoque)}
                for i, v in enumerate(produto.variacoes.all())
            ] or [_variacao_vazia(0)]
        else:
            linhas = [_variacao_vazia(0)]
        erros_var = []

    contexto = {
        "evento": evento,
        "form": form,
        "produto": produto,
        "linhas": linhas,
        "linha_modelo": _variacao_vazia("__IDX__"),
        "erros_var": erros_var,
    }
    return render(request, "core/evento_produto_form.html", contexto)


@diretor_required
def evento_produto_novo_view(request, pk):
    """Cadastra um novo produto na lojinha do evento."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    return _produto_form(request, evento, None)


@diretor_required
def evento_produto_editar_view(request, pk, produto_id):
    """Edita um produto da lojinha (dados + variações)."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    produto = get_object_or_404(ProdutoEvento, pk=produto_id, evento=evento)
    return _produto_form(request, evento, produto)


@diretor_required
@require_POST
def evento_produto_excluir_view(request, pk, produto_id):
    """Remove um produto da lojinha."""
    evento = get_object_or_404(Evento, pk=pk)
    produto = evento.produtos.filter(pk=produto_id).first()
    if produto is not None:
        produto.delete()
        messages.success(request, "Produto removido.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#lojinha")


# ---------------------------------------------------------------------------
# Lojinha — Fase 4.2/4.3: comprar (carrinho + pedido simulado)
# ---------------------------------------------------------------------------
def _coletar_itens_loja(request, produtos):
    """Lê qtd_<vid> do POST → (desejados [(variacao, qtd)], erros de estoque)."""
    variacoes = {v.id: v for p in produtos for v in p.variacoes.all()}
    desejados = []
    erros = []
    for vid, v in variacoes.items():
        try:
            qtd = int(request.POST.get(f"qtd_{vid}") or 0)
        except (TypeError, ValueError):
            qtd = 0
        if qtd > 0:
            desejados.append((v, qtd))
    for v, qtd in desejados:
        if v.produto.controla_estoque and qtd > v.estoque:
            erros.append(
                f"Estoque insuficiente para {v.produto.nome} — {v.rotulo}: "
                f"{v.estoque} disponível(is)."
            )
    return desejados, erros


def _marcar_quantidades(produtos, desejados):
    """Anexa `qtd_atual` a cada variação (repõe o que foi digitado no formulário)."""
    escolhidas = {v.id: qtd for v, qtd in desejados}
    for p in produtos:
        for v in p.variacoes.all():
            v.qtd_atual = escolhidas.get(v.id, 0)


def _criar_pedido(evento, desejados, comprador, usuario=None, inscricao=None,
                  forma_pagamento="online", valor_recebido=None, origem="online",
                  registrado_por=None, entregar_agora=False):
    """Cria o PedidoLoja + itens e baixa o estoque. Retorna o pedido (ou None se vazio).

    Se `forma_pagamento` == "cortesia", os itens são registrados como grátis
    (valor 0), mas o estoque é baixado normalmente.

    Se `entregar_agora` (venda de balcão retirada na hora — Fase 5.4c), cada item
    já nasce **entregue** (quantidade_entregue = quantidade), registrando quem/quando.
    """
    if not desejados:
        return None
    cortesia = forma_pagamento == "cortesia"
    agora = timezone.now() if entregar_agora else None
    pedido = PedidoLoja(
        evento=evento,
        usuario=usuario,
        inscricao=inscricao,
        comprador_nome=comprador.get("nome", ""),
        comprador_whatsapp=comprador.get("whatsapp", ""),
        comprador_email=comprador.get("email", ""),
        codigo=PedidoLoja.gerar_codigo_unico(),
        status="confirmado",
        origem=origem,
        forma_pagamento=forma_pagamento,
        valor_recebido=valor_recebido if forma_pagamento == "dinheiro" else None,
        registrado_por=registrado_por,
    )
    total = Decimal("0")
    itens = []
    for v, qtd in desejados:
        subtotal = Decimal("0") if cortesia else v.valor * qtd
        total += subtotal
        itens.append(ItemPedidoLoja(
            variacao=v, produto_nome=v.produto.nome, variacao_nome=v.nome,
            quantidade=qtd, valor_unitario=v.valor, valor_total=subtotal,
            quantidade_entregue=qtd if entregar_agora else 0,
            entregue_em=agora, entregue_por=registrado_por if entregar_agora else None,
        ))
        if v.produto.controla_estoque:
            VariacaoProduto.objects.filter(pk=v.id).update(estoque=F("estoque") - qtd)
    pedido.valor_total = total
    pedido.save()
    for item in itens:
        item.pedido = pedido
        item.save()
    return pedido


def _erros_estoque(desejados):
    """Revalida o estoque de uma lista [(variacao, qtd)]. Retorna lista de erros."""
    erros = []
    for v, qtd in desejados:
        if v.produto.controla_estoque and qtd > v.estoque:
            erros.append(
                f"Estoque insuficiente para {v.produto.nome} — {v.rotulo}: "
                f"{v.estoque} disponível(is)."
            )
    return erros


def _pseudo_qr(texto, n=25):
    """Matriz booleana n×n que *parece* um QR Code (decorativa/SIMULADA — não é
    escaneável nem pagável). Determinística a partir do `texto`; desenha os três
    marcadores de canto (finder patterns) para dar a aparência clássica. O QR real
    virá com a integração de pagamento (Mercado Pago) — ver docs."""
    bits = []
    semente = hashlib.sha256(texto.encode("utf-8")).digest()
    while len(bits) < n * n:
        semente = hashlib.sha256(semente).digest()
        for b in semente:
            for i in range(8):
                bits.append((b >> i) & 1)
    matriz = [[bool(bits[r * n + c]) for c in range(n)] for r in range(n)]

    def marcador(r0, c0):
        for r in range(-1, 8):  # separador branco ao redor
            for c in range(-1, 8):
                rr, cc = r0 + r, c0 + c
                if 0 <= rr < n and 0 <= cc < n:
                    matriz[rr][cc] = False
        for r in range(7):
            for c in range(7):
                borda = r in (0, 6) or c in (0, 6)
                miolo = 2 <= r <= 4 and 2 <= c <= 4
                matriz[r0 + r][c0 + c] = borda or miolo

    marcador(0, 0)
    marcador(0, n - 7)
    marcador(n - 7, 0)
    return matriz


def _qr_svg(texto, modulo=9):
    """SVG (string segura) de um QR Code SIMULADO a partir do texto."""
    matriz = _pseudo_qr(texto)
    n = len(matriz)
    tam = n * modulo
    partes = [
        f'<svg viewBox="0 0 {tam} {tam}" width="{tam}" height="{tam}" '
        f'role="img" aria-label="QR Code Pix (simulado)" '
        f'xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{tam}" height="{tam}" fill="#ffffff"/>',
    ]
    for r, linha in enumerate(matriz):
        for c, ligado in enumerate(linha):
            if ligado:
                partes.append(
                    f'<rect x="{c * modulo}" y="{r * modulo}" '
                    f'width="{modulo}" height="{modulo}" fill="#0f2a43"/>'
                )
    partes.append("</svg>")
    return mark_safe("".join(partes))


def _pix_copia_cola(total, codigo):
    """Código Pix "copia e cola" SIMULADO (não é um BR Code real / não é pagável).
    Só ilustra a tela clássica de pagamento. O payload real virá com o gateway."""
    valor = f"{total:.2f}"
    nome = "CLUBE AVENTUREIROS PINHAL JR"
    return (
        "00020126360014BR.GOV.BCB.PIX0114" + codigo.ljust(14, "0")
        + "520400005303986540" + f"{len(valor)}" + valor
        + "5802BR5925" + nome.ljust(25)[:25]
        + "6009SAO PAULO62070503" + codigo[:3] + "6304SIMU"
    )


# Formas de pagamento do cliente final na loja online (só as que a pessoa
# consegue fazer sozinha pelo site). Dinheiro/cortesia ficam no PDV/balcão.
FORMAS_PAGAMENTO_ONLINE = [
    ("pix", "Pix"),
    ("cartao", "Cartão de crédito"),
]


def evento_loja_view(request, pk):
    """Loja do evento: escolher itens/quantidades e a forma de pagamento.

    Ao finalizar, os dados vão para a **tela de pagamento** (`evento_pagamento`):
    o pedido só é criado no banco após a aprovação (simulada) do pagamento — assim
    não fica pedido "pendente" nem estoque reservado por quem abandona o carrinho.
    """
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    if not evento.inscricao_aberta_publico and not request.user.is_authenticated:
        return redirect(f"{reverse('core:login')}?next={request.path}")
    if evento.ja_terminou():
        messages.error(request, "Este evento já terminou; a lojinha está fechada.")
        return redirect("core:evento_pagina", pk=evento.pk)

    produtos = list(evento.produtos.filter(ativo=True).prefetch_related("variacoes"))
    if not produtos:
        messages.info(request, "A lojinha deste evento ainda não tem produtos.")
        return redirect("core:evento_pagina", pk=evento.pk)

    comprador = {"nome": "", "whatsapp": "", "email": ""}
    desejados = []
    erros = []
    forma = ""

    if request.method == "POST":
        comprador = {
            "nome": (request.POST.get("comprador_nome") or "").strip(),
            "whatsapp": (request.POST.get("comprador_whatsapp") or "").strip(),
            "email": (request.POST.get("comprador_email") or "").strip(),
        }
        forma = request.POST.get("forma_pagamento") or ""
        desejados, erros = _coletar_itens_loja(request, produtos)
        if not comprador["nome"]:
            erros.append("Informe o nome do comprador.")
        if not comprador["whatsapp"]:
            erros.append("Informe o WhatsApp para contato.")
        if not desejados:
            erros.append("Escolha ao menos um item (quantidade maior que zero).")
        if forma not in dict(FORMAS_PAGAMENTO_ONLINE):
            erros.append("Escolha a forma de pagamento (Pix ou cartão de crédito).")

        if not erros:
            # Guarda o pedido na sessão e leva para o pagamento (simulado).
            request.session["loja_checkout"] = {
                "itens": [[v.id, qtd] for v, qtd in desejados],
                "comprador": comprador,
                "forma": forma,
            }
            return redirect("core:evento_pagamento", pk=evento.pk)
        messages.error(request, "Verifique os itens escolhidos e os seus dados.")
    else:
        if request.user.is_authenticated and request.user.email:
            comprador["email"] = request.user.email

    _marcar_quantidades(produtos, desejados)
    contexto = {
        "evento": evento,
        "produtos_loja": produtos,
        "comprador": comprador,
        "erros": erros,
        "formas_pagamento": FORMAS_PAGAMENTO_ONLINE,
        "forma_sel": forma,
    }
    return render(request, "core/evento_loja.html", contexto)


def evento_pagamento_view(request, pk):
    """Tela de pagamento (SIMULADA) do pedido da lojinha online.

    GET: mostra a tela clássica — Pix (QR + código "copia e cola") ou cartão
    (aviso de redirecionamento ao Mercado Pago, ainda a implementar). O pedido
    ainda NÃO existe no banco (os dados ficam na sessão em `loja_checkout`).
    POST: simula a aprovação do pagamento, cria o pedido (confirmado) e leva à
    tela de sucesso. Baixa o estoque só aqui (revalidando antes).
    """
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    dados = request.session.get("loja_checkout")
    if not dados or not dados.get("itens"):
        return redirect("core:evento_loja", pk=evento.pk)

    produtos = list(evento.produtos.filter(ativo=True).prefetch_related("variacoes"))
    variacoes = {v.id: v for p in produtos for v in p.variacoes.all()}
    desejados = []
    itens_resumo = []
    total = Decimal("0")
    for vid, qtd in dados["itens"]:
        v = variacoes.get(vid)
        if v and qtd > 0:
            desejados.append((v, qtd))
            subtotal = v.valor * qtd
            total += subtotal
            itens_resumo.append({
                "produto": v.produto.nome, "variacao": v.nome,
                "quantidade": qtd, "valor_unitario": v.valor, "subtotal": subtotal,
            })

    if not desejados:
        request.session.pop("loja_checkout", None)
        return redirect("core:evento_loja", pk=evento.pk)

    comprador = dados["comprador"]
    forma = dados["forma"]

    if request.method == "POST":
        erros = _erros_estoque(desejados)
        if erros:
            request.session.pop("loja_checkout", None)
            for e in erros:
                messages.error(request, e)
            messages.error(request, "Refaça o pedido, por favor.")
            return redirect("core:evento_loja", pk=evento.pk)
        with transaction.atomic():
            pedido = _criar_pedido(
                evento, desejados, comprador,
                usuario=request.user if request.user.is_authenticated else None,
                forma_pagamento=forma, origem="online",
            )
        request.session.pop("loja_checkout", None)
        request.session["pedido_codigo"] = pedido.codigo
        messages.success(request, "Pagamento aprovado! Pedido confirmado.")
        return redirect("core:evento_pedido_sucesso", pk=evento.pk)

    forma_nome = dict(FORMAS_PAGAMENTO_ONLINE).get(forma, forma)
    contexto = {
        "evento": evento,
        "comprador": comprador,
        "forma": forma,
        "forma_nome": forma_nome,
        "itens_resumo": itens_resumo,
        "total": total,
    }
    if forma == "pix":
        contexto["qr_svg"] = _qr_svg(f"PIX-{evento.id}-{total}")
        contexto["pix_codigo"] = _pix_copia_cola(total, f"L{evento.id:04d}")
    return render(request, "core/evento_pagamento.html", contexto)


def evento_pedido_sucesso_view(request, pk):
    """Confirmação do pedido da lojinha (código + total). Pagamento simulado."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    codigo = request.session.get("pedido_codigo")
    pedido = evento.pedidos.filter(codigo=codigo).first() if codigo else None
    if pedido is None:
        return redirect("core:evento_pagina", pk=evento.pk)
    return render(
        request, "core/evento_pedido_sucesso.html",
        {"evento": evento, "pedido": pedido},
    )


@diretor_required
@require_POST
def evento_pedido_cancelar_view(request, pk, pedido_id):
    """Cancela um pedido da lojinha (Diretor) e devolve os itens ao estoque."""
    evento = get_object_or_404(Evento, pk=pk)
    pedido = evento.pedidos.filter(pk=pedido_id).first()
    if pedido is not None and pedido.status != "cancelado":
        with transaction.atomic():
            for item in pedido.itens.all():
                if item.variacao_id and item.variacao.produto.controla_estoque:
                    VariacaoProduto.objects.filter(pk=item.variacao_id).update(
                        estoque=F("estoque") + item.quantidade
                    )
            pedido.status = "cancelado"
            pedido.save(update_fields=["status"])
        messages.success(request, f"Pedido {pedido.codigo} cancelado (estoque devolvido).")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#lojinha")


@operador_required
def evento_pdv_view(request, pk):
    """PDV / balcão do evento (Fase 4.4a): vende itens da lojinha com forma de
    pagamento (troco no dinheiro) e vínculo opcional a uma inscrição.

    Por ora restrito ao Diretor; operadores (diretoria selecionada + ajudantes
    externos) virão na 4.4c.
    """
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    if evento.ja_terminou():
        messages.error(request, "Este evento já terminou; o PDV está fechado.")
        return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#lojinha")

    produtos = list(evento.produtos.filter(ativo=True).prefetch_related("variacoes"))
    if not produtos:
        messages.info(request, "Cadastre produtos na lojinha antes de usar o PDV.")
        return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#lojinha")

    formas = [f for f in FORMA_PAGAMENTO_CHOICES if f[0] != "online"]
    comprador = {"nome": ""}
    desejados = []
    erros = []
    forma = "dinheiro"
    valor_recebido_raw = ""
    inscricao_sel = ""
    entregar_agora = True  # venda de balcão: normalmente leva na hora
    # "de=dia" quando veio do console "Dia do evento" (para o botão Voltar).
    de = request.POST.get("de") or request.GET.get("de") or ""

    if request.method == "POST":
        comprador = {"nome": (request.POST.get("comprador_nome") or "").strip()}
        forma = request.POST.get("forma_pagamento") or ""
        valor_recebido_raw = (request.POST.get("valor_recebido") or "").strip()
        entregar_agora = request.POST.get("entregar_agora") == "1"
        desejados, erros = _coletar_itens_loja(request, produtos)
        if not desejados:
            erros.append("Escolha ao menos um item.")
        if forma not in {f[0] for f in formas}:
            erros.append("Escolha a forma de pagamento.")

        total = sum((v.valor * qtd for v, qtd in desejados), Decimal("0"))
        valor_recebido = None
        if forma == "dinheiro":
            try:
                valor_recebido = Decimal(valor_recebido_raw.replace(",", "."))
            except (InvalidOperation, ValueError):
                valor_recebido = None
            if valor_recebido is None:
                erros.append("Informe o valor recebido em dinheiro.")
            elif valor_recebido < total:
                erros.append("Valor recebido é menor que o total.")

        inscricao_obj = None
        if inscricao_sel.isdigit():
            inscricao_obj = evento.inscricoes.filter(pk=int(inscricao_sel)).first()

        if not erros:
            nome = comprador["nome"]
            if not nome:
                nome = inscricao_obj.responsavel_nome if inscricao_obj else "Cliente (balcão)"
            with transaction.atomic():
                pedido = _criar_pedido(
                    evento, desejados, {"nome": nome},
                    inscricao=inscricao_obj, forma_pagamento=forma,
                    valor_recebido=valor_recebido, origem="pdv",
                    registrado_por=request.user, entregar_agora=entregar_agora,
                )
            msg = f"Venda {pedido.codigo} registrada."
            if entregar_agora:
                msg += " Itens entregues."
            if forma == "dinheiro" and pedido.troco is not None:
                msg += " Troco: R$ " + f"{pedido.troco:.2f}".replace(".", ",")
            messages.success(request, msg)
            destino = reverse("core:evento_pdv", args=[evento.pk])
            if de == "dia":
                destino += "?de=dia"
            return redirect(destino)
        messages.error(request, "Verifique os itens e o pagamento.")

    _marcar_quantidades(produtos, desejados)
    contexto = {
        "evento": evento,
        "produtos_loja": produtos,
        "inscricoes": list(evento.inscricoes.filter(status="confirmada")),
        "comprador": comprador,
        "formas": formas,
        "forma": forma,
        "valor_recebido_raw": valor_recebido_raw,
        "inscricao_sel": inscricao_sel,
        "entregar_agora": entregar_agora,
        "de": de,
        "erros": erros,
    }
    return render(request, "core/evento_pdv.html", contexto)


@operador_required
def evento_pdv_inscricao_view(request, pk):
    """PDV: inscrição presencial (Fase 4.4b) — o atendente faz a inscrição e,
    opcionalmente, já adiciona itens da lojinha; tudo num pagamento só (com troco
    no dinheiro). Cria a inscrição + um pedido de lojinha vinculado."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    if evento.ja_terminou():
        messages.error(request, "Este evento já terminou.")
        return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")

    faixas = list(evento.faixas_preco.all())
    tem_diretoria = evento.valor_diretoria is not None
    campos_part = list(evento.campos_inscricao.filter(por_participante=True))
    produtos_loja = (
        list(evento.produtos.filter(ativo=True).prefetch_related("variacoes"))
        if evento.loja_aberta() else []
    )
    formas = [f for f in FORMA_PAGAMENTO_CHOICES if f[0] != "online"]
    linhas = []
    erros_part = []
    desejados_loja = []
    erros_loja = []
    forma = "dinheiro"
    valor_recebido_raw = ""
    entregar_agora = True  # itens da lojinha: normalmente levados na hora
    # "de=dia" quando veio do console "Dia do evento" (para o botão Voltar).
    de = request.POST.get("de") or request.GET.get("de") or ""

    if request.method == "POST":
        form = InscricaoForm(request.POST, evento=evento)
        forma = request.POST.get("forma_pagamento") or ""
        valor_recebido_raw = (request.POST.get("valor_recebido") or "").strip()
        entregar_agora = request.POST.get("entregar_agora") == "1"
        cortesia = forma == "cortesia"
        if produtos_loja:
            desejados_loja, erros_loja = _coletar_itens_loja(request, produtos_loja)
        for idx in request.POST.getlist("part_idx"):
            linha = _linha_participante(request, idx, campos_part, tem_diretoria)
            if not linha["nome"]:
                continue
            if linha["idade"] is None and not linha["diretoria"]:
                erros_part.append(f"Informe a idade de “{linha['nome']}”.")
            for c in linha["campos"]:
                if c["erro"]:
                    erros_part.append(f"“{linha['nome']}”: {c['campo'].rotulo} — {c['erro']}.")
            linhas.append(linha)
        if not linhas:
            erros_part.append("Adicione ao menos um participante.")
        if forma not in {f[0] for f in formas}:
            erros_part.append("Escolha a forma de pagamento.")

        # Preços (cortesia zera tudo) e cupom por participante (só quando não é
        # cortesia, que já é grátis). Total combinado (inscrição + lojinha).
        dados = []  # (participante, linha)
        for linha in linhas:
            valor, faixa = evento.preco_participante(
                linha["idade"], linha["diretoria"], faixas
            )
            if cortesia:
                valor = Decimal("0")
            p = ParticipanteInscricao(
                nome=linha["nome"], idade=linha["idade"],
                eh_diretoria=linha["diretoria"], faixa=faixa, valor=valor,
            )
            dados.append((p, linha))
        aplicados, erros_cupom = _processar_cupons_participantes(
            evento, dados, cortesia=cortesia
        )
        erros_part.extend(erros_cupom)
        insc_total = sum((p.valor for p, _ in dados), Decimal("0"))
        loja_total = Decimal("0") if cortesia else sum(
            (v.valor * q for v, q in desejados_loja), Decimal("0")
        )
        combinado = insc_total + loja_total

        valor_recebido = None
        if forma == "dinheiro":
            try:
                valor_recebido = Decimal(valor_recebido_raw.replace(",", "."))
            except (InvalidOperation, ValueError):
                valor_recebido = None
            if valor_recebido is None:
                erros_part.append("Informe o valor recebido em dinheiro.")
            elif valor_recebido < combinado:
                erros_part.append("Valor recebido é menor que o total.")

        if form.is_valid() and not erros_part and not erros_loja:
            with transaction.atomic():
                inscricao = Inscricao(
                    evento=evento,
                    responsavel_nome=form.cleaned_data["responsavel_nome"],
                    responsavel_whatsapp=form.cleaned_data["responsavel_whatsapp"],
                    responsavel_email=form.cleaned_data["responsavel_email"],
                    responsavel_cpf=form.cleaned_data["responsavel_cpf"],
                    codigo=Inscricao.gerar_codigo_unico(), status="confirmada",
                    origem="pdv", forma_pagamento=forma,
                    valor_recebido=valor_recebido if forma == "dinheiro" else None,
                    registrado_por=request.user,
                )
                inscricao.valor_total = insc_total
                inscricao.save()
                for p, linha in dados:
                    p.inscricao = inscricao
                    p.save()
                    for c in linha["campos"]:
                        RespostaInscricao.objects.create(
                            inscricao=inscricao, participante=p, campo=c["campo"],
                            campo_rotulo=c["campo"].rotulo, valor=c["texto"],
                        )
                for campo, nome in form.campos_extra:
                    RespostaInscricao.objects.create(
                        inscricao=inscricao, campo=campo, campo_rotulo=campo.rotulo,
                        valor=form.resposta_texto(campo, nome),
                    )
                # Pedido da lojinha vinculado (o pagamento já foi contabilizado na
                # inscrição; aqui só registramos os itens/forma).
                _criar_pedido(
                    evento, desejados_loja,
                    {
                        "nome": inscricao.responsavel_nome,
                        "whatsapp": inscricao.responsavel_whatsapp,
                        "email": inscricao.responsavel_email,
                    },
                    inscricao=inscricao, forma_pagamento=forma,
                    valor_recebido=None, origem="pdv", registrado_por=request.user,
                    entregar_agora=entregar_agora,
                )
                _marcar_cupons_usados(aplicados, inscricao)
            msg = f"Inscrição {inscricao.codigo} registrada."
            if forma == "dinheiro" and inscricao.troco is not None:
                msg += " Troco: R$ " + f"{inscricao.troco:.2f}".replace(".", ",")
            messages.success(request, msg)
            destino = reverse("core:evento_pdv_inscricao", args=[evento.pk])
            if de == "dia":
                destino += "?de=dia"
            return redirect(destino)
        messages.error(request, "Verifique os dados, os participantes e o pagamento.")
    else:
        form = InscricaoForm(evento=evento)

    _marcar_quantidades(produtos_loja, desejados_loja)
    contexto = {
        "evento": evento,
        "form": form,
        "faixas": faixas,
        "tem_diretoria": tem_diretoria,
        "campos_participante": campos_part,
        "linhas": linhas or [_linha_vazia(0, campos_part)],
        "linha_modelo": _linha_vazia("__IDX__", campos_part),
        "erros_part": erros_part,
        "produtos_loja": produtos_loja,
        "erros_loja": erros_loja,
        "entregar_agora": entregar_agora,
        "de": de,
        "formas": formas,
        "forma": forma,
        "valor_recebido_raw": valor_recebido_raw,
        "tem_cupons": evento.cupons.filter(ativo=True, usado_em__isnull=True).exists(),
        "faixas_json": [
            {"min": f.idade_min, "max": f.idade_max, "valor": str(f.valor)}
            for f in faixas
        ],
        "diretoria_json": (
            str(evento.valor_diretoria) if evento.valor_diretoria is not None else None
        ),
    }
    return render(request, "core/evento_pdv_inscricao.html", contexto)


# ---------------------------------------------------------------------------
# Lojinha — Fase 4.4c: operadores do evento (diretoria selecionada + ajudantes
# externos com conta temporária) e a troca de senha obrigatória.
# ---------------------------------------------------------------------------
GRUPOS_DIRETORIA = ["Diretor", "Tesoureiro", "Secretário", "Professor"]


@operador_required
def evento_operar_view(request, pk):
    """Landing do operador do evento: vender na lojinha ou fazer inscrição."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    return render(request, "core/evento_operar.html", {
        "evento": evento,
        "tem_produtos": evento.produtos.filter(ativo=True).exists(),
        "loja_aberta": evento.loja_aberta(),
    })


def _casar_pedidos_inscricoes(inscricoes, pedidos):
    """Casa pedidos da lojinha com a inscrição da pessoa (mesma regra do painel):
    vínculo direto (FK) ou mesma conta logada — só quando o responsável tem UMA
    inscrição no evento (evita atribuir errado). Anexa `.compras` a cada inscrição
    e retorna a lista de pedidos avulsos (sem dono)."""
    insc_por_usuario = {}
    for i in inscricoes:
        if i.usuario_id:
            insc_por_usuario[i.usuario_id] = insc_por_usuario.get(i.usuario_id, 0) + 1
    compras_por_insc = {}
    avulsos = []
    for p in pedidos:
        alvo = None
        if p.inscricao_id:
            alvo = p.inscricao_id
        elif p.usuario_id and insc_por_usuario.get(p.usuario_id) == 1:
            alvo = next((i.id for i in inscricoes if i.usuario_id == p.usuario_id), None)
        if alvo:
            compras_por_insc.setdefault(alvo, []).append(p)
        else:
            avulsos.append(p)
    for i in inscricoes:
        i.compras = compras_por_insc.get(i.id, [])
    return avulsos


def _resumo_dia(evento):
    """Contadores do "Dia do evento": check-in (participantes de inscrições
    confirmadas) e retiradas (itens por unidade em pedidos confirmados). Fonte
    única, reusada pela tela e pelos endpoints de marcar."""
    part = ParticipanteInscricao.objects.filter(
        inscricao__evento=evento, inscricao__status="confirmada"
    ).aggregate(total=Count("id"), presentes=Count("id", filter=Q(presente=True)))
    itens = ItemPedidoLoja.objects.filter(
        pedido__evento=evento, pedido__status="confirmado"
    ).aggregate(total=Sum("quantidade"), entregues=Sum("quantidade_entregue"))
    total_part = part["total"] or 0
    presentes = part["presentes"] or 0
    total_itens = itens["total"] or 0
    entregues = itens["entregues"] or 0
    return {
        "presentes": presentes,
        "total_part": total_part,
        "faltam_part": total_part - presentes,
        "entregues": entregues,
        "total_itens": total_itens,
        "pendentes_itens": total_itens - entregues,
    }


@operador_required
def evento_dia_view(request, pk):
    """Console "Dia do evento" (Fase 5.4): check-in dos participantes e retirada/
    entrega dos itens da lojinha, por família.

    Mostra o status de cada participante (presente/não chegou) e de cada item
    (não entregue / parcial / entregue) e permite **marcar** cada um (5.4b): o
    check-in é por participante e a entrega é por unidade (permite parcial). As
    marcações usam endpoints JSON (`evento_checkin`/`evento_entrega`) e atualizam
    a tela sem recarregar."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    inscricoes = list(
        evento.inscricoes.filter(status="confirmada")
        .prefetch_related("participantes", "pedidos__itens")
        .order_by("responsavel_nome")
    )
    pedidos = list(
        evento.pedidos.filter(status="confirmado").prefetch_related("itens")
    )
    avulsos = _casar_pedidos_inscricoes(inscricoes, pedidos)

    contexto = {
        "evento": evento,
        "inscricoes": inscricoes,
        "avulsos": avulsos,
        "resumo_dia": _resumo_dia(evento),
        # Atalhos de balcão (mesma tela): inscrição enquanto o evento não terminou;
        # venda quando a loja está aberta e há produtos ativos.
        "pode_inscrever": not evento.ja_terminou(),
        "pode_vender": evento.loja_aberta() and evento.produtos.filter(ativo=True).exists(),
    }
    return render(request, "core/evento_dia.html", contexto)


@operador_required
@require_POST
def evento_checkin_view(request, pk):
    """Marca/desmarca o check-in (presença) de um participante (Fase 5.4b).
    Endpoint JSON: recebe `participante` e `presente` (1/0)."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    p = ParticipanteInscricao.objects.filter(
        pk=request.POST.get("participante"),
        inscricao__evento=evento,
        inscricao__status="confirmada",
    ).first()
    if p is None:
        return JsonResponse({"ok": False, "erro": "Participante não encontrado."}, status=404)
    presente = request.POST.get("presente") == "1"
    p.presente = presente
    p.presente_em = timezone.now() if presente else None
    p.presente_por = request.user if presente else None
    p.save(update_fields=["presente", "presente_em", "presente_por"])
    return JsonResponse({
        "ok": True, "presente": p.presente, "resumo": _resumo_dia(evento),
    })


@operador_required
@require_POST
def evento_entrega_view(request, pk):
    """Registra a retirada/entrega de um item da lojinha, **por unidade** (Fase
    5.4b). Endpoint JSON: recebe `item` e `quantidade` (nova quantidade entregue,
    limitada a 0..quantidade do item)."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    it = ItemPedidoLoja.objects.filter(
        pk=request.POST.get("item"),
        pedido__evento=evento,
        pedido__status="confirmado",
    ).first()
    if it is None:
        return JsonResponse({"ok": False, "erro": "Item não encontrado."}, status=404)
    try:
        qtd = int(request.POST.get("quantidade"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "erro": "Quantidade inválida."}, status=400)
    qtd = max(0, min(qtd, it.quantidade))
    it.quantidade_entregue = qtd
    it.entregue_em = timezone.now() if qtd > 0 else None
    it.entregue_por = request.user if qtd > 0 else None
    it.save(update_fields=["quantidade_entregue", "entregue_em", "entregue_por"])
    return JsonResponse({
        "ok": True,
        "quantidade_entregue": it.quantidade_entregue,
        "status": it.status_entrega,
        "resumo": _resumo_dia(evento),
    })


@diretor_required
def evento_operadores_view(request, pk):
    """Gerência dos operadores do evento (Diretor)."""
    evento = get_object_or_404(Evento, pk=pk)
    operadores = list(evento.operadores.select_related("usuario").all())
    ids = {o.usuario_id for o in operadores}
    trocar = set(
        PerfilUsuario.objects
        .filter(usuario__in=[o.usuario_id for o in operadores], precisa_trocar_senha=True)
        .values_list("usuario_id", flat=True)
    )
    for o in operadores:
        o.precisa_trocar = o.usuario_id in trocar
    diretoria = (
        User.objects.filter(groups__name__in=GRUPOS_DIRETORIA)
        .distinct().exclude(id__in=ids).order_by("username")
    )
    return render(request, "core/evento_operadores.html", {
        "evento": evento,
        "operadores": operadores,
        "diretoria_disponivel": diretoria,
    })


@diretor_required
@require_POST
def evento_operador_add_diretoria_view(request, pk):
    """Habilita um membro da diretoria como operador do evento."""
    evento = get_object_or_404(Evento, pk=pk)
    uid = request.POST.get("usuario") or ""
    usuario = User.objects.filter(pk=uid).first() if uid.isdigit() else None
    if usuario is not None:
        OperadorEvento.objects.get_or_create(
            evento=evento, usuario=usuario, defaults={"externo": False}
        )
        messages.success(request, f"{usuario.username} agora pode operar este evento.")
    else:
        messages.error(request, "Selecione um membro da diretoria.")
    return redirect("core:evento_operadores", pk=evento.pk)


@diretor_required
@require_POST
def evento_operador_add_externo_view(request, pk):
    """Cria uma conta temporária de ajudante externo (senha inicial 1234)."""
    evento = get_object_or_404(Evento, pk=pk)
    username = (request.POST.get("username") or "").strip()
    if not username:
        messages.error(request, "Informe um nome de usuário para o ajudante.")
    elif User.objects.filter(username__iexact=username).exists():
        messages.error(request, "Esse nome de usuário já existe. Escolha outro.")
    else:
        usuario = User.objects.create_user(username=username, password="1234")
        PerfilUsuario.objects.update_or_create(
            usuario=usuario, defaults={"precisa_trocar_senha": True}
        )
        OperadorEvento.objects.create(evento=evento, usuario=usuario, externo=True)
        messages.success(
            request,
            f"Ajudante “{username}” criado. Senha inicial: 1234 "
            "(ele troca no primeiro acesso).",
        )
    return redirect("core:evento_operadores", pk=evento.pk)


@diretor_required
@require_POST
def evento_operador_reset_view(request, pk, operador_id):
    """Redefine a senha de um ajudante externo para 1234 (troca obrigatória)."""
    evento = get_object_or_404(Evento, pk=pk)
    op = evento.operadores.filter(pk=operador_id, externo=True).first()
    if op is not None:
        op.usuario.set_password("1234")
        op.usuario.save()
        PerfilUsuario.objects.update_or_create(
            usuario=op.usuario, defaults={"precisa_trocar_senha": True}
        )
        messages.success(
            request, f"Senha de {op.usuario.username} redefinida para 1234."
        )
    return redirect("core:evento_operadores", pk=evento.pk)


@diretor_required
@require_POST
def evento_operador_remover_view(request, pk, operador_id):
    """Remove um operador; se for ajudante externo sem outros eventos, apaga a conta."""
    evento = get_object_or_404(Evento, pk=pk)
    op = evento.operadores.filter(pk=operador_id).first()
    if op is not None:
        usuario, externo = op.usuario, op.externo
        op.delete()
        if externo and not usuario.eventos_operados.exists():
            usuario.delete()
        messages.success(request, "Operador removido.")
    return redirect("core:evento_operadores", pk=evento.pk)


@login_required
def trocar_senha_view(request):
    """Troca de senha (obrigatória no 1º acesso das contas temporárias)."""
    erro = None
    if request.method == "POST":
        senha = request.POST.get("senha") or ""
        confirmar = request.POST.get("confirmar") or ""
        if len(senha) < 4:
            erro = "A senha precisa ter ao menos 4 caracteres."
        elif senha != confirmar:
            erro = "As senhas não conferem."
        else:
            request.user.set_password(senha)
            request.user.save()
            PerfilUsuario.objects.update_or_create(
                usuario=request.user, defaults={"precisa_trocar_senha": False}
            )
            update_session_auth_hash(request, request.user)  # mantém logado
            messages.success(request, "Senha alterada com sucesso.")
            op = OperadorEvento.objects.filter(
                usuario=request.user, externo=True
            ).first()
            if op is not None:
                return redirect("core:evento_operar", pk=op.evento_id)
            return redirect("core:inicio")
    return render(request, "core/trocar_senha.html", {"erro": erro})


@diretor_required
@require_POST
def evento_custo_novo_view(request, pk):
    """Adiciona um custo ao evento (com comprovante opcional)."""
    evento = get_object_or_404(Evento, pk=pk)
    form = CustoEventoForm(request.POST, request.FILES)
    if form.is_valid():
        custo = form.save(commit=False)
        custo.evento = evento
        custo.criado_por = request.user
        custo.save()
        messages.success(request, "Custo adicionado com sucesso.")
    else:
        messages.error(request, "Não foi possível adicionar o custo. Verifique os campos.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#custos")


@diretor_required
@require_POST
def evento_custo_excluir_view(request, pk, custo_id):
    """Remove um custo do evento."""
    evento = get_object_or_404(Evento, pk=pk)
    custo = evento.custos.filter(pk=custo_id).first()
    if custo is not None:
        custo.delete()
        messages.success(request, "Custo removido.")
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#custos")


# ---------------------------------------------------------------------------
# Presença do clube: marca quais aventureiros estiveram num evento. Restrito ao
# Diretor. Independente do check-in de inscrição do evento complexo.
# ---------------------------------------------------------------------------
@diretor_required
def presenca_view(request):
    """Passo 1: escolher o evento para marcar presença (lista de eventos)."""
    eventos = list(Evento.objects.all())
    for e in eventos:
        e.qtd_presentes = e.presencas.count()
    return render(request, "core/presenca_selecionar.html", {"eventos": eventos})


@diretor_required
def presenca_evento_view(request, pk):
    """Passo 2: lista de todos os aventureiros do clube para marcar presença
    naquele evento (com foto grande e toggle presente/ausente)."""
    evento = Evento.objects.filter(pk=pk).first()
    if evento is None:
        messages.info(request, "Esse evento não existe mais.")
        return redirect("core:presenca")
    # Só aventureiros ativos (os inativos/desligados não frequentam mais).
    aventureiros = list(
        Aventureiro.objects.filter(ativo=True).order_by("nome_completo")
    )
    presentes_ids = set(
        evento.presencas.values_list("aventureiro_id", flat=True)
    )
    for av in aventureiros:
        av.foto_ok = _foto_valida(av)
        av.iniciais = _iniciais(av.nome_completo)
        av.idade = _idade(av.data_nascimento)
        av.presente = av.id in presentes_ids
    contexto = {
        "evento": evento,
        "aventureiros": aventureiros,
        "total": len(aventureiros),
        "presentes": len(presentes_ids),
    }
    return render(request, "core/presenca_evento.html", contexto)


@diretor_required
@require_POST
def presenca_marcar_view(request, pk):
    """Marca/desmarca a presença de um aventureiro no evento (JSON, sem recarregar)."""
    evento = get_object_or_404(Evento, pk=pk)
    av = Aventureiro.objects.filter(pk=request.POST.get("aventureiro")).first()
    if av is None:
        return JsonResponse({"ok": False, "erro": "Aventureiro não encontrado."}, status=404)
    presente = request.POST.get("presente") == "1"
    if presente:
        PresencaEvento.objects.get_or_create(
            evento=evento, aventureiro=av, defaults={"marcado_por": request.user}
        )
    else:
        evento.presencas.filter(aventureiro=av).delete()
    return JsonResponse({
        "ok": True, "presente": presente, "presentes": evento.presencas.count(),
    })


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


# ---------------------------------------------------------------------------
# WhatsApp (W-API) — configuração e envio de mensagens (só Diretor)
# ---------------------------------------------------------------------------
def normalizar_telefone(bruto):
    """Normaliza um telefone digitado (com espaços, traços, parênteses, +55…)
    para o formato que a W-API espera: só dígitos, com DDI 55 do Brasil.

    Aceita entradas como "(47) 99224-9708", "47 99224 9708", "+55 47 9922-4708"
    e devolve algo como "5547992249708". Se não for possível reconhecer um
    número brasileiro válido, devolve os dígitos como estão (melhor esforço)."""
    digitos = re.sub(r"\D", "", bruto or "")
    if not digitos:
        return ""
    # Tira o "00" de discagem internacional, se vier (ex.: 0055…).
    if digitos.startswith("00"):
        digitos = digitos[2:]
    # Já veio com DDI 55 e comprimento de número BR (12 = fixo, 13 = celular).
    if digitos.startswith("55") and len(digitos) in (12, 13):
        return digitos
    # Número local: DDD + número (10 dígitos = fixo, 11 = celular) → põe o 55.
    if len(digitos) in (10, 11):
        return "55" + digitos
    # Formato inesperado: devolve o que temos (a W-API valida no envio).
    return digitos


def _enviar_whatsapp(config, phone, message):
    """Faz o POST na W-API para enviar um texto. Usa só a stdlib (urllib).
    Retorna (ok: bool, detalhe: str). `detalhe` é a mensagem de erro ou o
    messageId em caso de sucesso."""
    base = (config.base_url or "https://api.w-api.app/v1").rstrip("/")
    url = f"{base}/message/send-text?instanceId={urllib.parse.quote(config.instance_id)}"
    corpo = json.dumps({"phone": phone, "message": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=corpo,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            bruto = resp.read().decode("utf-8", "replace")
        dados = json.loads(bruto) if bruto else {}
        msg_id = dados.get("messageId") or dados.get("insertedId") or ""
        return True, msg_id
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "replace") if e.fp else ""
        try:
            j = json.loads(detalhe)
            detalhe = j.get("message") or j.get("error") or detalhe
        except (ValueError, TypeError):
            pass
        return False, f"Erro {e.code}: {detalhe or e.reason}"
    except urllib.error.URLError as e:
        return False, f"Falha de conexão: {e.reason}"
    except Exception as e:  # noqa: BLE001 — qualquer imprevisto vira mensagem amigável
        return False, f"Erro inesperado: {e}"


@diretor_required
def whatsapp_view(request):
    """Tela do módulo WhatsApp (só Diretor): configurar a instância (ID/token
    da W-API) e enviar uma mensagem de teste."""
    config = WhatsappConfig.get_solo()
    return render(request, "core/whatsapp.html", {"config": config})


@diretor_required
@require_POST
def whatsapp_config_view(request):
    """Salva o ID da instância, o token e (opcional) a URL base da W-API.

    O token só é substituído se um novo for digitado — assim a tela pode
    exibir apenas os últimos dígitos sem apagar o token guardado."""
    config = WhatsappConfig.get_solo()
    config.instance_id = (request.POST.get("instance_id") or "").strip()
    base_url = (request.POST.get("base_url") or "").strip()
    if base_url:
        config.base_url = base_url
    novo_token = (request.POST.get("token") or "").strip()
    if novo_token:
        config.token = novo_token
    config.atualizado_por = request.user
    config.save()
    messages.success(request, "Configuração do WhatsApp salva.")
    return redirect("core:whatsapp")


@diretor_required
@require_POST
def whatsapp_enviar_view(request):
    """Envia uma mensagem de teste pela W-API (JSON, sem recarregar a página)."""
    config = WhatsappConfig.get_solo()
    if not config.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Configure o ID da instância e o token antes de enviar."},
            status=400,
        )
    mensagem = (request.POST.get("mensagem") or "").strip()
    telefone = normalizar_telefone(request.POST.get("telefone"))
    if not mensagem:
        return JsonResponse({"ok": False, "erro": "Digite a mensagem."}, status=400)
    if not telefone or len(telefone) < 12:
        return JsonResponse(
            {"ok": False, "erro": "Número de telefone inválido. Verifique o DDD."},
            status=400,
        )
    ok, detalhe = _enviar_whatsapp(config, telefone, mensagem)
    if ok:
        return JsonResponse({"ok": True, "telefone": telefone, "message_id": detalhe})
    return JsonResponse({"ok": False, "erro": detalhe, "telefone": telefone}, status=502)


# ---------------------------------------------------------------------------
# Recuperação de senha pelo WhatsApp (público, sem login)
#
# Fluxo em 3 etapas guardadas na sessão (`request.session["recup"]`):
#   1) CPF do responsável legal → identifica a conta e envia um código de 4
#      dígitos para o WhatsApp principal (definido pelo Diretor em Usuários;
#      padrão = WhatsApp do responsável legal).
#   2) Código → valida (com limite de tentativas e expiração).
#   3) Nova senha (2x) → grava e limpa a sessão.
# O código é guardado **com hash** na sessão (server-side); nunca em texto puro.
# ---------------------------------------------------------------------------
RECUP_TTL_MIN = 10          # validade do código, em minutos
RECUP_MAX_TENTATIVAS = 5    # tentativas erradas antes de invalidar
RECUP_REENVIO_ESPERA = 60   # segundos mínimos entre reenvios


def _so_digitos(valor):
    """Só os dígitos de um texto (para comparar CPF/telefone sem pontuação)."""
    return re.sub(r"\D", "", valor or "")


def _mascara_telefone(numero):
    """Mostra o telefone só com os últimos 4 dígitos: (••) •••••-1234."""
    d = _so_digitos(numero)
    if len(d) < 4:
        return "número cadastrado"
    return "•••••-" + d[-4:]


def _numeros_conta(usuario):
    """Números de WhatsApp disponíveis na conta (pai/mãe/resp legal), pegando o
    primeiro não-vazio entre os aventureiros. Lista de dicts {origem, rotulo, numero}."""
    avs = list(Aventureiro.objects.filter(usuario=usuario))

    def primeiro(attr):
        for a in avs:
            v = (getattr(a, attr) or "").strip()
            if v:
                return v
        return ""

    out = []
    for origem, rotulo, attr in (
        ("pai", "Pai", "pai_whatsapp"),
        ("mae", "Mãe", "mae_whatsapp"),
        ("resp", "Responsável legal", "resp_whatsapp"),
    ):
        num = primeiro(attr)
        if num:
            out.append({"origem": origem, "rotulo": rotulo, "numero": num})
    return out


def _whatsapp_principal(usuario):
    """Número de WhatsApp para onde enviar o código: o principal escolhido pelo
    Diretor (PerfilUsuario.whatsapp_principal_origem) ou, como padrão, o do
    responsável legal. Devolve o número **normalizado** (ou "")."""
    numeros = {n["origem"]: n["numero"] for n in _numeros_conta(usuario)}
    origem = ""
    perfil = getattr(usuario, "perfil", None)
    if perfil is not None:
        origem = perfil.whatsapp_principal_origem or ""
    bruto = numeros.get(origem) or numeros.get("resp") or ""
    return normalizar_telefone(bruto)


def _conta_por_cpf_resp(cpf):
    """Acha a conta (User) cujo **responsável legal** tem esse CPF. Prefere conta
    ativa. Devolve o User ou None."""
    alvo = _so_digitos(cpf)
    if len(alvo) != 11:
        return None
    achados = []
    for av in Aventureiro.objects.filter(usuario__isnull=False).select_related("usuario"):
        if _so_digitos(av.resp_cpf) == alvo:
            achados.append(av.usuario)
    if not achados:
        return None
    for u in achados:
        if u.is_active:
            return u
    return achados[0]


def _recup_gerar_e_enviar(usuario, destino):
    """Gera um código de 4 dígitos, envia pelo WhatsApp e devolve (ok, sessao|erro).
    `sessao` é o dict a guardar em request.session["recup"]."""
    config = WhatsappConfig.get_solo()
    if not config.configurado:
        return False, "O envio por WhatsApp não está configurado. Procure a diretoria."
    codigo = f"{secrets.randbelow(10000):04d}"
    mensagem = (
        "Clube de Aventureiros Pinhal Júnior\n"
        f"Seu código para redefinir a senha é: {codigo}\n"
        f"Ele vale por {RECUP_TTL_MIN} minutos. Se não foi você, ignore esta mensagem."
    )
    ok, detalhe = _enviar_whatsapp(config, destino, mensagem)
    if not ok:
        return False, "Não foi possível enviar o código agora. Tente novamente em instantes."
    agora = timezone.now()
    sessao = {
        "user_id": usuario.id,
        "codigo_hash": make_password(codigo),
        "telefone": destino,
        "expira": (agora + datetime.timedelta(minutes=RECUP_TTL_MIN)).isoformat(),
        "tentativas": 0,
        "validado": False,
        "reenviado_em": agora.isoformat(),
    }
    return True, sessao


def _recup_expirado(sessao):
    try:
        return timezone.now() >= datetime.datetime.fromisoformat(sessao["expira"])
    except (KeyError, ValueError, TypeError):
        return True


def _eh_ajax(request):
    """True se a requisição veio do fetch das telas de recuperação (JS)."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _ajax_redirect(url):
    """Resposta AJAX que manda o JS navegar (mensagens já enfileiradas aparecem lá)."""
    return JsonResponse({"redirect": url})


def _ajax_toast(msg, tipo="error"):
    """Resposta AJAX que só mostra um toast, sem recarregar a página."""
    return JsonResponse({"msg": msg, "tipo": tipo})


def recuperar_senha_view(request):
    """Etapa 1: digitar o CPF do responsável legal para receber o código."""
    if request.user.is_authenticated:
        return redirect("core:inicio")
    cpf_digitado = ""
    if request.method == "POST":
        ajax = _eh_ajax(request)
        cpf_digitado = (request.POST.get("cpf") or "").strip()
        erro = None
        if len(_so_digitos(cpf_digitado)) != 11:
            erro = "Digite um CPF válido (11 dígitos)."
        else:
            usuario = _conta_por_cpf_resp(cpf_digitado)
            if usuario is None:
                erro = "Não encontramos uma conta com esse CPF de responsável legal."
            else:
                destino = _whatsapp_principal(usuario)
                if not destino:
                    erro = "Não há WhatsApp cadastrado para enviar o código. Procure a diretoria."
                else:
                    ok, resultado = _recup_gerar_e_enviar(usuario, destino)
                    if not ok:
                        erro = resultado
                    else:
                        request.session["recup"] = resultado
                        messages.success(
                            request,
                            f"Código enviado para o WhatsApp {_mascara_telefone(destino)}.",
                        )
                        if ajax:
                            return _ajax_redirect(reverse("core:recuperar_senha_codigo"))
                        return redirect("core:recuperar_senha_codigo")
        if ajax:
            return _ajax_toast(erro)
        messages.error(request, erro)
    return render(request, "core/recuperar_cpf.html", {"cpf_digitado": cpf_digitado})


def recuperar_senha_codigo_view(request):
    """Etapa 2: digitar o código de 4 dígitos recebido no WhatsApp."""
    if request.user.is_authenticated:
        return redirect("core:inicio")
    sessao = request.session.get("recup")
    if not sessao or not sessao.get("user_id"):
        messages.info(request, "Comece informando o seu CPF.")
        return redirect("core:recuperar_senha")
    if _recup_expirado(sessao):
        request.session.pop("recup", None)
        messages.error(request, "O código expirou. Peça um novo.")
        return redirect("core:recuperar_senha")

    if request.method == "POST":
        ajax = _eh_ajax(request)
        codigo = _so_digitos(request.POST.get("codigo"))
        if check_password(codigo, sessao["codigo_hash"]):
            sessao["validado"] = True
            request.session["recup"] = sessao
            request.session.modified = True
            if ajax:
                return _ajax_redirect(reverse("core:recuperar_senha_nova"))
            return redirect("core:recuperar_senha_nova")
        sessao["tentativas"] = int(sessao.get("tentativas", 0)) + 1
        request.session["recup"] = sessao
        request.session.modified = True
        if sessao["tentativas"] >= RECUP_MAX_TENTATIVAS:
            request.session.pop("recup", None)
            messages.error(request, "Muitas tentativas. Peça um novo código.")
            if ajax:
                return _ajax_redirect(reverse("core:recuperar_senha"))
            return redirect("core:recuperar_senha")
        restantes = RECUP_MAX_TENTATIVAS - sessao["tentativas"]
        erro = f"Código incorreto. Você ainda tem {restantes} tentativa{'s' if restantes != 1 else ''}."
        if ajax:
            return _ajax_toast(erro)
        messages.error(request, erro)

    contexto = {"mascara": _mascara_telefone(sessao.get("telefone", ""))}
    return render(request, "core/recuperar_codigo.html", contexto)


@require_POST
def recuperar_senha_reenviar_view(request):
    """Reenvia o código (respeitando a espera mínima entre reenvios)."""
    ajax = _eh_ajax(request)
    sessao = request.session.get("recup")
    if not sessao or not sessao.get("user_id"):
        return _ajax_redirect(reverse("core:recuperar_senha")) if ajax else redirect("core:recuperar_senha")
    try:
        ultimo = datetime.datetime.fromisoformat(sessao.get("reenviado_em"))
        espera = (timezone.now() - ultimo).total_seconds()
    except (ValueError, TypeError):
        espera = RECUP_REENVIO_ESPERA
    if espera < RECUP_REENVIO_ESPERA:
        msg = f"Aguarde {int(RECUP_REENVIO_ESPERA - espera)}s para reenviar."
        if ajax:
            return _ajax_toast(msg, "info")
        messages.info(request, msg)
        return redirect("core:recuperar_senha_codigo")
    usuario = User.objects.filter(pk=sessao["user_id"]).first()
    if usuario is None:
        request.session.pop("recup", None)
        return _ajax_redirect(reverse("core:recuperar_senha")) if ajax else redirect("core:recuperar_senha")
    ok, resultado = _recup_gerar_e_enviar(usuario, sessao["telefone"])
    if not ok:
        if ajax:
            return _ajax_toast(resultado)
        messages.error(request, resultado)
        return redirect("core:recuperar_senha_codigo")
    request.session["recup"] = resultado
    msg = f"Novo código enviado para o WhatsApp {_mascara_telefone(sessao['telefone'])}."
    if ajax:
        return _ajax_toast(msg, "success")
    messages.success(request, msg)
    return redirect("core:recuperar_senha_codigo")


def recuperar_senha_nova_view(request):
    """Etapa 3: definir a nova senha (2x). Só após validar o código."""
    if request.user.is_authenticated:
        return redirect("core:inicio")
    sessao = request.session.get("recup")
    if not sessao or not sessao.get("validado"):
        messages.info(request, "Valide o código antes de definir a nova senha.")
        return redirect("core:recuperar_senha")
    if _recup_expirado(sessao):
        request.session.pop("recup", None)
        messages.error(request, "A sessão expirou. Recomece a recuperação.")
        return redirect("core:recuperar_senha")

    if request.method == "POST":
        ajax = _eh_ajax(request)
        s1 = request.POST.get("senha1") or ""
        s2 = request.POST.get("senha2") or ""
        erro = None
        if len(s1) < 6:
            erro = "A senha deve ter pelo menos 6 caracteres."
        elif s1 != s2:
            erro = "As duas senhas não coincidem."
        else:
            usuario = User.objects.filter(pk=sessao["user_id"]).first()
            if usuario is None:
                request.session.pop("recup", None)
                messages.error(request, "Conta não encontrada. Recomece a recuperação.")
                if ajax:
                    return _ajax_redirect(reverse("core:recuperar_senha"))
                return redirect("core:recuperar_senha")
            usuario.set_password(s1)
            usuario.save(update_fields=["password"])
            # Se a conta exigia troca obrigatória (ajudante), já foi resolvida.
            perfil = getattr(usuario, "perfil", None)
            if perfil is not None and perfil.precisa_trocar_senha:
                perfil.precisa_trocar_senha = False
                perfil.save(update_fields=["precisa_trocar_senha"])
            request.session.pop("recup", None)
            messages.success(request, "Senha redefinida! Faça login com a nova senha.")
            if ajax:
                return _ajax_redirect(reverse("core:login"))
            return redirect("core:login")
        if ajax:
            return _ajax_toast(erro)
        messages.error(request, erro)

    return render(request, "core/recuperar_nova_senha.html", {})


@diretor_required
@require_POST
def usuario_principal_view(request, conta_id):
    """Define qual WhatsApp (pai/mãe/resp legal) é o principal da conta — para onde
    o código de recuperação será enviado. Acionado pelo Diretor na tela Usuários."""
    usuario = get_object_or_404(User, pk=conta_id)
    origem = (request.POST.get("origem") or "").strip()
    validas = {"pai", "mae", "resp", ""}
    if origem not in validas:
        messages.error(request, "Opção de WhatsApp inválida.")
        return redirect("core:usuarios")
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    perfil.whatsapp_principal_origem = origem
    perfil.save(update_fields=["whatsapp_principal_origem"])
    messages.success(request, "WhatsApp principal atualizado.")
    return redirect("core:usuarios")


# ===========================================================================
# Loja do Clube (loja oficial: uniformes, lenços etc.) — independente da
# lojinha de evento. Cadastro (Diretor) + vitrine com carrinho na sessão +
# pagamento simulado (Pix/cartão), igual à lojinha do evento.
# ===========================================================================

# --- Cadastro de produtos (grupos + variações) -----------------------------
def _variacao_loja_vazia(vidx):
    return {"idx": str(vidx), "id": "", "nome": "", "valor_raw": "",
            "estoque_raw": "", "obrig": False}


def _grupo_loja_vazio(gidx):
    return {"idx": str(gidx), "id": "", "nome": "", "modo": "itens",
            "obrig": False, "orient": "", "linhas": [_variacao_loja_vazia(0)]}


def _parse_grupos_loja(request, composto, controla):
    """Lê os grupos e suas variações do POST → (grupos_data, erros). Não salva.

    Para produto simples (não composto), consolida tudo num único grupo padrão.
    """
    grupos = []
    erros = []
    total_vars = 0
    for gidx in request.POST.getlist("grupo_idx"):
        gnome = (request.POST.get(f"grupo_nome_{gidx}") or "").strip()
        gmodo = request.POST.get(f"grupo_modo_{gidx}") or "itens"
        if gmodo not in ("unica", "itens"):
            gmodo = "itens"
        gobrig = bool(request.POST.get(f"grupo_obrig_{gidx}"))
        gorient = (request.POST.get(f"grupo_orient_{gidx}") or "").strip()
        gid = request.POST.get(f"grupo_id_{gidx}") or ""
        linhas = []
        for vidx in request.POST.getlist(f"var_idx_{gidx}"):
            nome = (request.POST.get(f"var_nome_{gidx}_{vidx}") or "").strip()
            valor_raw = (request.POST.get(f"var_valor_{gidx}_{vidx}") or "").strip()
            estoque_raw = (request.POST.get(f"var_estoque_{gidx}_{vidx}") or "").strip()
            vobrig = bool(request.POST.get(f"var_obrig_{gidx}_{vidx}"))
            vid = request.POST.get(f"var_id_{gidx}_{vidx}") or ""
            if not nome and not valor_raw:
                continue  # linha em branco
            valor = None
            try:
                valor = Decimal(valor_raw.replace(",", "."))
                if valor < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                erros.append(f"Preço inválido na variação “{nome or 'sem nome'}”.")
            try:
                estoque = int(estoque_raw) if (controla and estoque_raw) else 0
                estoque = max(estoque, 0)
            except ValueError:
                estoque = 0
            linhas.append({
                "idx": str(vidx), "id": vid, "nome": nome, "valor": valor,
                "valor_raw": valor_raw, "estoque": estoque,
                "estoque_raw": estoque_raw, "obrig": vobrig,
            })
        if not linhas:
            continue  # grupo sem variações é ignorado
        grupos.append({
            "idx": str(gidx), "id": gid, "nome": gnome, "modo": gmodo,
            "obrig": gobrig, "orient": gorient, "linhas": linhas,
        })
        total_vars += len(linhas)
    if not composto and grupos:
        # Produto simples: um único grupo, sem nome/obrigatoriedade de grupo.
        grupos = grupos[:1]
        grupos[0]["nome"] = ""
        grupos[0]["obrig"] = False
        grupos[0]["orient"] = ""
    if total_vars == 0:
        erros.append("Adicione ao menos uma variação (com preço).")
    return grupos, erros


def _salvar_grupos_loja(produto, grupos_data):
    """Cria/atualiza grupos e variações; remove os que não vieram."""
    grupos_vistos = []
    for gi, g in enumerate(grupos_data):
        grp = None
        if g["id"]:
            grp = produto.grupos.filter(pk=g["id"]).first()
        if grp is None:
            grp = GrupoLoja(produto=produto)
        grp.nome = g["nome"]
        grp.modo = g["modo"]
        grp.obrigatorio = g["obrig"]
        grp.orientacao = g["orient"]
        grp.ordem = gi
        grp.save()
        grupos_vistos.append(grp.id)
        vars_vistos = []
        for vi, ln in enumerate(g["linhas"]):
            var = None
            if ln["id"]:
                var = grp.variacoes.filter(pk=ln["id"]).first()
            if var is None:
                var = VariacaoLoja(grupo=grp)
            var.nome = ln["nome"]
            var.valor = ln["valor"] or Decimal("0")
            var.estoque = ln["estoque"]
            var.obrigatorio = ln["obrig"]
            var.ativo = True
            var.ordem = vi
            var.save()
            vars_vistos.append(var.id)
        grp.variacoes.exclude(id__in=vars_vistos).delete()
    produto.grupos.exclude(id__in=grupos_vistos).delete()


def _grupos_iniciais_loja(produto):
    """Grupos no formato do template a partir do produto (edição/novo)."""
    if produto is None:
        return [_grupo_loja_vazio(0)]
    grupos = []
    for gi, g in enumerate(produto.grupos.all()):
        linhas = [
            {"idx": str(vi), "id": v.id, "nome": v.nome, "valor_raw": str(v.valor),
             "estoque_raw": str(v.estoque), "obrig": v.obrigatorio}
            for vi, v in enumerate(g.variacoes.all())
        ] or [_variacao_loja_vazia(0)]
        grupos.append({
            "idx": str(gi), "id": g.id, "nome": g.nome, "modo": g.modo,
            "obrig": g.obrigatorio, "orient": g.orientacao, "linhas": linhas,
        })
    return grupos or [_grupo_loja_vazio(0)]


def _grupos_do_post_loja(grupos_data):
    """Grupos no formato do template a partir do POST (re-render com erro)."""
    out = []
    for gi, g in enumerate(grupos_data):
        linhas = [
            {"idx": str(vi), "id": ln["id"], "nome": ln["nome"],
             "valor_raw": ln["valor_raw"], "estoque_raw": ln["estoque_raw"],
             "obrig": ln["obrig"]}
            for vi, ln in enumerate(g["linhas"])
        ] or [_variacao_loja_vazia(0)]
        out.append({
            "idx": str(gi), "id": g["id"], "nome": g["nome"], "modo": g["modo"],
            "obrig": g["obrig"], "orient": g["orient"], "linhas": linhas,
        })
    return out or [_grupo_loja_vazio(0)]


def _produto_loja_form(request, produto):
    """Cria ou edita um produto da loja (com grupos e variações)."""
    if request.method == "POST":
        form = ProdutoLojaForm(request.POST, request.FILES, instance=produto)
        composto = bool(request.POST.get("composto"))
        controla = bool(request.POST.get("controla_estoque"))
        grupos_data, erros_var = _parse_grupos_loja(request, composto, controla)
        if form.is_valid() and not erros_var:
            with transaction.atomic():
                prod = form.save(commit=False)
                if produto is None:
                    ultimo = ProdutoLoja.objects.order_by("-ordem").first()
                    prod.ordem = (ultimo.ordem + 1) if ultimo else 0
                prod.save()
                _salvar_grupos_loja(prod, grupos_data)
                _salvar_fotos_loja(request, prod)
            messages.success(request, "Produto salvo.")
            return redirect(reverse("core:loja") + "?aba=gerenciar")
        messages.error(request, "Verifique os dados do produto e as variações.")
        grupos = _grupos_do_post_loja(grupos_data)
    else:
        form = ProdutoLojaForm(instance=produto)
        grupos = _grupos_iniciais_loja(produto)
        erros_var = []

    contexto = {
        "form": form,
        "produto": produto,
        "fotos": list(produto.fotos.all()) if produto else [],
        "grupos": grupos,
        "grupo_modelo": _grupo_loja_vazio("__G__"),
        "linha_modelo": _variacao_loja_vazia("__V__"),
        "erros_var": erros_var,
    }
    return render(request, "core/loja_produto_form.html", contexto)


def _salvar_fotos_loja(request, produto):
    """Remove as fotos marcadas e adiciona as novas enviadas (upload múltiplo)."""
    for foto in list(produto.fotos.all()):
        if request.POST.get(f"foto_remover_{foto.id}"):
            foto.delete()
    ultimo = produto.fotos.order_by("-ordem").first()
    ordem = (ultimo.ordem + 1) if ultimo else 0
    for arquivo in request.FILES.getlist("fotos"):
        FotoProdutoLoja.objects.create(produto=produto, imagem=arquivo, ordem=ordem)
        ordem += 1


@diretor_required
def loja_produto_novo_view(request):
    return _produto_loja_form(request, None)


@diretor_required
def loja_produto_editar_view(request, pk):
    produto = get_object_or_404(ProdutoLoja, pk=pk)
    return _produto_loja_form(request, produto)


@diretor_required
@require_POST
def loja_produto_excluir_view(request, pk):
    produto = ProdutoLoja.objects.filter(pk=pk).first()
    if produto is not None:
        produto.delete()
        messages.success(request, "Produto removido.")
    return redirect(reverse("core:loja") + "?aba=gerenciar")


# --- Carrinho (sessão) e comprador -----------------------------------------
def _aventureiros_do_usuario(user):
    """Aventureiros ativos vinculados ao login (para 'para quem é a compra')."""
    if not getattr(user, "is_authenticated", False):
        return Aventureiro.objects.none()
    return Aventureiro.objects.filter(usuario=user, ativo=True).order_by("nome_completo")


def _comprador_padrao(user):
    """Dados do comprador pré-preenchidos a partir do login."""
    dados = {
        "nome": (user.get_full_name() or user.username) if getattr(user, "is_authenticated", False) else "",
        "whatsapp": "",
        "email": (user.email or "") if getattr(user, "is_authenticated", False) else "",
    }
    if getattr(user, "is_authenticated", False):
        av = Aventureiro.objects.filter(usuario=user).order_by("-criado_em").first()
        if av:
            dados["nome"] = av.resp_nome or dados["nome"]
            dados["whatsapp"] = av.resp_whatsapp or ""
    return dados


def _loja_cart(request):
    return request.session.get("loja_carrinho", [])


def _loja_cart_save(request, cart):
    request.session["loja_carrinho"] = cart
    request.session.modified = True


def _loja_cart_detalhado(request):
    """Resolve o carrinho da sessão em kits (produto + itens) e o total.

    Descarta silenciosamente itens/produtos que ficaram indisponíveis, reescrevendo
    o carrinho — assim a seleção da pessoa é preservada enquanto for válida."""
    cart = _loja_cart(request)
    kits = []
    total = Decimal("0")
    novo = []
    mudou = False
    for entry in cart:
        prod = (
            ProdutoLoja.objects.filter(pk=entry.get("produto_id"), ativo=True)
            .prefetch_related("grupos__variacoes").first()
        )
        if prod is None:
            mudou = True
            continue
        aventureiro = None
        if entry.get("aventureiro_id"):
            aventureiro = Aventureiro.objects.filter(pk=entry["aventureiro_id"]).first()
        variacoes = {v.id: v for g in prod.grupos.all() for v in g.variacoes.all() if v.ativo}
        itens = []
        itens_ok = []
        subtotal = Decimal("0")
        for it in entry.get("itens", []):
            v = variacoes.get(it.get("variacao_id"))
            try:
                qtd = int(it.get("qtd") or 0)
            except (TypeError, ValueError):
                qtd = 0
            if v is None or qtd <= 0:
                mudou = True
                continue
            st = v.valor * qtd
            subtotal += st
            itens.append({"variacao": v, "grupo": v.grupo, "qtd": qtd, "subtotal": st})
            itens_ok.append({"variacao_id": v.id, "qtd": qtd})
        if not itens:
            mudou = True
            continue
        total += subtotal
        kits.append({
            "index": len(kits), "produto": prod, "aventureiro": aventureiro,
            "itens": itens, "subtotal": subtotal,
        })
        novo.append({
            "produto_id": prod.id,
            "aventureiro_id": aventureiro.id if aventureiro else None,
            "itens": itens_ok,
        })
    if mudou:
        _loja_cart_save(request, novo)
    return kits, total


# --- Telas da loja ---------------------------------------------------------
@diretor_required
def loja_view(request):
    """Tela "Loja" (Diretor): abas Gerenciar (cadastro + compras) e Loja (vitrine
    com carrinho). Por ora, só o Diretor vê o menu; a vitrine já é @login_required
    para quando abrirmos aos responsáveis."""
    produtos = list(
        ProdutoLoja.objects.prefetch_related("grupos__variacoes", "fotos").all()
    )
    compras = list(
        CompraLoja.objects.prefetch_related("itens").select_related("usuario").all()
    )
    kits, total = _loja_cart_detalhado(request)
    contexto = {
        "produtos": produtos,
        "produtos_ativos": [p for p in produtos if p.ativo],
        "compras": compras,
        "relatorio": _loja_relatorio(),
        "cart_kits": kits,
        "cart_total": total,
        "comprador": _comprador_padrao(request.user),
        "formas_pagamento": FORMAS_PAGAMENTO_ONLINE,
        "aba": request.GET.get("aba", "gerenciar"),
    }
    return render(request, "core/loja.html", contexto)


def _loja_relatorio():
    """Consolida os números de vendas da loja (só compras confirmadas).

    "Mais vendidos": produto **composto** (ex.: Uniforme de Gala) conta **por
    pedido** (cada pedido que levou o produto = 1), pois ele tem vários itens
    obrigatórios; produto **simples** conta por **quantidade** de unidades.
    """
    conf = CompraLoja.objects.filter(status="confirmado")
    itens = ItemCompraLoja.objects.filter(compra__status="confirmado").select_related("produto")
    n_compras = conf.count()
    arrecadado = conf.aggregate(s=Sum("valor_total"))["s"] or Decimal("0")
    ticket = (arrecadado / n_compras) if n_compras else Decimal("0")

    agrup = {}
    for it in itens:
        d = agrup.setdefault(it.produto_nome, {
            "produto_nome": it.produto_nome, "qtd": 0,
            "total": Decimal("0"), "compras": set(), "composto": False,
        })
        d["qtd"] += it.quantidade
        d["total"] += it.valor_total
        d["compras"].add(it.compra_id)
        if it.produto and it.produto.composto:
            d["composto"] = True
    mais_vendidos = []
    for d in agrup.values():
        if d["composto"]:
            contagem, unidade = len(d["compras"]), "pedido(s)"
        else:
            contagem, unidade = d["qtd"], "un."
        mais_vendidos.append({
            "produto_nome": d["produto_nome"], "contagem": contagem,
            "unidade": unidade, "total": d["total"],
        })
    mais_vendidos.sort(key=lambda x: x["total"], reverse=True)

    por_forma = list(
        conf.values("forma_pagamento")
        .annotate(n=Count("id"), total=Sum("valor_total"))
        .order_by("-total")
    )
    formas_nomes = dict(FORMA_PAGAMENTO_CHOICES)
    for f in por_forma:
        f["nome"] = formas_nomes.get(f["forma_pagamento"], f["forma_pagamento"])
    pendentes = list(
        itens.filter(quantidade_entregue__lt=F("quantidade"))
        .select_related("compra")
        .order_by("compra__criado_em")
    )
    unidades_a_entregar = sum(i.falta_entregar for i in pendentes)
    return {
        "n_compras": n_compras,
        "arrecadado": arrecadado,
        "ticket": ticket,
        "mais_vendidos": mais_vendidos,
        "por_forma": por_forma,
        "pendentes": pendentes,
        "unidades_a_entregar": unidades_a_entregar,
        "n_pendentes": len(pendentes),
    }


@diretor_required
@require_POST
def loja_entrega_view(request):
    """Marca/desmarca a entrega de um item de compra (toggle total). JSON."""
    try:
        item = ItemCompraLoja.objects.select_related("compra").get(
            pk=request.POST.get("item_id")
        )
    except (ItemCompraLoja.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"ok": False, "erro": "Item não encontrado."}, status=404)
    entregar = request.POST.get("entregar") == "1"
    if entregar:
        item.quantidade_entregue = item.quantidade
        item.entregue_em = timezone.now()
        item.entregue_por = request.user
    else:
        item.quantidade_entregue = 0
        item.entregue_em = None
        item.entregue_por = None
    item.save(update_fields=["quantidade_entregue", "entregue_em", "entregue_por"])
    return JsonResponse({
        "ok": True,
        "status": item.status_entrega,
        "falta": item.falta_entregar,
        "compra_status": item.compra.status_entrega,
        "compra_falta": item.compra.falta_entregar_total,
    })


@diretor_required
@require_POST
def loja_entrega_compra_view(request):
    """Marca/desmarca a entrega de TODOS os itens de uma compra de uma vez. JSON."""
    compra = get_object_or_404(CompraLoja, pk=request.POST.get("compra_id"))
    entregar = request.POST.get("entregar") == "1"
    agora = timezone.now() if entregar else None
    itens = []
    for item in compra.itens.all():
        item.quantidade_entregue = item.quantidade if entregar else 0
        item.entregue_em = agora
        item.entregue_por = request.user if entregar else None
        item.save(update_fields=["quantidade_entregue", "entregue_em", "entregue_por"])
        itens.append({"id": item.id, "status": item.status_entrega})
    return JsonResponse({
        "ok": True,
        "compra_status": compra.status_entrega,
        "itens": itens,
    })


@login_required
def loja_produto_view(request, pk):
    """Página de um produto na vitrine: configurar (tamanhos/itens) e adicionar ao
    carrinho. Mostra o seletor de aventureiro quando o login tem mais de um."""
    produto = get_object_or_404(
        ProdutoLoja.objects.prefetch_related("grupos__variacoes", "fotos"),
        pk=pk, ativo=True,
    )
    aventureiros = list(_aventureiros_do_usuario(request.user))
    contexto = {
        "produto": produto,
        "grupos": list(produto.grupos.all()),
        "fotos": list(produto.fotos.all()),
        "aventureiros": aventureiros,
    }
    return render(request, "core/loja_produto.html", contexto)


@login_required
@require_POST
def loja_carrinho_add_view(request):
    """Adiciona um produto configurado ao carrinho (sessão)."""
    produto = get_object_or_404(
        ProdutoLoja.objects.prefetch_related("grupos__variacoes"),
        pk=request.POST.get("produto_id"), ativo=True,
    )
    aventureiro = None
    av_id = request.POST.get("aventureiro_id") or ""
    if av_id:
        aventureiro = _aventureiros_do_usuario(request.user).filter(pk=av_id).first()

    itens = []
    for g in produto.grupos.all():
        ativos = [v for v in g.variacoes.all() if v.ativo]
        if g.modo == "unica":
            sel = request.POST.get(f"grupo_{g.id}") or ""
            v = next((x for x in ativos if str(x.id) == sel), None)
            if v is not None:
                itens.append((v, 1))
        else:
            for v in ativos:
                try:
                    qtd = int(request.POST.get(f"item_{v.id}") or 0)
                except (TypeError, ValueError):
                    qtd = 0
                if qtd > 0:
                    itens.append((v, qtd))

    if not itens:
        messages.error(request, "Escolha ao menos uma opção para adicionar.")
        return redirect("core:loja_produto", pk=produto.id)

    erros = []
    for v, qtd in itens:
        if produto.controla_estoque and qtd > v.estoque:
            erros.append(f"Estoque insuficiente para {v.rotulo} ({v.estoque} disponível).")
    if erros:
        for e in erros:
            messages.error(request, e)
        return redirect("core:loja_produto", pk=produto.id)

    cart = _loja_cart(request)
    cart.append({
        "produto_id": produto.id,
        "aventureiro_id": aventureiro.id if aventureiro else None,
        "itens": [{"variacao_id": v.id, "qtd": qtd} for v, qtd in itens],
    })
    _loja_cart_save(request, cart)
    messages.success(request, f"“{produto.nome}” foi adicionado ao carrinho.")
    return redirect(reverse("core:loja") + "?aba=loja#carrinho")


@login_required
@require_POST
def loja_carrinho_remover_view(request):
    """Remove um kit do carrinho pelo índice."""
    try:
        idx = int(request.POST.get("idx"))
    except (TypeError, ValueError):
        idx = -1
    cart = _loja_cart(request)
    if 0 <= idx < len(cart):
        cart.pop(idx)
        _loja_cart_save(request, cart)
        messages.success(request, "Item removido do carrinho.")
    return redirect(reverse("core:loja") + "?aba=loja#carrinho")


@login_required
@require_POST
def loja_finalizar_view(request):
    """Valida carrinho + dados do comprador + forma e leva ao pagamento."""
    kits, total = _loja_cart_detalhado(request)
    comprador = {
        "nome": (request.POST.get("comprador_nome") or "").strip(),
        "whatsapp": (request.POST.get("comprador_whatsapp") or "").strip(),
        "email": (request.POST.get("comprador_email") or "").strip(),
    }
    forma = request.POST.get("forma_pagamento") or ""
    erros = []
    if not kits:
        erros.append("Seu carrinho está vazio.")
    if not comprador["nome"]:
        erros.append("Informe o nome do comprador.")
    if not comprador["whatsapp"]:
        erros.append("Informe o WhatsApp para contato.")
    if forma not in dict(FORMAS_PAGAMENTO_ONLINE):
        erros.append("Escolha a forma de pagamento (Pix ou cartão de crédito).")
    if erros:
        for e in erros:
            messages.error(request, e)
        return redirect(reverse("core:loja") + "?aba=loja#carrinho")
    request.session["loja_clube_checkout"] = {"comprador": comprador, "forma": forma}
    return redirect("core:loja_pagamento")


def _criar_compra_loja(usuario, kits, comprador, forma):
    """Cria a CompraLoja + itens e baixa o estoque. Retorna a compra."""
    compra = CompraLoja(
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        comprador_nome=comprador.get("nome", ""),
        comprador_whatsapp=comprador.get("whatsapp", ""),
        comprador_email=comprador.get("email", ""),
        codigo=CompraLoja.gerar_codigo_unico(),
        status="confirmado",
        forma_pagamento=forma,
    )
    total = Decimal("0")
    itens_obj = []
    for ki, kit in enumerate(kits):
        prod = kit["produto"]
        av = kit["aventureiro"]
        for it in kit["itens"]:
            v = it["variacao"]
            qtd = it["qtd"]
            st = it["subtotal"]
            total += st
            itens_obj.append(ItemCompraLoja(
                produto=prod, variacao=v, aventureiro=av,
                produto_nome=prod.nome, grupo_nome=v.grupo.nome,
                variacao_nome=v.nome,
                aventureiro_nome=av.nome_completo if av else "",
                quantidade=qtd, valor_unitario=v.valor, valor_total=st, kit=ki,
            ))
            if prod.controla_estoque:
                VariacaoLoja.objects.filter(pk=v.id).update(estoque=F("estoque") - qtd)
    compra.valor_total = total
    compra.save()
    for item in itens_obj:
        item.compra = compra
        item.save()
    return compra


@login_required
def loja_pagamento_view(request):
    """Tela de pagamento (SIMULADA) da compra da loja. Cria a compra só após a
    aprovação (o carrinho fica na sessão até lá). Espelha a lojinha do evento."""
    kits, total = _loja_cart_detalhado(request)
    dados = request.session.get("loja_clube_checkout")
    if not kits or not dados:
        return redirect(reverse("core:loja") + "?aba=loja")
    comprador = dados["comprador"]
    forma = dados["forma"]

    if request.method == "POST":
        erros = []
        for kit in kits:
            for it in kit["itens"]:
                v = it["variacao"]
                if v.grupo.produto.controla_estoque and it["qtd"] > v.estoque:
                    erros.append(f"Estoque insuficiente para {v.rotulo}.")
        if erros:
            request.session.pop("loja_clube_checkout", None)
            for e in erros:
                messages.error(request, e)
            messages.error(request, "Refaça a compra, por favor.")
            return redirect(reverse("core:loja") + "?aba=loja")
        with transaction.atomic():
            compra = _criar_compra_loja(request.user, kits, comprador, forma)
        request.session.pop("loja_clube_checkout", None)
        _loja_cart_save(request, [])
        request.session["loja_compra_codigo"] = compra.codigo
        messages.success(request, "Pagamento aprovado! Compra confirmada.")
        return redirect("core:loja_sucesso")

    forma_nome = dict(FORMAS_PAGAMENTO_ONLINE).get(forma, forma)
    contexto = {
        "kits": kits, "total": total, "comprador": comprador,
        "forma": forma, "forma_nome": forma_nome,
    }
    if forma == "pix":
        contexto["qr_svg"] = _qr_svg(f"LOJA-{total}")
        contexto["pix_codigo"] = _pix_copia_cola(total, "LC000")
    return render(request, "core/loja_pagamento.html", contexto)


@login_required
def loja_sucesso_view(request):
    """Confirmação da compra (código + itens). Pagamento simulado."""
    codigo = request.session.get("loja_compra_codigo")
    compra = (
        CompraLoja.objects.prefetch_related("itens").filter(codigo=codigo).first()
        if codigo else None
    )
    if compra is None:
        return redirect("core:loja")
    return render(request, "core/loja_sucesso.html", {"compra": compra})


@diretor_required
@require_POST
def loja_compra_cancelar_view(request, compra_id):
    """Cancela uma compra (Diretor) e devolve os itens ao estoque."""
    compra = get_object_or_404(CompraLoja, pk=compra_id)
    if compra.status != "cancelado":
        with transaction.atomic():
            for item in compra.itens.all():
                if item.variacao_id and item.variacao.grupo.produto.controla_estoque:
                    VariacaoLoja.objects.filter(pk=item.variacao_id).update(
                        estoque=F("estoque") + item.quantidade
                    )
            compra.status = "cancelado"
            compra.save(update_fields=["status"])
        messages.success(request, "Compra cancelada.")
    return redirect(reverse("core:loja") + "?aba=gerenciar")


# ===========================================================================
# Mensalidades do clube
# ===========================================================================
def _valor_mensalidade(config, aventureiro, tipo):
    """(valor, isento) de uma cobrança conforme config + isenção/desconto do av."""
    if aventureiro.mensalidade_isento:
        return Decimal("0"), True
    base = config.valor_base(tipo)
    pct = aventureiro.mensalidade_desconto_pct or 0
    if pct:
        base = (base * (100 - pct) / Decimal("100")).quantize(Decimal("0.01"))
    return base, False


def _gerar_mensalidades(aventureiro, ano, mes_inscricao=None):
    """Cria as cobranças que faltam do ano: `mes_inscricao` (se dado) nasce como
    'inscrição' e os demais como 'mensalidade'. Idempotente. Retorna quantas criou."""
    config = ConfigMensalidade.get_solo()
    inicio = mes_inscricao or 1
    existentes = set(
        aventureiro.mensalidades.filter(ano=ano).values_list("mes", flat=True)
    )
    novas = 0
    for mes in range(inicio, 13):
        if mes in existentes:
            continue
        tipo = "inscricao" if mes == mes_inscricao else "mensalidade"
        valor, isento = _valor_mensalidade(config, aventureiro, tipo)
        Mensalidade.objects.create(
            aventureiro=aventureiro, ano=ano, mes=mes, tipo=tipo,
            valor=valor, isento=isento, status="aberta",
        )
        novas += 1
    return novas


def _resumo_mensalidades(meses):
    """Resumo de uma lista de Mensalidade (de um aventureiro/ano)."""
    pagas = [m for m in meses if m.status == "paga"]
    abertas = [m for m in meses if m.em_aberto]
    isentas = [m for m in meses if m.isento and m.status != "cancelada"]
    return {
        "pagas": len(pagas),
        "abertas": len(abertas),
        "isentas": len(isentas),
        "total": len([m for m in meses if m.status != "cancelada"]),
        "aberto_valor": sum((m.valor for m in abertas), Decimal("0")),
        "recebido": sum((m.valor_pago or Decimal("0") for m in pagas), Decimal("0")),
        "previsto": sum(
            (m.valor for m in meses if m.status != "cancelada" and not m.isento),
            Decimal("0"),
        ),
    }


@diretor_required
def mensalidades_view(request):
    """Painel de mensalidades (Diretor): por aventureiro, os meses do ano com o
    controle de pago/em aberto, isenção/desconto e geração das cobranças."""
    anos = sorted(
        set(Mensalidade.objects.values_list("ano", flat=True)) | {timezone.localdate().year},
        reverse=True,
    )
    try:
        ano = int(request.GET.get("ano", anos[0]))
    except (TypeError, ValueError):
        ano = anos[0]

    aventureiros = list(Aventureiro.objects.filter(ativo=True).order_by("nome_completo"))
    mens = Mensalidade.objects.filter(ano=ano).select_related("aventureiro")
    por_av = defaultdict(list)
    for m in mens:
        por_av[m.aventureiro_id].append(m)

    linhas = []
    tot = {"previsto": Decimal("0"), "recebido": Decimal("0"),
           "aberto": Decimal("0"), "isentos": 0}
    for av in aventureiros:
        meses = sorted(por_av.get(av.id, []), key=lambda x: x.mes)
        resumo = _resumo_mensalidades(meses)
        linhas.append({"av": av, "meses": meses, "resumo": resumo,
                       "tem": bool(meses)})
        tot["previsto"] += resumo["previsto"]
        tot["recebido"] += resumo["recebido"]
        tot["aberto"] += resumo["aberto_valor"]
        if av.mensalidade_isento:
            tot["isentos"] += 1

    contexto = {
        "config": ConfigMensalidade.get_solo(),
        "ano": ano,
        "anos": anos,
        "linhas": linhas,
        "totais": tot,
        "formas_pagamento": [
            ("dinheiro", "Dinheiro"), ("pix", "Pix"),
            ("cartao", "Cartão"), ("online", "Online"),
        ],
    }
    return render(request, "core/mensalidades.html", contexto)


@diretor_required
@require_POST
def mensalidade_config_view(request):
    """Salva os valores padrão de inscrição/mensalidade."""
    config = ConfigMensalidade.get_solo()
    try:
        config.valor_inscricao = Decimal((request.POST.get("valor_inscricao") or "0").replace(",", "."))
        config.valor_mensalidade = Decimal((request.POST.get("valor_mensalidade") or "0").replace(",", "."))
        if config.valor_inscricao < 0 or config.valor_mensalidade < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        messages.error(request, "Valores inválidos.")
        return redirect("core:mensalidades")
    config.atualizado_por = request.user
    config.save()
    messages.success(request, "Valores atualizados. Novas cobranças usarão esses valores.")
    return redirect("core:mensalidades")


@diretor_required
@require_POST
def mensalidades_gerar_view(request):
    """Gera as cobranças do ano que faltam (um aventureiro ou todos os ativos)."""
    try:
        ano = int(request.POST.get("ano") or timezone.localdate().year)
    except (TypeError, ValueError):
        ano = timezone.localdate().year
    av_id = request.POST.get("aventureiro_id") or ""
    if av_id:
        alvos = Aventureiro.objects.filter(pk=av_id, ativo=True)
    else:
        alvos = Aventureiro.objects.filter(ativo=True)
    total = 0
    for av in alvos:
        total += _gerar_mensalidades(av, ano)
    messages.success(request, f"{total} cobrança(s) gerada(s) para {ano}.")
    return redirect(f"{reverse('core:mensalidades')}?ano={ano}")


@diretor_required
@require_POST
def mensalidade_pagar_view(request):
    """Marca/desmarca uma mensalidade como paga (JSON). Retorna o resumo do av."""
    try:
        m = Mensalidade.objects.select_related("aventureiro").get(pk=request.POST.get("mensalidade_id"))
    except (Mensalidade.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"ok": False}, status=404)
    pagar = request.POST.get("pagar") == "1"
    if pagar:
        m.status = "paga"
        m.forma_pagamento = request.POST.get("forma") or "dinheiro"
        m.valor_pago = m.valor
        m.pago_em = timezone.now()
        m.registrado_por = request.user
    else:
        m.status = "aberta"
        m.forma_pagamento = ""
        m.valor_pago = None
        m.pago_em = None
        m.registrado_por = None
    m.save()
    meses = list(m.aventureiro.mensalidades.filter(ano=m.ano))
    r = _resumo_mensalidades(meses)
    return JsonResponse({
        "ok": True,
        "status": m.status,
        "pagas": r["pagas"],
        "total": r["total"],
        "aberto_fmt": _fmt_moeda(r["aberto_valor"]),
    })


@diretor_required
@require_POST
def mensalidade_isencao_view(request):
    """Define isenção/desconto de um aventureiro e (opcional) reaplica nas
    cobranças em aberto do ano."""
    av = get_object_or_404(Aventureiro, pk=request.POST.get("aventureiro_id"))
    av.mensalidade_isento = bool(request.POST.get("isento"))
    try:
        pct = int(request.POST.get("desconto_pct") or 0)
    except (TypeError, ValueError):
        pct = 0
    av.mensalidade_desconto_pct = min(max(pct, 0), 100)
    av.save(update_fields=["mensalidade_isento", "mensalidade_desconto_pct"])

    try:
        ano = int(request.POST.get("ano") or timezone.localdate().year)
    except (TypeError, ValueError):
        ano = timezone.localdate().year
    config = ConfigMensalidade.get_solo()
    afetadas = 0
    for m in av.mensalidades.filter(ano=ano).exclude(status="paga").exclude(status="cancelada"):
        valor, isento = _valor_mensalidade(config, av, m.tipo)
        m.valor, m.isento = valor, isento
        m.save(update_fields=["valor", "isento"])
        afetadas += 1
    messages.success(
        request,
        f"Atualizado: {'isento' if av.mensalidade_isento else (str(av.mensalidade_desconto_pct) + '% de desconto' if av.mensalidade_desconto_pct else 'sem desconto')}. "
        f"{afetadas} cobrança(s) em aberto recalculada(s).",
    )
    return redirect(f"{reverse('core:mensalidades')}?ano={ano}")


@diretor_required
@require_POST
def mensalidade_editar_view(request):
    """Edita UMA cobrança específica: define o valor (desconto pontual) ou isenta
    aquele mês. Não mexe em cobranças já pagas."""
    m = get_object_or_404(Mensalidade, pk=request.POST.get("mensalidade_id"))
    if m.status == "paga":
        messages.error(request, "Essa cobrança está paga. Desfaça o pagamento antes de editar.")
        return redirect(f"{reverse('core:mensalidades')}?ano={m.ano}")
    if request.POST.get("isento"):
        m.isento = True
        m.valor = Decimal("0")
    else:
        m.isento = False
        try:
            pct = int(request.POST.get("desconto_pct") or 0)
        except (TypeError, ValueError):
            pct = 0
        pct = min(max(pct, 0), 100)
        base = ConfigMensalidade.get_solo().valor_base(m.tipo)
        m.valor = (base * (100 - pct) / Decimal("100")).quantize(Decimal("0.01"))
    m.save(update_fields=["isento", "valor"])
    messages.success(request, f"{m.mes_nome}/{m.ano} de {m.aventureiro.nome_completo} atualizado.")
    return redirect(f"{reverse('core:mensalidades')}?ano={m.ano}")


def _fmt_moeda(valor):
    """R$ no formato pt-BR (para respostas JSON)."""
    s = f"{valor:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")

