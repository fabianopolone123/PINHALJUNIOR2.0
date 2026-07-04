import datetime
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
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
    ResponsavelLegalForm,
)
from .models import (
    Aventureiro,
    Evento,
    Inscricao,
    ParticipanteInscricao,
    ProdutoEvento,
    RespostaInscricao,
    VariacaoProduto,
)
from .permissoes import diretor_required

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
        .select_related("ficha_medica", "autorizacao_imagem")
        .all()
    )

    responsaveis = {}   # chave -> {nome, papeis, contato..., vinculos: {av_id: {...}}}
    total_vinculos = 0

    for av in aventureiros:
        # Dados de exibição do aventureiro (usados no modal detalhado).
        av.idade = _idade(av.data_nascimento)
        av.classes = _classes_investidas(av)
        av.foto_ok = _foto_valida(av)
        av.iniciais = _iniciais(av.nome_completo)
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
            total_vinculos += 1
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
                av.id, {"nome": av.nome_completo, "idade": av.idade, "papeis": set()}
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
            "cpf": resp["cpf"], "email": resp["email"],
            "celular": resp["celular"], "whatsapp": resp["whatsapp"],
            "vinculos": vinculos,
        })
    lista_responsaveis.sort(key=lambda x: _normaliza(x["nome"]))
    for i, resp in enumerate(lista_responsaveis):
        resp["id"] = f"resp-{i}"

    aventureiros.sort(key=lambda a: _normaliza(a.nome_completo))

    contexto = {
        "responsaveis": lista_responsaveis,
        "aventureiros": aventureiros,
        "total_responsaveis": len(lista_responsaveis),
        "total_aventureiros": len(aventureiros),
        "total_vinculos": total_vinculos,
    }
    return render(request, "core/usuarios.html", contexto)


@diretor_required
def eventos_view(request):
    """Lista os eventos do clube. Restrito ao perfil Diretor."""
    eventos = list(Evento.objects.all())
    return render(request, "core/eventos.html", {"eventos": eventos})


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


@diretor_required
def evento_painel_view(request, pk):
    """Painel (dashboard) de um evento complexo.

    Fase 1: resumo + custos. Parte 2.1: configuração de inscrição
    (visibilidade, prazo, faixas etárias de preço e valor da diretoria).
    """
    evento = get_object_or_404(Evento, pk=pk)
    custos = list(evento.custos.all())
    total_custos = sum((c.valor for c in custos), Decimal("0"))
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

    vendas_loja = Decimal("0")  # Fase 4 (lojinha).
    receitas = arrecadacao_inscricoes + vendas_loja

    contexto = {
        "evento": evento,
        "custos": custos,
        "form_custo": CustoEventoForm(),
        "faixas": faixas,
        "campos_inscricao": campos_inscricao,
        "produtos": produtos,
        "inscricoes": inscricoes,
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
    return redirect(reverse("core:evento_painel", args=[evento.pk]) + "#inscricoes")


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
    return {"idx": str(idx), "nome": nome, "idade": idade, "diretoria": eh_dir, "campos": campos}


def _linha_vazia(idx, campos_part):
    """Linha de participante em branco (para GET e para o modelo do JS)."""
    return {
        "idx": str(idx), "nome": "", "idade": None, "diretoria": False,
        "campos": [
            {"campo": c, "valor": "", "valores": [], "texto": "", "erro": None}
            for c in campos_part
        ],
    }


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
    linhas = []
    erros_part = []

    if request.method == "POST":
        form = InscricaoForm(request.POST, evento=evento)
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

        if form.is_valid() and not erros_part:
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
                total = Decimal("0")
                dados = []
                for linha in linhas:
                    valor, faixa = evento.preco_participante(
                        linha["idade"], linha["diretoria"], faixas
                    )
                    total += valor
                    p = ParticipanteInscricao(
                        nome=linha["nome"], idade=linha["idade"],
                        eh_diretoria=linha["diretoria"], faixa=faixa, valor=valor,
                    )
                    dados.append((p, linha["campos"]))
                inscricao.valor_total = total
                inscricao.save()
                for p, campos in dados:
                    p.inscricao = inscricao
                    p.save()
                    for c in campos:
                        RespostaInscricao.objects.create(
                            inscricao=inscricao, participante=p, campo=c["campo"],
                            campo_rotulo=c["campo"].rotulo, valor=c["texto"],
                        )
                for campo, nome in form.campos_extra:
                    RespostaInscricao.objects.create(
                        inscricao=inscricao, campo=campo, campo_rotulo=campo.rotulo,
                        valor=form.resposta_texto(campo, nome),
                    )
            request.session["inscricao_codigo"] = inscricao.codigo
            return redirect("core:evento_inscricao_sucesso", pk=evento.pk)
        messages.error(request, "Verifique os campos destacados e os participantes.")
    else:
        inicial = {}
        if request.user.is_authenticated and request.user.email:
            inicial["responsavel_email"] = request.user.email
        form = InscricaoForm(evento=evento, initial=inicial)

    contexto = {
        "evento": evento,
        "form": form,
        "faixas": faixas,
        "tem_diretoria": tem_diretoria,
        "campos_participante": campos_part,
        "linhas": linhas or [_linha_vazia(0, campos_part)],
        "linha_modelo": _linha_vazia("__IDX__", campos_part),
        "erros_part": erros_part,
    }
    return render(request, "core/evento_inscrever.html", contexto)


def evento_inscricao_sucesso_view(request, pk):
    """Confirmação da inscrição (código + valor total). Pagamento simulado."""
    evento = get_object_or_404(Evento, pk=pk, tipo="inscricao")
    codigo = request.session.get("inscricao_codigo")
    inscricao = evento.inscricoes.filter(codigo=codigo).first() if codigo else None
    if inscricao is None:
        return redirect("core:evento_pagina", pk=evento.pk)
    return render(
        request, "core/evento_inscricao_sucesso.html",
        {"evento": evento, "inscricao": inscricao},
    )


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
            linhas = [
                {"idx": str(i), "id": v.id, "nome": v.nome,
                 "valor_raw": v.valor, "estoque_raw": v.estoque}
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
