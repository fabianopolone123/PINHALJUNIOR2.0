"""Regras do pregão. **Toda** mudança de estado do leilão passa por aqui.

As views (HTTP) só traduzem pedido → chamada daqui → resposta. O laço central
(`hub.laco_central`) chama `verificar_prazos()`. Assim existe um lugar só onde
o leilão muda de estado — e é esse lugar que publica no `HUB`.

Os dois pontos delicados do arquivo:

- **Lance sem corrida** (`dar_lance`): dois toques no mesmo milissegundo não
  podem virar dois incrementos sobre o mesmo valor.
- **Dinheiro** (`fechar_lote`, `cobranca_do_participante`): quem arremata **não
  paga na hora**. Os itens se acumulam na conta da pessoa e ela paga tudo num
  Pix só, quando o locutor libera no fim — não há prazo, e o lote **não volta**
  para a fila por relógio nenhum. (`verificar_prazos` ficou vazia de
  propósito; o docstring dela conta a história.)
"""

import logging
import threading
import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, connections, transaction
from django.db.models import F, Max, Sum
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
    _esquecer_martelo(lote)
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
        # O chat NÃO fecha mais ao abrir um item: ele fica aberto a noite
        # inteira (pedido do clube). Ver `Leilao.chat_aberto`.

    HUB.publicar("lote_aberto", est.estado_publico(leilao))
    return lote


class MarteloRecusado(Exception):
    """O VENDIDO não cabe agora — a mensagem é para quem está na mesa."""


