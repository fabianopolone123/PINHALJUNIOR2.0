"""Views do leilão.

Camada fina de propósito: traduz pedido HTTP → chamada em `servicos.py` →
resposta. **Nenhuma regra de pregão mora aqui.**

A única view fora do comum é o `stream` (SSE): é assíncrona e segura a conexão
aberta enquanto a pessoa estiver no leilão. Ela existe porque o serviço roda em
ASGI com **um worker só** (ver `config/settings_leilao.py`).
"""

import asyncio
import json
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core import mercadopago

from . import equipe
from . import estado as est
from . import entregas
from . import papeis
from . import reacoes
from . import servicos
from .forms import (
    ConfigLeilaoForm,
    EntrarForm,
    LeilaoForm,
    LoteForm,
    TrocarSenhaForm,
    UsuarioEquipeForm,
)
from .hub import HUB, garantir_laco, sse
from .imagens import preparar_foto
from .models import (
    Arremate,
    AtribuicaoEntrega,
    ConfigLeilao,
    EntregadorLeilao,
    Leilao,
    Lote,
    PagamentoLeilao,
    Participante,
)
from .sessao import entrar as sessao_entrar
from .sessao import participante_atual
from .sessao import sair as sessao_sair

logger = logging.getLogger(__name__)


def _json(request):
    """Corpo JSON do pedido (as telas mandam `fetch` com JSON)."""
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return {}


# ===========================================================================
# Participante
# ===========================================================================
def entrar_view(request):
    """A porta: nome, WhatsApp e endereço. Sem senha."""
    if participante_atual(request):
        return redirect("leilao:leilao")

    leilao = Leilao.ao_vivo()
    if request.method == "POST":
        form = EntrarForm(request.POST)
        if form.is_valid():
            participante = form.save(commit=False)
            # Entrar de novo NÃO limpa o bloqueio: sem isto, quem o locutor
            # bloqueou voltava em dois toques com um cadastro novo. O registro é
            # novo (a sessão é de outro aparelho), mas a PESSOA é a mesma.
            participante.bloqueado = servicos.pessoa_bloqueada(participante)
            participante.save()
            sessao_entrar(request, participante)
            messages.success(request, f"Bem-vindo, {participante.nome_curto}!")
            return redirect("leilao:leilao")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = EntrarForm()

    return render(request, "leilao/entrar.html", {"form": form, "leilao": leilao})


def sair_view(request):
    sessao_sair(request)
    return redirect("leilao:entrar")


def leilao_view(request):
    """A tela do pregão. Uma só, que nunca recarrega."""
    participante = participante_atual(request)
    if not participante:
        return redirect("leilao:entrar")

    Participante.objects.filter(pk=participante.pk).update(ultimo_visto_em=timezone.now())
    leilao = Leilao.ao_vivo()
    return render(
        request,
        "leilao/leilao.html",
        {
            "leilao": leilao,
            # Objeto, não string: o `json_script` do template é quem serializa.
            # A lista de arremates NÃO vai aqui: a tela a busca por `fetch`
            # (`/meus-arremates/`), porque ela muda sozinha durante o pregão.
            "estado_inicial": est.estado_publico(leilao),
            "emojis": reacoes.EMOJIS,
            # Quantos emojis cada toque solta. O número é do servidor; a tela
            # só o lê para não desenhar duas vezes o que ela mesma mandou.
            "rajada_reacoes": reacoes.EMOJIS_POR_TOQUE,
        },
    )


def _arremates_do(participante, limite=30):
    return (
        Arremate.objects.filter(participante=participante)
        .exclude(status="cancelado")
        .select_related("lote", "pagamento")
        .order_by("-criado_em")[:limite]
    )


# ---------------------------------------------------------------------------
# O stream (SSE)
# ---------------------------------------------------------------------------
async def stream_view(request):
    """Canal de eventos do leilão (`text/event-stream`).

    Manda o **estado inteiro** ao conectar e a cada `resync`. Isso dispensa
    repetir eventos perdidos: quem reconecta está sempre correto, sem lógica de
    histórico.

    O `X-Accel-Buffering: no` é obrigatório — sem ele o Nginx segura os pedaços
    e o "tempo real" vira entrega em lotes.
    """
    garantir_laco(getattr(settings, "LEILAO_TICK_SEGUNDOS", 1))

    teto = getattr(settings, "LEILAO_MAX_CONEXOES", 300)
    # O teto olha TODAS as conexões (é um limite de recurso); a contagem que vai
    # para a tela olha só o público (é um número sobre gente).
    if HUB.total >= teto:
        return HttpResponse("Leilão lotado. Tente novamente em instantes.", status=503)

    # A tela da equipe se identifica: ela acompanha o pregão, mas não é alguém
    # que chegou para dar lance.
    publico = request.GET.get("equipe") != "1"

    ping = getattr(settings, "LEILAO_PING_SEGUNDOS", 15)
    montar = sync_to_async(
        lambda: est.estado_publico(Leilao.ao_vivo()), thread_sensitive=False
    )

    async def gerador():
        fila = HUB.assinar(publico=publico)
        HUB.publicar("online", {"online": HUB.conectados})
        try:
            yield sse({"seq": 0, "tipo": "estado", "dados": await montar()})
            while True:
                try:
                    evento = await asyncio.wait_for(fila.get(), timeout=ping)
                except (asyncio.TimeoutError, TimeoutError):
                    # Comentário SSE: mantém a conexão viva sem inventar evento.
                    yield ": ping\n\n"
                    continue
                if evento["tipo"] == "resync":
                    yield sse({"seq": evento["seq"], "tipo": "estado", "dados": await montar()})
                else:
                    yield sse(evento)
        except asyncio.CancelledError:  # navegador fechou
            raise
        finally:
            HUB.cancelar(fila)
            HUB.publicar("online", {"online": HUB.conectados})

    resposta = StreamingHttpResponse(gerador(), content_type="text/event-stream")
    resposta["Cache-Control"] = "no-cache, no-transform"
    resposta["X-Accel-Buffering"] = "no"
    resposta["Connection"] = "keep-alive"
    return resposta


