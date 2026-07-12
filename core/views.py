import base64
import binascii
import datetime
import hashlib
import json
from collections import defaultdict
import re
import secrets
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import (
    AutorizacaoImagemForm,
    AventureiroForm,
    CaixaClubeForm,
    CampoInscricaoForm,
    ContaForm,
    CustoClubeForm,
    CustoEventoForm,
    EventoComplexoForm,
    EventoForm,
    EventoInscricaoConfigForm,
    FaixaEtariaPrecoForm,
    FichaMedicaForm,
    FichaMedicaDiretoriaForm,
    InscricaoForm,
    MembroDiretoriaForm,
    ProdutoEventoForm,
    ProdutoLojaForm,
    ResponsavelLegalForm,
)
from . import mercadopago as mp
from . import openai_ia
from . import termos
from . import wapi
from . import wapi_parser
from .models import (
    FORMA_PAGAMENTO_CHOICES,
    MESES_PT,
    AssinaturaDocumento,
    Aventureiro,
    CaixaClube,
    CobrancaEnviada,
    CompraLoja,
    ComprovanteCustoClube,
    ConfigMensalidade,
    MENSAGEM_APELO_PADRAO,
    MENSAGEM_COBRANCA_PADRAO,
    PROMPT_COBRANCA_IA_PADRAO,
    AssinaturaDocumentoDiretoria,
    CupomDesconto,
    CustoClube,
    CustoEvento,
    Evento,
    FotoProdutoLoja,
    GrupoLoja,
    GrupoWhatsapp,
    Inscricao,
    ItemCompraLoja,
    ItemPedidoLoja,
    MembroDiretoria,
    MercadoPagoConfig,
    Mensalidade,
    OpenAIConfig,
    OperadorEvento,
    Pagamento,
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
    WhatsappWebhookEvent,
)
from .menus import PERFIL_ATIVO_KEY, atua_como_responsavel, perfis_do_usuario
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


def _preparar_assinaturas(av):
    """Anexa ao aventureiro as datas de assinatura por documento (ou None), para
    exibir o status "assinado em ..." em Meus Dados/Usuários. **Não** expõe a
    imagem da assinatura (só a tela do Diretor mostra o termo assinado)."""
    por_doc = {a.documento: a for a in av.assinaturas.all()}
    av.assinado_medica = por_doc.get(AssinaturaDocumento.DOC_DECLARACAO_MEDICA)
    av.assinado_imagem = por_doc.get(AssinaturaDocumento.DOC_AUTORIZACAO_IMAGEM)
    av.assinado_inscricao = por_doc.get(AssinaturaDocumento.DOC_INSCRICAO)


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
        (fm.variola, "Varíola"), (fm.coqueluche, "Coqueluche"),
        (fm.difteria, "Difteria"), (fm.caxumba, "Caxumba"),
        (fm.rinite, "Rinite"), (fm.bronquite, "Bronquite"),
    ]
    fm.doencas_lista = [r for marcado, r in doencas if marcado]

    deficiencias = [
        (fm.deficiente_cadeirante, "Cadeirante"),
        (fm.deficiente_visual, "Visual"),
        (fm.deficiente_auditivo, "Auditiva"),
        (fm.deficiente_fala, "Fala (mudez/dificuldade)"),
    ]
    fm.deficiencias_lista = [r for marcado, r in deficiencias if marcado]

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
        .prefetch_related("assinaturas")
        .all()
    )

    for av in aventureiros:
        av.idade = _idade(av.data_nascimento)
        av.classes = _classes_investidas(av)
        av.foto_ok = _foto_valida(av)
        av.iniciais = _iniciais(av.nome_completo)
        # Reverse OneToOne pode não existir; getattr evita exceção.
        _preparar_ficha(getattr(av, "ficha_medica", None))
        _preparar_assinaturas(av)

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

    # Dados da diretoria (se o usuário for voluntário/diretoria).
    membro = (
        MembroDiretoria.objects
        .filter(usuario=usuario)
        .select_related("ficha_medica")
        .first()
    )
    if membro is not None:
        membro.idade = _idade(membro.data_nascimento)
        membro.foto_ok = _foto_valida(membro)
        membro.iniciais = _iniciais(membro.nome_completo)
        membro.papel = _papel_diretoria(usuario)
        _preparar_ficha(getattr(membro, "ficha_medica", None))

    contexto = {
        "aventureiros": aventureiros,
        "total_aventureiros": len(aventureiros),
        "responsavel": responsavel,
        "membro_diretoria": membro,
    }
    return render(request, "core/inicio.html", contexto)


# Papéis da diretoria (grupos). "Diretoria" = genérico (sem papel específico).
PAPEIS_ESPECIFICOS = ["Diretor", "Secretário", "Tesoureiro", "Professor"]
GRUPOS_PAPEL_DIRETORIA = ["Diretoria"] + PAPEIS_ESPECIFICOS
PAPEIS_DIRETORIA_OPCOES = [
    ("Diretoria", "Diretoria (sem papel definido)"),
    ("Diretor", "Diretor"),
    ("Secretário", "Secretário"),
    ("Tesoureiro", "Tesoureiro"),
    ("Professor", "Professor"),
]


def _papel_atual_diretoria(usuario):
    """Grupo de papel específico do usuário (ou 'Diretoria' genérico)."""
    nomes = set(usuario.groups.values_list("name", flat=True))
    for papel in PAPEIS_ESPECIFICOS:
        if papel in nomes:
            return papel
    return "Diretoria"


def _papel_diretoria(usuario):
    """Papel do membro da diretoria para exibição (ou genérico 'a definir')."""
    papel = _papel_atual_diretoria(usuario)
    return papel if papel in PAPEIS_ESPECIFICOS else "Diretoria (papel a definir)"


@diretor_required
def diretoria_equipe_view(request):
    """Diretor: lista os integrantes da diretoria e permite atribuir o papel."""
    membros = list(
        MembroDiretoria.objects.filter(demo=False)
        .select_related("usuario")
        .order_by("nome_completo")
    )
    for m in membros:
        m.papel_atual = _papel_atual_diretoria(m.usuario)
    contexto = {"membros": membros, "papeis": PAPEIS_DIRETORIA_OPCOES}
    return render(request, "core/diretoria_equipe.html", contexto)


@diretor_required
@require_POST
def diretoria_papel_view(request, pk):
    """Diretor: define o papel de um integrante da diretoria (via grupo)."""
    membro = get_object_or_404(MembroDiretoria, pk=pk)
    papel = request.POST.get("papel", "")
    if papel not in {p for p, _ in PAPEIS_DIRETORIA_OPCOES}:
        messages.error(request, "Papel inválido.")
        return redirect("core:diretoria_equipe")
    usuario = membro.usuario
    # Remove todos os grupos de papel e aplica só o escolhido.
    for nome in GRUPOS_PAPEL_DIRETORIA:
        grupo = Group.objects.filter(name=nome).first()
        if grupo:
            usuario.groups.remove(grupo)
    grupo, _ = Group.objects.get_or_create(name=papel)
    usuario.groups.add(grupo)
    messages.success(
        request, f"Papel de {membro.nome_completo} definido como {papel}."
    )
    return redirect("core:diretoria_equipe")


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


# Campos (name) de cada assinatura no POST → documento correspondente.
CAMPOS_ASSINATURA = [
    ("assinatura_inscricao", AssinaturaDocumento.DOC_INSCRICAO, "ficha de inscrição"),
    ("assinatura_declaracao_medica", AssinaturaDocumento.DOC_DECLARACAO_MEDICA, "declaração médica"),
    ("assinatura_termo_imagem", AssinaturaDocumento.DOC_AUTORIZACAO_IMAGEM, "autorização de uso de imagem"),
]


def _decode_signature(signature_data):
    """Converte o data-URL (base64 PNG) da assinatura desenhada em um arquivo
    pronto para gravar num ImageField. Retorna None se vazio/ inválido."""
    if not signature_data:
        return None
    payload = signature_data
    if "," in payload:
        payload = payload.split(",", 1)[1]
    try:
        binario = base64.b64decode(payload)
    except (binascii.Error, ValueError, TypeError):
        return None
    if not binario:
        return None
    return ContentFile(binario, name=f"assinatura_{uuid.uuid4().hex}.png")


def _validar_aceites(request):
    """Valida os aceites obrigatórios: exige a assinatura desenhada dos três
    documentos (ficha de inscrição, declaração médica e uso de imagem)."""
    erros = []
    for campo, _doc, rotulo in CAMPOS_ASSINATURA:
        if not _decode_signature(request.POST.get(campo, "")):
            erros.append(f"É necessário assinar a {rotulo}.")
    return erros


def _salvar_aventureiro(usuario, aventureiro, medica, imagem, request):
    """Salva o aventureiro + ficha médica + autorização de imagem e as três
    assinaturas dos documentos (transacional)."""
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

        _salvar_assinaturas(aventureiro_obj, autorizacao, request)

        # Gera as mensalidades do ano: o mês atual como inscrição e os
        # seguintes como mensalidade (valores/isenção conforme configuração).
        hoje = timezone.localdate()
        _gerar_mensalidades(aventureiro_obj, hoje.year, mes_inscricao=hoje.month)
    return aventureiro_obj


def _salvar_assinaturas(aventureiro_obj, autorizacao, request):
    """Cria os três AssinaturaDocumento, guardando o texto do termo preenchido
    (snapshot) e a imagem desenhada. A validação já garantiu que vieram."""
    for campo, doc, _rotulo in CAMPOS_ASSINATURA:
        imagem_assinatura = _decode_signature(request.POST.get(campo, ""))
        if imagem_assinatura is None:
            continue
        titulo, texto = termos.montar_texto(doc, aventureiro_obj, autorizacao)
        AssinaturaDocumento.objects.create(
            aventureiro=aventureiro_obj,
            documento=doc,
            imagem=imagem_assinatura,
            titulo_documento=titulo,
            texto_documento=texto,
            assinante_nome=aventureiro_obj.resp_nome,
            assinante_cpf=aventureiro_obj.resp_cpf,
        )


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


def _dados_diretoria_para_responsavel(usuario):
    """No fluxo mesclado (diretoria + aventureiro), pré-preenche o responsável
    com os dados já digitados na diretoria. Devolve None se não houver diretoria."""
    membro = MembroDiretoria.objects.filter(usuario=usuario).first()
    if membro is None:
        return None
    return {
        "resp_nome": membro.nome_completo,
        "resp_cpf": membro.cpf,
        "resp_email": membro.email,
        "resp_whatsapp": membro.whatsapp,
    }


def _dados_anteriores_ou_diretoria(usuario):
    """Dados de outro aventureiro (se houver) ou, na falta, os da diretoria."""
    return _dados_responsaveis_anteriores(usuario) or _dados_diretoria_para_responsavel(usuario)


def cadastro_view(request):
    """Tela "Cadastre-se": escolha do tipo de cadastro.

    Três opções: Aventureiro (fluxo do responsável), Diretoria (só voluntário) e
    Diretoria + Aventureiro (voluntário que também é responsável — 2 perfis)."""
    return render(request, "core/cadastro_escolha.html")


