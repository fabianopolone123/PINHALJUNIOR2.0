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

# Validade do Pix de quem combinou pagar depois. O relógio dos 15 minutos não
# vale mais para essa pessoa (o item não volta para a fila), então o código
# precisa durar o quanto a conversa durar — uma hora, três, amanhã de manhã.
MINUTOS_PIX_COMBINADO = 60 * 24 * 7

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


def _mesma_pessoa(a, b):
    """Duas entradas são da mesma pessoa?

    Pelo id (o caso normal) **ou pelo telefone** — a pessoa que entra no celular
    e no computador vira dois registros, e sem esta segunda comparação ela
    cobriria o próprio lance.

    Consequência aceita: duas pessoas que compartilham um WhatsApp (marido e
    mulher, por exemplo) não disputam entre si. Num leilão isso é o lado certo
    do erro — inflar o próprio preço é o que a trava existe para impedir.
    """
    if a is None or b is None:
        return False
    if a.pk and a.pk == b.pk:
        return True
    tel_a, tel_b = a.telefone_normalizado, b.telefone_normalizado
    return bool(tel_a) and tel_a == tel_b


def _mesmos_cadastros(participante):
    """Todos os cadastros da mesma pessoa (ela pode ter entrado de dois aparelhos)."""
    from .models import Participante

    tel = participante.telefone_normalizado
    if not tel:
        return Participante.objects.filter(pk=participante.pk)
    # O telefone é guardado como veio (com ou sem DDI); busca pelas duas formas.
    return Participante.objects.filter(whatsapp__in=[tel, f"55{tel}"]) | (
        Participante.objects.filter(pk=participante.pk)
    )


def pessoa_bloqueada(participante):
    """Esta PESSOA está bloqueada, mesmo que este cadastro seja novo?"""
    return _mesmos_cadastros(participante).filter(bloqueado=True).exists()


def bloquear_pessoa(participante, bloquear=True):
    """Bloqueia/desbloqueia todos os cadastros da pessoa. Devolve (estado, quantos)."""
    alvos = _mesmos_cadastros(participante).distinct()
    quantos = alvos.update(bloqueado=bloquear)
    return bloquear, quantos


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
    """Põe o lote em pregão.

    Não há cronômetro: quem bate o martelo é o locutor, como num leilão de
    verdade. O `segundos` sobrou da assinatura antiga e é ignorado.
    """
    leilao = lote.leilao
    agora = timezone.now()

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
        lote.fecha_em = None
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
            "vencedor_chave": lote.lider.chave_pessoa if lote.lider_id else "",
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
            # TRAVA: ninguém cobre o próprio lance.
            #
            # A comparação é pela **pessoa**, não pelo registro. A entrada cria
            # um `Participante` novo a cada vez, então a mesma pessoa que abre o
            # leilão no celular E no computador vira dois registros — e, pelo
            # id, conseguiria dar lance contra si mesma, inflando o próprio
            # preço. O WhatsApp é a identidade que o clube usa em todo o resto
            # do sistema; é por ele que se compara.
            if lote.lider_id and _mesma_pessoa(lote.lider, participante):
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
            lote.save(update_fields=["valor_atual", "lider"])

        _ultimo_lance[participante.id] = agora_mono

    dados = {"lote": est.lote_publico(lote), "lance": est.lance_publico(lance)}
    HUB.publicar("lance", dados)
    return True, "Lance registrado!", dados


# ---------------------------------------------------------------------------
# Dinheiro
# ---------------------------------------------------------------------------
def marcar_combinado(arremate, usuario=None, observacao=""):
    """A pessoa foi contatada e vai pagar depois.

    Trava o relógio: o arremate sai de `aguardando`, então **o item não volta
    para a fila** — sem isto, quem combinou de pagar amanhã perdia o item para
    o cronômetro, que é o oposto do que o caixa acabou de acertar.

    Gera um **Pix novo com prazo de 24 h**: o código original foi criado com
    validade de 15 minutos e já está vencido. Oferecer um botão de copiar que
    entrega um código morto é pior do que não oferecer nada.
    """
    if arremate.status == "pago":
        return arremate
    arremate.status = "combinado"
    arremate.combinado_em = timezone.now()
    arremate.combinado_por = usuario
    if observacao:
        arremate.observacao = observacao[:200]
    arremate.save(update_fields=["status", "combinado_em", "combinado_por", "observacao"])

    # Sete dias, não 24 horas: "vai pagar depois" na prática é "pago hoje à
    # noite, amanhã, ou quando a pessoa conseguir". Um código que vence antes
    # disso faz o caixa refazer tudo — e, pior, entrega à pessoa um copia e cola
    # que o banco recusa.
    agendar(garantir_cobranca, arremate.id, MINUTOS_PIX_COMBINADO, True)
    HUB.publicar(
        "arremate_combinado",
        {
            "arremate": arremate.id,
            "participante": arremate.participante_id,
            "situacao": "combinado",
        },
    )
    return arremate