# ---------------------------------------------------------------------------
# Ações do participante
# ---------------------------------------------------------------------------
@require_POST
def lance_view(request):
    """O botão gigante. Devolve o lote já atualizado."""
    participante = participante_atual(request)
    if not participante:
        return JsonResponse({"ok": False, "msg": "Entre no leilão para dar lance."}, status=401)

    dados = _json(request)
    lote_id = dados.get("lote")
    if not lote_id:
        return JsonResponse({"ok": False, "msg": "Lote não informado."}, status=400)

    ok, msg, extra = servicos.dar_lance(
        lote_id, participante, valor_visto=dados.get("valor_visto")
    )
    corpo = {"ok": ok, "msg": msg}
    if extra:
        corpo["lote"] = extra.get("lote")
    return JsonResponse(corpo, status=200 if ok else 409)


@require_POST
def chat_enviar_view(request):
    participante = participante_atual(request)
    if not participante:
        return JsonResponse({"ok": False, "msg": "Entre no leilão para conversar."}, status=401)
    leilao = Leilao.ao_vivo()
    if not leilao:
        # "Nenhum leilão ao vivo" era verdade para o servidor e mentira para
        # quem estava na tela do leilão. Quem lê isto está com a caixa de
        # conversa aberta na frente: o recado tem de explicar o que aconteceu.
        return JsonResponse(
            {"ok": False, "msg": "O leilão foi encerrado."}, status=409
        )
    if not leilao.chat_aberto:
        return JsonResponse({"ok": False, "msg": "O chat está fechado agora."}, status=409)

    m = servicos.enviar_mensagem(leilao, participante, _json(request).get("texto"))
    if not m:
        return JsonResponse({"ok": False, "msg": "Mensagem vazia ou bloqueada."}, status=400)
    return JsonResponse({"ok": True})


@require_POST
def reagir_view(request):
    """Manda um emoji para a tela de todo mundo.

    De propósito, a view mais barata do sistema: **nenhuma escrita no banco**.
    Ela só soma num contador em memória, que um laço despeja de meio em meio
    segundo — é isso que faz 50 pessoas martelando emoji não atrapalharem quem
    está dando lance.
    """
    participante = participante_atual(request)
    if not participante:
        return JsonResponse({"ok": False}, status=401)
    if participante.bloqueado:
        return JsonResponse({"ok": False}, status=403)

    # Descartar reação NÃO é erro: quem tocou já viu o próprio emoji subir (a
    # tela desenha na hora), e o que se ganha é processador para o lance e para
    # a voz ao vivo. Por isso a resposta é 200 mesmo quando o freio segura —
    # avisar a tela só faria o celular tentar de novo, que é o oposto.
    if not reacoes.aceitar(participante.id):
        return JsonResponse({"ok": True, "freio": True})

    dados = _json(request)
    ok = reacoes.registrar(dados.get("emoji"), dados.get("quantos"))
    return JsonResponse({"ok": ok}, status=200 if ok else 400)


def meus_arremates_view(request):
    """Lista do participante — com o que é **privado** (o Pix é dele).

    Nada disso passa pelo broadcast: sai só aqui, autenticado pela sessão.
    """
    participante = participante_atual(request)
    if not participante:
        return JsonResponse({"ok": False}, status=401)

    itens = []
    for a in _arremates_do(participante):
        itens.append(
            {
                "id": a.id,
                "lote": a.lote.nome,
                "foto": est._foto(a.lote.foto_mini) or est._foto(a.lote.foto),
                "valor": str(a.valor),
                "status": a.status,
                "status_texto": a.get_status_display(),
                "segundos": a.segundos_para_pagar,
                "expira_em": est.iso(a.expira_em),
                "tem_pix": bool(a.pagamento_id and a.pagamento.qr_code),
                "combinado": a.status == "combinado",
            }
        )
    # Sem Mercado Pago configurado, Pix nenhum vai nascer — e a tela precisa
    # dizer isso, em vez de prometer um "gerando…" que nunca termina. O leilão
    # segue: o locutor combina o pagamento e dá baixa manual.
    return JsonResponse(
        {
            "ok": True,
            "arremates": itens,
            "pix_possivel": ConfigLeilao.get_solo().configurado,
        }
    )


def arremate_pix_view(request, pk):
    """Código copia e cola + QR do arremate. **Só do dono.**"""
    participante = participante_atual(request)
    if not participante:
        return JsonResponse({"ok": False}, status=401)
    arremate = (
        Arremate.objects.select_related("pagamento", "lote")
        .filter(pk=pk, participante=participante)
        .first()
    )
    if not arremate:
        raise Http404

    pagamento = arremate.pagamento
    if not pagamento:
        if not ConfigLeilao.get_solo().configurado:
            return JsonResponse({
                "ok": False,
                "gerando": False,
                "msg": "O pagamento deste leilão é combinado com a organização.",
            })
        # Pode estar sendo gerado ainda (thread de fundo) — a tela espera e tenta de novo.
        return JsonResponse({"ok": False, "gerando": True, "msg": "Gerando seu Pix…"})

    return JsonResponse(
        {
            "ok": True,
            "lote": arremate.lote.nome,
            "valor": str(arremate.valor),
            "status": arremate.status,
            "segundos": arremate.segundos_para_pagar,
            "copia_e_cola": pagamento.qr_code,
            "qr_base64": pagamento.qr_code_base64,
        }
    )


def arremate_conferir_view(request, pk):
    """Pergunta ao Mercado Pago se caiu (reforço do webhook, que atrasa)."""
    participante = participante_atual(request)
    if not participante:
        return JsonResponse({"ok": False}, status=401)
    arremate = (
        Arremate.objects.select_related("pagamento", "lote")
        .filter(pk=pk, participante=participante)
        .first()
    )
    if not arremate:
        raise Http404
    pago = servicos.conferir_pagamento(arremate)
    arremate.refresh_from_db()
    return JsonResponse({"ok": True, "pago": pago, "status": arremate.status})