def cadastro_aventureiro_view(request):
    """
    Cadastro inicial de aventureiro: cria a conta de acesso + o primeiro aventureiro.

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
        erro_aceites = _validar_aceites(request)

        if formularios_ok and not erro_aceites:
            usuario = User.objects.create_user(
                username=conta.cleaned_data["username"],
                password=conta.cleaned_data["senha"],
            )
            aventureiro_obj = _salvar_aventureiro(usuario, aventureiro, medica, imagem, request)
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
        erro_aceites = _validar_aceites(request)

        if formularios_ok and not erro_aceites:
            aventureiro_obj = _salvar_aventureiro(usuario, aventureiro, medica, imagem, request)
            request.session[SESSAO_ULTIMO_NOME] = aventureiro_obj.nome_completo
            return redirect("core:cadastro_sucesso")

    contexto = {
        "aventureiro_form": aventureiro,
        "medica_form": medica,
        "imagem_form": imagem,
        "erro_aceites": erro_aceites,
        "modo_novo": True,
        "dados_anteriores": _dados_anteriores_ou_diretoria(usuario),
    }
    return render(request, "core/cadastro.html", contexto)


# Assinaturas do cadastro de diretoria: campo (name) no POST → documento + rótulo.
CAMPOS_ASSINATURA_DIRETORIA = [
    ("assinatura_compromisso", AssinaturaDocumentoDiretoria.DOC_COMPROMISSO, "o compromisso de voluntário"),
    ("assinatura_medica_dir", AssinaturaDocumentoDiretoria.DOC_DECLARACAO_MEDICA, "a declaração médica"),
    ("assinatura_imagem_dir", AssinaturaDocumentoDiretoria.DOC_AUTORIZACAO_IMAGEM, "a autorização de uso de imagem"),
]


def _validar_aceites_diretoria(request):
    """Exige a assinatura desenhada dos três documentos da diretoria."""
    erros = []
    for campo, _doc, rotulo in CAMPOS_ASSINATURA_DIRETORIA:
        if not _decode_signature(request.POST.get(campo, "")):
            erros.append(f"É necessário assinar {rotulo}.")
    return erros


def _salvar_assinaturas_diretoria(membro_obj, request):
    """Cria os três AssinaturaDocumentoDiretoria (imagem + snapshot do termo)."""
    for campo, doc, _rotulo in CAMPOS_ASSINATURA_DIRETORIA:
        imagem_assinatura = _decode_signature(request.POST.get(campo, ""))
        if imagem_assinatura is None:
            continue
        titulo, texto = termos.montar_texto_diretoria(doc, membro_obj)
        AssinaturaDocumentoDiretoria.objects.create(
            membro=membro_obj,
            documento=doc,
            imagem=imagem_assinatura,
            titulo_documento=titulo,
            texto_documento=texto,
            assinante_nome=membro_obj.nome_completo,
            assinante_cpf=membro_obj.cpf,
        )


def cadastro_diretoria_view(request):
    """Cadastro de diretoria (ficha "Compromisso para Voluntários").

    Cria a conta + o `MembroDiretoria` + a ficha médica, vincula ao perfil
    "Diretoria" e loga. Com `?com_aventureiro=1`, emenda no cadastro de
    aventureiro (resultando em 1 login com 2 perfis: Diretoria + Responsável)."""
    com_aventureiro = (
        request.GET.get("com_aventureiro") == "1"
        or request.POST.get("com_aventureiro") == "1"
    )
    conta = ContaForm(request.POST or None, prefix="conta")
    if request.method == "POST":
        membro = MembroDiretoriaForm(request.POST, request.FILES, prefix="dir")
        medica = FichaMedicaDiretoriaForm(request.POST, prefix="med")
    else:
        membro = MembroDiretoriaForm(prefix="dir")
        medica = FichaMedicaDiretoriaForm(prefix="med")
    erro_aceites = []

    if request.method == "POST":
        formularios_ok = all([conta.is_valid(), membro.is_valid(), medica.is_valid()])
        erro_aceites = _validar_aceites_diretoria(request)

        if formularios_ok and not erro_aceites:
            with transaction.atomic():
                usuario = User.objects.create_user(
                    username=conta.cleaned_data["username"],
                    password=conta.cleaned_data["senha"],
                )
                grupo, _ = Group.objects.get_or_create(name="Diretoria")
                usuario.groups.add(grupo)

                membro_obj = membro.save(commit=False)
                membro_obj.usuario = usuario
                membro_obj.compromisso_aceito = True
                membro_obj.declaracao_medica_aceita = True
                membro_obj.autorizacao_imagem_aceita = True
                membro_obj.save()

                ficha = medica.save(commit=False)
                ficha.membro = membro_obj
                ficha.save()

                _salvar_assinaturas_diretoria(membro_obj, request)

            login(request, usuario, backend=BACKEND_PADRAO)
            request.session[SESSAO_USUARIO_ID] = usuario.pk
            request.session[SESSAO_ULTIMO_NOME] = membro_obj.nome_completo
            if com_aventureiro:
                messages.success(
                    request,
                    "Cadastro de diretoria concluído! Agora cadastre o aventureiro.",
                )
                return redirect("core:cadastro_novo_aventureiro")
            request.session["cadastro_tipo"] = "diretoria"
            return redirect("core:cadastro_sucesso")

    contexto = {
        "conta_form": conta,
        "membro_form": membro,
        "medica_form": medica,
        "erro_aceites": erro_aceites,
        "com_aventureiro": com_aventureiro,
    }
    return render(request, "core/cadastro_diretoria.html", contexto)


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
        .prefetch_related("assinaturas")
        .filter(demo=False)   # aventureiros fictícios (demo) não entram na tela Usuários
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
        _preparar_assinaturas(av)

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
def aventureiro_termos_view(request, pk):
    """Termos assinados de um aventureiro (só Diretor): monta cada termo com o
    texto preenchido no momento da assinatura e a imagem da assinatura. Página
    pronta para impressão (o navegador salva em PDF)."""
    av = get_object_or_404(Aventureiro, pk=pk)
    assinaturas = list(av.assinaturas.all())
    # Mantém a ordem lógica dos documentos (inscrição → médica → imagem).
    ordem = {
        AssinaturaDocumento.DOC_INSCRICAO: 0,
        AssinaturaDocumento.DOC_DECLARACAO_MEDICA: 1,
        AssinaturaDocumento.DOC_AUTORIZACAO_IMAGEM: 2,
    }
    assinaturas.sort(key=lambda a: ordem.get(a.documento, 9))
    contexto = {
        "aventureiro": av,
        "assinaturas": assinaturas,
    }
    return render(request, "core/aventureiro_termos.html", contexto)


@diretor_required
def eventos_view(request):
    """Lista os eventos do clube. Restrito ao perfil Diretor."""
    eventos = list(Evento.objects.filter(demo=False))   # eventos fictícios (demo) ficam de fora
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
    # Taxa do gateway (Mercado Pago) deste evento: soma sobre os Pagamentos DISTINTOS
    # ligados às inscrições/pedidos confirmados (uma inscrição e o pedido de lojinha
    # que veio junto compartilham o MESMO Pagamento — o set evita contagem dupla).
    pag_ids = {i.pagamento_id for i in confirmadas if i.pagamento_id}
    pag_ids |= {p.pagamento_id for p in pedidos_confirmados if p.pagamento_id}
    taxa_total = (
        Pagamento.objects.filter(id__in=pag_ids, status="aprovado").aggregate(
            t=Sum("taxa"))["t"] or Decimal("0")
    ) if pag_ids else Decimal("0")
    resultado = receitas - total_custos - taxa_total
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
    for pg in Pagamento.objects.filter(id__in=pag_ids, status="aprovado").exclude(taxa=0):
        extrato.append({
            "data": pg.pago_em or pg.criado_em, "tipo": "Taxa Mercado Pago",
            "codigo": "", "descricao": pg.get_forma_display(), "forma": "", "canal": "",
            "valor": pg.taxa, "entrada": False, "cancelado": False,
        })
    extrato.sort(key=lambda x: x["data"], reverse=True)

    return {
        "arrecadacao_inscricoes": arrecadacao_inscricoes,
        "vendas_loja": vendas_loja,
        "receitas": receitas,
        "custos": total_custos,
        "taxa": taxa_total,
        "saidas_total": total_custos + taxa_total,
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
        Aventureiro.objects.filter(ativo=True, demo=False).order_by("nome_completo")
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
            "taxa": financeiro["taxa"],
            "resultado": receitas - total_custos - financeiro["taxa"],
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
            # Serializa tudo o que foi validado (responsável + participantes com
            # preço já calculado/descontado + respostas + cupons + lojinha) para
            # criar a inscrição agora (grátis/sem MP) ou na aprovação do Pix.
            desc_por_p = {id(p): (c.codigo, d) for c, p, d in aplicados}
            participantes_payload = []
            for p, linha in dados:
                cod, desc = desc_por_p.get(id(p), ("", Decimal("0")))
                participantes_payload.append({
                    "nome": p.nome, "idade": p.idade, "diretoria": p.eh_diretoria,
                    "faixa_id": p.faixa_id, "valor": str(p.valor),
                    "campos": [
                        {"campo_id": c["campo"].id, "texto": c["texto"]}
                        for c in linha["campos"]
                    ],
                    "cupom_codigo": cod, "cupom_desconto": str(desc),
                })
            payload = {
                "evento_id": evento.id,
                "responsavel": {
                    "nome": form.cleaned_data["responsavel_nome"],
                    "whatsapp": form.cleaned_data["responsavel_whatsapp"],
                    "email": form.cleaned_data["responsavel_email"],
                    "cpf": form.cleaned_data["responsavel_cpf"],
                },
                "participantes": participantes_payload,
                "campos_extra": [
                    {"campo_id": campo.id, "texto": form.resposta_texto(campo, nome)}
                    for campo, nome in form.campos_extra
                ],
                "loja_itens": [[v.id, qtd] for v, qtd in desejados_loja],
            }
            inscr_total = sum((p.valor for p, _ in dados), Decimal("0"))
            loja_total = sum((v.valor * qtd for v, qtd in desejados_loja), Decimal("0"))
            grand_total = inscr_total + loja_total

            config = _mp_config()
            if config.configurado and grand_total > 0:
                itens_disp = [
                    {"nome": p.nome or "Participante", "valor": str(p.valor)}
                    for p, _ in dados
                ]
                itens_disp += [
                    {"nome": f"{qtd}× {v.produto.nome}"
                             + (f" ({v.nome})" if v.nome else ""),
                     "valor": str(v.valor * qtd)}
                    for v, qtd in desejados_loja
                ]
                payload["titulo"] = f"Inscrição — {evento.nome}"
                payload["itens"] = itens_disp
                comprador_pg = {"nome": form.cleaned_data["responsavel_nome"],
                                "email": form.cleaned_data["responsavel_email"]}
                forma_inscr = request.POST.get("forma_pagamento") or "pix"
                if forma_inscr == "cartao":
                    pagamento, init_point, erro = _criar_pagamento_cartao(
                        request, tipo="inscricao", valor=grand_total,
                        descricao=f"Inscrição — {evento.nome}", payload=payload,
                        comprador=comprador_pg, usuario=request.user,
                    )
                    if erro:
                        messages.error(request, f"Não foi possível iniciar o cartão: {erro}")
                    else:
                        return redirect(init_point)
                else:
                    pagamento, erro = _criar_pagamento_pix(
                        request, tipo="inscricao", valor=grand_total,
                        descricao=f"Inscrição — {evento.nome}", payload=payload,
                        comprador=comprador_pg, usuario=request.user,
                    )
                    if erro:
                        messages.error(request, f"Não foi possível gerar o Pix: {erro}")
                    else:
                        return redirect("core:pagamento", ref=pagamento.referencia)
            else:
                with transaction.atomic():
                    inscricao = _criar_inscricao_de_payload(evento, payload, request.user)
                request.session["inscricao_codigo"] = inscricao.codigo
                return redirect("core:evento_inscricao_sucesso", pk=evento.pk)
        else:
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
        "mp_configurado": _mp_config().configurado,
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
    config = _mp_config()

    # Pix com Mercado Pago configurado → cobrança real (QR do MP + webhook).
    if forma == "pix" and config.configurado:
        return _evento_pagamento_pix_mp(
            request, evento, dados, comprador, itens_resumo, total, config
        )

    # Cartão com Mercado Pago configurado → Checkout Pro (redireciona ao MP).
    if forma == "cartao" and config.configurado:
        pagamento, init_point, erro = _criar_pagamento_cartao(
            request, tipo="loja_evento", valor=total,
            descricao=f"Lojinha — {evento.nome}",
            payload={"evento_id": evento.id, "itens": dados["itens"], "comprador": comprador},
            comprador=comprador, usuario=request.user,
        )
        if erro:
            messages.error(request, f"Não foi possível iniciar o pagamento no cartão: {erro}")
            return redirect("core:evento_loja", pk=evento.pk)
        request.session.pop("loja_checkout", None)
        return redirect(init_point)

    # Fluxo SIMULADO (sem MP configurado, ou cartão): comportamento anterior.
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


def _evento_pagamento_pix_mp(request, evento, dados, comprador, itens_resumo, total, config):
    """Tela de pagamento Pix com cobrança REAL no Mercado Pago. Reaproveita o
    `Pagamento` pendente do checkout (na sessão) para não gerar um QR novo a cada
    recarregamento. O pedido só nasce quando o pagamento é aprovado (webhook)."""
    ref = dados.get("pagamento_ref")
    pagamento = Pagamento.objects.filter(referencia=ref).first() if ref else None
    erro_pix = ""
    if pagamento is None or pagamento.status in ("rejeitado", "cancelado", "expirado"):
        pagamento, erro_pix = _criar_pagamento_pix(
            request,
            tipo="loja_evento",
            valor=total,
            descricao=f"Lojinha — {evento.nome}",
            payload={
                "evento_id": evento.id,
                "itens": dados["itens"],
                "comprador": comprador,
            },
            comprador=comprador,
            usuario=request.user,
        )
        if not erro_pix:
            dados["pagamento_ref"] = pagamento.referencia
            request.session["loja_checkout"] = dados
            request.session.modified = True

    # Se já foi aprovado (o webhook pode ter chegado antes do recarregamento), vai
    # direto para o sucesso.
    if pagamento and pagamento.status == "aprovado" and pagamento.finalizado:
        request.session.pop("loja_checkout", None)
        return redirect(_sucesso_url_e_sessao(request, pagamento))

    contexto = {
        "evento": evento,
        "comprador": comprador,
        "forma": "pix",
        "forma_nome": "Pix",
        "itens_resumo": itens_resumo,
        "total": total,
        "pagamento": pagamento,
        "erro_pix": erro_pix,
        "is_teste": config.is_teste,
        "qr_base64": pagamento.qr_code_base64 if pagamento else "",
        "pix_codigo": pagamento.qr_code if pagamento else "",
        "status_url": reverse("core:pagamento_status", args=[pagamento.referencia]) if pagamento else "",
        "simular_url": reverse("core:pagamento_simular", args=[pagamento.referencia]) if pagamento else "",
    }
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
@login_required
def presenca_view(request):
    """Tela "Presença". O Diretor escolhe o evento para marcar presença; o
    Responsável (ou o Diretor em modo preview) vê o relatório só-leitura dos
    próprios filhos (`_presenca_responsavel`)."""
    if atua_como_responsavel(request):
        return _presenca_responsavel(request)
    eventos = list(Evento.objects.filter(demo=False))   # eventos fictícios (demo) ficam de fora
    for e in eventos:
        e.qtd_presentes = e.presencas.count()
    return render(request, "core/presenca_selecionar.html", {"eventos": eventos})


def _presenca_responsavel(request):
    """Relatório de presença (só-leitura) dos aventureiros do RESPONSÁVEL: por
    filho, em quantos eventos com chamada esteve/faltou e em quais. Considera
    só eventos que tiveram chamada (≥1 presença marcada)."""
    aventureiros = list(
        Aventureiro.objects.filter(usuario=request.user, ativo=True).order_by("nome_completo")
    )
    # Casa a "demo-ness": família fictícia (demo) só considera eventos fictícios;
    # família real só considera eventos reais — assim os dados de teste não se
    # misturam com os do clube (nem aparecem como "falta" para responsáveis reais).
    sao_demo = any(av.demo for av in aventureiros)
    eventos_chamada = list(
        Evento.objects.filter(presencas__isnull=False, demo=sao_demo).distinct()
        .order_by("-data", "-horario_inicio")
    )
    presentes = set(
        PresencaEvento.objects.filter(
            aventureiro__in=aventureiros, evento__in=eventos_chamada
        ).values_list("aventureiro_id", "evento_id")
    )
    total = len(eventos_chamada)
    relatorio = []
    for av in aventureiros:
        foi, faltou = [], []
        for e in eventos_chamada:
            (foi if (av.id, e.id) in presentes else faltou).append(e)
        relatorio.append({
            "aventureiro": av,
            "foto_ok": _foto_valida(av),
            "iniciais": _iniciais(av.nome_completo),
            "total": total,
            "n_foi": len(foi),
            "n_faltou": len(faltou),
            "pct": int(round(len(foi) / total * 100)) if total else 0,
            "foi": foi,
            "faltou": faltou,
        })
    contexto = {
        "relatorio": relatorio,
        "tem_aventureiros": bool(aventureiros),
        "tem_chamada": total > 0,
        "n_eventos": total,
    }
    return render(request, "core/presenca_responsavel.html", contexto)


@login_required
@require_POST
def trocar_perfil_view(request):
    """Troca o perfil ATIVO do usuário (seletor no menu). Só aceita perfis que o
    usuário realmente possui — muda o menu e as telas. Volta para "Meus Dados"."""
    perfil = (request.POST.get("perfil") or "").strip()
    if perfil in perfis_do_usuario(request.user):
        request.session[PERFIL_ATIVO_KEY] = perfil
        messages.info(request, f"Você está usando o sistema como {perfil}.")
    return redirect("core:inicio")


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
        Aventureiro.objects.filter(ativo=True, demo=False).order_by("nome_completo")
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
    tipo = request.session.pop("cadastro_tipo", "aventureiro")
    pode_cadastrar_outro = (
        request.user.is_authenticated
        or bool(request.session.get(SESSAO_USUARIO_ID))
    )
    contexto = {
        "nome_aventureiro": request.session.get(SESSAO_ULTIMO_NOME),
        "pode_cadastrar_outro": pode_cadastrar_outro,
        "tipo": tipo,
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
    """Tela do módulo WhatsApp (só Diretor): abas Configurações (instância + teste)
    e Grupos (lista de grupos da conta, vínculo ID↔nome)."""
    config = WhatsappConfig.get_solo()
    liberacao = _liberacao_lista()
    liberados = sum(1 for x in liberacao if x["ultima_msg_em"] or x["autorizou"])
    autorizados = sum(1 for x in liberacao if x["autorizou"])
    reengajar_alvos = _inativos_para_reengajar(config)
    return render(request, "core/whatsapp.html", {
        "config": config,
        "grupos": list(GrupoWhatsapp.objects.all()),
        "webhook_url": _webhook_whatsapp_url(request),
        "mensagem_autorizacao": config.mensagem_autorizacao,
        "resposta_autorizacao": config.resposta_autorizacao,
        "wa_link_autorizacao": _wa_link_autorizacao(config),
        # Link curto/branded (redireciona pro wa.me) — melhor para compartilhar.
        "link_autorizar_curto": request.build_absolute_uri(reverse("core:autorizar")),
        "liberacao": liberacao,
        "liberacao_total": len(liberacao),
        "liberacao_liberados": liberados,
        "liberacao_autorizados": autorizados,
        "reengajar_dias": config.reengajar_dias,
        "mensagem_reengajamento": config.mensagem_reengajamento,
        "reengajar_alvos": reengajar_alvos,
        "reengajar_inativos_n": len(reengajar_alvos),
        "aba": request.GET.get("aba", "config"),
    })


def _liberacao_lista():
    """Todos os contatos que o clube pode precisar acionar (responsáveis + diretoria),
    com o status de contato (última mensagem / autorização). Uma linha por conta de
    responsável e uma por membro da diretoria (ativos, não-demo)."""
    itens = []
    contas = {}
    for av in (
        Aventureiro.objects.filter(usuario__isnull=False, ativo=True, demo=False)
        .select_related("usuario")
    ):
        contas.setdefault(av.usuario_id, av.usuario)
    for u in contas.values():
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=u)
        _, numero = _resolver_origem_numero(_numeros_conta(u), perfil.cobranca_whatsapp_origem or "")
        resp_nome, _ = _responsavel_da_familia(u)
        itens.append({
            "tipo": "Responsável", "nome": resp_nome, "numero": numero,
            "usuario_id": u.id,
            "autorizou": bool(perfil.autorizacao_recebida_em),
            "ultima_msg_em": perfil.ultima_msg_whatsapp_em,
            "reengajado_em": perfil.reengajado_em,
        })
    for m in MembroDiretoria.objects.filter(ativo=True, demo=False).select_related("usuario"):
        perfil = None
        if m.usuario_id:
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=m.usuario)
        itens.append({
            "tipo": "Diretoria", "nome": m.nome_completo, "numero": normalizar_telefone(m.whatsapp),
            "usuario_id": m.usuario_id,
            "autorizou": bool(perfil and perfil.autorizacao_recebida_em),
            "ultima_msg_em": perfil.ultima_msg_whatsapp_em if perfil else None,
            "reengajado_em": perfil.reengajado_em if perfil else None,
        })
    itens.sort(key=lambda x: (x["tipo"], (x["nome"] or "").lower()))
    return itens


def _inativos_para_reengajar(config, agora=None):
    """Contatos a reengajar. Critérios (uma entrada por conta):
    - JÁ interagiram alguma vez (têm última msg) — cold (nunca mandou) NÃO entra
      (mandar para quem nunca interagiu é o que causa bloqueio);
    - estão calados há pelo menos `reengajar_dias`;
    - e **ainda não foram reengajados desde a última mensagem deles** — ou seja,
      manda **uma vez só** por período de silêncio. Se a pessoa não responder, NÃO
      insiste; só volta a ser elegível se ela mandar mensagem de novo (e depois
      ficar calada outra vez)."""
    agora = agora or timezone.now()
    limite = agora - datetime.timedelta(days=config.reengajar_dias or 30)
    vistos, alvos = set(), []
    for p in _liberacao_lista():
        uid = p["usuario_id"]
        if not uid or uid in vistos or not p["numero"]:
            continue
        ultima = p["ultima_msg_em"]
        if not ultima or ultima >= limite:
            continue  # nunca interagiu, ou respondeu recentemente
        reeng = p["reengajado_em"]
        if reeng and reeng >= ultima:
            continue  # já reengajado desde a última msg dele → não insiste
        vistos.add(uid)
        alvos.append({"usuario_id": uid, "nome": p["nome"], "numero": p["numero"]})
    return alvos


# Intervalo entre envios em lote (evita parecer spam). Mesmo padrão da cobrança.
DELAY_ENVIO_LOTE_S = 10


def _numero_do_contato(user):
    """Número de WhatsApp para acionar esta conta: o de cobrança (se responsável)
    ou o da diretoria. Normalizado (ou "")."""
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
    if Aventureiro.objects.filter(usuario=user, ativo=True, demo=False).exists():
        _, num = _resolver_origem_numero(_numeros_conta(user), perfil.cobranca_whatsapp_origem or "")
        if num:
            return num
    m = MembroDiretoria.objects.filter(usuario=user, ativo=True, demo=False).first()
    if m:
        return normalizar_telefone(m.whatsapp)
    return ""


def _reengajar_um(config, usuario_id):
    """Manda a mensagem de reengajamento a UMA conta e marca `reengajado_em`.
    Retorna (ok, detalhe)."""
    msg = (config.mensagem_reengajamento or "").strip()
    if not msg:
        return False, "mensagem de reengajamento vazia"
    user = User.objects.filter(id=usuario_id).first()
    if user is None:
        return False, "conta não encontrada"
    numero = _numero_do_contato(user)
    if not numero:
        return False, "sem WhatsApp"
    ok, detalhe = _enviar_whatsapp(config, numero, msg)
    if ok:
        PerfilUsuario.objects.filter(usuario=user).update(reengajado_em=timezone.now())
    return ok, detalhe


def _reengajar_inativos(config):
    """Reengaja todos os inativos, com **pausa** entre envios (usado pelo comando de
    cron, que pode dormir sem estourar timeout). Retorna (enviados, falhas)."""
    if not (config.mensagem_reengajamento or "").strip() or not config.configurado:
        return 0, []
    enviados, falhas = 0, []
    for i, a in enumerate(_inativos_para_reengajar(config)):
        if i:
            time.sleep(DELAY_ENVIO_LOTE_S)
        ok, detalhe = _reengajar_um(config, a["usuario_id"])
        if ok:
            enviados += 1
        else:
            falhas.append(f"{a['nome']}: {detalhe}")
    return enviados, falhas


def _wa_link_autorizacao(config):
    """Monta o link wa.me com a mensagem de autorização pronta (ou "" se faltar
    número do clube ou mensagem)."""
    numero = normalizar_telefone(config.numero_clube)
    if numero and config.mensagem_autorizacao:
        return f"https://wa.me/{numero}?text={urllib.parse.quote(config.mensagem_autorizacao)}"
    return ""


def autorizar_view(request):
    """Link curto PÚBLICO (`/autorizar/`): redireciona para o wa.me de autorização.
    Curto e com a marca do clube — o que se compartilha; o wa.me fica escondido."""
    link = _wa_link_autorizacao(WhatsappConfig.get_solo())
    if not link:
        return HttpResponse(
            "Link de autorização ainda não configurado.",
            content_type="text/plain; charset=utf-8", status=503,
        )
    return redirect(link)


@diretor_required
@require_POST
def whatsapp_grupos_sync_view(request):
    """Sincroniza a lista de grupos da W-API para o banco (upsert por ID). Devolve
    JSON com a lista atualizada (sem recarregar a página)."""
    config = WhatsappConfig.get_solo()
    if not config.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Configure a instância do WhatsApp antes de buscar os grupos."},
            status=400,
        )
    ok, resultado = wapi.listar_grupos(config)
    if not ok:
        return JsonResponse({"ok": False, "erro": resultado}, status=502)
    vistos = set()
    for g in resultado:
        vistos.add(g["group_id"])
        GrupoWhatsapp.objects.update_or_create(
            group_id=g["group_id"],
            defaults={"nome": g["nome"], "tamanho": g["tamanho"]},
        )
    # Remove os que não existem mais na conta (mantém os marcados p/ liberação).
    GrupoWhatsapp.objects.exclude(group_id__in=vistos).filter(usar_liberacao=False).delete()
    grupos = [
        {"group_id": x.group_id, "nome": x.nome, "tamanho": x.tamanho, "usar_liberacao": x.usar_liberacao}
        for x in GrupoWhatsapp.objects.all()
    ]
    return JsonResponse({"ok": True, "grupos": grupos, "total": len(grupos)})


def _webhook_whatsapp_url(request):
    """URL pública do webhook de mensagens recebidas (respeita o prefixo do VPS)."""
    return request.build_absolute_uri(reverse("core:whatsapp_webhook"))


def _norm_comparacao(texto):
    """Normaliza texto para comparação (minúsculas, sem acento, espaços colapsados)."""
    s = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _perfil_por_whatsapp(numero_recebido):
    """Acha o PerfilUsuario dono deste número — seja **responsável** (pai/mãe/resp de
    aventureiro ativo não-demo) ou **diretoria** (MembroDiretoria ativo não-demo).
    None se não encontrar."""
    alvo = normalizar_telefone(numero_recebido)
    if not alvo or len(alvo) < 12:
        return None
    for av in Aventureiro.objects.filter(usuario__isnull=False, ativo=True, demo=False):
        for attr in ("pai_whatsapp", "mae_whatsapp", "resp_whatsapp"):
            if normalizar_telefone(getattr(av, attr) or "") == alvo:
                perfil, _ = PerfilUsuario.objects.get_or_create(usuario=av.usuario)
                return perfil
    for m in MembroDiretoria.objects.filter(usuario__isnull=False, ativo=True, demo=False):
        if normalizar_telefone(m.whatsapp or "") == alvo:
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=m.usuario)
            return perfil
    return None


def _registrar_contato_whatsapp(numero, texto):
    """Registra que um responsável/diretor mandou mensagem (data da última) e, se o
    texto bate com a mensagem de autorização configurada, marca a autorização e
    responde com uma confirmação automática (uma vez só)."""
    perfil = _perfil_por_whatsapp(numero)
    if perfil is None:
        return
    cfg = WhatsappConfig.get_solo()
    agora = timezone.now()
    perfil.ultima_msg_whatsapp_em = agora
    campos = ["ultima_msg_whatsapp_em"]
    autorizou_agora = False
    esperado = _norm_comparacao(cfg.mensagem_autorizacao)
    if esperado and not perfil.autorizacao_recebida_em:
        recebido = _norm_comparacao(texto)
        if recebido and (esperado in recebido or recebido == esperado):
            perfil.autorizacao_recebida_em = agora
            campos.append("autorizacao_recebida_em")
            autorizou_agora = True
    perfil.save(update_fields=campos)
    # Resposta automática de confirmação — só na 1ª vez que a autorização é
    # reconhecida, e é uma RESPOSTA (a pessoa acabou de escrever), então é seguro.
    resposta = (cfg.resposta_autorizacao or "").strip()
    if autorizou_agora and cfg.configurado and resposta:
        try:
            _enviar_whatsapp(cfg, numero, resposta)
        except Exception:  # noqa: BLE001 — nunca derrubar o webhook
            pass


@diretor_required
@require_POST
def whatsapp_reengajar_config_view(request):
    """Salva a config de reengajamento (dias sem resposta + mensagem)."""
    config = WhatsappConfig.get_solo()
    try:
        dias = int(request.POST.get("reengajar_dias") or 0)
        if dias > 0:
            config.reengajar_dias = dias
    except (TypeError, ValueError):
        pass
    config.mensagem_reengajamento = (request.POST.get("mensagem_reengajamento") or "").strip()
    config.atualizado_por = request.user
    config.save(update_fields=["reengajar_dias", "mensagem_reengajamento", "atualizado_por", "atualizado_em"])
    messages.success(request, "Reengajamento salvo.")
    return redirect(reverse("core:whatsapp") + "?aba=liberacao")


@diretor_required
@require_POST
def whatsapp_reengajar_view(request):
    """Reengaja UMA conta (`usuario_id`) — o pacing (10s entre cada) é feito no
    front, um envio por vez, igual ao 'Enviar a todos' da cobrança."""
    config = WhatsappConfig.get_solo()
    if not config.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Configure a instância do WhatsApp antes."}, status=400
        )
    uid = request.POST.get("usuario_id")
    if not uid:
        return JsonResponse({"ok": False, "erro": "Conta não informada."}, status=400)
    ok, detalhe = _reengajar_um(config, uid)
    if ok:
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "erro": detalhe}, status=502)


@diretor_required
@require_POST
def whatsapp_autorizacao_config_view(request):
    """Salva a mensagem de autorização (o texto que o responsável deve enviar) e a
    resposta automática de confirmação."""
    config = WhatsappConfig.get_solo()
    config.mensagem_autorizacao = (request.POST.get("mensagem_autorizacao") or "").strip()
    config.resposta_autorizacao = (request.POST.get("resposta_autorizacao") or "").strip()
    config.atualizado_por = request.user
    config.save(update_fields=["mensagem_autorizacao", "resposta_autorizacao", "atualizado_por", "atualizado_em"])
    messages.success(request, "Mensagem de autorização salva.")
    return redirect(reverse("core:whatsapp") + "?aba=autorizacao")


@diretor_required
@require_POST
def whatsapp_webhook_config_view(request):
    """Cadastra a URL do nosso webhook na W-API (mensagens recebidas)."""
    config = WhatsappConfig.get_solo()
    if not config.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Configure a instância do WhatsApp primeiro."}, status=400
        )
    url = _webhook_whatsapp_url(request)
    ok, resultado = wapi.configurar_webhook_recebido(config, url)
    if not ok:
        return JsonResponse({"ok": False, "erro": resultado}, status=502)
    return JsonResponse({"ok": True, "url": url})


@diretor_required
def whatsapp_webhook_eventos_view(request):
    """Últimos eventos recebidos pelo webhook (para a atualização ao vivo na tela)."""
    eventos = [
        {
            "id": e.id,
            "event_type": e.event_type or "-",
            "phone": e.phone or "-",
            "contact_name": e.contact_name or "-",
            "message_text": e.texto_curto or "-",
            "from_me": e.from_me,
            "is_group": e.is_group,
            "recebido_em": timezone.localtime(e.recebido_em).strftime("%d/%m/%Y %H:%M:%S"),
        }
        for e in WhatsappWebhookEvent.objects.all()[:5]
    ]
    return JsonResponse({"ok": True, "eventos": eventos})


@csrf_exempt
@require_POST
def whatsapp_webhook_view(request):
    """Endpoint PÚBLICO que recebe as mensagens da W-API (mensagens recebidas).
    Faz parsing defensivo, ignora status/transmissão e guarda o evento (com o
    payload cru) para diagnóstico e para o módulo de liberação de números.
    Nunca expõe erro ao chamador."""
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, ValueError):
        payload = {}
    # Ignora atualizações de Status/transmissão (não são conversa).
    if wapi_parser.is_status_or_broadcast(payload):
        return JsonResponse({"ok": True, "ignorado": "status"})
    try:
        dados = wapi_parser.parse_webhook_payload(payload)
        WhatsappWebhookEvent.objects.create(
            raw_payload=payload if isinstance(payload, dict) else {}, **dados
        )
        # Rastreio de contato: mensagem DIRETA (não grupo) recebida de um responsável
        # marca a data da última mensagem e, se for o texto de autorização, a autorização.
        if not dados["from_me"] and not dados["is_group"] and dados["phone"]:
            _registrar_contato_whatsapp(dados["phone"], dados["message_text"])
        # Mantém a tabela enxuta (é só diagnóstico): guarda os 100 mais recentes.
        ids = list(
            WhatsappWebhookEvent.objects.values_list("id", flat=True)[100:]
        )
        if ids:
            WhatsappWebhookEvent.objects.filter(id__in=ids).delete()
    except Exception:  # noqa: BLE001 — nunca derrubar o webhook
        return JsonResponse({"ok": False}, status=200)
    return JsonResponse({"ok": True})


@diretor_required
@require_POST
def whatsapp_config_view(request):
    """Salva o ID da instância, o token e (opcional) a URL base da W-API.

    O token só é substituído se um novo for digitado — assim a tela pode
    exibir apenas os últimos dígitos sem apagar o token guardado."""
    config = WhatsappConfig.get_solo()
    novo_instance_id = (request.POST.get("instance_id") or "").strip()
    if novo_instance_id:
        config.instance_id = novo_instance_id
    base_url = (request.POST.get("base_url") or "").strip()
    if base_url:
        config.base_url = base_url
    novo_token = (request.POST.get("token") or "").strip()
    if novo_token:
        config.token = novo_token
    config.numero_clube = (request.POST.get("numero_clube") or "").strip()
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


# ===========================================================================
# Configurações IA (API do GPT / OpenAI) — só Diretor.
# ===========================================================================
@diretor_required
def ia_view(request):
    """Tela Configurações IA (só Diretor): guarda a chave da API do GPT e permite
    enviar um teste. O modelo é fixo (o mais barato) e a URL base não é
    configurável; a tela ainda mostra o consumo de tokens acumulado."""
    config = OpenAIConfig.get_solo()
    return render(request, "core/ia.html", {"config": config, "modelo": openai_ia.MODELO})


@diretor_required
@require_POST
def ia_config_view(request):
    """Salva a chave da API da OpenAI. A chave só é substituída se uma nova for
    digitada — assim a tela exibe apenas os últimos dígitos sem apagar a guardada."""
    config = OpenAIConfig.get_solo()
    nova_chave = (request.POST.get("api_key") or "").strip()
    if nova_chave:
        config.api_key = nova_chave
    config.atualizado_por = request.user
    config.save()
    messages.success(request, "Configuração da IA salva.")
    return redirect("core:ia")


@diretor_required
@require_POST
def ia_testar_view(request):
    """Envia um prompt de teste para a IA e devolve a resposta (JSON, sem
    recarregar a página). Contabiliza os tokens consumidos."""
    config = OpenAIConfig.get_solo()
    if not config.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Configure a chave da API antes de enviar."},
            status=400,
        )
    prompt = (request.POST.get("prompt") or "").strip()
    if not prompt:
        return JsonResponse({"ok": False, "erro": "Digite o texto do teste."}, status=400)
    ok, detalhe, uso = openai_ia.enviar_prompt(config, prompt)
    if ok:
        config.registrar_uso(uso)
        return JsonResponse({
            "ok": True, "resposta": detalhe, "modelo": openai_ia.MODELO,
            "uso": uso,
            "acumulado": {
                "chamadas": config.chamadas,
                "prompt": config.tokens_prompt,
                "cache": config.tokens_cache,
                "sem_cache": config.tokens_prompt_sem_cache,
                "completion": config.tokens_completion,
                "total": config.tokens_total,
            },
        })
    return JsonResponse({"ok": False, "erro": detalhe}, status=502)


@diretor_required
@require_POST
def ia_zerar_view(request):
    """Zera o contador de consumo de tokens."""
    config = OpenAIConfig.get_solo()
    config.zerar_uso()
    messages.success(request, "Contador de tokens zerado.")
    return redirect("core:ia")


# ===========================================================================
# Pagamentos online (Mercado Pago) — engine única reaproveitada nos 4 pontos.
#
# Fluxo: geramos um `Pagamento` (pendente) + a cobrança Pix no MP → o cliente paga
# → o Mercado Pago chama o WEBHOOK (ou, no modo teste, o botão "Simular aprovação")
# → marcamos aprovado, gravamos a TAXA REAL + o líquido, e "finalizamos" (criamos/
# baixamos o objeto pago conforme o `tipo`). O `payload` do Pagamento guarda o que
# está sendo pago, então o webhook sabe quem pagou e o quê sem depender da sessão.
# ===========================================================================
PIX_EXPIRA_MIN = 30  # validade do QR Pix, em minutos


def _mp_config():
    return MercadoPagoConfig.get_solo()


def _webhook_url(request):
    """URL absoluta do nosso webhook (respeita prefixo/HTTPS do proxy do VPS)."""
    try:
        return request.build_absolute_uri(reverse("core:mercadopago_webhook"))
    except Exception:  # noqa: BLE001
        return ""


def _criar_pagamento_pix(request, *, tipo, valor, descricao, payload,
                         comprador=None, usuario=None):
    """Cria um `Pagamento` (pendente) e a cobrança Pix no Mercado Pago.
    Retorna (pagamento, erro); `erro` != "" indica falha ao falar com o MP."""
    config = _mp_config()
    comprador = comprador or {}
    pagamento = Pagamento.objects.create(
        tipo=tipo,
        forma="pix",
        referencia=Pagamento.gerar_referencia(),
        modo=config.modo,
        valor_bruto=valor,
        payload=payload,
        usuario=usuario if (usuario and usuario.is_authenticated) else None,
    )
    resp = mp.criar_pix(
        config,
        referencia=pagamento.referencia,
        valor=valor,
        descricao=descricao,
        payer_email=comprador.get("email", ""),
        payer_nome=comprador.get("nome", ""),
        notification_url=_webhook_url(request),
        expira_minutos=PIX_EXPIRA_MIN,
    )
    if not resp.get("ok"):
        pagamento.status = "rejeitado"
        pagamento.detalhe = resp.get("erro", "")
        pagamento.save(update_fields=["status", "detalhe"])
        return pagamento, resp.get("erro", "Falha ao gerar o Pix.")
    pagamento.mp_payment_id = resp["mp_payment_id"]
    pagamento.status = resp["status"]
    pagamento.qr_code = resp["qr_code"]
    pagamento.qr_code_base64 = resp["qr_code_base64"]
    pagamento.ticket_url = resp["ticket_url"]
    pagamento.save(update_fields=[
        "mp_payment_id", "status", "qr_code", "qr_code_base64", "ticket_url",
    ])
    return pagamento, ""


def _grossar_cartao(config, valor):
    """Total a cobrar no cartão para o clube RECEBER `valor` líquido, repassando a
    taxa de intermediação ao cliente: cobrado = valor ÷ (1 − taxa%)."""
    taxa = (config.taxa_cartao_pct or Decimal("0")) / Decimal("100")
    if taxa <= 0 or taxa >= 1:
        return Decimal(valor).quantize(Decimal("0.01"))
    return (Decimal(valor) / (Decimal("1") - taxa)).quantize(Decimal("0.01"))


def _criar_pagamento_cartao(request, *, tipo, valor, descricao, payload,
                            comprador=None, usuario=None):
    """Cria um Pagamento (cartão) + a preferência do Checkout Pro e devolve
    (pagamento, init_point, erro). `valor` é o valor da VENDA (o clube recebe isso
    líquido); o cliente paga o valor "grossado" (venda ÷ (1 − taxa)) + juros de
    parcela (por conta dele, no MP). `valor_bruto` guarda a venda, então nos
    relatórios a taxa do clube fica ≈ 0 (repassada)."""
    config = _mp_config()
    comprador = comprador or {}
    cobrado = _grossar_cartao(config, valor)
    dados = dict(payload or {})
    dados["valor_cobrado"] = str(cobrado)
    pagamento = Pagamento.objects.create(
        tipo=tipo,
        forma="cartao",
        referencia=Pagamento.gerar_referencia(),
        modo=config.modo,
        valor_bruto=valor,
        payload=dados,
        usuario=usuario if (usuario and usuario.is_authenticated) else None,
    )
    # Volta para a nossa tela de acompanhamento (que confirma pelo webhook).
    retorno = request.build_absolute_uri(
        reverse("core:pagamento", args=[pagamento.referencia])
    )
    resp = mp.criar_preferencia(
        config,
        referencia=pagamento.referencia,
        valor=cobrado,
        descricao=descricao,
        payer_email=comprador.get("email", ""),
        payer_nome=comprador.get("nome", ""),
        notification_url=_webhook_url(request),
        back_sucesso=retorno,
        back_falha=retorno,
        max_parcelas=12,
    )
    if not resp.get("ok"):
        pagamento.status = "rejeitado"
        pagamento.detalhe = resp.get("erro", "")
        pagamento.save(update_fields=["status", "detalhe"])
        return pagamento, "", resp.get("erro", "Falha ao gerar a cobrança de cartão.")
    return pagamento, resp["init_point"], ""


def _aprovar_pagamento(pagamento, *, liquido=None):
    """Marca o Pagamento como aprovado e dispara a finalização. Idempotente.

    `taxa` (custo do clube) = valor_bruto − líquido que caiu no banco. No Pix, o
    clube absorve → taxa ≈ 1% (o bruto não muda). No cartão, o total é "grossado"
    para o cliente cobrir a taxa → o líquido volta a bater com o bruto → taxa ≈ 0.
    Assim o mesmo cálculo serve para os dois e reflete quem de fato pagou a taxa.
    `liquido=None` (simulação de teste, sem net real) → estima 1%."""
    if pagamento.finalizado:
        return
    if liquido is None:
        # Simulação de teste (sem net real do MP): estima o que o CLUBE arcaria.
        # Cartão → taxa repassada ao cliente → clube arca ≈ 0. Pix → clube absorve ~1%.
        if pagamento.forma == "cartao":
            taxa = Decimal("0.00")
        else:
            taxa = (pagamento.valor_bruto * Decimal("0.01")).quantize(Decimal("0.01"))
        liq = pagamento.valor_bruto - taxa
    else:
        liq = min(Decimal(str(liquido)), pagamento.valor_bruto)
        taxa = pagamento.valor_bruto - liq
    pagamento.status = "aprovado"
    pagamento.taxa = taxa
    pagamento.valor_liquido = liq
    pagamento.pago_em = timezone.now()
    with transaction.atomic():
        _finalizar_pagamento(pagamento)
        pagamento.finalizado = True
        pagamento.save()


def _finalizar_pagamento(pagamento):
    """Cria/baixa o objeto pago conforme o tipo (roda dentro de transação)."""
    if pagamento.tipo == "loja_evento":
        _finalizar_loja_evento(pagamento)
    elif pagamento.tipo == "mensalidade":
        _finalizar_mensalidade(pagamento)
    elif pagamento.tipo == "loja_clube":
        _finalizar_loja_clube(pagamento)
    elif pagamento.tipo == "inscricao":
        _finalizar_inscricao(pagamento)


def _finalizar_inscricao(pagamento):
    """Cria a Inscrição confirmada (+ participantes/respostas/lojinha/cupons) a
    partir do payload salvo, no momento da aprovação do Pix."""
    dados = pagamento.payload or {}
    evento = Evento.objects.filter(pk=dados.get("evento_id")).first()
    if evento is None:
        pagamento.detalhe = "Evento não encontrado ao finalizar o pagamento."
        return
    inscricao = _criar_inscricao_de_payload(evento, dados, pagamento.usuario, pagamento=pagamento)
    dados["inscricao_codigo"] = inscricao.codigo
    pagamento.payload = dados


def _criar_inscricao_de_payload(evento, payload, usuario, pagamento=None):
    """Cria a Inscrição (+ participantes, respostas, pedido de lojinha e marca os
    cupons) a partir do payload serializado. Usado na criação imediata (grátis / sem
    MP) e na finalização do Pix. Os preços já vêm no payload (com desconto de cupom
    aplicado no ato); os cupons são marcados aqui (uso único revalidado)."""
    resp = payload.get("responsavel", {})
    logado = usuario if (usuario and getattr(usuario, "is_authenticated", False)) else None
    inscricao = Inscricao(
        evento=evento,
        usuario=logado,
        responsavel_nome=resp.get("nome", ""),
        responsavel_whatsapp=resp.get("whatsapp", ""),
        responsavel_email=resp.get("email", ""),
        responsavel_cpf=resp.get("cpf", ""),
        codigo=Inscricao.gerar_codigo_unico(),
        status="confirmada",
        forma_pagamento=(pagamento.forma if pagamento else "online"),
        pagamento=pagamento,
    )
    inscricao.valor_total = sum(
        (Decimal(str(pl.get("valor") or "0")) for pl in payload.get("participantes", [])),
        Decimal("0"),
    )
    inscricao.save()
    for pl in payload.get("participantes", []):
        faixa = evento.faixas_preco.filter(pk=pl["faixa_id"]).first() if pl.get("faixa_id") else None
        p = ParticipanteInscricao(
            inscricao=inscricao, nome=pl.get("nome", ""), idade=pl.get("idade"),
            eh_diretoria=bool(pl.get("diretoria")), faixa=faixa,
            valor=Decimal(str(pl.get("valor") or "0")),
        )
        p.save()
        for c in pl.get("campos", []):
            campo = evento.campos_inscricao.filter(pk=c.get("campo_id")).first()
            if campo:
                RespostaInscricao.objects.create(
                    inscricao=inscricao, participante=p, campo=campo,
                    campo_rotulo=campo.rotulo, valor=c.get("texto", ""),
                )
        cod = pl.get("cupom_codigo")
        if cod:
            cupom = _buscar_cupom_valido(evento, cod)
            if cupom is not None:
                cupom.usado_em = timezone.now()
                cupom.inscricao = inscricao
                cupom.participante = p
                cupom.usado_por = p.nome or inscricao.responsavel_nome
                cupom.valor_desconto = Decimal(str(pl.get("cupom_desconto") or "0"))
                cupom.save(update_fields=[
                    "usado_em", "inscricao", "participante", "usado_por", "valor_desconto"
                ])
    for c in payload.get("campos_extra", []):
        campo = evento.campos_inscricao.filter(pk=c.get("campo_id")).first()
        if campo:
            RespostaInscricao.objects.create(
                inscricao=inscricao, campo=campo, campo_rotulo=campo.rotulo,
                valor=c.get("texto", ""),
            )
    # Itens da lojinha comprados junto (opcional).
    itens = payload.get("loja_itens", [])
    if itens:
        variacoes = {
            v.id: v for v in VariacaoProduto.objects.filter(
                produto__evento=evento
            ).select_related("produto")
        }
        desejados = [
            (variacoes[vid], qtd) for vid, qtd in itens
            if variacoes.get(vid) and qtd > 0
        ]
        if desejados:
            pedido = _criar_pedido(
                evento, desejados,
                {"nome": inscricao.responsavel_nome, "whatsapp": inscricao.responsavel_whatsapp,
                 "email": inscricao.responsavel_email},
                usuario=logado, inscricao=inscricao,
                forma_pagamento=(pagamento.forma if pagamento else "online"),
            )
            if pagamento and pedido is not None:
                pedido.pagamento = pagamento
                pedido.save(update_fields=["pagamento"])
    return inscricao


def _finalizar_loja_clube(pagamento):
    """Cria a CompraLoja da Loja do Clube a partir do carrinho salvo no payload."""
    dados = pagamento.payload or {}
    kits, total, _ = _loja_resolver_kits(dados.get("cart", []))
    if not kits:
        pagamento.detalhe = "Carrinho indisponível ao finalizar o pagamento."
        return
    compra = _criar_compra_loja(pagamento.usuario, kits, dados.get("comprador", {}), pagamento.forma)
    compra.pagamento = pagamento
    compra.save(update_fields=["pagamento"])
    dados["compra_codigo"] = compra.codigo
    pagamento.payload = dados


def _finalizar_mensalidade(pagamento):
    """Marca como pagas as mensalidades do payload (baixa múltipla de uma cobrança
    Pix só). Idempotente: só mexe nas que ainda estão em aberto."""
    dados = pagamento.payload or {}
    ids = dados.get("mensalidade_ids", [])
    qtd = 0
    for m in Mensalidade.objects.filter(pk__in=ids, status="aberta"):
        m.status = "paga"
        m.forma_pagamento = pagamento.forma
        m.valor_pago = m.valor
        m.pago_em = timezone.now()
        m.registrado_por = pagamento.usuario
        m.pagamento = pagamento
        m.save(update_fields=[
            "status", "forma_pagamento", "valor_pago", "pago_em",
            "registrado_por", "pagamento",
        ])
        qtd += 1
    dados["quitadas"] = qtd
    pagamento.payload = dados


def _finalizar_loja_evento(pagamento):
    """Cria o PedidoLoja da lojinha de evento a partir do payload do pagamento."""
    dados = pagamento.payload or {}
    evento = Evento.objects.filter(pk=dados.get("evento_id")).first()
    if evento is None:
        pagamento.detalhe = "Evento não encontrado ao finalizar o pagamento."
        return
    variacoes = {
        v.id: v for v in VariacaoProduto.objects.filter(
            produto__evento=evento
        ).select_related("produto")
    }
    desejados = []
    for vid, qtd in dados.get("itens", []):
        v = variacoes.get(vid)
        if v and qtd > 0:
            desejados.append((v, qtd))
    if not desejados:
        pagamento.detalhe = "Itens indisponíveis ao finalizar o pagamento."
        return
    pedido = _criar_pedido(
        evento, desejados, dados.get("comprador", {}),
        usuario=pagamento.usuario, forma_pagamento=pagamento.forma, origem="online",
    )
    pedido.pagamento = pagamento
    pedido.save(update_fields=["pagamento"])
    dados["pedido_codigo"] = pedido.codigo  # para a tela de sucesso achar o pedido
    pagamento.payload = dados


def _sucesso_url_e_sessao(request, pagamento):
    """Prepara a sessão para a tela de sucesso e devolve a URL de destino."""
    dados = pagamento.payload or {}
    if pagamento.tipo == "loja_evento":
        codigo = dados.get("pedido_codigo")
        if codigo:
            request.session["pedido_codigo"] = codigo
        return reverse("core:evento_pedido_sucesso", args=[dados.get("evento_id")])
    if pagamento.tipo == "loja_clube":
        codigo = dados.get("compra_codigo")
        if codigo:
            request.session["loja_compra_codigo"] = codigo
        request.session.pop("loja_clube_checkout", None)
        _loja_cart_save(request, [])
        return reverse("core:loja_sucesso")
    if pagamento.tipo == "inscricao":
        codigo = dados.get("inscricao_codigo")
        if codigo:
            request.session["inscricao_codigo"] = codigo
        return reverse("core:evento_inscricao_sucesso", args=[dados.get("evento_id")])
    # Demais tipos usam a tela de sucesso genérica (por referência do pagamento).
    return reverse("core:pagamento_sucesso", args=[pagamento.referencia])


# --------------------------- Configuração (Diretor) ---------------------------
@diretor_required
def mercadopago_view(request):
    """Tela de configuração do Mercado Pago (só Diretor): credenciais de teste e
    de produção, modo ativo e a URL do webhook para cadastrar no painel do MP."""
    config = MercadoPagoConfig.get_solo()
    # Termômetro do cartão: nas vendas de cartão, quanto o clube ACABOU arcando de
    # taxa (residual = bruto − líquido). Se o repasse estiver certo, fica ≈ 0. Se
    # > 0, a `taxa_cartao_pct` está baixa e vale aumentar.
    cartoes = Pagamento.objects.filter(forma="cartao", status="aprovado")
    n_cartao = cartoes.count()
    residual = cartoes.aggregate(t=Sum("taxa"))["t"] or Decimal("0")
    bruto_cartao = cartoes.aggregate(b=Sum("valor_bruto"))["b"] or Decimal("0")
    residual_pct = (residual / bruto_cartao * 100) if bruto_cartao else Decimal("0")
    return render(request, "core/mercadopago.html", {
        "config": config,
        "webhook_url": _webhook_url(request),
        "cartao_stats": {
            "n": n_cartao, "residual": residual, "residual_pct": residual_pct,
        },
    })


@diretor_required
@require_POST
def mercadopago_config_view(request):
    """Salva o modo e as credenciais. Cada segredo só é substituído se um novo for
    digitado (a tela mostra só os últimos dígitos, sem apagar o guardado)."""
    config = MercadoPagoConfig.get_solo()
    modo = request.POST.get("modo")
    if modo in dict(MercadoPagoConfig.MODO_CHOICES):
        config.modo = modo
    for campo in ("access_token_teste", "public_key_teste", "webhook_secret_teste",
                  "access_token_prod", "public_key_prod", "webhook_secret_prod"):
        novo = (request.POST.get(campo) or "").strip()
        if novo:
            setattr(config, campo, novo)
    taxa = (request.POST.get("taxa_cartao_pct") or "").strip().replace(",", ".")
    if taxa:
        try:
            config.taxa_cartao_pct = max(Decimal("0"), min(Decimal(taxa), Decimal("99")))
        except (InvalidOperation, ValueError):
            pass
    config.atualizado_por = request.user
    config.save()
    messages.success(request, "Configuração do Mercado Pago salva.")
    return redirect("core:mercadopago")


# ------------------------------- Webhook (público) ---------------------------
@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """Notificações do Mercado Pago (público). Valida a assinatura, consulta o
    pagamento no MP (fonte da verdade) e aprova/finaliza. Idempotente e tolerante
    (sempre responde rápido; erros de rede pedem retry)."""
    config = MercadoPagoConfig.get_solo()
    try:
        corpo = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (ValueError, TypeError):
        corpo = {}
    data_id = (
        request.GET.get("data.id") or request.GET.get("id")
        or str((corpo.get("data") or {}).get("id") or corpo.get("id") or "")
    )
    tipo_evt = (
        request.GET.get("type") or request.GET.get("topic")
        or corpo.get("type") or corpo.get("topic") or ""
    )
    # Só tratamos notificações de pagamento (ignora merchant_order etc.).
    if tipo_evt and "payment" not in tipo_evt:
        return JsonResponse({"ok": True, "ignorado": tipo_evt})

    assinatura_ok = mp.validar_assinatura(
        config,
        x_signature=request.headers.get("x-signature", ""),
        x_request_id=request.headers.get("x-request-id", ""),
        data_id=data_id,
    )
    if config.webhook_secret and not assinatura_ok:
        return JsonResponse({"ok": False, "erro": "assinatura inválida"}, status=401)
    if not data_id:
        return JsonResponse({"ok": True, "sem_id": True})

    info = mp.consultar_pagamento(config, data_id)
    if not info.get("ok"):
        # Não deu para consultar agora — 502 faz o MP tentar de novo depois.
        return JsonResponse({"ok": False, "erro": info.get("erro", "")}, status=502)

    ref = info.get("external_reference") or ""
    pagamento = (
        Pagamento.objects.filter(referencia=ref).first()
        or Pagamento.objects.filter(mp_payment_id=str(data_id)).first()
    )
    if pagamento is None:
        return JsonResponse({"ok": True, "desconhecido": True})

    pagamento.mp_payment_id = str(data_id)
    if info["status"] == "aprovado":
        _aprovar_pagamento(pagamento, liquido=info["liquido"])
    else:
        pagamento.status = info["status"]
        pagamento.save(update_fields=["status", "mp_payment_id"])
    return JsonResponse({"ok": True, "status": pagamento.status})


# ----------------------- Status (polling) e simulação -------------------------
def pagamento_status_view(request, ref):
    """JSON com o status do pagamento (a tela de pagamento faz polling nisto).
    Quando aprovado, devolve a URL de sucesso (e prepara a sessão)."""
    pagamento = get_object_or_404(Pagamento, referencia=ref)
    resposta = {"status": pagamento.status}
    if pagamento.status == "aprovado" and pagamento.finalizado:
        resposta["redirect"] = _sucesso_url_e_sessao(request, pagamento)
    return JsonResponse(resposta)


@require_POST
def pagamento_simular_view(request, ref):
    """Simula a aprovação (SÓ no modo teste): roda o mesmo caminho do webhook, com
    taxa estimada de 1%. Serve para testar o fluxo inteiro sem pagar um Pix real."""
    config = MercadoPagoConfig.get_solo()
    if not config.is_teste:
        return JsonResponse(
            {"ok": False, "erro": "Só disponível no modo teste."}, status=403
        )
    pagamento = get_object_or_404(Pagamento, referencia=ref)
    _aprovar_pagamento(pagamento)
    return JsonResponse(
        {"ok": True, "redirect": _sucesso_url_e_sessao(request, pagamento)}
    )


# ------------------- Página de pagamento e sucesso (genéricas) ----------------
def pagamento_view(request, ref):
    """Tela de pagamento Pix GENÉRICA (reaproveitável por qualquer `tipo`): QR do
    Mercado Pago + copia e cola + polling; no modo teste, botão de simular."""
    pagamento = get_object_or_404(Pagamento, referencia=ref)
    if pagamento.status == "aprovado" and pagamento.finalizado:
        return redirect(_sucesso_url_e_sessao(request, pagamento))
    config = _mp_config()
    dados = pagamento.payload or {}
    # Para onde voltar se o pagamento for recusado/cancelado (por tipo).
    if pagamento.tipo == "mensalidade":
        voltar = reverse("core:mensalidades")
    elif pagamento.tipo == "loja_clube":
        voltar = reverse("core:loja")
    elif pagamento.tipo in ("loja_evento", "inscricao") and dados.get("evento_id"):
        voltar = reverse("core:evento_pagina", args=[dados["evento_id"]])
    else:
        voltar = reverse("core:inicio")
    contexto = {
        "pagamento": pagamento,
        "titulo": dados.get("titulo") or pagamento.get_tipo_display(),
        "itens_resumo": dados.get("itens", []),
        "total": pagamento.valor_bruto,
        "is_teste": config.is_teste,
        "qr_base64": pagamento.qr_code_base64,
        "pix_codigo": pagamento.qr_code,
        "erro_pix": pagamento.detalhe if pagamento.status == "rejeitado" else "",
        "status_url": reverse("core:pagamento_status", args=[ref]),
        "simular_url": reverse("core:pagamento_simular", args=[ref]),
        "voltar_url": voltar,
    }
    return render(request, "core/pagamento.html", contexto)


def pagamento_sucesso_view(request, ref):
    """Tela de sucesso GENÉRICA (mostra o que foi pago a partir do payload)."""
    pagamento = get_object_or_404(Pagamento, referencia=ref)
    dados = pagamento.payload or {}
    voltar = reverse("core:mensalidades") if pagamento.tipo == "mensalidade" \
        else reverse("core:inicio")
    return render(request, "core/pagamento_sucesso.html", {
        "pagamento": pagamento,
        "titulo": dados.get("titulo") or pagamento.get_tipo_display(),
        "itens_resumo": dados.get("itens", []),
        "total": pagamento.valor_bruto,
        "voltar_url": voltar,
    })


# ------------------- Cobrança de mensalidades via Pix (Etapa 2) ---------------
@diretor_required
@require_POST
def mensalidade_cobrar_view(request):
    """Gera UMA cobrança Pix para as mensalidades selecionadas (baixa múltipla no
    webhook). Hoje disparada pelo Diretor para testar; a mesma engine servirá a
    futura tela do responsável (selecionar as em aberto → pagar → baixa tudo)."""
    config = _mp_config()
    if not config.configurado:
        messages.error(request, "Configure o Mercado Pago antes de cobrar via Pix.")
        return redirect("core:mensalidades")
    ids = request.POST.getlist("mensalidade_ids")
    mens = list(
        Mensalidade.objects.filter(pk__in=ids, status="aberta", isento=False)
        .select_related("aventureiro")
    )
    if not mens:
        messages.error(request, "Selecione ao menos uma mensalidade em aberto.")
        return redirect("core:mensalidades")
    # Segurança: todas devem ser do mesmo aventureiro (uma cobrança por pessoa).
    av = mens[0].aventureiro
    mens = [m for m in mens if m.aventureiro_id == av.id]
    total = sum((m.valor for m in mens), Decimal("0"))
    payload = {
        "mensalidade_ids": [m.id for m in mens],
        "aventureiro_id": av.id,
        "titulo": f"Mensalidades — {av.nome_completo}",
        "itens": [
            {"nome": f"{m.mes_nome}/{m.ano}"
                     + (" (inscrição)" if m.tipo == "inscricao" else ""),
             "valor": f"{m.valor:.2f}"}
            for m in mens
        ],
    }
    comprador = {"nome": av.resp_nome or av.nome_completo, "email": av.resp_email}
    if (request.POST.get("forma_pagamento") or "pix") == "cartao":
        pagamento, init_point, erro = _criar_pagamento_cartao(
            request, tipo="mensalidade", valor=total,
            descricao=f"Mensalidades — {av.nome_completo}", payload=payload,
            comprador=comprador, usuario=request.user,
        )
        if erro:
            messages.error(request, f"Não foi possível iniciar o cartão: {erro}")
            return redirect("core:mensalidades")
        return redirect(init_point)
    pagamento, erro = _criar_pagamento_pix(
        request, tipo="mensalidade", valor=total,
        descricao=f"Mensalidades — {av.nome_completo}", payload=payload,
        comprador=comprador, usuario=request.user,
    )
    if erro:
        messages.error(request, f"Não foi possível gerar o Pix: {erro}")
        return redirect("core:mensalidades")
    return redirect("core:pagamento", ref=pagamento.referencia)


# ---------------------------------------------------------------------------
# Cobranças de mensalidades por WhatsApp (aba "Cobranças" do Diretor).
# ---------------------------------------------------------------------------
def _moeda_txt(v):
    """Formata um Decimal como pt-BR (1.234,56) para a mensagem de texto."""
    s = f"{v:,.2f}"                       # 1,234.56
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _cobrancas_familias():
    """Famílias (contas) com mensalidades em aberto: dados para a aba Cobranças
    (responsável, total, WhatsApp, token do link e nº de cobranças enviadas no mês)."""
    hoje = timezone.localdate()
    abertas = (
        Mensalidade.objects.filter(
            status="aberta", isento=False, aventureiro__ativo=True, aventureiro__demo=False)
        .filter(_q_mens_vencidas())
        .select_related("aventureiro")
    )
    por_conta = defaultdict(list)
    for m in abertas:
        if m.aventureiro.usuario_id:
            por_conta[m.aventureiro.usuario_id].append(m)

    cont_mes = {
        e["usuario"]: e["n"]
        for e in CobrancaEnviada.objects.filter(ano=hoje.year, mes=hoje.month)
        .values("usuario").annotate(n=Count("id"))
    }
    users = {u.id: u for u in User.objects.filter(id__in=por_conta.keys())}
    familias = []
    for uid, mens in por_conta.items():
        u = users.get(uid)
        if u is None:
            continue
        resp_nome, _ = _responsavel_da_familia(u)
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=u)
        numeros = _numeros_conta(u)
        origem_atual, numero = _resolver_origem_numero(numeros, perfil.cobranca_whatsapp_origem or "")
        # Detalhe por criança (aventureiro): nome, total em aberto e meses.
        por_av = {}
        for m in mens:
            a = m.aventureiro
            c = por_av.setdefault(a.id, {"nome": a.nome_completo, "total": Decimal("0"), "meses": []})
            c["total"] += m.valor
            c["meses"].append(
                f"{m.mes_nome}/{m.ano}" + (" (inscrição)" if m.tipo == "inscricao" else "")
            )
        criancas = sorted(por_av.values(), key=lambda c: c["nome"])
        familias.append({
            "usuario_id": uid,
            "resp_nome": resp_nome,
            "primeiro_nome": (resp_nome or "").split(" ")[0],
            "total": sum((m.valor for m in mens), Decimal("0")),
            "n_mens": len(mens),
            "criancas": criancas,
            "numero": numero,
            "tem_numero": bool(numero),
            "numeros": numeros,
            "origem_atual": origem_atual,
            "ultima_msg_em": perfil.ultima_msg_whatsapp_em,
            "autorizou": bool(perfil.autorizacao_recebida_em),
            "cobrado_mes": cont_mes.get(uid, 0),
            "token": perfil.get_token_acerto(),
            "mensalidades": sorted(
                mens, key=lambda x: (x.aventureiro.nome_completo, x.ano, x.mes)
            ),
        })
    familias.sort(key=lambda f: (f["resp_nome"] or "").lower())
    return familias


def _montar_mensagem_cobranca(template, familia, request):
    """Interpola o template com os dados da família ({nome}/{itens}/{total}/{link})."""
    itens = "\n".join(
        f"• {m.aventureiro.nome_completo} — {m.mes_nome}/{m.ano}"
        + (" (inscrição)" if m.tipo == "inscricao" else "")
        + f": R$ {_moeda_txt(m.valor)}"
        for m in familia["mensalidades"]
    )
    link = request.build_absolute_uri(reverse("core:acerto", args=[familia["token"]]))
    return (
        (template or MENSAGEM_COBRANCA_PADRAO)
        .replace("{nome}", familia["primeiro_nome"] or "")
        .replace("{itens}", itens)
        .replace("{total}", _moeda_txt(familia["total"]))
        .replace("{link}", link)
    )


@diretor_required
@require_POST
def mensalidade_cobranca_config_view(request):
    """Salva o template da mensagem de cobrança (WhatsApp), o prompt da IA e a
    mensagem de apelo (exibida ao responsável na área de mensalidades dele)."""
    c = ConfigMensalidade.get_solo()
    c.mensagem_cobranca = (request.POST.get("mensagem_cobranca") or "").strip() or MENSAGEM_COBRANCA_PADRAO
    c.prompt_cobranca_ia = (request.POST.get("prompt_cobranca_ia") or "").strip() or PROMPT_COBRANCA_IA_PADRAO
    c.mensagem_apelo = (request.POST.get("mensagem_apelo") or "").strip() or MENSAGEM_APELO_PADRAO
    c.atualizado_por = request.user
    c.save()
    messages.success(request, "Mensagens salvas.")
    return redirect(reverse("core:mensalidades") + "?aba=cobrancas")


@diretor_required
@require_POST
def mensalidade_cobranca_modo_view(request):
    """Liga/desliga o modo IA da cobrança (a "alavanca"). Persiste na hora."""
    c = ConfigMensalidade.get_solo()
    c.cobranca_via_ia = request.POST.get("via_ia") == "1"
    c.atualizado_por = request.user
    c.save(update_fields=["cobranca_via_ia", "atualizado_por", "atualizado_em"])
    return JsonResponse({"ok": True, "via_ia": c.cobranca_via_ia})


@diretor_required
@require_POST
def mensalidade_cobranca_telefone_view(request):
    """Define qual WhatsApp (pai/mãe/resp legal) recebe a cobrança da família — o do
    RESPONSÁVEL FINANCEIRO, persistido em PerfilUsuario.cobranca_whatsapp_origem.
    É independente do WhatsApp principal (recuperação de senha). Fica salvo até
    trocar de novo."""
    usuario = get_object_or_404(User, pk=request.POST.get("usuario_id"))
    origem = (request.POST.get("origem") or "").strip()
    if origem not in {"pai", "mae", "resp"}:
        return JsonResponse({"ok": False, "erro": "Opção de WhatsApp inválida."}, status=400)
    numeros = {n["origem"]: n["numero"] for n in _numeros_conta(usuario)}
    numero = numeros.get(origem)
    if not numero:
        return JsonResponse(
            {"ok": False, "erro": "Esse responsável não tem WhatsApp cadastrado."}, status=400
        )
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    perfil.cobranca_whatsapp_origem = origem
    perfil.save(update_fields=["cobranca_whatsapp_origem"])
    return JsonResponse({"ok": True, "origem": origem, "numero": numero})


def _gerar_cobranca_ia(prompt_template, familia, request, ia_cfg):
    """Pede ao GPT a mensagem de cobrança personalizada da família. Reaproveita a
    interpolação dos marcadores ({nome}/{itens}/{total}/{link}) para montar o prompt.
    Retorna (ok, texto|erro); contabiliza os tokens no sucesso."""
    prompt = _montar_mensagem_cobranca(prompt_template, familia, request)
    ok, texto, uso = openai_ia.enviar_prompt(ia_cfg, prompt)
    if ok:
        ia_cfg.registrar_uso(uso)
        return True, texto
    return False, texto


@diretor_required
@require_POST
def mensalidade_cobranca_enviar_view(request):
    """Envia a cobrança por WhatsApp (uma família ou todas) e registra o histórico.
    A mensagem vem do template padrão ou é redigida pela IA (conforme a alavanca).
    Filtro opcional: só quem ainda não recebeu neste mês."""
    wa = WhatsappConfig.get_solo()
    if not wa.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Configure o WhatsApp antes de enviar cobranças."}, status=400
        )
    cfg = ConfigMensalidade.get_solo()
    via_ia = cfg.cobranca_via_ia
    template = cfg.mensagem_cobranca or MENSAGEM_COBRANCA_PADRAO
    prompt_ia = cfg.prompt_cobranca_ia or PROMPT_COBRANCA_IA_PADRAO
    ia_cfg = OpenAIConfig.get_solo()
    if via_ia and not ia_cfg.configurado:
        return JsonResponse(
            {"ok": False, "erro": "Modo IA ligado, mas a IA não está configurada. "
                                  "Configure em Configurações IA ou desligue o modo IA."},
            status=400,
        )
    alvo = request.POST.get("usuario_id")
    so_nao_enviados = request.POST.get("so_nao_enviados") == "1"
    hoje = timezone.localdate()

    familias = _cobrancas_familias()
    if alvo:
        familias = [f for f in familias if str(f["usuario_id"]) == str(alvo)]
    if so_nao_enviados:
        familias = [f for f in familias if not f["cobrado_mes"]]

    enviados = 0
    falhas = []
    for f in familias:
        if not f["tem_numero"]:
            falhas.append(f"{f['resp_nome']}: sem WhatsApp cadastrado")
            continue
        if via_ia:
            ok_ia, msg = _gerar_cobranca_ia(prompt_ia, f, request, ia_cfg)
            if not ok_ia:
                falhas.append(f"{f['resp_nome']}: IA falhou ({msg})")
                continue
        else:
            msg = _montar_mensagem_cobranca(template, f, request)
        ok, detalhe = _enviar_whatsapp(wa, f["numero"], msg)
        if ok:
            CobrancaEnviada.objects.create(
                usuario_id=f["usuario_id"], ano=hoje.year, mes=hoje.month,
                enviada_por=request.user,
            )
            enviados += 1
        else:
            falhas.append(f"{f['resp_nome']}: {detalhe}")
    return JsonResponse({"ok": True, "enviados": enviados, "falhas": falhas, "via_ia": via_ia})


# ---------------------------------------------------------------------------
# Página pública de ACERTO (link do WhatsApp de cobrança). Sem login: o token
# identifica a família; a página mostra o que está em aberto AGORA e a pessoa
# paga (Pix/cartão) — o Pix é gerado só no clique, então nada "vence" se ela
# demorar a abrir o link.
# ---------------------------------------------------------------------------
def _q_mens_vencidas():
    """Q das mensalidades já VENCIDAS (competência ≤ mês atual): cobra o mês atual e
    os meses anteriores em aberto, NUNCA meses à frente (o ano nasce todo gerado)."""
    hoje = timezone.localdate()
    return Q(ano__lt=hoje.year) | Q(ano=hoje.year, mes__lte=hoje.month)


def _mensalidades_abertas_familia(usuario):
    """Mensalidades VENCIDAS em aberto (não isentas) de todos os aventureiros da conta.
    Não inclui meses futuros (que ainda não venceram)."""
    return list(
        Mensalidade.objects.filter(
            aventureiro__usuario=usuario, status="aberta", isento=False
        ).filter(_q_mens_vencidas()).select_related("aventureiro").order_by(
            "aventureiro__nome_completo", "ano", "mes"
        )
    )


def _responsavel_da_familia(usuario):
    """(nome, email) do responsável da conta, a partir do 1º aventureiro."""
    av = Aventureiro.objects.filter(usuario=usuario).first()
    if av is None:
        return usuario.get_full_name() or usuario.username, ""
    return (av.resp_nome or av.nome_completo), (av.resp_email or "")


def acerto_view(request, token):
    """Página pública de acerto: mostra o que a família deve e permite pagar."""
    perfil = (
        PerfilUsuario.objects.filter(token_acerto=token).select_related("usuario").first()
        if token else None
    )
    if perfil is None:
        return render(request, "core/acerto.html", {"invalido": True})
    usuario = perfil.usuario
    mens = _mensalidades_abertas_familia(usuario)
    total = sum((m.valor for m in mens), Decimal("0"))
    resp_nome, _ = _responsavel_da_familia(usuario)
    return render(request, "core/acerto.html", {
        "token": token,
        "mensalidades": mens,
        "total": total,
        "resp_nome": resp_nome,
        "primeiro_nome": (resp_nome or "").split(" ")[0],
        "mp_configurado": _mp_config().configurado,
    })


@require_POST
def acerto_cobrar_view(request, token):
    """Gera a cobrança (Pix/cartão) de TODAS as mensalidades em aberto da família."""
    perfil = (
        PerfilUsuario.objects.filter(token_acerto=token).select_related("usuario").first()
        if token else None
    )
    if perfil is None:
        return redirect("core:login")
    usuario = perfil.usuario
    mens = _mensalidades_abertas_familia(usuario)
    if not mens:
        return redirect("core:acerto", token=token)
    total = sum((m.valor for m in mens), Decimal("0"))
    resp_nome, resp_email = _responsavel_da_familia(usuario)
    payload = {
        "mensalidade_ids": [m.id for m in mens],
        "titulo": f"Mensalidades — {resp_nome}",
        "itens": [
            {"nome": f"{m.aventureiro.nome_completo} · {m.mes_nome}/{m.ano}"
                     + (" (inscrição)" if m.tipo == "inscricao" else ""),
             "valor": f"{m.valor:.2f}"}
            for m in mens
        ],
    }
    comprador = {"nome": resp_nome, "email": resp_email}
    descricao = f"Mensalidades — {resp_nome}"
    if (request.POST.get("forma_pagamento") or "pix") == "cartao":
        pagamento, init_point, erro = _criar_pagamento_cartao(
            request, tipo="mensalidade", valor=total, descricao=descricao,
            payload=payload, comprador=comprador, usuario=usuario,
        )
        if erro:
            return redirect("core:acerto", token=token)
        return redirect(init_point)
    pagamento, erro = _criar_pagamento_pix(
        request, tipo="mensalidade", valor=total, descricao=descricao,
        payload=payload, comprador=comprador, usuario=usuario,
    )
    if erro:
        return redirect("core:acerto", token=token)
    return redirect("core:pagamento", ref=pagamento.referencia)


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


def _resolver_origem_numero(numeros, escolhido):
    """(origem_efetiva, número normalizado) dada a lista `numeros` de `_numeros_conta`
    e a origem `escolhido`. Se a escolhida tiver número usa ela; senão cai no
    responsável legal; senão "" (nenhum número disponível)."""
    mapa = {n["origem"]: n["numero"] for n in numeros}
    if escolhido and mapa.get(escolhido):
        origem = escolhido
    elif mapa.get("resp"):
        origem = "resp"
    else:
        origem = ""
    return origem, normalizar_telefone(mapa.get(origem) or "")


def _whatsapp_principal(usuario):
    """Número de WhatsApp principal da conta (para o código de recuperação de
    senha), **normalizado** (ou ""). É independente do WhatsApp de cobrança."""
    perfil = getattr(usuario, "perfil", None)
    escolhido = (perfil.whatsapp_principal_origem or "") if perfil is not None else ""
    return _resolver_origem_numero(_numeros_conta(usuario), escolhido)[1]


def _conta_por_cpf_resp(cpf):
    """Acha a conta (User) cujo **responsável legal** tem esse CPF. Prefere conta
    ativa. Devolve o User ou None."""
    alvo = _so_digitos(cpf)
    if len(alvo) != 11:
        return None
    achados = []
    for av in Aventureiro.objects.filter(usuario__isnull=False, demo=False).select_related("usuario"):
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


def _loja_resolver_kits(cart):
    """Resolve uma lista de carrinho (JSON) em kits (produto + itens) + total, e
    devolve também o carrinho "limpo" (sem itens/produtos indisponíveis). Puro: não
    toca na sessão — usado pelo carrinho (sessão) e pela finalização do Pix."""
    kits = []
    total = Decimal("0")
    novo = []
    for entry in cart or []:
        prod = (
            ProdutoLoja.objects.filter(pk=entry.get("produto_id"), ativo=True)
            .prefetch_related("grupos__variacoes").first()
        )
        if prod is None:
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
                continue
            st = v.valor * qtd
            subtotal += st
            itens.append({"variacao": v, "grupo": v.grupo, "qtd": qtd, "subtotal": st})
            itens_ok.append({"variacao_id": v.id, "qtd": qtd})
        if not itens:
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
    return kits, total, novo


def _loja_cart_detalhado(request):
    """Resolve o carrinho da SESSÃO em kits + total; descarta silenciosamente o que
    ficou indisponível, reescrevendo o carrinho (preserva a seleção válida)."""
    cart = _loja_cart(request)
    kits, total, novo = _loja_resolver_kits(cart)
    if novo != cart:
        _loja_cart_save(request, novo)
    return kits, total


# --- Telas da loja ---------------------------------------------------------
def _loja_responsavel(request):
    """Tela da Loja para o RESPONSÁVEL: só a vitrine (comprar) + "Meus pedidos"
    (acompanhar). Sem Gerenciar/Vendas. Reaproveita o carrinho e o pagamento."""
    produtos_ativos = list(
        ProdutoLoja.objects.filter(ativo=True)
        .prefetch_related("grupos__variacoes", "fotos")
    )
    kits, total = _loja_cart_detalhado(request)
    meus_pedidos = list(
        CompraLoja.objects.filter(usuario=request.user)
        .prefetch_related("itens").order_by("-criado_em")
    )
    contexto = {
        "produtos_ativos": produtos_ativos,
        "meus_pedidos": meus_pedidos,
        "cart_kits": kits,
        "cart_total": total,
        "comprador": _comprador_padrao(request.user),
        "formas_pagamento": FORMAS_PAGAMENTO_ONLINE,
        "aba": request.GET.get("aba", "loja"),
    }
    return render(request, "core/loja_responsavel.html", contexto)


@login_required
def loja_view(request):
    """Tela "Loja". O Diretor vê o painel completo (Gerenciar/Loja/Vendas); o
    Responsável (ou o Diretor em modo preview) vê só a vitrine + "Meus pedidos"."""
    if atua_como_responsavel(request):
        return _loja_responsavel(request)
    produtos = list(
        ProdutoLoja.objects.prefetch_related("grupos__variacoes", "fotos").all()
    )
    compras = list(
        CompraLoja.objects.prefetch_related("itens").select_related("usuario").all()
    )
    kits, total = _loja_cart_detalhado(request)
    relatorio = _loja_relatorio()
    custos_loja = list(CustoClube.objects.filter(destino="loja").prefetch_related("comprovantes"))
    custos_loja_total = sum((c.valor for c in custos_loja), Decimal("0"))
    # Taxa do gateway (Mercado Pago) nas vendas da loja (Pix/cartão aprovados).
    taxa_loja = Pagamento.objects.filter(tipo="loja_clube", status="aprovado").aggregate(
        t=Sum("taxa"))["t"] or Decimal("0")
    contexto = {
        "produtos": produtos,
        "produtos_ativos": [p for p in produtos if p.ativo],
        "compras": compras,
        "relatorio": relatorio,
        "custos_loja": custos_loja,
        "custos_loja_total": custos_loja_total,
        "taxa_loja": taxa_loja,
        "loja_resultado": relatorio["arrecadado"] - custos_loja_total - taxa_loja,
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

    # Relatório para o fornecedor: por produto → variação (tamanho/item), só o
    # que FALTA entregar (= o que precisa pedir ao fornecedor). Já entregue não entra.
    forn = {}
    for it in itens:
        if it.falta_entregar <= 0:
            continue
        prod = forn.setdefault(it.produto_nome, {
            "produto_nome": it.produto_nome, "vars": {}, "falta": 0,
        })
        rot = " · ".join(p for p in [it.grupo_nome, it.variacao_nome] if p) or "Único"
        v = prod["vars"].setdefault(rot, {"rotulo": rot, "falta": 0})
        v["falta"] += it.falta_entregar
        prod["falta"] += it.falta_entregar
    fornecedor = []
    for prod in forn.values():
        prod["variacoes"] = sorted(prod["vars"].values(), key=lambda x: x["rotulo"])
        prod.pop("vars")
        fornecedor.append(prod)
    fornecedor.sort(key=lambda x: x["produto_nome"])

    return {
        "n_compras": n_compras,
        "arrecadado": arrecadado,
        "ticket": ticket,
        "mais_vendidos": mais_vendidos,
        "por_forma": por_forma,
        "pendentes": pendentes,
        "unidades_a_entregar": unidades_a_entregar,
        "n_pendentes": len(pendentes),
        "fornecedor": fornecedor,
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
    config = _mp_config()

    # Pix com Mercado Pago configurado → cobrança real (usa a página genérica).
    if forma == "pix" and config.configurado:
        ref = dados.get("pagamento_ref")
        pagamento = Pagamento.objects.filter(referencia=ref).first() if ref else None
        if pagamento is None or pagamento.status in ("rejeitado", "cancelado", "expirado"):
            itens_disp = [
                {"nome": f'{it["qtd"]}× {kit["produto"].nome}'
                         + (f' ({it["variacao"].nome})' if it["variacao"].nome else ''),
                 "valor": f'{it["subtotal"]:.2f}'}
                for kit in kits for it in kit["itens"]
            ]
            pagamento, erro = _criar_pagamento_pix(
                request,
                tipo="loja_clube",
                valor=total,
                descricao="Loja do Clube",
                payload={
                    "cart": _loja_cart(request),
                    "comprador": comprador,
                    "titulo": "Loja do Clube",
                    "itens": itens_disp,
                },
                comprador=comprador,
                usuario=request.user,
            )
            if erro:
                messages.error(request, f"Não foi possível gerar o Pix: {erro}")
                return redirect(reverse("core:loja") + "?aba=loja#carrinho")
            dados["pagamento_ref"] = pagamento.referencia
            request.session["loja_clube_checkout"] = dados
            request.session.modified = True
        return redirect("core:pagamento", ref=pagamento.referencia)

    # Cartão com Mercado Pago configurado → Checkout Pro (redireciona ao MP).
    if forma == "cartao" and config.configurado:
        itens_disp = [
            {"nome": f'{it["qtd"]}× {kit["produto"].nome}'
                     + (f' ({it["variacao"].nome})' if it["variacao"].nome else ''),
             "valor": f'{it["subtotal"]:.2f}'}
            for kit in kits for it in kit["itens"]
        ]
        pagamento, init_point, erro = _criar_pagamento_cartao(
            request, tipo="loja_clube", valor=total, descricao="Loja do Clube",
            payload={"cart": _loja_cart(request), "comprador": comprador,
                     "titulo": "Loja do Clube", "itens": itens_disp},
            comprador=comprador, usuario=request.user,
        )
        if erro:
            messages.error(request, f"Não foi possível iniciar o pagamento no cartão: {erro}")
            return redirect(reverse("core:loja") + "?aba=loja#carrinho")
        return redirect(init_point)

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


@login_required
def mensalidades_view(request):
    """Tela "Mensalidades". O Diretor vê o painel completo; o Responsável (ou o
    Diretor em modo preview) vê a própria visão: o que pagou, o que está em
    aberto e a opção de pagar."""
    if atua_como_responsavel(request):
        return _mensalidades_responsavel(request)
    anos = sorted(
        set(Mensalidade.objects.values_list("ano", flat=True)) | {timezone.localdate().year},
        reverse=True,
    )
    try:
        ano = int(request.GET.get("ano", anos[0]))
    except (TypeError, ValueError):
        ano = anos[0]

    # Aventureiros/mensalidades FICTÍCIOS (demo) não entram no painel do Diretor.
    aventureiros = list(
        Aventureiro.objects.filter(ativo=True, demo=False).order_by("nome_completo")
    )
    mens = list(
        Mensalidade.objects.filter(ano=ano).exclude(aventureiro__demo=True)
        .select_related("aventureiro")
    )
    por_av = defaultdict(list)
    for m in mens:
        por_av[m.aventureiro_id].append(m)

    # A lista mostra só aventureiros ativos (cada um com seus meses).
    linhas = []
    for av in aventureiros:
        meses = sorted(por_av.get(av.id, []), key=lambda x: x.mes)
        linhas.append({"av": av, "meses": meses,
                       "resumo": _resumo_mensalidades(meses), "tem": bool(meses)})

    # Totais/relatório: aventureiro INATIVO não interfere — só entram os dados de
    # antes de ficar inativo (as cobranças PAGAS contam sempre; as em aberto de
    # inativos não). Recebido = todos os pagos; em aberto = só de ativos.
    tot = {"previsto": Decimal("0"), "recebido": Decimal("0"),
           "aberto": Decimal("0"), "isentos": 0}
    for m in mens:
        if m.status == "paga":
            tot["recebido"] += (m.valor_pago or Decimal("0"))
        elif m.em_aberto and m.aventureiro.ativo:
            tot["aberto"] += m.valor
    tot["previsto"] = tot["recebido"] + tot["aberto"]
    tot["isentos"] = sum(1 for av in aventureiros if av.mensalidade_isento)

    # Taxa do gateway (Mercado Pago) nas mensalidades do ano pagas via Pix/cartão.
    pag_ids = set(
        Mensalidade.objects.filter(ano=ano, pagamento__isnull=False)
        .exclude(aventureiro__demo=True)
        .values_list("pagamento_id", flat=True)
    )
    tot["taxa_gateway"] = (
        Pagamento.objects.filter(id__in=pag_ids, status="aprovado").aggregate(
            t=Sum("taxa"))["t"] or Decimal("0")
    ) if pag_ids else Decimal("0")
    tot["liquido"] = tot["recebido"] - tot["taxa_gateway"]

    taxa = (tot["recebido"] / (tot["recebido"] + tot["aberto"]) * 100) \
        if (tot["recebido"] + tot["aberto"]) else Decimal("0")
    contexto = {
        "config": ConfigMensalidade.get_solo(),
        "ano": ano,
        "anos": anos,
        "linhas": linhas,
        "totais": tot,
        "taxa": taxa,
        "dashboard": _mensalidades_dashboard(mens),
        "aba": request.GET.get("aba", "resumo"),
        "meses": [(i, MESES_PT[i]) for i in range(1, 13)],
        "mes_atual": timezone.localdate().month,
        "formas_pagamento": [
            ("dinheiro", "Dinheiro"), ("pix", "Pix"),
            ("cartao", "Cartão"), ("online", "Online"),
        ],
        # Aba Cobranças
        "cobrancas": _cobrancas_familias(),
        "mensagem_cobranca": ConfigMensalidade.get_solo().mensagem_cobranca or MENSAGEM_COBRANCA_PADRAO,
        "prompt_cobranca_ia": ConfigMensalidade.get_solo().prompt_cobranca_ia or PROMPT_COBRANCA_IA_PADRAO,
        "cobranca_via_ia": ConfigMensalidade.get_solo().cobranca_via_ia,
        "mensagem_apelo": ConfigMensalidade.get_solo().mensagem_apelo or MENSAGEM_APELO_PADRAO,
        "wa_configurado": WhatsappConfig.get_solo().configurado,
        "ia_configurada": OpenAIConfig.get_solo().configurado,
    }
    return render(request, "core/mensalidades.html", contexto)


def _mensalidades_dashboard(mens):
    """Resumo mês a mês (para o dashboard): recebido, em aberto e % pago por mês."""
    por_mes = {m: [] for m in range(1, 13)}
    for x in mens:
        if 1 <= x.mes <= 12:
            por_mes[x.mes].append(x)
    linhas = []
    maxv = Decimal("0")
    for mes in range(1, 13):
        ms = por_mes[mes]
        # Recebido (pago) conta sempre — é dado histórico, mesmo de quem depois
        # ficou inativo. Em aberto só conta de aventureiros ATIVOS.
        recebido = sum((x.valor_pago or Decimal("0") for x in ms if x.status == "paga"), Decimal("0"))
        aberto = sum((x.valor for x in ms if x.em_aberto and x.aventureiro.ativo), Decimal("0"))
        pagas = sum(1 for x in ms if x.status == "paga")
        abertas = sum(1 for x in ms if x.em_aberto and x.aventureiro.ativo)
        isentas = sum(1 for x in ms if x.isento and x.status != "cancelada" and x.aventureiro.ativo)
        total_valor = recebido + aberto
        if total_valor > maxv:
            maxv = total_valor
        pct = (recebido / total_valor * 100) if total_valor else (100 if pagas else 0)
        cor = "alto" if pct >= 80 else ("medio" if pct >= 40 else "baixo")
        linhas.append({
            "mes": mes, "nome": MESES_PT[mes], "abrev": MESES_PT[mes][:3],
            "recebido": recebido, "aberto": aberto, "total_valor": total_valor,
            "pagas": pagas, "abertas": abertas, "isentas": isentas,
            "cobrancas": pagas + abertas + isentas, "pct": pct, "cor": cor,
        })
    # Percentuais de altura das barras (0-100) para o gráfico em CSS.
    maxv = maxv or Decimal("1")
    for l in linhas:
        l["h_recebido"] = int(l["recebido"] / maxv * 100)
        l["h_aberto"] = int(l["aberto"] / maxv * 100)
    return linhas


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
def mensalidade_reajustar_view(request):
    """Aplica os valores atuais da configuração às cobranças **em aberto** de um ano
    a partir de um mês (respeitando isenção/desconto de cada aventureiro). Útil para
    reajustar a mensalidade "a partir do próximo mês" para todos de uma vez."""
    try:
        ano = int(request.POST.get("ano") or timezone.localdate().year)
        mes_ini = int(request.POST.get("mes") or 1)
    except (TypeError, ValueError):
        return redirect("core:mensalidades")
    mes_ini = min(max(mes_ini, 1), 12)
    config = ConfigMensalidade.get_solo()
    afetadas = 0
    for m in Mensalidade.objects.filter(
        ano=ano, mes__gte=mes_ini, status="aberta",
        aventureiro__ativo=True, aventureiro__demo=False,
    ).select_related("aventureiro"):
        valor, isento = _valor_mensalidade(config, m.aventureiro, m.tipo)
        m.valor, m.isento = valor, isento
        m.save(update_fields=["valor", "isento"])
        afetadas += 1
    messages.success(
        request,
        f"{afetadas} cobrança(s) em aberto de {MESES_PT[mes_ini]}/{ano} em diante "
        f"reajustada(s) para os valores atuais.",
    )
    return redirect(f"{reverse('core:mensalidades')}?ano={ano}&aba=aventureiros")


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
        alvos = Aventureiro.objects.filter(pk=av_id, ativo=True, demo=False)
    else:
        alvos = Aventureiro.objects.filter(ativo=True, demo=False)
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


# ---------------------------------------------------------------------------
# Mensalidades — visão do RESPONSÁVEL (dentro do sistema, logado).
# ---------------------------------------------------------------------------
def _mensalidades_familia_abertas(usuario, incluir_futuras=False):
    """Mensalidades em aberto (não isentas) dos aventureiros ATIVOS da família.
    Por padrão só as VENCIDAS (mês atual + atrasadas); com `incluir_futuras`,
    inclui também as em aberto dos meses à frente (para adiantar)."""
    qs = Mensalidade.objects.filter(
        aventureiro__usuario=usuario, aventureiro__ativo=True,
        status="aberta", isento=False,
    ).select_related("aventureiro")
    if not incluir_futuras:
        qs = qs.filter(_q_mens_vencidas())
    return list(qs.order_by("aventureiro__nome_completo", "ano", "mes"))


def _mensalidades_responsavel(request):
    """Visão do RESPONSÁVEL: resumo (pago no ano × em aberto), lista das
    mensalidades em aberto (vencidas por padrão; futuras sob demanda) para
    selecionar e pagar, e o texto de apelo configurado pelo Diretor."""
    usuario = request.user
    ano = timezone.localdate().year
    incluir_futuras = request.GET.get("frente") == "1"

    abertas = _mensalidades_familia_abertas(usuario, incluir_futuras=incluir_futuras)
    # Agrupa por criança (aventureiro) para exibição.
    por_av = {}
    for m in abertas:
        a = m.aventureiro
        c = por_av.setdefault(
            a.id, {"aventureiro": a, "itens": [], "total": Decimal("0")}
        )
        c["itens"].append(m)
        c["total"] += m.valor
    criancas = sorted(por_av.values(), key=lambda c: c["aventureiro"].nome_completo)
    total_aberto = sum((m.valor for m in abertas), Decimal("0"))

    # Quanto já pagou no ano (histórico dos aventureiros da família).
    pagas_ano = list(
        Mensalidade.objects.filter(
            aventureiro__usuario=usuario, ano=ano, status="paga"
        )
    )
    pago_ano = sum((m.valor_pago or Decimal("0") for m in pagas_ano), Decimal("0"))

    # Há algo em aberto no futuro? (para oferecer o botão "adiantar meses").
    tem_futuras = (
        Mensalidade.objects.filter(
            aventureiro__usuario=usuario, aventureiro__ativo=True,
            status="aberta", isento=False,
        ).exclude(_q_mens_vencidas()).exists()
    )

    resp_nome, _ = _responsavel_da_familia(usuario)
    contexto = {
        "criancas": criancas,
        "total_aberto": total_aberto,
        "n_abertas": len(abertas),
        "pago_ano": pago_ano,
        "n_pagas_ano": len(pagas_ano),
        "ano": ano,
        "incluir_futuras": incluir_futuras,
        "tem_futuras": tem_futuras,
        "mensagem_apelo": ConfigMensalidade.get_solo().mensagem_apelo or MENSAGEM_APELO_PADRAO,
        "mp_configurado": _mp_config().configurado,
        "primeiro_nome": (resp_nome or "").split(" ")[0],
        "formas_pagamento": FORMAS_PAGAMENTO_ONLINE,
    }
    return render(request, "core/mensalidades_responsavel.html", contexto)


@login_required
@require_POST
def minhas_mensalidades_pagar_view(request):
    """Responsável paga as mensalidades selecionadas: gera UMA cobrança (Pix ou
    cartão) das mensalidades em aberto escolhidas — todas da própria família (o
    filtro por `aventureiro__usuario` garante que ninguém pague de outra conta).
    A baixa das mensalidades é feita na aprovação por `_finalizar_mensalidade`."""
    ids = request.POST.getlist("mensalidade_ids")
    mens = list(
        Mensalidade.objects.filter(
            pk__in=ids, status="aberta", isento=False,
            aventureiro__usuario=request.user,
        ).select_related("aventureiro").order_by(
            "aventureiro__nome_completo", "ano", "mes"
        )
    )
    if not mens:
        messages.error(request, "Selecione ao menos uma mensalidade em aberto.")
        return redirect("core:mensalidades")
    if not _mp_config().configurado:
        messages.error(
            request,
            "O pagamento online está indisponível no momento. Procure a diretoria.",
        )
        return redirect("core:mensalidades")
    total = sum((m.valor for m in mens), Decimal("0"))
    resp_nome, resp_email = _responsavel_da_familia(request.user)
    payload = {
        "mensalidade_ids": [m.id for m in mens],
        "titulo": f"Mensalidades — {resp_nome}",
        "itens": [
            {"nome": f"{m.aventureiro.nome_completo} · {m.mes_nome}/{m.ano}"
                     + (" (inscrição)" if m.tipo == "inscricao" else ""),
             "valor": f"{m.valor:.2f}"}
            for m in mens
        ],
    }
    comprador = {"nome": resp_nome, "email": resp_email}
    descricao = f"Mensalidades — {resp_nome}"
    if (request.POST.get("forma_pagamento") or "pix") == "cartao":
        pagamento, init_point, erro = _criar_pagamento_cartao(
            request, tipo="mensalidade", valor=total, descricao=descricao,
            payload=payload, comprador=comprador, usuario=request.user,
        )
        if erro:
            messages.error(request, f"Não foi possível iniciar o cartão: {erro}")
            return redirect("core:mensalidades")
        return redirect(init_point)
    pagamento, erro = _criar_pagamento_pix(
        request, tipo="mensalidade", valor=total, descricao=descricao,
        payload=payload, comprador=comprador, usuario=request.user,
    )
    if erro:
        messages.error(request, f"Não foi possível gerar o Pix: {erro}")
        return redirect("core:mensalidades")
    return redirect("core:pagamento", ref=pagamento.referencia)


# ===========================================================================
# Financeiro geral do clube (consolida mensalidades + loja + eventos + custos)
# ===========================================================================
def _dt_data(dt):
    """Devolve o datetime como veio (para ordenar/exibir o extrato COM hora)."""
    return dt


def _ordem_extrato(e):
    """Chave de ordenação do extrato: datetime aware (data + hora). Normaliza
    date/datetime/None para comparar sem erro."""
    d = e.get("data")
    if d is None:
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    if isinstance(d, datetime.datetime):
        return d if timezone.is_aware(d) else timezone.make_aware(d)
    return timezone.make_aware(datetime.datetime.combine(d, datetime.time.min))


@diretor_required
def financeiro_view(request):
    """Painel financeiro do clube inteiro: resumo por fonte, gráficos, custos do
    clube e extrato consolidado (mensalidades + loja + eventos)."""
    hoje = timezone.localdate()

    mens_pagas = list(
        Mensalidade.objects.filter(status="paga").exclude(aventureiro__demo=True)
        .select_related("aventureiro")
    )
    compras = list(CompraLoja.objects.filter(status="confirmado"))
    inscricoes = list(Inscricao.objects.exclude(status="cancelada").select_related("evento"))
    pedidos_ev = list(PedidoLoja.objects.filter(status="confirmado").select_related("evento"))
    custos_ev = list(CustoEvento.objects.select_related("evento"))
    custos_clube = list(CustoClube.objects.prefetch_related("comprovantes"))

    mens_recebido = sum((m.valor_pago or Decimal("0") for m in mens_pagas), Decimal("0"))
    mens_aberto = sum(
        (m.valor for m in Mensalidade.objects.filter(
            status="aberta", aventureiro__ativo=True, aventureiro__demo=False)),
        Decimal("0"),
    )
    loja_total = sum((c.valor_total for c in compras), Decimal("0"))
    inscr_total = sum((i.valor_total for i in inscricoes), Decimal("0"))
    pedidos_total = sum((p.valor_total for p in pedidos_ev), Decimal("0"))
    eventos_entradas = inscr_total + pedidos_total
    custos_ev_total = sum((c.valor for c in custos_ev), Decimal("0"))
    # Custos do clube separados por destino: 'loja' abate no líquido da loja;
    # 'geral' é custo do clube em si.
    custos_loja_total = sum((c.valor for c in custos_clube if c.destino == "loja"), Decimal("0"))
    custos_geral_total = sum((c.valor for c in custos_clube if c.destino != "loja"), Decimal("0"))

    # Taxas do gateway (Mercado Pago) — parte da venda que NÃO caiu no banco. Somadas
    # por TIPO de pagamento aprovado (cada Pagamento tem 1 taxa; somar por tipo evita
    # contagem dupla quando uma cobrança cobre inscrição + lojinha do evento).
    def _soma_taxa(tipos):
        return Pagamento.objects.filter(status="aprovado", tipo__in=tipos).aggregate(
            t=Sum("taxa"))["t"] or Decimal("0")
    taxa_mens = _soma_taxa(["mensalidade"])
    taxa_loja = _soma_taxa(["loja_clube"])
    taxa_eventos = _soma_taxa(["loja_evento", "inscricao"])
    taxa_total = taxa_mens + taxa_loja + taxa_eventos

    entradas = mens_recebido + loja_total + eventos_entradas
    saidas = custos_ev_total + custos_loja_total + custos_geral_total + taxa_total
    resultado = entradas - saidas

    resumo = {
        # Líquido de cada fonte = o que sobrou no banco (bruto − custos − taxa do gateway).
        "mensalidades": {"entradas": mens_recebido, "taxa": taxa_mens,
                         "liquido": mens_recebido - taxa_mens,
                         "aberto": mens_aberto, "n": len(mens_pagas)},
        "loja": {"entradas": loja_total, "custos": custos_loja_total, "taxa": taxa_loja,
                 "liquido": loja_total - custos_loja_total - taxa_loja, "n": len(compras)},
        "eventos": {
            "entradas": eventos_entradas, "inscricoes": inscr_total,
            "pedidos": pedidos_total, "custos": custos_ev_total, "taxa": taxa_eventos,
            "liquido": eventos_entradas - custos_ev_total - taxa_eventos,
        },
        "custos_clube": {"total": custos_geral_total,
                         "n": sum(1 for c in custos_clube if c.destino != "loja")},
        "taxas": {"total": taxa_total, "mensalidades": taxa_mens,
                  "loja": taxa_loja, "eventos": taxa_eventos},
    }

    # Duas "contas" do clube: o que pode gastar × o que está travado.
    # - Disponível: mensalidades + lucro dos eventos − custos gerais do clube.
    # - Reservado da loja: vendas − custos da loja (fica travado p/ pagar fornecedores).
    lucro_eventos = eventos_entradas - custos_ev_total - taxa_eventos
    disponivel = (mens_recebido - taxa_mens) + lucro_eventos - custos_geral_total
    reservado_loja = loja_total - custos_loja_total - taxa_loja

    # Onde está o dinheiro: banco (informado) e espécie = o que sobra.
    caixa = CaixaClube.get_solo()
    caixa_especie = resultado - caixa.saldo_banco

    # Extrato consolidado
    extrato = []
    for m in mens_pagas:
        extrato.append({"data": _dt_data(m.pago_em or m.criado_em), "fonte": "mensalidade",
                        "tipo": "Mensalidade", "desc": f"{m.aventureiro.nome_completo} — {m.mes:02d}/{m.ano}",
                        "valor": m.valor_pago or Decimal("0"), "saida": False, "comprovante": None})
    for c in compras:
        extrato.append({"data": _dt_data(c.criado_em), "fonte": "loja", "tipo": "Loja",
                        "desc": f"{c.comprador_nome} — {c.codigo}", "valor": c.valor_total,
                        "saida": False, "comprovante": None})
    for i in inscricoes:
        extrato.append({"data": _dt_data(i.criado_em), "fonte": "eventos", "tipo": "Inscrição",
                        "desc": f"{i.evento.nome} — {i.responsavel_nome}", "valor": i.valor_total,
                        "saida": False, "comprovante": None})
    for p in pedidos_ev:
        extrato.append({"data": _dt_data(p.criado_em), "fonte": "eventos", "tipo": "Lojinha do evento",
                        "desc": f"{p.evento.nome} — {p.comprador_nome}", "valor": p.valor_total,
                        "saida": False, "comprovante": None})
    for cu in custos_ev:
        extrato.append({"data": _dt_data(cu.criado_em), "fonte": "eventos", "tipo": "Custo do evento",
                        "desc": f"{cu.evento.nome} — {cu.nome}", "valor": cu.valor,
                        "saida": True, "comprovante": (cu.comprovante.url if cu.comprovante else None)})
    for cc in custos_clube:
        _prov = cc.comprovantes.all()
        _loja = cc.destino == "loja"
        # `cc.data` é um date (sem hora); vira datetime (meia-noite) para o extrato
        # exibir/ordenar por data+hora sem quebrar o filtro |date com H:i.
        _dtcc = (datetime.datetime.combine(cc.data, datetime.time.min)
                 if cc.data else cc.criado_em)
        extrato.append({"data": _dtcc, "fonte": ("loja" if _loja else "custos"),
                        "tipo": ("Custo da loja" if _loja else "Custo do clube"),
                        "desc": cc.nome, "valor": cc.valor, "saida": True,
                        "comprovante": (_prov[0].arquivo.url if _prov else None)})
    # Taxas do gateway como saída no extrato (para bater com o líquido). Uma linha
    # por cobrança aprovada com taxa > 0.
    _fonte_taxa = {"mensalidade": "mensalidade", "loja_clube": "loja"}
    for pg in Pagamento.objects.filter(status="aprovado").exclude(taxa=0):
        extrato.append({
            "data": _dt_data(pg.pago_em or pg.criado_em),
            "fonte": _fonte_taxa.get(pg.tipo, "eventos"),
            "tipo": "Taxa Mercado Pago",
            "desc": f"{pg.get_tipo_display()} · {pg.get_forma_display()}",
            "valor": pg.taxa, "saida": True, "comprovante": None,
        })
    extrato.sort(key=_ordem_extrato, reverse=True)

    # Fluxo mensal do ano atual (entradas x saídas por mês)
    ent_mes = [Decimal("0")] * 13
    sai_mes = [Decimal("0")] * 13
    for e in extrato:
        d = e["data"]
        if d and d.year == hoje.year and 1 <= d.month <= 12:
            if e["saida"]:
                sai_mes[d.month] += e["valor"]
            else:
                ent_mes[d.month] += e["valor"]
    maxm = max([Decimal("1")] + ent_mes[1:] + sai_mes[1:])
    fluxo = []
    for mes in range(1, 13):
        fluxo.append({
            "abrev": MESES_PT[mes][:3], "entrada": ent_mes[mes], "saida": sai_mes[mes],
            "h_ent": int(ent_mes[mes] / maxm * 100), "h_sai": int(sai_mes[mes] / maxm * 100),
        })

    # Donut de entradas por fonte
    total_ent = entradas or Decimal("1")
    p1 = float(mens_recebido / total_ent * 100)
    p2 = float((mens_recebido + loja_total) / total_ent * 100)
    donut = mark_safe(
        f"conic-gradient(#1f6fb2 0 {p1:.1f}%, #3a9d3a {p1:.1f}% {p2:.1f}%, "
        f"#e0a800 {p2:.1f}% 100%)"
    )

    contexto = {
        "entradas": entradas, "saidas": saidas, "resultado": resultado,
        "resumo": resumo, "extrato": extrato, "fluxo": fluxo, "donut": donut,
        "custos_gerais_total": custos_geral_total,
        "disponivel": disponivel, "reservado_loja": reservado_loja,
        "lucro_eventos": lucro_eventos,
        "caixa": caixa, "caixa_especie": caixa_especie,
        "caixa_form": CaixaClubeForm(instance=caixa),
        "custos_clube": custos_clube, "custo_form": CustoClubeForm(),
        "ano": hoje.year, "aba": request.GET.get("aba", "resumo"),
    }
    return render(request, "core/financeiro.html", contexto)


@diretor_required
@require_POST
def custo_clube_novo_view(request):
    """Lança um custo/gasto do clube (com comprovante)."""
    form = CustoClubeForm(request.POST)
    if form.is_valid():
        custo = form.save(commit=False)
        custo.criado_por = request.user
        custo.data = timezone.localdate()  # data do lançamento
        custo.save()
        for arquivo in request.FILES.getlist("comprovantes"):
            ComprovanteCustoClube.objects.create(custo=custo, arquivo=arquivo)
        messages.success(request, "Custo lançado.")
        destino_ok = custo.destino
    else:
        messages.error(request, "Informe a descrição e um valor válido.")
        destino_ok = request.POST.get("destino")
    # Volta para a loja se veio de lá; senão, para o Financeiro (aba custos).
    if request.POST.get("de") == "loja" or destino_ok == "loja":
        return redirect(reverse("core:loja") + "?aba=vendas")
    return redirect(reverse("core:financeiro") + "?aba=custos")


@diretor_required
@require_POST
def custo_clube_excluir_view(request, custo_id):
    """Remove um custo do clube."""
    custo = CustoClube.objects.filter(pk=custo_id).first()
    if custo is not None:
        custo.delete()
        messages.success(request, "Custo removido.")
    return redirect(reverse("core:financeiro") + "?aba=custos")


@diretor_required
@require_POST
def caixa_editar_view(request):
    """Atualiza 'Onde está o dinheiro': saldo na conta e valores a receber. A
    espécie é calculada (resultado − banco − a receber)."""
    caixa = CaixaClube.get_solo()
    form = CaixaClubeForm(request.POST, instance=caixa)
    if form.is_valid():
        caixa = form.save(commit=False)
        caixa.atualizado_por = request.user
        caixa.save()
        messages.success(request, "Caixa atualizado.")
    else:
        messages.error(request, "Informe valores válidos.")
    return redirect(reverse("core:financeiro"))