def estender_prazo(arremate, minutos):
    """Dá mais tempo a quem pediu mais tempo — e **refaz o Pix**.

    Esticar só o `expira_em` seria meia solução: o código Pix do arremate foi
    criado com a validade do prazo original e vence junto com ele. A pessoa
    ficaria com mais tempo na tela e um copia e cola que o banco recusa.

    Vale só para quem ainda está no relógio: quem já combinou de pagar depois
    não tem prazo para esticar, e quem pagou não precisa.
    """
    minutos = max(1, min(int(minutos or 0), 60 * 24))
    if arremate.status != "aguardando":
        return arremate

    # A partir de AGORA, não do prazo antigo: o caso real é o prazo prestes a
    # vencer (ou vencido há segundos), e somar ao passado daria tempo nenhum.
    base = max(arremate.expira_em, timezone.now())
    arremate.expira_em = base + timedelta(minutes=minutos)
    arremate.save(update_fields=["expira_em"])

    restante = int((arremate.expira_em - timezone.now()).total_seconds() // 60) + 1
    agendar(garantir_cobranca, arremate.id, restante, True)
    HUB.publicar(
        "arremate_prazo",
        {
            "arremate": arremate.id,
            "participante": arremate.participante_id,
            "expira_em": est.iso(arremate.expira_em),
            "segundos": arremate.segundos_para_pagar,
        },
    )
    return arremate


def garantir_cobranca(arremate_id, minutos=None, refazer=False):
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
    if not arremate or arremate.status not in {"aguardando", "combinado"}:
        return None
    if arremate.pagamento_id and not refazer:
        return None

    if minutos:
        restante = int(minutos)
    else:
        restante = max(1, int((arremate.expira_em - timezone.now()).total_seconds() // 60) + 1)
    # A referência precisa ser NOVA quando o Pix é refeito: ela é a chave de
    # idempotência no Mercado Pago, e repeti-la devolveria a cobrança vencida.
    referencia = f"LEILAO-{arremate.id}"
    if refazer:
        referencia += f"-R{int(timezone.now().timestamp())}"
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
    """Abre o chat do intervalo — uma conversa NOVA a cada vez.

    O marco `chat_aberto_em` é o que faz a tela do participante começar limpa:
    cada intervalo é um papo do intervalo, não um fio que se arrasta a noite
    toda. O locutor continua vendo o histórico inteiro, pelo caminho dele.
    """
    agora = timezone.now()
    leilao.chat_aberto_em = agora
    leilao.chat_aberto_ate = agora + timedelta(seconds=int(segundos))
    leilao.save(update_fields=["chat_aberto_em", "chat_aberto_ate"])
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


def mudar_status(leilao, novo):
    """Coloca no ar / tira do ar — e AVISA quem está esperando.

    Sem este aviso, a tela que diz "assim que iniciarmos, isto acende sozinho"
    mentia: ela só acordava quando o primeiro item abria. Quem estava com o
    celular na mão desde antes continuava vendo a tela de espera.
    """
    if novo == "ao_vivo":
        # O leilão que sai do ar leva o chat dele junto (ver abaixo).
        Leilao.objects.filter(status="ao_vivo").exclude(pk=leilao.pk).update(
            status="encerrado", chat_aberto_ate=None
        )
    leilao.status = novo

    campos = ["status"]
    if novo != "ao_vivo" and leilao.chat_aberto_ate:
        # Sair do ar FECHA o chat. `chat_aberto_ate` é uma hora futura gravada
        # no banco: ela não sabe que o leilão acabou. Deixando-a de pé, a tela
        # continuava mostrando a caixa de conversa e o servidor recusava cada
        # mensagem — a pessoa digitava contra uma porta fechada.
        leilao.chat_aberto_ate = None
        campos.append("chat_aberto_ate")
        HUB.publicar("chat_estado", {"aberto": False, "ate": None})

    leilao.save(update_fields=campos)

    # Quem sai do ar também precisa avisar: as telas voltam para a espera em vez
    # de ficar congeladas no último item.
    ao_vivo = Leilao.ao_vivo()
    HUB.publicar("estado", est.estado_publico(ao_vivo))
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

    Tudo que depende do relógio está aqui — prazo de pagamento e fim do chat.
    Concentrar isso num lugar é o que impede dois caminhos diferentes fecharem
    a mesma coisa de dois jeitos.

    **O item em pregão não está nesta lista**, e é de propósito: não há
    cronômetro. Quem bate o martelo é o locutor, como num leilão de verdade — o
    "dou-lhe uma, dou-lhe duas" é do leiloeiro, e fechar sozinho tiraria dele o
    momento que mais importa.
    """
    leilao = Leilao.ao_vivo()
    if not leilao:
        return
    agora = timezone.now()

    # Só quem está `aguardando` vence. Quem combinou de pagar depois fica fora
    # do relógio de propósito — é o acerto que o caixa fez.
    vencidos = Arremate.objects.select_related("lote", "lote__leilao", "participante").filter(
        status="aguardando", expira_em__lte=agora, lote__leilao=leilao
    )
    for arremate in vencidos:
        expirar_arremate(arremate)

    if leilao.chat_aberto_ate and leilao.chat_aberto_ate <= agora:
        fechar_chat(leilao)