# ---------------------------------------------------------------------------
# Webhook do Mercado Pago
# ---------------------------------------------------------------------------
@csrf_exempt
def webhook_mp_view(request):
    """Aviso de pagamento. **Nunca** devolve erro ao Mercado Pago.

    Mesma regra dos webhooks do clube: público, idempotente e silencioso. Um
    500 aqui faz o MP reenviar em cascata e não conserta nada.
    """
    try:
        corpo = _json(request)
        data_id = str(
            (corpo.get("data") or {}).get("id")
            or request.GET.get("data.id")
            or request.GET.get("id")
            or ""
        )
        if not data_id:
            return HttpResponse("sem id", status=200)

        cfg = ConfigLeilao.get_solo()
        if cfg.webhook_secret:
            valida = mercadopago.validar_assinatura(
                cfg,
                x_signature=request.headers.get("x-signature", ""),
                x_request_id=request.headers.get("x-request-id", ""),
                data_id=data_id,
            )
            if not valida:
                logger.warning("Leilão: webhook do MP com assinatura inválida (%s).", data_id)
                return HttpResponse("ok", status=200)

        pagamento = PagamentoLeilao.objects.filter(mp_payment_id=data_id).first()
        if not pagamento:
            # Pode ser aviso de um pagamento do clube chegando aqui por engano.
            return HttpResponse("ok", status=200)

        resultado = mercadopago.consultar_pagamento(cfg, data_id)
        if resultado.get("ok"):
            servicos._aplicar_retorno(pagamento, resultado)
    except Exception:  # noqa: BLE001 — webhook nunca estoura para fora
        logger.exception("Leilão: falha ao tratar webhook do Mercado Pago")
    return HttpResponse("ok", status=200)




# ===========================================================================
# Equipe do leilão — três áreas (ver `leilao/papeis.py`)
#
#   Preparação → cadastra itens, monta a fila, configura
#   Locutor    → conduz o pregão
#   Caixa      → confere pagamento e cuida da entrega
#
# O Diretor abre as três. Cada view diz de qual área ela é; nenhuma confia no
# menu para se proteger (esconder o botão não barra quem digita a URL).
# ===========================================================================
def entrar_equipe_view(request):
    """Login da equipe. Depois de entrar, cada um cai na sua área."""
    if request.user.is_authenticated and papeis.papeis_do(request.user):
        return redirect("leilao:equipe")
    if request.method == "POST":
        chave = _ip_do(request)
        if equipe.login_barrado(chave):
            # A senha padrão é curta e o usuário sai do nome: sem freio, dá para
            # varrer da internet até acertar — e quem acertasse primeiro
            # trocaria a senha, trancando a pessoa de verdade do lado de fora.
            messages.error(
                request, "Muitas tentativas. Espere alguns minutos e tente de novo."
            )
            return render(request, "leilao/equipe_entrar.html")

        usuario = authenticate(
            request,
            username=request.POST.get("usuario", "").strip(),
            password=request.POST.get("senha", ""),
        )
        if usuario and usuario.is_staff:
            equipe.limpar_tentativas(chave)
            auth_login(request, usuario)
            return redirect("leilao:equipe")
        equipe.registrar_erro_de_login(chave)
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "leilao/equipe_entrar.html")


def _ip_do(request):
    """O IP de quem está batendo na porta, atrás do Nginx.

    `X-Forwarded-For` vem do nosso próprio proxy; o primeiro da lista é o
    cliente. Sem ele (desenvolvimento), o `REMOTE_ADDR` serve.
    """
    encaminhado = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "?"


@require_POST
def sair_equipe_view(request):
    auth_logout(request)
    return redirect("leilao:entrar_equipe")


@login_required
def equipe_view(request):
    """Porta de entrada da equipe.

    Quem tem **uma** área só vai direto para ela — no dia do evento ninguém quer
    um menu entre o login e o trabalho. Com mais de uma, escolhe.
    """
    # Mesma guarda do `papeis.exige`: com a senha padrão na mão, a única tela
    # que abre é a da troca. Aqui o decorator é o `login_required` puro, então a
    # checagem precisa ser explícita.
    if papeis.senha_pendente(request.user):
        return redirect("leilao:trocar_senha")

    meus = papeis.papeis_do(request.user)
    if not meus:
        messages.error(request, "Sua conta ainda não tem papel no leilão.")
        return redirect("leilao:entrar_equipe")

    areas = papeis.menu_do(request.user)
    if len(areas) == 1:
        return redirect(areas[0]["rota"])

    leilao = Leilao.ao_vivo()
    return render(
        request,
        "leilao/equipe.html",
        {
            "areas": areas,
            "leilao_ao_vivo": leilao,
            "a_pagar": Arremate.objects.filter(status="aguardando").count(),
            "a_entregar": Arremate.objects.filter(
                status="pago", entregue_em__isnull=True
            ).count(),
        },
    )


# ---------------------------------------------------------------------------
# Área do LOCUTOR
# ---------------------------------------------------------------------------
@papeis.exige("locutor")
def locutor_view(request):
    """A mesa: pregão, cronômetro, fila, participantes, chat e microfone.

    **Sem pagamentos**: quem bate o martelo não é quem confirma o recebimento, e
    o locutor já tem as mãos cheias falando e olhando o cronômetro.
    """
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        messages.info(request, "Nenhum leilão criado ainda.")
        return redirect("leilao:equipe")

    return render(
        request,
        "leilao/locutor.html",
        {
            "leilao": leilao,
            "estado_inicial": json.dumps(
                est.estado_publico(leilao), ensure_ascii=False, default=str
            ),
            "lotes": leilao.lotes.all().order_by("ordem", "id"),
            "painel": _painel_locutor(leilao),
        },
    )


def _painel_locutor(leilao):
    """Quem está no leilão — para a moderação do pregão."""
    return {
        "participantes": Participante.objects.annotate(
            n_lances=Count(
                "lances", filter=Q(lances__lote__leilao=leilao, lances__cancelado=False)
            ),
            n_arremates=Count("arremates", filter=Q(arremates__lote__leilao=leilao)),
        ).order_by("-n_lances", "nome")[:200],
    }


@papeis.exige("locutor")
def locutor_dados_view(request):
    """Estado + histórico do pregão para a mesa (recarga por `fetch`)."""
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return JsonResponse({"ok": False})
    lote = leilao.lote_atual
    historico = []
    if lote:
        historico = [
            {**est.lance_publico(x), "cancelado": x.cancelado}
            for x in lote.lances_da_rodada()
            .select_related("participante")
            .order_by("-criado_em", "-id")[:50]
        ]
    # A FILA vem por aqui, não pelo broadcast: o público não pode saber quantos
    # itens faltam (muda como a pessoa dá lance), mas a mesa precisa ver.
    fila = [
        {
            "id": x.id,
            "numero": x.numero,
            "nome": x.nome,
            "lance_inicial": str(x.lance_inicial),
            "voltas": x.voltas,
        }
        for x in leilao.lotes.filter(status="fila").order_by("ordem", "id")[:40]
    ]
    # O número do item em pregão vem por AQUI, nunca pelo broadcast: "item 12"
    # conta que existem pelo menos 12 itens, e quantos faltam é justamente o que
    # o público não pode saber (muda como a pessoa dá lance).
    em_pregao = leilao.lote_atual
    return JsonResponse(
        {
            "ok": True,
            "estado": est.estado_publico(leilao),
            "historico": historico,
            "numero_atual": em_pregao.numero if em_pregao else None,
            "fila": fila,
            "restam_na_fila": leilao.lotes.filter(status="fila").count(),
            # O chat do participante zera a cada intervalo; o do locutor, não.
            # Ele precisa do fio inteiro da noite para moderar.
            "chat": [
                est.mensagem_publica(m)
                for m in leilao.mensagens.filter(removida=False)
                .select_related("participante")
                .order_by("-criado_em", "-id")[:120]
            ][::-1],
        }
    )


