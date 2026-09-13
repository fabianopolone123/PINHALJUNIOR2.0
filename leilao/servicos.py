"""Regras do pregão. **Toda** mudança de estado do leilão passa por aqui.

As views (HTTP) só traduzem pedido → chamada daqui → resposta. O laço central
(`hub.laco_central`) chama `verificar_prazos()`. Assim existe um lugar só onde
o leilão muda de estado — e é esse lugar que publica no `HUB`.

Os dois pontos delicados do arquivo:

- **Lance sem corrida** (`dar_lance`): dois toques no mesmo milissegundo não
  podem virar dois incrementos sobre o mesmo valor.
- **Dinheiro e tempo** (`fechar_lote`, `verificar_prazos`): quem arremata tem
  prazo para pagar; vencido o prazo, o lote **volta para a fila**.
"""

import logging
import threading
import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import connections, transaction
from django.db.models import Max
from django.utils import timezone

# Biblioteca PURA (só `urllib`), reaproveitada do sistema do clube. Ela recebe o
# objeto de configuração de quem chama, então funciona sem o app `core` estar
# instalado neste serviço — que é exatamente o isolamento que queremos.
from core import mercadopago

from . import estado as est
from .hub import HUB
from .models import (
    Arremate,
    ConfigLeilao,
    Lance,
    Leilao,
    Lote,
    MensagemChat,
    PagamentoLeilao,
)

logger = logging.getLogger(__name__)

# Intervalo mínimo entre dois lances da mesma pessoa. Segura dedo nervoso e
# script — sem atrapalhar quem está disputando de verdade.
INTERVALO_MIN_LANCE = 0.3

_locks = {}
_locks_guard = threading.Lock()
_ultimo_lance = {}


def limpar_limites():
    """Zera o freio de repetição e os cadeados em memória.

    Existe para o **teste** e para o começo de um leilão novo. O freio é
    guardado por id de participante em memória do processo; entre um evento e
    outro (ou entre um teste e outro, onde os ids se repetem) isso vira estado
    velho recusando lance legítimo com "Calma!".
    """
    with _locks_guard:
        _locks.clear()
    _ultimo_lance.clear()


def _lock_do_lote(lote_id):
    """Um cadeado por lote.

    O serviço roda com **um processo só** (ver `settings_leilao`), então um
    cadeado em memória basta para serializar os lances daquele lote — não
    precisa de lock no banco, que no SQLite seria bem mais caro.
    """
    with _locks_guard:
        return _locks.setdefault(lote_id, threading.Lock())


def agendar(funcao, *args):
    """Roda algo lento fora do caminho crítico (thread solta).

    Serve para a chamada HTTP ao Mercado Pago: gerar o Pix leva segundos e
    **não pode** segurar o "vendido!" na tela de 50 pessoas. O pregão segue; o
    QR chega logo atrás, por um evento próprio.
    """

    def _rodar():
        try:
            funcao(*args)
        except Exception:  # noqa: BLE001 — tarefa de fundo não derruba o leilão
            logger.exception("Falha em tarefa de fundo do leilão: %s", funcao.__name__)
        finally:
            # Thread própria = conexão própria. Sem fechar, cada item vendido
            # deixa uma conexão pendurada no SQLite até o processo morrer.
            connections.close_all()

    threading.Thread(target=_rodar, daemon=True).start()


# ---------------------------------------------------------------------------
# Abrir / fechar lote
# ---------------------------------------------------------------------------
def abrir_lote(lote, *, segundos=None):
    """Põe o lote em pregão e liga o cronômetro."""
    leilao = lote.leilao
    agora = timezone.now()
    duracao = int(segundos or leilao.segundos_por_lote)

    with transaction.atomic():
        # Guarda: só um lote em pregão por vez. Se sobrou outro aberto (queda de
        # serviço no meio do pregão, ou o locutor abriu o próximo sem fechar),
        # ele volta para a fila em vez de existirem dois cronômetros rodando.
        #
        # Volta **limpo**: os lances daquela rodada continuam no banco (histórico),
        # mas o lote não pode ficar na fila exibindo líder e valor de uma disputa
        # que foi abandonada.
        Lote.objects.filter(leilao=leilao, status="aberto").exclude(pk=lote.pk).update(
            status="fila",
            fecha_em=None,
            pausado_restante=None,
            valor_atual=Decimal("0.00"),
            lider=None,
        )
        lote.status = "aberto"
        lote.aberto_em = agora
        lote.fechado_em = None
        lote.valor_atual = Decimal("0.00")
        lote.lider = None
        lote.pausado_restante = None
        lote.fecha_em = agora + timedelta(seconds=duracao)
        lote.save(
            update_fields=[
                "status", "aberto_em", "fechado_em", "valor_atual",
                "lider", "pausado_restante", "fecha_em",
            ]
        )
        if leilao.chat_aberto_ate:
            # Abriu lote, fecha o chat do intervalo: a atenção volta para o pregão.
            leilao.chat_aberto_ate = None
            leilao.save(update_fields=["chat_aberto_ate"])

    HUB.publicar("lote_aberto", est.estado_publico(leilao))
    return lote


