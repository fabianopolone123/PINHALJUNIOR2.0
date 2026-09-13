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
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core import mercadopago

from . import estado as est
from . import servicos
from .forms import ConfigLeilaoForm, EntrarForm, LeilaoForm, LoteForm
from .hub import HUB, garantir_laco, sse
from .imagens import preparar_foto
from .models import Arremate, ConfigLeilao, Leilao, Lote, PagamentoLeilao, Participante
from .sessao import entrar as sessao_entrar
from .sessao import participante_atual
from .sessao import sair as sessao_sair

logger = logging.getLogger(__name__)


def locutor_required(view):
    """Só a equipe do leilão. Usa o `is_staff` do Django."""

    @login_required
    def _wrap(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Esta área é da equipe do leilão.")
            return redirect("leilao:entrar_locutor")
        return view(request, *args, **kwargs)

    return _wrap


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
            participante = form.save()
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
    if HUB.conectados >= teto:
        return HttpResponse("Leilão lotado. Tente novamente em instantes.", status=503)

    ping = getattr(settings, "LEILAO_PING_SEGUNDOS", 15)
    montar = sync_to_async(
        lambda: est.estado_publico(Leilao.ao_vivo()), thread_sensitive=False
    )

    async def gerador():
        fila = HUB.assinar()
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
        return JsonResponse({"ok": False, "msg": "Nenhum leilão ao vivo."}, status=409)
    if not leilao.chat_aberto:
        return JsonResponse({"ok": False, "msg": "O chat está fechado agora."}, status=409)

    m = servicos.enviar_mensagem(leilao, participante, _json(request).get("texto"))
    if not m:
        return JsonResponse({"ok": False, "msg": "Mensagem vazia ou bloqueada."}, status=400)
    return JsonResponse({"ok": True})


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
                "msg": "O pagamento deste leilão é combinado com o locutor.",
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
# Locutor
# ===========================================================================
def entrar_locutor_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("leilao:locutor")
    if request.method == "POST":
        usuario = authenticate(
            request,
            username=request.POST.get("usuario", "").strip(),
            password=request.POST.get("senha", ""),
        )
        if usuario and usuario.is_staff:
            auth_login(request, usuario)
            return redirect("leilao:locutor")
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "leilao/locutor_entrar.html")


@require_POST
def sair_locutor_view(request):
    auth_logout(request)
    return redirect("leilao:entrar_locutor")


@locutor_required
def locutor_view(request):
    """A mesa do locutor: pregão, fila, pagamentos, participantes e chat."""
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return redirect("leilao:leiloes")

    return render(
        request,
        "leilao/locutor.html",
        {
            "leilao": leilao,
            "estado_inicial": json.dumps(
                est.estado_publico(leilao), ensure_ascii=False, default=str
            ),
            "lotes": leilao.lotes.all().order_by("ordem", "id"),
            "form_lote": LoteForm(),
            "painel": _painel_locutor(leilao),
        },
    )


def _painel_locutor(leilao):
    """Números da mesa: quanto foi batido, quanto entrou, quem deve."""
    arremates = Arremate.objects.filter(lote__leilao=leilao).select_related(
        "lote", "participante"
    )
    resumo = arremates.aggregate(
        total=Count("id"),
        pagos=Count("id", filter=Q(status="pago")),
        aguardando=Count("id", filter=Q(status="aguardando")),
        expirados=Count("id", filter=Q(status="expirado")),
        arrecadado=Sum("valor", filter=Q(status="pago")),
        a_receber=Sum("valor", filter=Q(status="aguardando")),
    )
    return {
        "resumo": resumo,
        "arremates": arremates.order_by("-criado_em")[:60],
        "participantes": Participante.objects.annotate(
            n_lances=Count("lances", filter=Q(lances__lote__leilao=leilao, lances__cancelado=False)),
            n_arremates=Count("arremates", filter=Q(arremates__lote__leilao=leilao)),
        ).order_by("-n_lances", "nome")[:200],
    }


@locutor_required
def locutor_dados_view(request):
    """Estado + histórico do pregão para a mesa (recarga por `fetch`)."""
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return JsonResponse({"ok": False})
    lote = leilao.lote_atual
    historico = []
    if lote:
        historico = [
            {
                **est.lance_publico(x),
                "cancelado": x.cancelado,
            }
            for x in lote.lances_da_rodada()
            .select_related("participante")
            .order_by("-criado_em", "-id")[:50]
        ]
    return JsonResponse(
        {"ok": True, "estado": est.estado_publico(leilao), "historico": historico}
    )