# Qual área pode disparar cada ação da mesa. É aqui que "o locutor não mexe em
# dinheiro" deixa de ser combinado e vira regra: `pago` é do caixa.
ACOES_AREAS = {
    "abrir": ("locutor",),
    "fechar": ("locutor",),
    "chat": ("locutor",),
    "aviso": ("locutor",),
    "mover": ("locutor", "preparacao"),
    "bloquear": ("locutor", "caixa"),
    "pago": ("caixa",),
    "combinado": ("caixa",),
    # Esticar o prazo é conversa de caixa ("me dá mais uns minutos"), não de
    # quem está com o martelo na mão.
    "prazo": ("caixa",),
    "entregue": ("caixa",),
    # Quadro de entregas: arrastar uma parada e nomear a coluna.
    "entrega_mover": ("caixa",),
    "entrega_nome": ("caixa",),
}


@login_required
@require_POST
def locutor_acao_view(request):
    """Todos os botões da equipe num POST só (`acao` diz qual)."""
    dados = _json(request) or request.POST
    acao = dados.get("acao")

    permitidas = ACOES_AREAS.get(acao)
    if permitidas is None:
        return JsonResponse({"ok": False, "msg": "Ação desconhecida."}, status=400)
    # A trava da senha provisória vale para o POST também: esconder a tela não
    # protege nada se o botão continuar respondendo por `fetch`.
    if papeis.senha_pendente(request.user):
        return JsonResponse(
            {"ok": False, "msg": "Troque a sua senha para continuar."}, status=403
        )
    meus = papeis.papeis_do(request.user)
    if not meus.intersection(permitidas):
        rotulos = " ou ".join(papeis.AREAS[a][0] for a in permitidas)
        return JsonResponse(
            {"ok": False, "msg": f"Esta ação é de {rotulos}."}, status=403
        )

    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return JsonResponse({"ok": False, "msg": "Nenhum leilão."}, status=404)

    lote_id = dados.get("lote")
    lote = get_object_or_404(Lote, pk=lote_id, leilao=leilao) if lote_id else None

    if acao == "abrir":
        if not lote:
            lote = leilao.lotes.filter(status="fila").order_by("ordem", "id").first()
        if not lote:
            return JsonResponse({"ok": False, "msg": "A fila está vazia."}, status=409)
        servicos.abrir_lote(lote)
        return JsonResponse({"ok": True, "msg": f"{lote.nome} em pregão!"})

    if acao == "fechar":
        lote = lote or leilao.lote_atual
        if not lote:
            return JsonResponse({"ok": False, "msg": "Nenhum lote em pregão."}, status=409)
        servicos.fechar_lote(lote, motivo="locutor")
        return JsonResponse({"ok": True, "msg": "Vendido!"})

    if acao == "chat":
        segundos = int(dados.get("segundos") or leilao.chat_segundos or 120)
        if dados.get("fechar"):
            servicos.fechar_chat(leilao)
            return JsonResponse({"ok": True, "msg": "Chat fechado."})
        servicos.abrir_chat(leilao, segundos)
        return JsonResponse({"ok": True, "msg": "Chat aberto."})

    if acao == "aviso":
        servicos.enviar_mensagem(leilao, None, dados.get("texto"))
        return JsonResponse({"ok": True, "msg": "Aviso enviado."})

    if acao == "mover":
        if not lote:
            return JsonResponse({"ok": False, "msg": "Lote não informado."}, status=400)
        _mover_lote(lote, dados.get("direcao") or "cima")
        return JsonResponse({"ok": True, "msg": "Fila reordenada."})

    if acao == "bloquear":
        participante = get_object_or_404(Participante, pk=dados.get("participante"))
        # Bloqueia a PESSOA, não o registro: quem entrou de dois aparelhos tem
        # dois cadastros, e bloquear só o que está na tela deixaria o outro
        # dando lance.
        bloqueado, quantos = servicos.bloquear_pessoa(
            participante, not participante.bloqueado
        )
        recado = "Bloqueado." if bloqueado else "Desbloqueado."
        if quantos > 1:
            recado += f" ({quantos} cadastros da mesma pessoa)"
        return JsonResponse({"ok": True, "msg": recado, "bloqueado": bloqueado})

    if acao == "entrega_mover":
        try:
            pessoa_id = int(dados.get("participante") or 0)
            numero = int(dados.get("entregador") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "msg": "Parada inválida."}, status=400)
        # A parada tem de ser deste leilão e estar de fato a entregar: sem esta
        # conferência, um POST forjado encheria o quadro de gente que não tem
        # nada para receber.
        pendente = Arremate.objects.filter(
            lote__leilao=leilao, participante_id=pessoa_id,
            status="pago", entregue_em__isnull=True,
        ).exists()
        if not pendente:
            return JsonResponse(
                {"ok": False, "msg": "Essa pessoa não tem entrega pendente."}, status=404
            )
        if numero and not leilao.entregadores.filter(numero=numero).exists():
            return JsonResponse(
                {"ok": False, "msg": "Esse entregador não existe."}, status=400
            )
        AtribuicaoEntrega.objects.update_or_create(
            leilao=leilao, participante_id=pessoa_id,
            defaults={"entregador": numero},
        )
        return JsonResponse({"ok": True, **_resumo_colunas(leilao)})

    if acao == "entrega_nome":
        try:
            numero = int(dados.get("entregador") or 0)
        except (TypeError, ValueError):
            numero = 0
        coluna = leilao.entregadores.filter(numero=numero).first()
        if coluna is None:
            return JsonResponse(
                {"ok": False, "msg": "Esse entregador não existe."}, status=404
            )
        coluna.nome = (dados.get("nome") or "").strip()[:80]
        coluna.save(update_fields=["nome"])
        return JsonResponse(
            {"ok": True, "rotulo": coluna.rotulo, **_resumo_colunas(leilao)}
        )

    if acao == "pago":
        arremate = get_object_or_404(Arremate, pk=dados.get("arremate"))
        servicos.marcar_pago(arremate, manual=True)
        return JsonResponse({"ok": True, "msg": "Marcado como pago."})

    if acao == "combinado":
        arremate = get_object_or_404(Arremate, pk=dados.get("arremate"))
        servicos.marcar_combinado(
            arremate, request.user, (dados.get("observacao") or "").strip()
        )
        return JsonResponse(
            {"ok": True, "msg": "Combinado — o item não volta para a fila."}
        )

    if acao == "prazo":
        arremate = get_object_or_404(Arremate, pk=dados.get("arremate"))
        if arremate.status != "aguardando":
            return JsonResponse(
                {"ok": False, "msg": "Só dá para esticar o prazo de quem ainda está no relógio."},
                status=409,
            )
        try:
            minutos = int(dados.get("minutos") or 15)
        except (TypeError, ValueError):
            # Toda recusa desta view é JSON; um 500 de HTML aqui deixaria a tela
            # sem explicação nenhuma no meio do evento.
            return JsonResponse({"ok": False, "msg": "Tempo inválido."}, status=400)
        servicos.estender_prazo(arremate, minutos)
        arremate.refresh_from_db()
        return JsonResponse(
            {
                "ok": True,
                "msg": "Prazo esticado — o Pix novo chega em segundos.",
                "segundos": arremate.segundos_para_pagar,
            }
        )

    if acao == "entregue":
        arremate = get_object_or_404(Arremate, pk=dados.get("arremate"))
        return JsonResponse(_marcar_entrega(arremate, request.user, dados))

    return JsonResponse({"ok": False, "msg": "Ação desconhecida."}, status=400)