def fechar_lote(lote, *, motivo="cronometro"):
    """Bate o martelo: vendido (com líder) ou sem lance (volta para a fila).

    Publica o resultado **na hora** e só então manda gerar o Pix numa thread —
    ninguém fica olhando uma tela parada esperando o Mercado Pago responder.
    """
    leilao = lote.leilao
    agora = timezone.now()
    arremate = None

    with transaction.atomic():
        lote.refresh_from_db()
        if lote.status != "aberto":
            return None  # já fechado por outro caminho (locutor + cronômetro juntos)

        if lote.tem_lance:
            lote.status = "vendido"
            arremate = Arremate.objects.create(
                lote=lote,
                participante=lote.lider,
                valor=lote.valor_atual,
                expira_em=agora + timedelta(minutes=leilao.minutos_para_pagar),
            )
        else:
            lote.status = "sem_lance"

        lote.fechado_em = agora
        lote.fecha_em = None
        lote.pausado_restante = None
        lote.save(update_fields=["status", "fechado_em", "fecha_em", "pausado_restante"])

    HUB.publicar(
        "lote_vendido",
        {
            "lote": est.lote_publico(lote),
            "vendido": lote.status == "vendido",
            "motivo": motivo,
            "vencedor_id": lote.lider_id,
            "vencedor": lote.lider.nome_curto if lote.lider_id else "",
            "valor": str(lote.valor_atual),
            "arremate_id": arremate.id if arremate else None,
            "estado": est.estado_publico(leilao),
        },
    )

    if arremate:
        agendar(garantir_cobranca, arremate.id)
    if leilao.chat_segundos:
        abrir_chat(leilao, leilao.chat_segundos)
    return arremate


def pausar_lote(lote, pausar=True):
    """Congela/retoma o cronômetro sem perder o tempo que faltava."""
    if lote.status != "aberto":
        return lote
    agora = timezone.now()
    if pausar and lote.pausado_restante is None:
        restante = max(0, int((lote.fecha_em - agora).total_seconds())) if lote.fecha_em else 0
        lote.pausado_restante = restante
        lote.fecha_em = None
    elif not pausar and lote.pausado_restante is not None:
        lote.fecha_em = agora + timedelta(seconds=lote.pausado_restante)
        lote.pausado_restante = None
    lote.save(update_fields=["pausado_restante", "fecha_em"])
    HUB.publicar("cronometro", {"lote": est.lote_publico(lote)})
    return lote


def somar_tempo(lote, segundos):
    """Botão '+tempo' do locutor."""
    if lote.status != "aberto":
        return lote
    if lote.pausado_restante is not None:
        lote.pausado_restante += int(segundos)
    else:
        base = lote.fecha_em or timezone.now()
        lote.fecha_em = max(base, timezone.now()) + timedelta(seconds=int(segundos))
    lote.save(update_fields=["pausado_restante", "fecha_em"])
    HUB.publicar("cronometro", {"lote": est.lote_publico(lote)})
    return lote