def fechar_lote(lote, *, motivo="cronometro", escada=False, visto=None):
    """Bate o martelo: vendido (com líder) ou sem lance (volta para a fila).

    **Não nasce cobrança aqui.** O arremate entra na conta da pessoa e o Pix só
    existe no fim, quando o locutor libera os pagamentos e ela paga tudo de uma
    vez. Antes saía um Pix por item, com 15 minutos correndo — o que tirava do
    pregão exatamente quem estava disputando.

    `escada=True` (o VENDIDO da mesa) e `visto` (o valor que a mesa estava
    mostrando, `""` = sem lance) são conferidos DENTRO da transação, depois de
    reler o item: um lance que entra entre o clique e o martelo não vende sem
    dou-lhe, e o "sem lance" da mesa não vende um item que acabou de ganhar
    lance (revisão de 26/09). Recusa com `MarteloRecusado`.
    """
    leilao = lote.leilao
    agora = timezone.now()
    arremate = None

    with transaction.atomic():
        lote.refresh_from_db()
        if lote.status != "aberto":
            return None  # já fechado por outro caminho (locutor + cronômetro juntos)
        if visto is not None:
            viu_lance = str(visto).strip() != ""
            if viu_lance != lote.tem_lance or (
                viu_lance and _decimal_ou_none(visto) != lote.valor_atual
            ):
                raise MarteloRecusado("Entrou lance novo agora — confira antes de bater o martelo.")
        if escada and not martelo_liberado(lote):
            raise MarteloRecusado("Primeiro o dou-lhe uma e o dou-lhe duas.")
        _esquecer_martelo(lote)

        if lote.tem_lance:
            lote.status = "vendido"
            # Sem `expira_em`: não há prazo. O item fica na conta da pessoa
            # até ela pagar, e quem não paga é cobrado pelo caixa — não perde
            # o item para um relógio.
            arremate = Arremate.objects.create(
                lote=lote,
                participante=lote.lider,
                valor=lote.valor_atual,
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

    # Nenhuma cobrança é gerada aqui: o Pix nasce uma vez só, pelo TOTAL, e só
    # depois que o locutor libera (ver `cobranca_do_participante`). O chat
    # também não é mais "do intervalo" — fica aberto o leilão inteiro.
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
            # Item aberto num leilão que não está no ar não recebe lance: sem
            # público não há pregão (e o `abrir` sem leilão no ar caía no mais
            # recente, que podia ser o rascunho do mês seguinte).
            if lote.leilao.status != "ao_vivo":
                return False, "Este leilão não está no ar.", None
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

    Não gera cobrança: o Pix da pessoa é UM só, pelo total do que ela levou, e
    nasce quando o caixa/ela abre a cobrança. Aqui só se registra o combinado.
    """
    if arremate.status in {"pago", "combinado"}:
        # Idempotente de propósito: o botão continua na tela até a página se
        # refazer, e um segundo clique geraria um SEGUNDO Pix válido para o
        # mesmo item — dois códigos vivos, e o caixa sem saber qual a pessoa
        # pagou.
        return arremate
    arremate.status = "combinado"
    arremate.combinado_em = timezone.now()
    arremate.combinado_por = usuario
    if observacao:
        arremate.observacao = observacao[:200]
    arremate.save(update_fields=["status", "combinado_em", "combinado_por", "observacao"])

    HUB.publicar(
        "arremate_combinado",
        {
            "arremate": arremate.id,
            "participante": arremate.participante_id,
            "situacao": "combinado",
        },
    )
    return arremate


# `estender_prazo` NÃO EXISTE MAIS: não há prazo para esticar. Quem arremata
# acumula os itens e paga no fim, e quem não pagar é cobrado pelo caixa — o
# item não volta para a fila por relógio nenhum.


def arremates_em_aberto(participante):
    """O que esta pessoa levou e ainda não pagou, nesta sessão.

    **Escopo é o cadastro da sessão, de propósito.** Juntar os arremates de
    quem tem o mesmo telefone parece certo (a pessoa pode ter entrado do
    celular e do computador) e é exatamente o que o `REGRAS_CODEX` proíbe:
    quem soubesse o seu WhatsApp veria os seus itens e o seu código Pix.
    """
    return (
        Arremate.objects.filter(participante=participante, status__in=("aguardando", "combinado"))
        .select_related("lote")
        .order_by("criado_em")
    )


def conta_aberta(participante):
    """`(leilao_id, abertos)` — a conta em aberto da pessoa, de UM leilão só.

    A sessão dura 30 dias: quem volta no leilão do mês seguinte ainda carrega
    o que deixou em aberto no anterior. Somar os dois num total só era errado
    duas vezes — a tela mostrava um valor que nenhuma cobrança cobria, e a
    referência do Pix (`LEILAOC-<pessoa>-<leilão>`) levava só um dos leilões.
    A conta é a do leilão do item MAIS ANTIGO em aberto: ela é paga primeiro,
    e a seguinte aparece quando esta fechar.
    """
    abertos = list(arremates_em_aberto(participante))
    if not abertos:
        return None, []
    leilao_id = abertos[0].lote.leilao_id
    return leilao_id, [a for a in abertos if a.lote.leilao_id == leilao_id]


def total_em_aberto(participante):
    _, abertos = conta_aberta(participante)
    return sum((a.valor for a in abertos), Decimal("0.00"))


def pagamento_aberto_para(leilao_id):
    """Já se pode pagar a conta deste leilão?

    Durante o pregão, só depois de o locutor liberar (`pagamentos_liberados`).
    **Depois de encerrado, sempre**: o caixa cobra por dias quem ficou devendo,
    e antes daqui o Pix exigia um leilão AO VIVO — encerrar à noite deixava
    quem não tinha aberto o próprio Pix sem jeito nenhum de pagar.
    """
    if not leilao_id:
        return False
    leilao = Leilao.objects.filter(pk=leilao_id).first()
    return bool(leilao and (leilao.pagamentos_liberados or leilao.status == "encerrado"))


def liberar_pagamentos(leilao, liberar=True):
    """Abre (ou fecha) a bilheteria para TODO MUNDO de uma vez.

    É um botão só, no fim do leilão, e não um por pessoa: enquanto o pregão
    corre ninguém deve estar mexendo em Pix — o ponto de tirar o prazo foi
    justamente não tirar ninguém da disputa para pagar.
    """
    if leilao.pagamentos_liberados == bool(liberar):
        return leilao
    leilao.pagamentos_liberados = bool(liberar)
    leilao.save(update_fields=["pagamentos_liberados"])
    # O estado inteiro, como sempre: quem está com a tela aberta vê o botão de
    # pagar aparecer sem recarregar nada.
    publicar_estado()
    return leilao


def _decimal_ou_none(valor):
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d.is_finite() else None


class DouLheRecusado(Exception):
    """O "dou-lhe" não cabe agora (sem item, sem lance, item trocado, fora da ordem)."""


# O MARTELO EM ESCADA (pedido do clube em 26/09): dou-lhe uma → dou-lhe duas →
# VENDIDO, um só depois do outro, e sem janela de confirmação. A escada vale
# no SERVIDOR, não só no botão apagado: toque duplo, duas telas de mesa ou um
# POST forjado não pulam etapa.
#
# Em memória (o serviço é de UM worker, como o hub e o relógio), por item, e
# amarrada a `(aberto_em, valor_atual)`: lance novo muda o valor e a escada
# recomeça sozinha; item devolvido e reaberto tem outro `aberto_em`. Se o
# serviço reiniciar no meio, o pior que acontece é o locutor ter de apertar
# o "dou-lhe uma" de novo.
_ESCADA = {}
_ESCADA_TRAVA = threading.Lock()


def _marca_do_martelo(lote):
    return (lote.aberto_em.isoformat() if lote.aberto_em else "", str(lote.valor_atual))


def martelo_vez(lote):
    """Em que degrau o item está agora: 0 (nada), 1 (dou-lhe uma), 2 (duas)."""
    if not lote:
        return 0
    with _ESCADA_TRAVA:
        registro = _ESCADA.get(lote.pk)
    if not registro or registro[0] != _marca_do_martelo(lote):
        return 0
    return registro[1]


def martelo_liberado(lote):
    """O VENDIDO pode bater? Só depois do "dou-lhe duas" — ou em item SEM
    lance, que o VENDIDO encerra devolvendo para a fila (senão ele ficaria
    preso no pregão, porque sem lance não há "dou-lhe")."""
    return not lote.tem_lance or martelo_vez(lote) >= 2


def _esquecer_martelo(lote):
    with _ESCADA_TRAVA:
        _ESCADA.pop(lote.pk, None)


def dou_lhe(leilao, vez, lote=None):
    """O locutor anuncia "dou-lhe uma" (vez=1) ou "dou-lhe duas" (vez=2).

    **Não muda nada no banco e não fecha nada sozinho**: o martelo continua
    sendo do locutor (regra do módulo — não há cronômetro). É um anúncio, como
    o locutor dizendo em voz alta, e por isso pode ir no broadcast: todas as
    telas mostram o efeito ao mesmo tempo, e quem estava em dúvida corre para
    dar o lance.

    O `lote` é o que a MESA estava mostrando. Se ele não é mais o do pregão (o
    locutor apertou no instante em que o item trocou), o anúncio é recusado —
    senão o "dou-lhe duas" do item anterior cairia em cima do item novo.

    Só com lance: "dou-lhe uma" sem ninguém ter dado lance não é anúncio de
    nada (o VENDIDO de um item sem lance devolve para a fila).
    """
    if vez not in (1, 2):
        raise DouLheRecusado("Diga 1 ou 2.")
    if leilao.status != "ao_vivo":
        raise DouLheRecusado("Este leilão não está no ar.")
    atual = leilao.lote_atual
    if not atual:
        raise DouLheRecusado("Nenhum item em pregão.")
    if lote is not None and lote.pk != atual.pk:
        raise DouLheRecusado("Esse item não está mais em pregão.")
    if not atual.tem_lance:
        raise DouLheRecusado("Ainda não há lance neste item.")
    marca = _marca_do_martelo(atual)
    with _ESCADA_TRAVA:
        registro = _ESCADA.get(atual.pk)
        degrau = registro[1] if registro and registro[0] == marca else 0
        if vez == 2 and degrau < 1:
            raise DouLheRecusado("Primeiro o dou-lhe uma.")
        # Nunca desce: apertar o "uma" de novo depois do "duas" não volta atrás.
        _ESCADA[atual.pk] = (marca, max(degrau, vez))
    dados = {
        "vez": vez,
        "lote": atual.pk,
        "valor": str(atual.valor_atual),
        "lider": est.participante_publico(atual.lider),
    }
    HUB.publicar("dou_lhe", dados)
    return dados


def publicar_estado():
    """Publica o estado do leilão QUE ESTÁ NO AR — sempre ele.

    O stream é um só, e quem está nele é a sala do leilão ao vivo. Publicar o
    `estado_publico` de outro leilão (a mesa aberta no rascunho do mês que vem
    ligando o som, ou liberando pagamentos) mandava `{"ativo": False}` para
    todo mundo, e a sala via "sem leilão" no meio do pregão (revisão de 24/09).
    """
    HUB.publicar("estado", est.estado_publico(Leilao.ao_vivo()))


def cobranca_viva(participante):
    """A cobrança que ainda vale para a conta em aberto, ou `None`.

    Vale se cobre **exatamente** os itens em aberto, **pelo mesmo valor**, e
    ainda está pendente com código. "Exatamente" é o que faltava: bastava os
    itens em aberto apontarem para ela. Quando o caixa dava baixa na mão num
    deles (ou o devolvia ao leilão), os que sobravam CONTINUAVAM apontando para
    a cobrança antiga, e ela voltava com o valor antigo — a tela dizia R$ 30 e
    o código cobrava R$ 80.
    """
    _, abertos = conta_aberta(participante)
    if not abertos:
        return None
    total = sum((a.valor for a in abertos), Decimal("0.00"))
    ids = sorted(a.pk for a in abertos)
    atual = abertos[0].pagamento
    if (
        atual
        and atual.status == "pendente" and atual.qr_code
        and atual.valor_bruto == total
        and all(a.pagamento_id == atual.id for a in abertos)
        and (not atual.cobre or sorted(atual.cobre) == ids)
    ):
        return atual
    return None


def _valor_confere(resposta, total):
    """A cobrança que o MP devolveu é deste valor? Sem o dado, confia."""
    bruto = (resposta.get("raw") or {}).get("transaction_amount")
    if bruto is None:
        return True
    try:
        return abs(Decimal(str(bruto)) - total) < Decimal("0.01")
    except (InvalidOperation, ValueError):
        return True


def cobranca_do_participante(participante, *, refazer=False):
    """UM Pix pelo TOTAL do que a pessoa levou.

    Era um Pix por item, com 15 minutos correndo. Agora é uma cobrança só:
    quem levou quatro coisas copia um código, não quatro.

    **A âncora é a referência, não a FK** — a lição que o projeto já pagou
    caro. `Arremate.pagamento` é trocado quando a cobrança é refeita e a
    anterior fica órfã, e é ela que pode estar na tela da pessoa naquele
    instante. Por isso a referência carrega participante e leilão
    (`LEILAOC-<participante>-<leilao>`), e é por ela que
    `_arremates_do_pagamento` reencontra o que foi pago.

    Sem Mercado Pago configurado o leilão **não para**: o caixa dá baixa
    manual. Por isso a falha aqui é registro, não exceção na cara de ninguém.
    """
    cfg = ConfigLeilao.get_solo()
    if not cfg.configurado:
        logger.warning("Leilão: Mercado Pago não configurado — sem Pix para %s.", participante.id)
        return None

    leilao_id, abertos = conta_aberta(participante)
    if not abertos:
        return None

    total = sum((a.valor for a in abertos), Decimal("0.00"))
    ids = sorted(a.pk for a in abertos)

    # Já existe cobrança viva cobrindo exatamente estes itens, por este valor?
    # Devolve a mesma — sem isto, cada abertura da gaveta geraria um Pix novo,
    # vários códigos vivos do mesmo dinheiro.
    if not refazer:
        viva = cobranca_viva(participante)
        if viva:
            return viva

    base = f"LEILAOC-{participante.id}-{leilao_id}"
    referencia = base
    if refazer or PagamentoLeilao.objects.filter(referencia=referencia).exists():
        # A referência é a chave de idempotência no Mercado Pago: repeti-la
        # devolveria a cobrança antiga, com o valor antigo. O sufixo era em
        # SEGUNDOS — refazer duas vezes no mesmo segundo (baixa na mão e novo
        # pedido) repetia a chave e voltava o Pix velho. Milissegundos e, se
        # ainda assim colidir, o seguinte livre.
        marca = int(timezone.now().timestamp() * 1000)
        referencia = f"{base}-R{marca}"
        while PagamentoLeilao.objects.filter(referencia=referencia).exists():
            marca += 1
            referencia = f"{base}-R{marca}"

    notificacao = ""
    if cfg.site_url:
        notificacao = f"{cfg.site_url.rstrip('/')}/webhooks/mercadopago/"

    quantos = len(abertos)
    descricao = f"Leilão — {quantos} item{'s' if quantos > 1 else ''}"
    resposta = mercadopago.criar_pix(
        cfg,
        referencia=referencia,
        valor=total,
        descricao=descricao,
        payer_nome=participante.nome,
        notification_url=notificacao,
        expira_minutos=MINUTOS_PIX_COMBINADO,
    )
    if resposta.get("ok") and not _valor_confere(resposta, total):
        # A referência é a chave de idempotência do MP. Se uma tentativa
        # anterior criou a cobrança lá e caiu antes de gravar aqui (timeout),
        # a mesma chave devolve AQUELA cobrança — com o valor de antes. Uma
        # referência nova pede uma cobrança nova, pelo total de agora.
        logger.warning("Leilão: Pix de %s voltou com valor antigo; gerando outro.", participante.id)
        referencia = f"{base}-R{int(timezone.now().timestamp() * 1000)}"
        while PagamentoLeilao.objects.filter(referencia=referencia).exists():
            referencia += "1"
        resposta = mercadopago.criar_pix(
            cfg,
            referencia=referencia,
            valor=total,
            descricao=descricao,
            payer_nome=participante.nome,
            notification_url=notificacao,
            expira_minutos=MINUTOS_PIX_COMBINADO,
        )
        if resposta.get("ok") and not _valor_confere(resposta, total):
            logger.error("Leilão: Pix de %s segue com valor divergente; desisti.", participante.id)
            return None
    if not resposta.get("ok"):
        logger.error(
            "Leilão: falha ao gerar Pix de %s: %s", participante.id, resposta.get("erro")
        )
        return None

    import json

    try:
        pagamento = PagamentoLeilao.objects.create(
            referencia=referencia,
            mp_payment_id=resposta.get("mp_payment_id", ""),
            status=resposta.get("status", "pendente"),
            valor_bruto=total,
            cobre=ids,
            qr_code=resposta.get("qr_code", ""),
            qr_code_base64=resposta.get("qr_code_base64", ""),
            ticket_url=resposta.get("ticket_url", ""),
            payload=json.dumps(resposta.get("raw") or {}, ensure_ascii=False, default=str),
        )
    except IntegrityError:
        # Duas abas pedindo o Pix no mesmo instante passam juntas pela
        # conferência da referência e a segunda bate no `unique`. Em vez de um
        # 500 na cara de quem vai pagar, devolve a cobrança que a outra criou —
        # MAS só se ela cobre exatamente esta conta; senão, nada (a tela pede
        # de novo em instantes), nunca um Pix com o valor errado.
        logger.warning("Leilão: Pix de %s criado em dobro; conferindo o primeiro.", participante.id)
        outra = PagamentoLeilao.objects.filter(referencia=referencia).first()
        if outra and sorted(outra.cobre or []) == ids and outra.valor_bruto == total:
            return outra
        return None
    Arremate.objects.filter(pk__in=[a.pk for a in abertos]).update(pagamento=pagamento)
    HUB.publicar(
        "arremate_pix",
        {"participante": participante.id, "ok": True},
    )
    return pagamento


def marcar_pago(arremate, *, manual=False, pagamento=None):
    """Dá o arremate por pago. **Idempotente** (o webhook do MP repete o aviso)."""
    if arremate.status == "pago":
        return arremate
    arremate.status = "pago"
    arremate.pago_em = timezone.now()
    arremate.pago_manual = manual
    if pagamento:
        # Aponta para a cobrança que foi REALMENTE paga, mesmo que não seja a
        # última gerada: é dela que sai a taxa e é ela que o extrato explica.
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


# `expirar_arremate` NÃO EXISTE MAIS, e com ele foi embora a devolução
# automática do item à fila. Não há prazo: quem arremata paga no fim, e quem
# não paga **fica devendo** — o caixa cobra (WhatsApp e Pix estão lá). Devolver
# o item por relógio punia quem estava sem o celular na mão, e o status
# "expirado" continua nas linhas antigas só como histórico.


def cobrancas_do_arremate(arremate):
    """**Todas** as cobranças que já foram criadas para este arremate.

    Não só a atual: refazer o Pix (esticar o prazo, combinar de pagar depois)
    deixa a anterior para trás, e é ela que está **na tela da pessoa** no
    instante em que o caixa aperta o botão. Se ela pagar aquele código, é por
    esta lista que o sistema descobre.

    A ligação é a `referencia`, que nasce do id do arremate (`LEILAO-<id>` e
    `LEILAO-<id>-R<timestamp>`) e não muda.
    """
    refs = PagamentoLeilao.objects.filter(
        referencia__startswith=f"LEILAO-{arremate.id}"
    ).exclude(mp_payment_id="")
    # A referência com prefixo pega "LEILAO-1" e "LEILAO-1-R…", mas pegaria
    # "LEILAO-12" junto. Confere o id de verdade.
    achadas = [p for p in refs if _id_da_referencia(p.referencia) == arremate.id]
    if arremate.pagamento_id and arremate.pagamento.mp_payment_id:
        if all(p.pk != arremate.pagamento_id for p in achadas):
            achadas.append(arremate.pagamento)
    return achadas


def _id_da_referencia(referencia):
    """O id do arremate dentro de `LEILAO-<id>` / `LEILAO-<id>-R<timestamp>`.

    Formato **antigo**, de quando cada item tinha o seu Pix. Continua aqui
    porque as cobranças daquela época existem no banco e no Mercado Pago, e uma
    delas ainda pode ser paga.
    """
    partes = (referencia or "").split("-")
    if len(partes) < 2 or partes[0] != "LEILAO" or not partes[1].isdigit():
        return None
    return int(partes[1])


def _conta_da_referencia(referencia):
    """`(participante_id, leilao_id)` de `LEILAOC-<participante>-<leilao>[-R<ts>]`.

    Formato **atual**: uma cobrança pelo total do que a pessoa levou. A
    referência carrega quem e de qual leilão justamente para o dinheiro não
    depender da FK — que é trocada quando o Pix é refeito, deixando órfã a
    cobrança que está na tela da pessoa naquele instante.
    """
    partes = (referencia or "").split("-")
    if len(partes) < 3 or partes[0] != "LEILAOC":
        return None
    if not partes[1].isdigit() or not partes[2].isdigit():
        return None
    return int(partes[1]), int(partes[2])


def cobrancas_do_participante(participante):
    """Todas as cobranças já criadas para esta pessoa — não só a atual.

    Mesma razão da lista por arremate: refazer o Pix deixa a anterior para
    trás, e é ela que pode estar na tela no instante em que a pessoa paga.
    """
    achadas = list(
        PagamentoLeilao.objects.filter(
            referencia__startswith=f"LEILAOC-{participante.id}-"
        ).exclude(mp_payment_id="")
    )
    # O prefixo pega "LEILAOC-1-..." mas também "LEILAOC-12-..." se o separador
    # faltasse; confere o id de verdade, como a lista por arremate já fazia.
    return [
        p for p in achadas
        if (_conta_da_referencia(p.referencia) or (None, None))[0] == participante.id
    ]


def conferir_pagamento(arremate):
    """Consulta o Mercado Pago na marra (reforço para webhook atrasado).

    O webhook é o caminho normal, mas ele atrasa — e quem acabou de pagar está
    olhando a tela esperando o selo mudar. Esta consulta é o que fecha esse
    buraco enquanto o painel de pagamento está aberto.

    **Sem `site_url` configurado não existe webhook nenhum**, e esta consulta
    passa a ser o único caminho do dinheiro: por isso ela pergunta por **todas**
    as cobranças do arremate, não só a última.
    """
    if arremate.status == "pago":
        return True
    cfg = ConfigLeilao.get_solo()
    if not cfg.configurado:
        return False

    # As DUAS listas: a da pessoa (formato atual, um Pix pelo total) e a do
    # próprio arremate (formato antigo, um Pix por item). Sem `site_url` não há
    # webhook e esta consulta é o único caminho do dinheiro — então ela precisa
    # olhar tudo que pode ter sido pago, não só a cobrança mais recente.
    candidatas = cobrancas_do_participante(arremate.participante)
    vistas = {p.pk for p in candidatas}
    for antiga in cobrancas_do_arremate(arremate):
        if antiga.pk not in vistas:
            candidatas.append(antiga)

    # A pergunta é "ESTE item foi pago?", não "alguma cobrança desta pessoa
    # está aprovada?". Antes a volta parava no primeiro `True` do
    # `_aplicar_retorno` — que é `True` para QUALQUER cobrança aprovada, mesmo
    # uma antiga que não quitou nada agora: quem já tinha pago o Pix do item 1
    # e abria o QR do item 2 via "Pagamento confirmado! 🎉" com o item 2 em
    # aberto (revisão de 24/09).
    #
    # E só se consulta o Mercado Pago pelo que pode ter pago algo em aberto:
    # cobrança já processada (`finalizado`) ou que não cobre nenhum item em
    # aberto não vale uma chamada a cada 5 s.
    _, abertos = conta_aberta(arremate.participante)
    ids_abertos = {a.pk for a in abertos} | {arremate.pk}
    for pagamento in candidatas:
        if pagamento.finalizado:
            continue
        if pagamento.cobre and not (set(pagamento.cobre) & ids_abertos):
            continue
        if pagamento.status == "aprovado":
            _aplicar_retorno(pagamento, {"status": "aprovado"})
        else:
            r = mercadopago.consultar_pagamento(cfg, pagamento.mp_payment_id)
            if r.get("ok"):
                _aplicar_retorno(pagamento, r)
        arremate.refresh_from_db(fields=["status"])
        if arremate.status == "pago":
            return True
    return False


def _arremates_do_pagamento(pagamento):
    """Quem este pagamento quita — **inclusive quando o Pix foi refeito**.

    O caminho normal é a FK (`Arremate.pagamento`). Só que ela aponta para **uma**
    cobrança, e refazer o Pix (esticar o prazo, combinar de pagar depois) troca
    esse ponteiro: a cobrança antiga fica sem arremate nenhum.

    Isso é dinheiro no chão. O código antigo continua válido no Mercado Pago por
    algum tempo, e é justamente o que está **na tela da pessoa** quando o caixa
    aperta "+15 min" — ela paga aquele, o webhook chega, o pagamento é aprovado,
    e ninguém é marcado como pago. O sistema segue cobrando quem já pagou.

    Por isso, não achando pela FK, o arremate é recuperado da **referência**
    (`LEILAO-<id>` ou `LEILAO-<id>-R<timestamp>`), que é gravada na criação e
    não muda.
    """
    # A lista gravada na criação é a resposta EXATA (mig. 0014): nem a FK (que
    # muda quando o Pix é refeito) nem um palpite pelo que a pessoa tem em
    # aberto HOJE.
    if pagamento.cobre:
        return list(
            Arremate.objects.select_related("lote", "participante").filter(pk__in=pagamento.cobre)
        )

    ligados = list(pagamento.arremates.select_related("lote", "participante"))
    if ligados:
        return ligados

    # Formato ATUAL sem a lista (cobrança anterior à 0014): a cobrança é da
    # pessoa, pelo total. O palpite pelo que está em aberto agora só vale se o
    # VALOR bater — um Pix antigo de R$ 10 pago depois de ela arrematar outro
    # item de R$ 100 quitava os dois, e o de R$ 100 ia para a entrega sem ter
    # sido pago. Não batendo, ninguém é quitado sozinho: fica no log para o
    # caixa acertar, que é melhor do que dinheiro inventado.
    conta = _conta_da_referencia(pagamento.referencia)
    if conta:
        participante_id, leilao_id = conta
        achados = list(
            Arremate.objects.select_related("lote", "participante").filter(
                participante_id=participante_id,
                lote__leilao_id=leilao_id,
                status__in=("aguardando", "combinado"),
            )
        )
        soma = sum((a.valor for a in achados), Decimal("0.00"))
        if achados and soma != pagamento.valor_bruto:
            logger.error(
                "Leilão: pagamento %s (R$ %s) não bate com o que está em aberto "
                "(R$ %s em %s item(ns)) — nada quitado sozinho; acerto no caixa.",
                pagamento.referencia, pagamento.valor_bruto, soma, len(achados),
            )
            return []
        if achados:
            logger.warning(
                "Leilão: pagamento %s quitou %s arremate(s) pela referência "
                "(o Pix tinha sido refeito).",
                pagamento.referencia, len(achados),
            )
        return achados

    # Formato ANTIGO (um Pix por item), que ainda pode ser pago.
    arremate_id = _id_da_referencia(pagamento.referencia)
    if arremate_id is None:
        return []
    arremate = (
        Arremate.objects.select_related("lote", "participante")
        .filter(pk=arremate_id)
        .first()
    )
    if arremate:
        logger.warning(
            "Leilão: pagamento %s quitou o arremate %s pela referência "
            "(o Pix tinha sido refeito).",
            pagamento.referencia, arremate.id,
        )
    return [arremate] if arremate else []


def _aplicar_retorno(pagamento, r):
    """Grava o que o MP disse e, se aprovado, quita o arremate. Idempotente."""
    pagamento.status = r.get("status", pagamento.status)
    pagamento.taxa = r.get("taxa") or Decimal("0.00")
    pagamento.valor_liquido = r.get("liquido") or pagamento.valor_bruto
    pagamento.save(update_fields=["status", "taxa", "valor_liquido"])

    if pagamento.status == "estornado":
        _desfazer_baixa_do_estorno(pagamento)
        return False
    if pagamento.status != "aprovado":
        return False

    # O VALOR PAGO tem de cobrir o que a cobrança pedia. Sem esta conferência,
    # uma cobrança com valor antigo (ou paga a menos) quitava a conta INTEIRA
    # do `cobre` (revisão de 26/09). Não quita: registra e deixa para o caixa.
    pago = r.get("valor")
    if pago is not None and pagamento.valor_bruto and Decimal(str(pago)) + Decimal("0.01") < pagamento.valor_bruto:
        logger.error(
            "Leilão: pagamento %s aprovado por R$ %s, mas cobrava R$ %s — NÃO quitado; conferir com a pessoa.",
            pagamento.referencia, pago, pagamento.valor_bruto,
        )
        return False

    if not pagamento.finalizado:
        pagamento.finalizado = True
        pagamento.save(update_fields=["finalizado"])

    # Só quita o que AINDA ESTÁ EM ABERTO. Sem esta conferência, o Pix pago
    # depois de o caixa devolver um item ao leilão (ou dar baixa na mão)
    # transformava o arremate cancelado em "pago" — e o item, talvez já
    # vendido de novo para outra pessoa, voltava para a entrega de quem pagou.
    fora = []
    for arremate in _arremates_do_pagamento(pagamento):
        if arremate.status in ("aguardando", "combinado") and not arremate.devolvido_em:
            marcar_pago(arremate, pagamento=pagamento)
        elif arremate.status == "pago" and arremate.pagamento_id == pagamento.id and not arremate.pago_manual:
            continue   # o webhook repetiu o aviso: já quitado por esta mesma cobrança
        # Baixa MANUAL com a FK ainda apontando para este Pix (o caixa mandou o
        # Pix, a pessoa pagou em dinheiro, e depois pagou o Pix também): é
        # dinheiro em dobro, e cai em `fora` para gerar o alerta — antes o
        # `continue` acima o engolia calado (revisão de 26/09).
        else:
            fora.append(arremate)
    if fora:
        # Dinheiro que entrou por item que já não estava em aberto (pago na
        # mão, devolvido ao leilão). Não é estorno automático — quem decide é
        # o caixa, com a pessoa — mas não pode passar em silêncio.
        logger.error(
            "Leilão: pagamento %s aprovado cobre item(ns) que não estavam mais em "
            "aberto: %s — conferir com a pessoa (pagou em dobro ou item devolvido).",
            pagamento.referencia,
            ", ".join(f"#{a.pk} {a.lote.nome} ({a.status})" for a in fora),
        )
    return True


def _desfazer_baixa_do_estorno(pagamento):
    """O Mercado Pago devolveu o dinheiro (estorno, contestação): quem estava
    pago POR ESTA COBRANÇA volta a dever.

    Sem isto o item seguia "pago" e na lista de entrega — o voluntário
    levava na casa de alguém um item cujo dinheiro já tinha voltado para ela.
    A baixa manual não é tocada: ela não passou por esta cobrança.
    """
    voltaram = []
    for arremate in _arremates_do_pagamento(pagamento):
        if arremate.status == "pago" and arremate.pagamento_id == pagamento.id and not arremate.pago_manual:
            # Quem pagou EM DOBRO tem outra cobrança aprovada cobrindo o item:
            # estornar uma delas não o põe de volta na dívida — o item passa a
            # apontar para a que ficou.
            outra = next(
                (p for p in PagamentoLeilao.objects.filter(
                    status="aprovado", referencia__startswith=f"LEILAOC-{arremate.participante_id}-",
                ).exclude(pk=pagamento.pk)
                 if arremate.pk in (p.cobre or [])),
                None,
            )
            if outra:
                arremate.pagamento = outra
                arremate.save(update_fields=["pagamento"])
                continue
            if arremate.devolvido_em:
                # O item já foi DOADO DE VOLTA ao leilão (talvez revendido): o
                # dinheiro voltou para a pessoa e o item não vai para ela —
                # não há dívida. Antes virava "aguardando" e entrava na conta
                # dela de novo (revisão de 26/09).
                arremate.status = "cancelado"
                arremate.pago_em = None
                arremate.save(update_fields=["status", "pago_em"])
                continue
            arremate.status = "aguardando"
            arremate.pago_em = None
            arremate.save(update_fields=["status", "pago_em"])
            voltaram.append(arremate)
    if voltaram:
        logger.error(
            "Leilão: pagamento %s ESTORNADO — %s item(ns) voltaram a dever: %s.",
            pagamento.referencia, len(voltaram),
            ", ".join(f"#{a.pk} {a.lote.nome}" for a in voltaram),
        )
        # O caixa e a tela da pessoa refazem a conta sem ninguém recarregar.
        for a in voltaram:
            HUB.publicar("arremate_pix", {"participante": a.participante_id, "ok": True})


class DevolucaoRecusada(Exception):
    """A devolução não pode acontecer, e a mensagem é para quem está na tela."""


def devolver_ao_leilao(arremate, motivo, por=None):
    """Tira o item da conta de quem arrematou e o devolve à fila do leilão.

    Existe por dois casos reais, e o dinheiro se comporta diferente em cada um:

    - **não pagou**: a pessoa desistiu. A dívida some junto (o arremate vira
      `cancelado`) — continuar cobrando por um item que ela não vai receber
      seria errado, e o item volta a ser leiloável;
    - **pagou**: ela **doou o item de volta** para o clube leiloar outra vez.
      O arremate continua `pago`, porque o dinheiro entrou e é do clube: não é
      estorno. O que muda é que ela sai da **entrega** (`a_entregar` confere o
      `devolvido_em`), senão um voluntário sairia para levar na casa dela um
      objeto que está de volta na prateleira.

    O **motivo é obrigatório**: um item reaparecendo na fila depois de batido é
    a coisa mais estranha que pode acontecer num leilão, e quem abrir a lista
    amanhã precisa saber por quê sem ter de perguntar a alguém.

    O lote volta **limpo** (sem líder e sem valor), como em
    `_devolver_lotes_abertos` e no `abrir_lote`: a disputa anterior acabou, e
    item na fila exibindo o líder de uma rodada encerrada é pior do que item sem
    nada. `voltas` sobe — é o contador que a tela mostra como "voltou 2x".
    O **número do item não muda**: ele é a etiqueta colada na caixa.
    """
    motivo = (motivo or "").strip()
    if not motivo:
        raise DevolucaoRecusada("Escreva por que o item está voltando ao leilão.")
    if len(motivo) > 200:
        motivo = motivo[:200]

    # Idempotente: o botão sobrevive na tela até a página se refazer, e o
    # segundo clique não pode somar outra volta nem reescrever o motivo.
    if arremate.devolvido_em:
        raise DevolucaoRecusada("Este item já tinha voltado ao leilão.")

    lote = arremate.lote
    if lote.status == "aberto":
        raise DevolucaoRecusada(
            "Este item está em pregão agora. Espere o martelo para devolvê-lo."
        )

    with transaction.atomic():
        arremate.devolvido_em = timezone.now()
        arremate.devolvido_por = por
        arremate.motivo_devolucao = motivo
        campos = ["devolvido_em", "devolvido_por", "motivo_devolucao"]
        # Quem não pagou deixa de dever; quem pagou continua pago (doou).
        if arremate.status in {"aguardando", "combinado"}:
            arremate.status = "cancelado"
            campos.append("status")
        arremate.save(update_fields=campos)

        Lote.objects.filter(pk=lote.pk).update(
            status="fila",
            valor_atual=Decimal("0.00"),
            lider=None,
            fecha_em=None,
            pausado_restante=None,
            voltas=F("voltas") + 1,
        )

    lote.refresh_from_db()
    # A fila e o estado mudaram: quem está com a mesa ou o pregão aberto vê
    # sozinho, sem recarregar.
    #
    # O estado publicado é o do leilão QUE ESTÁ NO AR, não o do item: a
    # devolução quase sempre acontece depois do evento, e o `estado_publico` de
    # um leilão encerrado é "sem leilão" — publicá-lo apagava o pregão da tela
    # de todo mundo se outro leilão estivesse no ar.
    publicar_estado()
    return lote


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------
# `abrir_chat`/`fechar_chat` NÃO EXISTEM MAIS. O chat fica aberto enquanto o
# leilão está no ar (`Leilao.chat_aberto`), sem contagem e sem botão: o clube
# pediu a conversa aberta direto. Com isso saíram também a ação "chat" da mesa
# e o evento `chat_estado` com prazo — quem precisa saber se a caixa aparece lê
# `estado.chat.aberto`, que vem no broadcast como todo o resto.


def _devolver_lotes_abertos(leilao_ids):
    """Leilão fora do ar não deixa item em pregão para trás.

    O item aberto é um estado **do pregão**, e o pregão acabou: sem isto a
    linha fica `aberto` para sempre e a mesa do locutor volta a mostrar "item
    em pregão, sala calada" com o leilão encerrado há dias. É a mesma lição que
    o `chat_aberto_ate` ensinou — o que é do pregão morre com ele.

    Volta **limpo** para a fila, igualzinho ao que o `abrir_lote` já faz com o
    lote que sobrou aberto: o item não foi vendido (ninguém arrematou), então
    ele fica disponível de novo. Os lances continuam no banco como histórico,
    mas o lote não pode ficar na fila exibindo líder e valor de uma disputa que
    foi abandonada — `lances_da_rodada()` já sabe ignorar a rodada anulada.
    """
    return Lote.objects.filter(leilao_id__in=leilao_ids, status="aberto").update(
        status="fila",
        fecha_em=None,
        pausado_restante=None,
        valor_atual=Decimal("0.00"),
        lider=None,
    )


def mudar_status(leilao, novo):
    """Coloca no ar / tira do ar — e AVISA quem está esperando.

    Sem este aviso, a tela que diz "assim que iniciarmos, isto acende sozinho"
    mentia: ela só acordava quando o primeiro item abria. Quem estava com o
    celular na mão desde antes continuava vendo a tela de espera.
    """
    if novo == "ao_vivo":
        # O leilão que sai do ar leva o chat dele junto (ver abaixo) — e o
        # item que estava em pregão nele também.
        saindo = list(
            Leilao.objects.filter(status="ao_vivo")
            .exclude(pk=leilao.pk)
            .values_list("pk", flat=True)
        )
        if saindo:
            Leilao.objects.filter(pk__in=saindo).update(status="encerrado")
            _devolver_lotes_abertos(saindo)
    leilao.status = novo

    # Sair do ar fecha o chat SOZINHO: `Leilao.chat_aberto` é hoje só
    # `status == "ao_vivo"`. Antes havia uma hora futura no banco que não sabia
    # que o leilão tinha acabado, e era preciso apagá-la aqui à mão — a tela
    # mostrava a caixa de conversa e o servidor recusava cada mensagem. Com a
    # condição derivada do status, essa divergência não tem como existir.
    leilao.save(update_fields=["status"])

    if novo != "ao_vivo":
        # Sair do ar fecha o item em pregão. Sem isto o lote fica `aberto` no
        # banco e a mesa passa a mostrar um pregão que não existe.
        _devolver_lotes_abertos([leilao.pk])

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
    """Chamado pelo laço central a cada segundo. **Hoje não tem o que fazer.**

    Já foi o lugar de duas regras de tempo, e as duas saíram a pedido do clube:

    - o **prazo de pagamento** (15 minutos, e o item voltava para a fila) —
      quem arremata agora paga no fim, tudo de uma vez, e quem não paga fica
      devendo para o caixa cobrar;
    - o **fim do chat**, que fechava sozinho no prazo — o chat fica aberto o
      leilão inteiro.

    **O item em pregão nunca esteve nesta lista**: não há cronômetro, quem bate
    o martelo é o locutor.

    A função fica de pé porque é o ponto único onde o tempo decide alguma coisa
    (o laço central a chama a cada segundo). Regra de tempo nova entra AQUI, e
    não num caminho paralelo — foi assim que o projeto evitou dois lugares
    fechando a mesma coisa de dois jeitos.
    """
    return