def _mover_lote(lote, direcao):
    """Troca a ordem com o vizinho na fila."""
    lista = list(lote.leilao.lotes.filter(status="fila").order_by("ordem", "id"))
    if lote not in lista:
        return
    i = lista.index(lote)
    j = i - 1 if direcao == "cima" else i + 1
    if j < 0 or j >= len(lista):
        return
    outro = lista[j]
    lote.ordem, outro.ordem = outro.ordem, lote.ordem
    lote.save(update_fields=["ordem"])
    outro.save(update_fields=["ordem"])


# ---------------------------------------------------------------------------
# Área do CAIXA — pagamentos e entrega
# ---------------------------------------------------------------------------
def _marcar_entrega(arremate, usuario, dados):
    """Marca (ou desmarca) a entrega de um arremate.

    **Só entrega o que está pago.** Mandar o item antes de o dinheiro cair é
    justamente o erro que o prazo de 15 minutos existe para evitar.
    """
    if dados.get("desfazer"):
        arremate.entregue_em = None
        arremate.entregue_por = None
        arremate.save(update_fields=["entregue_em", "entregue_por"])
        return {"ok": True, "msg": "Entrega desmarcada.", "entregue": False}

    if arremate.status != "pago":
        return {"ok": False, "msg": "Este item ainda não foi pago."}

    arremate.entregue_em = timezone.now()
    arremate.entregue_por = usuario
    obs = (dados.get("observacao") or "").strip()[:200]
    if obs:
        arremate.entrega_obs = obs
    arremate.save(update_fields=["entregue_em", "entregue_por", "entrega_obs"])
    return {"ok": True, "msg": "Entrega registrada!", "entregue": True}


@papeis.exige("caixa")
def caixa_view(request):
    """Quem pagou, quem falta pagar e o que há para entregar."""
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        messages.info(request, "Nenhum leilão criado ainda.")
        return redirect("leilao:equipe")

    arremates = (
        Arremate.objects.filter(lote__leilao=leilao)
        .select_related("lote", "participante", "pagamento")
        .order_by("-criado_em")
    )
    resumo = arremates.aggregate(
        total=Count("id"),
        pagos=Count("id", filter=Q(status="pago")),
        aguardando=Count("id", filter=Q(status="aguardando")),
        combinados=Count("id", filter=Q(status="combinado")),
        expirados=Count("id", filter=Q(status="expirado")),
        arrecadado=Sum("valor", filter=Q(status="pago")),
        a_receber=Sum("valor", filter=Q(status__in=["aguardando", "combinado"])),
    )

    a_entregar = [a for a in arremates if a.a_entregar]
    entregues = [a for a in arremates if a.entregue]

    # A divisão em si saiu daqui: ela virou o **quadro** (`entregas_quadro_view`),
    # onde a equipe arrasta e o resultado fica salvo. Aqui ficou só a porta de
    # entrada — duas divisões na mesma tela, uma salva e outra não, seria a
    # receita para mandar ao voluntário a que não valia.
    return render(
        request,
        "leilao/caixa.html",
        {
            "leilao": leilao,
            "resumo": resumo,
            "arremates": arremates,
            "a_entregar": a_entregar,
            "entregues": entregues,
            "roteiro": _texto_roteiro_entregas(leilao, a_entregar),
            "entregadores": leilao.entregadores.count(),
        },
    )


# ---------------------------------------------------------------------------
# Quadro de entregas — a equipe arrasta quem leva o quê
#
# A divisão automática não sabe que um bairro é perto do outro: ela compara
# NOMES de bairro, e é tudo o que ela pode fazer sem mapa. Quem sabe que "isso
# aqui é tudo o mesmo lado" é a equipe, que conhece a cidade.
#
# Então a divisão virou **ponto de partida** e a palavra final é do quadro: o
# quadro abre já preenchido por bairro e a equipe arrasta o que estiver errado.
# Cada arrastada salva na hora — a noite do evento não é hora de descobrir que
# faltou apertar "salvar".
# ---------------------------------------------------------------------------
def _pendentes_do_leilao(leilao):
    """Os arremates a entregar: pagos e ainda não entregues."""
    return [
        a
        for a in Arremate.objects.filter(lote__leilao=leilao)
        .select_related("lote", "participante")
        .order_by("-criado_em")
        if a.a_entregar
    ]


