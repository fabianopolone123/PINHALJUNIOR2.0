"""Montagem do **estado público** do leilão (o que vai no stream).

Um lugar só serializa o pregão, e é usado por três caminhos: o `estado` inicial
do SSE, o evento de cada lance e a carga da página. Assim a tela nunca vê dois
formatos diferentes do mesmo dado.

Duas regras deste arquivo:

1. **Só entra o que é público.** Código Pix, telefone e endereço **nunca** vão
   no broadcast — eles saem por `GET` próprio, autenticado pela sessão. O que é
   transmitido para 100 pessoas tem que poder ser visto por 100 pessoas.
2. **Vai junto o relógio do servidor** (`servidor_em`). O navegador calcula a
   diferença entre ele e o próprio relógio uma vez e aplica em toda contagem —
   é isso que faz o cronômetro bater igual em todo mundo, mesmo no celular com
   a hora errada.
"""

from django.utils import timezone

from .hub import HUB


def iso(dt):
    return timezone.localtime(dt).isoformat() if dt else None


def _foto(campo):
    """URL da imagem, ou vazio. `campo.url` estoura se não houver arquivo."""
    try:
        return campo.url if campo else ""
    except ValueError:
        return ""


def participante_publico(p):
    """O que pode ser dito em voz alta sobre quem está ganhando."""
    if not p:
        return None
    return {"id": p.id, "nome": p.nome_curto}


def lote_publico(lote):
    if not lote:
        return None
    return {
        "id": lote.id,
        "nome": lote.nome,
        "descricao": lote.descricao,
        "foto": _foto(lote.foto),
        "foto_mini": _foto(lote.foto_mini) or _foto(lote.foto),
        "status": lote.status,
        "lance_inicial": str(lote.lance_inicial),
        "incremento": str(lote.incremento_efetivo),
        "valor_atual": str(lote.valor_atual),
        "proximo_valor": str(lote.proximo_valor),
        "tem_lance": lote.tem_lance,
        "lider": participante_publico(lote.lider),
        "fecha_em": iso(lote.fecha_em),
        "segundos": lote.segundos_restantes,
        # O anel do cronômetro precisa saber a duração CHEIA para desenhar a
        # fração que falta — senão ele nasceria sempre em 100% ou teria que
        # adivinhar o total.
        "total_segundos": lote.leilao.segundos_por_lote,
        "pausado": lote.pausado,
        "voltas": lote.voltas,
    }


def lance_publico(lance):
    return {
        "id": lance.id,
        "lote": lance.lote_id,
        "valor": str(lance.valor),
        "quem": lance.participante.nome_curto,
        "quem_id": lance.participante_id,
        "em": iso(lance.criado_em),
    }


def mensagem_publica(m):
    return {
        "id": m.id,
        "autor": m.autor,
        "autor_id": m.participante_id,
        "texto": m.texto,
        "em": iso(m.criado_em),
    }


def estado_publico(leilao, *, com_chat=True):
    """O retrato completo do pregão agora.

    É o que vai no `estado` da (re)conexão do SSE. Mandar o estado inteiro em
    vez de tentar repetir eventos perdidos é o que dispensa lógica de replay:
    **um cliente que reconecta está sempre correto**.
    """
    if leilao is None:
        return {"ativo": False, "servidor_em": iso(timezone.now())}

    lote = leilao.lote_atual
    fila = list(
        leilao.lotes.filter(status="fila").order_by("ordem", "id")[:12]
    )
    ultimos = []
    if lote:
        ultimos = [
            lance_publico(x)
            for x in lote.lances_da_rodada()
            .select_related("participante")
            .order_by("-criado_em", "-id")[:6]
        ]

    dados = {
        "ativo": True,
        "leilao": {
            "id": leilao.id,
            "nome": leilao.nome,
            "descricao": leilao.descricao,
            "status": leilao.status,
            "minutos_para_pagar": leilao.minutos_para_pagar,
        },
        "lote": lote_publico(lote),
        "fila": [
            {
                "id": x.id,
                "nome": x.nome,
                "foto_mini": _foto(x.foto_mini) or _foto(x.foto),
                # A foto GRANDE do próximo vai junto para a tela poder
                # pré-carregá-la. Sem isso, o primeiro segundo do lote novo — o
                # mais importante — mostra um quadro vazio enquanto a imagem
                # baixa. São ~50 bytes por item; vale a troca.
                "foto": _foto(x.foto),
            }
            for x in fila
        ],
        "restam_na_fila": leilao.lotes.filter(status="fila").count(),
        "vendidos": leilao.lotes.filter(status="vendido").count(),
        "ultimos_lances": ultimos,
        "online": HUB.conectados,
        "servidor_em": iso(timezone.now()),
    }

    if com_chat:
        dados["chat"] = {
            "aberto": leilao.chat_aberto,
            "ate": iso(leilao.chat_aberto_ate) if leilao.chat_aberto else None,
            "mensagens": [
                mensagem_publica(m)
                for m in leilao.mensagens.filter(removida=False)
                .select_related("participante")
                .order_by("-criado_em", "-id")[:40]
            ][::-1],
        }
    return dados