@locutor_required
@require_POST
def locutor_acao_view(request):
    """Todos os botões da mesa num POST só (`acao` diz qual)."""
    dados = _json(request) or request.POST
    acao = dados.get("acao")
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return JsonResponse({"ok": False, "msg": "Nenhum leilão."}, status=404)

    lote_id = dados.get("lote")
    lote = None
    if lote_id:
        lote = get_object_or_404(Lote, pk=lote_id, leilao=leilao)

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

    if acao in {"pausar", "retomar"}:
        lote = lote or leilao.lote_atual
        if not lote:
            return JsonResponse({"ok": False, "msg": "Nenhum lote em pregão."}, status=409)
        servicos.pausar_lote(lote, pausar=(acao == "pausar"))
        return JsonResponse({"ok": True, "msg": "Cronômetro " + ("pausado." if acao == "pausar" else "retomado.")})

    if acao == "tempo":
        lote = lote or leilao.lote_atual
        if not lote:
            return JsonResponse({"ok": False, "msg": "Nenhum lote em pregão."}, status=409)
        servicos.somar_tempo(lote, dados.get("segundos") or leilao.segundos_extra)
        return JsonResponse({"ok": True, "msg": "Tempo acrescentado."})

    if acao == "desfazer":
        lote = lote or leilao.lote_atual
        if not lote:
            return JsonResponse({"ok": False, "msg": "Nenhum lote em pregão."}, status=409)
        ok, msg = servicos.desfazer_ultimo_lance(lote)
        return JsonResponse({"ok": ok, "msg": msg}, status=200 if ok else 409)

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

    if acao == "pago":
        arremate = get_object_or_404(
            Arremate, pk=dados.get("arremate"), lote__leilao=leilao
        )
        servicos.marcar_pago(arremate, manual=True)
        return JsonResponse({"ok": True, "msg": "Marcado como pago."})

    if acao == "bloquear":
        participante = get_object_or_404(Participante, pk=dados.get("participante"))
        participante.bloqueado = not participante.bloqueado
        participante.save(update_fields=["bloqueado"])
        return JsonResponse(
            {
                "ok": True,
                "msg": ("Bloqueado." if participante.bloqueado else "Desbloqueado."),
                "bloqueado": participante.bloqueado,
            }
        )

    return JsonResponse({"ok": False, "msg": "Ação desconhecida."}, status=400)


def _mover_lote(lote, direcao):
    """Troca a ordem com o vizinho na fila."""
    vizinhos = lote.leilao.lotes.filter(status="fila").order_by("ordem", "id")
    lista = list(vizinhos)
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
# Cadastro de lotes e leilões
# ---------------------------------------------------------------------------
@locutor_required
def lote_form_view(request, pk=None):
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        messages.error(request, "Crie um leilão antes de cadastrar itens.")
        return redirect("leilao:leiloes")

    lote = get_object_or_404(Lote, pk=pk, leilao=leilao) if pk else None
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
            return redirect("leilao:lotes")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = LoteForm(instance=lote)

    return render(
        request, "leilao/lote_form.html", {"form": form, "lote": lote, "leilao": leilao}
    )


@locutor_required
def lotes_view(request):
    leilao = Leilao.ao_vivo() or Leilao.objects.order_by("-criado_em").first()
    if not leilao:
        return redirect("leilao:leiloes")
    return render(
        request,
        "leilao/lotes.html",
        {"leilao": leilao, "lotes": leilao.lotes.all().order_by("ordem", "id")},
    )


@locutor_required
@require_POST
def lote_excluir_view(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if lote.lances.exists() or lote.arremates.exists():
        messages.error(request, "Este item já teve lance — não dá para excluir.")
    else:
        lote.delete()
        messages.success(request, "Item removido.")
    return redirect("leilao:lotes")


@locutor_required
def leiloes_view(request):
    if request.method == "POST":
        form = LeilaoForm(request.POST)
        if form.is_valid():
            novo = form.save(commit=False)
            novo.criado_por = request.user
            novo.save()
            messages.success(request, "Leilão criado!")
            return redirect("leilao:locutor")
        messages.error(request, "Confira os campos destacados.")
    else:
        form = LeilaoForm()
    return render(
        request,
        "leilao/leiloes.html",
        {"form": form, "leiloes": Leilao.objects.all()},
    )


@locutor_required
@require_POST
def leilao_status_view(request, pk):
    """Coloca no ar / encerra. **Só um leilão ao vivo por vez.**"""
    leilao = get_object_or_404(Leilao, pk=pk)
    novo = request.POST.get("status")
    if novo not in {"rascunho", "ao_vivo", "encerrado"}:
        raise Http404
    if novo == "ao_vivo":
        Leilao.objects.filter(status="ao_vivo").exclude(pk=leilao.pk).update(status="encerrado")
    leilao.status = novo
    leilao.save(update_fields=["status"])
    messages.success(request, f"{leilao.nome}: {leilao.get_status_display()}.")
    return redirect("leilao:locutor" if novo == "ao_vivo" else "leilao:leiloes")


@locutor_required
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