def _ajustar_entregadores(leilao, quantos):
    """Deixa exatamente `quantos` colunas, numeradas de 1 a N.

    Diminuir **apaga a coluna, não a atribuição**: as paradas dela voltam para
    "a distribuir" (é o que `entregas.quadro` faz com número que não existe
    mais) e o trabalho das outras colunas fica de pé. Aumentar de novo devolve a
    coluna vazia — o que estava nela já voltou para a fila e é arrastado de novo,
    que é melhor do que ressuscitar uma divisão que a equipe já desfez.
    """
    atuais = {e.numero: e for e in leilao.entregadores.all()}
    for numero in range(1, quantos + 1):
        if numero not in atuais:
            EntregadorLeilao.objects.create(leilao=leilao, numero=numero)
    leilao.entregadores.filter(numero__gt=quantos).delete()


def _semear_quadro(leilao, quantos):
    """Primeira montagem: a divisão por bairro entra como ponto de partida.

    Só na primeira — depois disso, parada nova (quem pagou mais tarde) cai em
    "a distribuir". Redividir por cima apagaria o trabalho manual, que é
    justamente o que o quadro existe para guardar.
    """
    pendentes = _pendentes_do_leilao(leilao)
    if not pendentes:
        return
    for numero, paradas in enumerate(entregas.dividir(pendentes, quantos), start=1):
        for parada in paradas:
            AtribuicaoEntrega.objects.update_or_create(
                leilao=leilao, participante=parada["pessoa"],
                defaults={"entregador": numero},
            )


def _colunas_quadro(leilao):
    """`(a_distribuir, colunas)` — cada coluna com o texto pronto do WhatsApp.

    O texto vem **do servidor**, como todo texto copiável do projeto: depois de
    cada arrastada o servidor devolve o texto novo, e o botão de copiar nunca
    monta frase nenhuma.
    """
    lista = list(leilao.entregadores.all())
    atribuicoes = dict(
        AtribuicaoEntrega.objects.filter(leilao=leilao)
        .values_list("participante_id", "entregador")
    )
    colunas = entregas.quadro(_pendentes_do_leilao(leilao), atribuicoes, len(lista))
    montadas = []
    for e in lista:
        paradas = colunas.get(e.numero, [])
        montadas.append({
            "entregador": e,
            "paradas": paradas,
            "itens": sum(len(p["itens"]) for p in paradas),
            "regioes": sorted({p["rotulo"] for p in paradas}),
            "texto": entregas.texto_da_rota(
                leilao, e.numero, paradas, len(lista), nome=e.nome
            ),
        })
    return colunas.get(0, []), montadas


def _resumo_colunas(leilao):
    """O que o JS precisa depois de uma arrastada: contagens e textos novos."""
    a_distribuir, colunas = _colunas_quadro(leilao)
    return {
        "a_distribuir": len(a_distribuir),
        "colunas": [
            {
                "numero": c["entregador"].numero,
                "rotulo": c["entregador"].rotulo,
                "paradas": len(c["paradas"]),
                "itens": c["itens"],
                "regioes": c["regioes"],
                "texto": c["texto"],
            }
            for c in colunas
        ],
    }


@papeis.exige("caixa")
def entregas_quadro_view(request):
    """O quadro: uma coluna por entregador e as paradas para arrastar."""
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        messages.info(request, "Nenhum leilão criado ainda.")
        return redirect("leilao:equipe")

    try:
        pedido = int(request.GET.get("entregadores") or 0)
    except (TypeError, ValueError):
        pedido = 0
    pedido = max(0, min(20, pedido))
    if pedido:
        _ajustar_entregadores(leilao, pedido)

    quantos = leilao.entregadores.count()
    if not quantos:
        messages.info(request, "Diga quantos entregadores vocês têm para montar o quadro.")
        return redirect("leilao:caixa")

    if not AtribuicaoEntrega.objects.filter(leilao=leilao).exists():
        _semear_quadro(leilao, quantos)

    a_distribuir, colunas = _colunas_quadro(leilao)
    return render(
        request,
        "leilao/entregas_quadro.html",
        {
            "leilao": leilao,
            "a_distribuir": a_distribuir,
            "colunas": colunas,
            "quantos": quantos,
        },
    )


@papeis.exige("caixa")
@require_POST
def entregas_redistribuir_view(request):
    """Joga fora o que foi arrastado e refaz a divisão por bairro.

    Existe para a equipe que se perdeu no meio e quer recomeçar. Apaga trabalho,
    então o botão pergunta antes.
    """
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return redirect("leilao:caixa")
    AtribuicaoEntrega.objects.filter(leilao=leilao).delete()
    _semear_quadro(leilao, leilao.entregadores.count())
    messages.success(request, "Quadro refeito pela divisão por bairro.")
    return redirect("leilao:entregas_quadro")


def _texto_roteiro_entregas(leilao, pendentes):
    """Roteiro de entrega pronto para copiar (etiqueta/rota).

    Vem **pronto do servidor**, como manda a convenção do projeto — o JS só
    copia. Texto raspado do HTML quebraria no próximo ajuste visual.

    **Leva nome e endereço**: é documento de trabalho de quem entrega, não
    texto para grupo aberto.
    """
    if not pendentes:
        return ""

    linhas = [f"*ENTREGAS — {leilao.nome}*", f"{len(pendentes)} item(ns) a entregar", ""]
    por_pessoa = {}
    for a in pendentes:
        por_pessoa.setdefault(a.participante_id, {"p": a.participante, "itens": []})
        por_pessoa[a.participante_id]["itens"].append(a)

    for i, dados in enumerate(por_pessoa.values(), start=1):
        p = dados["p"]
        linhas.append(f"*{i}. {p.nome}*")
        linhas.append(f"📱 {p.whatsapp}")
        endereco = p.endereco_uma_linha
        if endereco:
            linhas.append(f"📍 {endereco}")
        for a in dados["itens"]:
            # O número vem PRIMEIRO: quem separa as caixas procura a etiqueta,
            # não o nome do item. É o único dado desta linha que existe no
            # mundo físico.
            linhas.append(f"   • nº {a.lote.numero} — {a.lote.nome} — R$ {a.valor}")
        linhas.append("")
    return "\n".join(linhas).strip()


# ---------------------------------------------------------------------------
# Área da PREPARAÇÃO — leilões, itens e configuração
# ---------------------------------------------------------------------------
@papeis.exige("preparacao")
def preparacao_view(request):
    """Lista de leilões: criar, montar, colocar no ar."""
    if request.method == "POST":
        form = LeilaoForm(request.POST)
        if form.is_valid():
            novo = form.save(commit=False)
            novo.criado_por = request.user
            novo.save()
            messages.success(request, f"“{novo.nome}” criado. Agora cadastre os itens.")
            return redirect("leilao:lotes", leilao_id=novo.pk)
        messages.error(request, "Confira os campos destacados.")
    else:
        form = LeilaoForm()

    leiloes = Leilao.objects.annotate(
        n_lotes=Count("lotes", distinct=True),
        n_vendidos=Count("lotes", filter=Q(lotes__status="vendido"), distinct=True),
    ).order_by("-criado_em")

    return render(
        request, "leilao/preparacao.html", {"form": form, "leiloes": leiloes}
    )


