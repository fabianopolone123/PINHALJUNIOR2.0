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
    """O que pode ser dito em voz alta sobre quem está ganhando.

    Vai junto a `chave` — um **hash** do telefone. É o que permite à tela saber
    "o líder sou eu" mesmo quando a pessoa entrou de novo em outro aparelho (e
    virou outro registro), sem expor o número para as outras 50 pessoas.
    """
    if not p:
        return None
    return {"id": p.id, "nome": p.nome_curto, "chave": p.chave_pessoa}


def ultimo_vendido(leilao):
    """A última venda — vira a FESTA do intervalo.

    Entre um item e outro a tela não fica dizendo quantos faltam (isso muda como
    a pessoa dá lance). Fica comemorando quem acabou de arrematar: é o momento
    bom do leilão, e o nome da pessoa na tela grande é o que anima a próxima
    disputa.
    """
    lote = (
        leilao.lotes.filter(status="vendido")
        .select_related("lider")
        .order_by("-fechado_em")
        .first()
    )
    if not lote or not lote.lider_id:
        return None
    return {
        "item": lote.nome,
        "foto": _foto(lote.foto_mini) or _foto(lote.foto),
        "vencedor": lote.lider.nome_curto,
        "vencedor_chave": lote.lider.chave_pessoa,
        "valor": str(lote.valor_atual),
    }


def _parado_desde(lote):
    """Quando foi o último lance (ou a abertura). O cliente conta a partir daí —
    o relógio continua sendo o do servidor."""
    if lote.status != "aberto":
        return None
    ultimo = (
        lote.lances_da_rodada().order_by("-criado_em")
        .values_list("criado_em", flat=True).first()
    )
    return ultimo or lote.aberto_em


def lote_publico(lote):
    if not lote:
        return None
    return {
        "id": lote.id,
        "nome": lote.nome,
        "descricao": lote.descricao,
        # Peso e dimensões podem ser ditos em voz alta: são o tamanho do que
        # está sendo vendido, não dado de ninguém. Vai o TEXTO já montado, e
        # não os quatro números: o formato é decidido num lugar só
        # (`Lote.medidas_texto`), senão a tela do público, a mesa, o caixa e o
        # roteiro de entrega escrevem a mesma medida de quatro jeitos.
        "medidas": lote.medidas_texto,
        "foto": _foto(lote.foto),
        "foto_mini": _foto(lote.foto_mini) or _foto(lote.foto),
        "status": lote.status,
        "lance_inicial": str(lote.lance_inicial),
        "incremento": str(lote.incremento_efetivo),
        "valor_atual": str(lote.valor_atual),
        "proximo_valor": str(lote.proximo_valor),
        "tem_lance": lote.tem_lance,
        "lider": participante_publico(lote.lider),
        # Só existe contagem regressiva quando o leilão está no modo de fechar
        # sozinho. No padrão, quem bate o martelo é o locutor — e o que a mesa
        # dele mostra é há quanto tempo a sala está calada (`parado_desde`),
        # contando para CIMA.
        "parado_desde": iso(_parado_desde(lote)),
        "voltas": lote.voltas,
    }