# ---------------------------------------------------------------------------
# O lance
# ---------------------------------------------------------------------------
def dar_lance(lote_id, participante, *, valor_visto=None, origem="botao"):
    """Registra um lance. Devolve `(ok, mensagem, dados)`.

    A correção depende de três coisas, nesta ordem:

    1. o **cadeado do lote**, que serializa os toques simultâneos;
    2. o `UPDATE` acontecer **dentro** do cadeado, lendo o lote de novo do banco
       (nada de confiar no objeto que a view carregou antes);
    3. a conferência do **valor que o cliente viu**: se o preço subiu mais de um
       degrau desde que a tela desenhou o botão, o lance é recusado e a pessoa
       toca de novo, já vendo o valor certo. Aceitar calado faria alguém pagar
       mais do que pretendia.
    """
    if participante.bloqueado:
        return False, "Seus lances estão bloqueados. Fale com o locutor.", None

    agora_mono = time.monotonic()

    with _lock_do_lote(lote_id):
        with transaction.atomic():
            try:
                lote = Lote.objects.select_related("leilao", "lider").get(pk=lote_id)
            except Lote.DoesNotExist:
                return False, "Lote não encontrado.", None

            if lote.status != "aberto":
                return False, "Este lote não está em pregão.", None
            if lote.pausado:
                return False, "O locutor pausou o cronômetro.", None
            if lote.fecha_em and lote.fecha_em <= timezone.now():
                return False, "Tempo esgotado neste lote.", None
            if lote.lider_id == participante.id:
                return False, "Você já está ganhando este lote.", None

            # Freio de repetição — DEPOIS das recusas que têm explicação própria.
            # Se vier antes, quem toca duas vezes seguidas ouve "Calma!" quando a
            # resposta certa era "você já está ganhando": a pessoa fica sem saber
            # se o lance entrou.
            ultimo = _ultimo_lance.get(participante.id, 0)
            if agora_mono - ultimo < INTERVALO_MIN_LANCE:
                return False, "Calma! Espere um instante antes do próximo lance.", None

            valor = lote.proximo_valor

            if valor_visto is not None:
                try:
                    visto = Decimal(str(valor_visto))
                except (InvalidOperation, ValueError):
                    visto = None
                # Um degrau de tolerância: o normal é o valor ter subido uma vez
                # entre o desenho da tela e o toque. Mais que isso, a pessoa
                # confirma de novo.
                if visto is not None and valor > visto + lote.incremento_efetivo:
                    return (
                        False,
                        f"O valor subiu para R$ {valor}. Confira e toque de novo.",
                        {"lote": est.lote_publico(lote)},
                    )

            lance = Lance.objects.create(
                lote=lote, participante=participante, valor=valor, origem=origem
            )
            lote.valor_atual = valor
            lote.lider = participante
            if lote.leilao.reiniciar_cronometro:
                lote.fecha_em = timezone.now() + timedelta(
                    seconds=lote.leilao.segundos_por_lote
                )
            lote.save(update_fields=["valor_atual", "lider", "fecha_em"])

        _ultimo_lance[participante.id] = agora_mono

    dados = {"lote": est.lote_publico(lote), "lance": est.lance_publico(lance)}
    HUB.publicar("lance", dados)
    return True, "Lance registrado!", dados


def desfazer_ultimo_lance(lote):
    """Desfaz o último lance válido do lote (o locutor erra; acontece).

    Não apaga: marca `cancelado`. O histórico do pregão continua auditável, que
    é o que responde a "mas eu dei esse lance!" no meio do evento.
    """
    with _lock_do_lote(lote.id):
        with transaction.atomic():
            lote.refresh_from_db()
            # Só a rodada atual: se o item voltou para a fila, desfazer não pode
            # ressuscitar o líder de uma rodada que já foi anulada.
            ultimo = (
                lote.lances_da_rodada()
                .select_related("participante")
                .order_by("-criado_em", "-id")
                .first()
            )
            if not ultimo:
                return False, "Não há lance para desfazer."

            ultimo.cancelado = True
            ultimo.save(update_fields=["cancelado"])

            anterior = (
                lote.lances_da_rodada()
                .select_related("participante")
                .order_by("-criado_em", "-id")
                .first()
            )
            if anterior:
                lote.valor_atual = anterior.valor
                lote.lider = anterior.participante
            else:
                lote.valor_atual = Decimal("0.00")
                lote.lider = None
            lote.save(update_fields=["valor_atual", "lider"])

    HUB.publicar(
        "lance_desfeito",
        {"lote": est.lote_publico(lote), "quem": ultimo.participante.nome_curto},
    )
    return True, f"Lance de {ultimo.participante.nome_curto} desfeito."