@papeis.exige("preparacao")
@require_POST
def leilao_status_view(request, pk):
    """Coloca no ar / encerra. **Só um leilão ao vivo por vez.**"""
    leilao = get_object_or_404(Leilao, pk=pk)
    novo = request.POST.get("status")
    if novo not in {"rascunho", "ao_vivo", "encerrado"}:
        raise Http404
    if novo == "ao_vivo" and not leilao.lotes.exists():
        messages.error(request, "Cadastre ao menos um item antes de colocar no ar.")
        return redirect("leilao:lotes", leilao_id=leilao.pk)

    # Passa pelo serviço para que as telas que estão esperando sejam avisadas.
    servicos.mudar_status(leilao, novo)
    messages.success(request, f"{leilao.nome}: {leilao.get_status_display()}.")
    return redirect("leilao:preparacao")


@papeis.exige("preparacao")
def lotes_view(request, leilao_id):
    """Itens **de um leilão específico** (o id vem na URL, nunca adivinhado)."""
    leilao = get_object_or_404(Leilao, pk=leilao_id)
    return render(
        request,
        "leilao/lotes.html",
        {"leilao": leilao, "lotes": leilao.lotes.all().order_by("ordem", "id")},
    )


@papeis.exige("preparacao")
def lote_form_view(request, leilao_id=None, pk=None):
    """Cadastro/edição de item.

    O leilão vem **da URL**. Antes, a view adivinhava ("o que está ao vivo, ou o
    mais recente") — e assim, preparar o leilão de dezembro com o de novembro
    rolando jogava os itens novos **dentro do pregão em andamento**.
    """
    if pk:
        lote = get_object_or_404(Lote, pk=pk)
        leilao = lote.leilao
    else:
        lote = None
        leilao = get_object_or_404(Leilao, pk=leilao_id)

    if request.method == "POST":
        form = LoteForm(request.POST, request.FILES, instance=lote)
        if form.is_valid():
            novo = form.save(commit=False)
            novo.leilao = leilao
            if not pk:
                ultima = leilao.lotes.order_by("-ordem").first()
                novo.ordem = (ultima.ordem + 1) if ultima else 1
            novo.save()
            preparar_foto(novo)
            messages.success(request, "Item salvo!")
            if "salvar_e_novo" in request.POST:
                return redirect("leilao:lote_novo", leilao_id=leilao.pk)
            return redirect("leilao:lotes", leilao_id=leilao.pk)
        messages.error(request, "Confira os campos destacados.")
    else:
        form = LoteForm(instance=lote)

    return render(
        request, "leilao/lote_form.html", {"form": form, "lote": lote, "leilao": leilao}
    )