def lance_publico(lance):
    """Um lance, para o evento em tempo real.

    A tela do participante **não lista lances** — ela usa isto só para saber se
    o lance foi dela (som e vibração diferentes). Quem exibe a lista é a mesa do
    locutor, que recebe o histórico por um caminho próprio e autenticado.
    """
    return {
        "id": lance.id,
        "lote": lance.lote_id,
        "valor": str(lance.valor),
        "quem": lance.participante.nome_curto,
        "quem_id": lance.participante_id,
        # A chave cobre a pessoa que entrou de dois aparelhos: são registros
        # diferentes, e sem ela o 2º aparelho acharia que o lance foi de outro.
        "quem_chave": lance.participante.chave_pessoa,
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
    # Fora do ar não há pregão — e a guarda mora AQUI, não em quem chama.
    # `estado_publico` dizia `ativo: True` para qualquer leilão não-nulo e
    # confiava no chamador ter passado o que está ao vivo. A tela pública
    # acertava por acidente (ela passa `Leilao.ao_vivo()`, que é `None`), mas a
    # mesa do locutor cai para o leilão **mais recente** quando não há nada no
    # ar: ela entregava um leilão encerrado e recebia de volta "item em pregão,
    # sala calada". É a mesma lição do chat (`Leilao.chat_aberto` exige
    # `status == "ao_vivo"`): estado do item e estado do leilão têm de concordar.
    if leilao is None or leilao.status != "ao_vivo":
        # `online` vai junto mesmo sem leilão no ar: antes de começar é
        # exatamente quando o locutor quer saber quantos já estão esperando na
        # tela — e é também como se confere que o hub não ficou com conexões
        # penduradas depois de um pico.
        return {
            "ativo": False,
            "online": HUB.conectados,
            "servidor_em": iso(timezone.now()),
        }

    lote = leilao.lote_atual
    # A FILA NÃO VAI NO BROADCAST. Saber quantos itens faltam muda como a
    # pessoa dá lance — quem descobre que falta pouco segura o dinheiro, e quem
    # vê 20 itens pela frente economiza no primeiro. O suspense é do leilão.
    # A mesa do locutor recebe a fila por um caminho PRÓPRIO e autenticado
    # (`/locutor/dados/`), que não é transmitido para ninguém.
    proximo = leilao.lotes.filter(status="fila").order_by("ordem", "id").first()

    dados = {
        "ativo": True,
        "leilao": {
            "id": leilao.id,
            "nome": leilao.nome,
            "descricao": leilao.descricao,
            "status": leilao.status,
            "minutos_para_pagar": leilao.minutos_para_pagar,
        },
        # Espera e intervalo são coisas diferentes, e a tela precisa saber qual
        # das duas mostrar: antes do primeiro item a pessoa acabou de chegar
        # ("bem-vindo"), depois dele ela está esperando o próximo ("já já").
        # Chamar as duas de "intervalo" dá a quem chega a impressão de que
        # perdeu o começo.
        "comecou": leilao.ja_comecou(),
        "boas_vindas": {
            "titulo": leilao.boas_vindas_titulo,
            # Uma informação por linha, como o campo é preenchido. A tela monta
            # a lista; o servidor não manda HTML.
            "linhas": [
                linha.strip()
                for linha in (leilao.boas_vindas_texto or "").splitlines()
                if linha.strip()
            ],
        },
        "lote": lote_publico(lote),
        # Só a FOTO do próximo, para a tela pré-carregar e a troca de item ser
        # instantânea. Sem nome, sem quantidade: a URL não conta o que vem nem
        # quantos faltam.
        "proxima_foto": _foto(proximo.foto) if proximo else "",
        "vendidos": leilao.lotes.filter(status="vendido").count(),
        "ultimo_vendido": ultimo_vendido(leilao),
        "online": HUB.conectados,
        "servidor_em": iso(timezone.now()),
    }

    if com_chat:
        # SÓ as mensagens desta rodada de chat. Cada intervalo abre uma conversa
        # nova para quem participa — o fio não se arrasta a noite toda. O
        # histórico completo é da mesa do locutor, por caminho próprio.
        msgs = leilao.mensagens.filter(removida=False)
        if leilao.chat_aberto_em:
            msgs = msgs.filter(criado_em__gte=leilao.chat_aberto_em)
        dados["chat"] = {
            "aberto": leilao.chat_aberto,
            "ate": iso(leilao.chat_aberto_ate) if leilao.chat_aberto else None,
            "mensagens": [
                mensagem_publica(m)
                for m in msgs.select_related("participante")
                .order_by("-criado_em", "-id")[:40]
            ][::-1],
        }
    return dados