# ---------------------------------------------------------------------------
# Dinheiro
# ---------------------------------------------------------------------------
def garantir_cobranca(arremate_id):
    """Cria (uma vez) a cobrança Pix do arremate e avisa o vencedor.

    Roda numa thread, fora do caminho crítico. Sem Mercado Pago configurado, o
    leilão **não para**: o locutor combina o pagamento por fora e dá baixa
    manual — por isso a falha aqui é registro, não exceção na cara de ninguém.
    """
    # A configuração vem PRIMEIRO, antes de qualquer consulta ao arremate: sem
    # credencial não há nada a fazer, e esta função roda numa thread solta — sem
    # essa saída antecipada ela iria ao banco à toa em toda instalação sem
    # Mercado Pago (e disputaria o banco com quem está dando lance).
    cfg = ConfigLeilao.get_solo()
    if not cfg.configurado:
        logger.warning("Leilão: Mercado Pago não configurado — arremate %s sem Pix.", arremate_id)
        return None

    arremate = (
        Arremate.objects.select_related("lote", "lote__leilao", "participante")
        .filter(pk=arremate_id)
        .first()
    )
    if not arremate or arremate.pagamento_id or arremate.status != "aguardando":
        return None

    restante = max(1, int((arremate.expira_em - timezone.now()).total_seconds() // 60) + 1)
    referencia = f"LEILAO-{arremate.id}"
    notificacao = ""
    if cfg.site_url:
        notificacao = f"{cfg.site_url.rstrip('/')}/webhooks/mercadopago/"

    resposta = mercadopago.criar_pix(
        cfg,
        referencia=referencia,
        valor=arremate.valor,
        descricao=f"Leilão — {arremate.lote.nome}",
        payer_nome=arremate.participante.nome,
        notification_url=notificacao,
        expira_minutos=restante,
    )
    if not resposta.get("ok"):
        logger.error("Leilão: falha ao gerar Pix do arremate %s: %s", arremate_id, resposta.get("erro"))
        HUB.publicar(
            "arremate_pix",
            {"arremate": arremate_id, "participante": arremate.participante_id, "ok": False},
        )
        return None

    import json

    pagamento = PagamentoLeilao.objects.create(
        referencia=referencia,
        mp_payment_id=resposta.get("mp_payment_id", ""),
        status=resposta.get("status", "pendente"),
        valor_bruto=arremate.valor,
        qr_code=resposta.get("qr_code", ""),
        qr_code_base64=resposta.get("qr_code_base64", ""),
        ticket_url=resposta.get("ticket_url", ""),
        payload=json.dumps(resposta.get("raw") or {}, ensure_ascii=False, default=str),
    )
    arremate.pagamento = pagamento
    arremate.save(update_fields=["pagamento"])

    HUB.publicar(
        "arremate_pix",
        {"arremate": arremate_id, "participante": arremate.participante_id, "ok": True},
    )
    return pagamento


def marcar_pago(arremate, *, manual=False, pagamento=None):
    """Dá o arremate por pago. **Idempotente** (o webhook do MP repete o aviso)."""
    if arremate.status == "pago":
        return arremate
    arremate.status = "pago"
    arremate.pago_em = timezone.now()
    arremate.pago_manual = manual
    if pagamento and not arremate.pagamento_id:
        arremate.pagamento = pagamento
    arremate.save(update_fields=["status", "pago_em", "pago_manual", "pagamento"])
    HUB.publicar(
        "pagamento",
        {
            "arremate": arremate.id,
            "participante": arremate.participante_id,
            "lote": arremate.lote.nome,
            "situacao": "pago",
        },
    )
    return arremate


def expirar_arremate(arremate):
    """Venceu o prazo sem pagar: o lote **volta para a fila**.

    Vai para o **fim** da fila, não para o lugar original: o pregão não pode
    parar para reabrir um item agora, e o locutor reordena se quiser. O item
    volta limpo (valor zerado, sem líder) — quem não pagou não guarda direito
    sobre ele.
    """
    with transaction.atomic():
        arremate.refresh_from_db()
        if arremate.status != "aguardando":
            return arremate
        arremate.status = "expirado"
        arremate.save(update_fields=["status"])

        lote = arremate.lote
        if lote.status == "vendido":
            ultima = lote.leilao.lotes.aggregate(m=Max("ordem"))["m"] or 0
            lote.status = "fila"
            lote.ordem = ultima + 1
            lote.valor_atual = Decimal("0.00")
            lote.lider = None
            lote.fechado_em = None
            lote.voltas = lote.voltas + 1
            lote.save(
                update_fields=["status", "ordem", "valor_atual", "lider", "fechado_em", "voltas"]
            )

    HUB.publicar(
        "arremate_expirado",
        {
            "arremate": arremate.id,
            "participante": arremate.participante_id,
            "lote": arremate.lote.nome,
            "estado": est.estado_publico(arremate.lote.leilao),
        },
    )
    return arremate


def conferir_pagamento(arremate):
    """Consulta o Mercado Pago na marra (reforço para webhook atrasado).

    O webhook é o caminho normal, mas ele atrasa — e quem acabou de pagar está
    olhando a tela esperando o selo mudar. Esta consulta é o que fecha esse
    buraco enquanto o painel de pagamento está aberto.
    """
    if arremate.status == "pago":
        return True
    pagamento = arremate.pagamento
    if not pagamento or not pagamento.mp_payment_id:
        return False
    cfg = ConfigLeilao.get_solo()
    if not cfg.configurado:
        return False
    r = mercadopago.consultar_pagamento(cfg, pagamento.mp_payment_id)
    if not r.get("ok"):
        return False
    return _aplicar_retorno(pagamento, r)


def _aplicar_retorno(pagamento, r):
    """Grava o que o MP disse e, se aprovado, quita o arremate. Idempotente."""
    pagamento.status = r.get("status", pagamento.status)
    pagamento.taxa = r.get("taxa") or Decimal("0.00")
    pagamento.valor_liquido = r.get("liquido") or pagamento.valor_bruto
    pagamento.save(update_fields=["status", "taxa", "valor_liquido"])

    if pagamento.status != "aprovado":
        return False
    if not pagamento.finalizado:
        pagamento.finalizado = True
        pagamento.save(update_fields=["finalizado"])
    for arremate in pagamento.arremates.select_related("lote", "participante"):
        marcar_pago(arremate, pagamento=pagamento)
    return True


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
def abrir_chat(leilao, segundos):
    leilao.chat_aberto_ate = timezone.now() + timedelta(seconds=int(segundos))
    leilao.save(update_fields=["chat_aberto_ate"])
    HUB.publicar(
        "chat_estado",
        {"aberto": True, "ate": est.iso(leilao.chat_aberto_ate), "segundos": int(segundos)},
    )
    return leilao


def fechar_chat(leilao):
    if not leilao.chat_aberto_ate:
        return leilao
    leilao.chat_aberto_ate = None
    leilao.save(update_fields=["chat_aberto_ate"])
    HUB.publicar("chat_estado", {"aberto": False, "ate": None, "segundos": 0})
    return leilao


def enviar_mensagem(leilao, participante, texto):
    texto = (texto or "").strip()[:300]
    if not texto:
        return None
    if participante is not None and participante.bloqueado:
        return None
    if participante is not None and not leilao.chat_aberto:
        return None
    m = MensagemChat.objects.create(leilao=leilao, participante=participante, texto=texto)
    HUB.publicar("chat", est.mensagem_publica(m))
    return m


# ---------------------------------------------------------------------------
# O laço central
# ---------------------------------------------------------------------------
def verificar_prazos():
    """Chamado pelo laço central a cada segundo. Fecha o que venceu.

    Tudo que depende do relógio está aqui — cronômetro do lote, prazo de
    pagamento e fim do chat. Concentrar isso num lugar é o que impede dois
    caminhos diferentes fecharem o mesmo lote de dois jeitos.
    """
    leilao = Leilao.ao_vivo()
    if not leilao:
        return
    agora = timezone.now()

    lote = (
        leilao.lotes.select_related("leilao", "lider")
        .filter(status="aberto", pausado_restante__isnull=True, fecha_em__lte=agora)
        .first()
    )
    if lote:
        fechar_lote(lote, motivo="cronometro")

    vencidos = Arremate.objects.select_related("lote", "lote__leilao", "participante").filter(
        status="aguardando", expira_em__lte=agora, lote__leilao=leilao
    )
    for arremate in vencidos:
        expirar_arremate(arremate)

    if leilao.chat_aberto_ate and leilao.chat_aberto_ate <= agora:
        fechar_chat(leilao)