@papeis.exige("preparacao")
@require_POST
def lote_excluir_view(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    leilao_id = lote.leilao_id
    if lote.lances.exists() or lote.arremates.exists():
        messages.error(request, "Este item já teve lance — não dá para excluir.")
    else:
        lote.delete()
        messages.success(request, "Item removido.")
    return redirect("leilao:lotes", leilao_id=leilao_id)


@papeis.exige("preparacao")
def config_view(request):
    cfg = ConfigLeilao.get_solo()
    if request.method == "POST":
        form = ConfigLeilaoForm(request.POST, instance=cfg)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.atualizado_por = request.user
            obj.save()
            messages.success(request, "Configuração salva.")
            return redirect("leilao:config")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = ConfigLeilaoForm(instance=cfg)
    return render(request, "leilao/config.html", {"form": form, "config": cfg})


# ---------------------------------------------------------------------------
# Área do DIRETOR — contas da equipe
# ---------------------------------------------------------------------------
def _pode_mexer(request, alvo):
    """Guarda das ações sobre uma conta. Devolve o motivo da recusa, ou "".

    Duas travas, as duas para o diretor não se trancar do lado de fora nem
    mexer em quem está acima dele:

    - **ninguém desliga a própria conta** — seria perder o acesso no meio do
      evento, com a tela aberta;
    - **conta de superusuário só é alterada por superusuário** — um diretor
      voluntário não reseta a senha de quem administra o sistema.
    """
    if alvo.is_superuser and not request.user.is_superuser:
        return "Esta conta é de administrador do sistema."
    return ""


@papeis.exige_diretor
def usuarios_view(request):
    """Cadastro da equipe: cria a conta com a senha padrão e dá as funções."""
    if request.method == "POST":
        form = UsuarioEquipeForm(request.POST)
        if form.is_valid():
            novo = equipe.criar_conta(
                form.cleaned_data["nome"],
                form.cleaned_data["papeis"],
                usuario=form.cleaned_data["usuario"],
                criado_por=request.user,
            )
            messages.success(
                request,
                f"{equipe.nome_de(novo)} cadastrada(o). Usuário: {novo.get_username()} · "
                f"senha: {equipe.SENHA_PADRAO} — ela troca no primeiro acesso.",
            )
            return redirect("leilao:usuarios")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = UsuarioEquipeForm()

    site_url = ConfigLeilao.get_solo().site_url
    pessoas = []
    for u in equipe.equipe():
        meus = papeis.papeis_do(u)
        conta = getattr(u, "conta_leilao", None)
        pessoas.append(
            {
                "user": u,
                "nome": equipe.nome_de(u),
                # A LINHA mostra o que a pessoa enxerga (`papeis_do`); as CAIXAS
                # de seleção mostram os grupos que ela tem de fato. São coisas
                # diferentes para quem é diretor: ele abre as três áreas sem
                # estar em nenhuma delas, e marcar tudo na edição faria parecer
                # que os grupos estão lá.
                "papeis": sorted(
                    set(u.groups.values_list("name", flat=True))
                    & set(equipe.PAPEIS_VALIDOS)
                ),
                # O que a linha mostra: o rótulo curto de cada função.
                "rotulos": [
                    papeis.AREAS[p][1] + " " + papeis.AREAS[p][0]
                    for p in papeis.ORDEM
                    if p in meus
                ] + (["👑 Diretor"] if papeis.DIRETOR in meus else []),
                "provisoria": bool(conta and conta.senha_provisoria),
                "recado": equipe.recado_de_acesso(u, site_url),
                "eu": u.pk == request.user.pk,
            }
        )

    return render(
        request,
        "leilao/usuarios.html",
        {
            "form": form,
            "pessoas": pessoas,
            "escolhas": equipe.escolhas_de_papel(),
            "senha_padrao": equipe.SENHA_PADRAO,
        },
    )


@papeis.exige_diretor
@require_POST
def usuario_acao_view(request, pk):
    """Funções, reset de senha e ligar/desligar a conta."""
    User = get_user_model()
    alvo = get_object_or_404(User, pk=pk)
    acao = request.POST.get("acao")

    recusa = _pode_mexer(request, alvo)
    if recusa:
        messages.error(request, recusa)
        return redirect("leilao:usuarios")

    if acao == "papeis":
        escolhidos = request.POST.getlist("papeis")
        # Tirar o próprio "diretor" é perder esta tela — e com ela o caminho de
        # volta. O erro seria descoberto no clique seguinte, sem saída.
        if alvo.pk == request.user.pk and papeis.DIRETOR not in escolhidos:
            messages.error(request, "Você não pode tirar a sua própria função de diretor.")
            return redirect("leilao:usuarios")
        equipe.definir_papeis(alvo, escolhidos)
        messages.success(request, f"Funções de {equipe.nome_de(alvo)} atualizadas.")

    elif acao == "resetar":
        equipe.resetar_senha(alvo)
        messages.success(
            request,
            f"Senha de {alvo.get_username()} voltou para {equipe.SENHA_PADRAO} — "
            "ela escolhe outra ao entrar.",
        )

    elif acao == "ativo":
        if alvo.pk == request.user.pk:
            messages.error(request, "Você não pode desligar a sua própria conta.")
            return redirect("leilao:usuarios")
        alvo.is_active = not alvo.is_active
        alvo.save(update_fields=["is_active"])
        messages.success(
            request,
            f"{equipe.nome_de(alvo)} {'liberada(o)' if alvo.is_active else 'desligada(o)'}.",
        )
    else:
        messages.error(request, "Ação desconhecida.")

    return redirect("leilao:usuarios")


@login_required
def trocar_senha_view(request):
    """A troca obrigatória do primeiro acesso — e a tela de trocar por vontade.

    Quem chega aqui pelas próprias pernas (já trocou um dia) também consegue
    trocar de novo: é a mesma tela, só sem a porta trancada atrás.
    """
    pendente = papeis.senha_pendente(request.user)

    if request.method == "POST":
        form = TrocarSenhaForm(request.POST)
        if form.is_valid():
            equipe.definir_senha(request.user, form.cleaned_data["senha"])
            # Sem isto o Django invalida a sessão ao trocar a senha e a pessoa
            # cai no login — logo depois de fazer o que o sistema exigiu.
            update_session_auth_hash(request, request.user)
            messages.success(request, "Senha trocada! Bom leilão.")
            return redirect("leilao:equipe")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = TrocarSenhaForm()

    return render(
        request,
        "leilao/trocar_senha.html",
        {"form": form, "pendente": pendente, "senha_padrao": equipe.SENHA_PADRAO},
    )


@papeis.exige("caixa")
def caixa_pix_view(request, pk):
    """O código Pix de um arremate, **para o caixa mandar para a pessoa**.

    Existe separada da `arremate_pix_view` (que é do dono) porque aqui quem
    pergunta é a equipe, e o que ela precisa é diferente: além do copia e cola,
    o **link do WhatsApp da pessoa com a mensagem pronta**. É a diferença entre
    "resolvi agora" e "depois eu vejo isso".
    """
    arremate = get_object_or_404(
        Arremate.objects.select_related("pagamento", "lote", "participante"), pk=pk
    )
    pagamento = arremate.pagamento
    if not pagamento or not pagamento.qr_code:
        if not ConfigLeilao.get_solo().configurado:
            return JsonResponse(
                {"ok": False, "msg": "Sem Mercado Pago configurado — o acerto é por fora."}
            )
        return JsonResponse({"ok": False, "gerando": True, "msg": "O Pix ainda está sendo gerado…"})

    return JsonResponse(
        {
            "ok": True,
            "arremate": arremate.id,
            "lote": arremate.lote.nome,
            "numero": arremate.lote.numero,
            "valor": str(arremate.valor),
            "status": arremate.status,
            "copia_e_cola": pagamento.qr_code,
            "whatsapp": arremate.participante.whatsapp_link,
            # A mensagem vem PRONTA do servidor, como o roteiro de entrega: o JS
            # só abre o WhatsApp com ela.
            "texto": _texto_pix_whatsapp(arremate, pagamento),
        }
    )


def _texto_pix_whatsapp(arremate, pagamento):
    """A mensagem que o caixa manda para quem vai pagar depois.

    O código Pix vai numa **linha sozinha, no fim**: é assim que a pessoa
    consegue segurar o dedo em cima dele e copiar no celular. Qualquer coisa
    depois dele atrapalha a seleção.
    """
    return "\n".join(
        [
            f"Oi, {arremate.participante.nome_curto}! Aqui é do leilão do clube.",
            f"Seu item: nº {arremate.lote.numero} — {arremate.lote.nome} (R$ {arremate.valor}).",
            "É só pagar com o Pix copia e cola abaixo 👇",
            "",
            pagamento.qr_code,
        ]
    )


@papeis.exige("preparacao")
def leilao_editar_view(request, pk):
    """Editar um leilão — inclusive **com ele no ar**.

    É o caminho de mudar a tela de boas-vindas no meio do evento ("começamos
    22h", "o Pix é na hora"). Ao salvar, o estado é publicado: as telas que já
    estão abertas se redesenham sozinhas, sem ninguém pedir para atualizar.
    """
    leilao = get_object_or_404(Leilao, pk=pk)
    if request.method == "POST":
        form = LeilaoForm(request.POST, instance=leilao)
        if form.is_valid():
            form.save()
            HUB.publicar("estado", est.estado_publico(Leilao.ao_vivo()))
            messages.success(request, f"“{leilao.nome}” atualizado.")
            return redirect("leilao:preparacao")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = LeilaoForm(instance=leilao)
    return render(
        request, "leilao/leilao_form.html", {"form": form, "leilao": leilao}
    )
