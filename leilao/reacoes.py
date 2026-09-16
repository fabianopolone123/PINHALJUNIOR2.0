"""Reações (emojis) que sobem na tela de todo mundo.

O problema que este arquivo resolve não é desenhar o coraçãozinho — é **escala**.
Numa disputa quente, 50 pessoas martelando o botão dariam centenas de toques por
segundo; repassar cada um para 100 conexões seriam **dezenas de milhares de
mensagens por segundo**, e o pregão — que é o que importa — morreria junto.

A saída é **agregar**: os toques caem num contador em memória e são despejados
de meio em meio segundo como um resumo (`{"❤️": 12, "👏": 3}`). A saída fica
**constante**, não importa quantas pessoas estejam tocando.

Nada disso encosta no banco: reação é enfeite, não registro — não vale uma
escrita em disco por coraçãozinho.
"""

import threading

# Poucos e claros. Emoji demais vira paleta de pintura e ninguém usa.
EMOJIS = ["❤️", "👏", "🔥", "😮", "🎉", "👍"]

# Quantos emojis sobem na tela por TOQUE. Um só some no meio do pregão — e o
# efeito existe justamente para a sala parecer cheia.
#
# Isto não custa requisição nenhuma: o que viaja é a **contagem** dentro do
# resumo que já ia de meio em meio segundo. Sai mais emoji na tela pelo mesmo
# preço de rede, que é o ponto do desenho agregado.
EMOJIS_POR_TOQUE = 4

# Teto por despejo: mais que isto não cabe na tela e só derruba o celular
# fraco. O contador segue somando; o que passa disso é descartado no desenho.
TETO_POR_DESPEJO = 40

_contagem = {}
_lock = threading.Lock()


def registrar(emoji, quantos=1):
    """Soma toques ao balde. Chamado pela view — barato de propósito."""
    if emoji not in EMOJIS:
        return False
    try:
        quantos = max(1, min(int(quantos or 1), 10))
    except (TypeError, ValueError):
        # Vem de JSON da internet: "quantos" pode chegar como texto, lista ou
        # nada. Um 500 aqui seria por causa de um emoji.
        return False
    # A multiplicação é do SERVIDOR, não do cliente: ele é a fonte única da
    # rajada (o navegador lê o mesmo número por `data-rajada` só para descontar
    # o que ele próprio já desenhou). Deixar o cliente mandar o total permitiria
    # a um toque forjado encher a tela de todo mundo.
    with _lock:
        _contagem[emoji] = _contagem.get(emoji, 0) + quantos * EMOJIS_POR_TOQUE
    return True


def drenar():
    """Devolve o acumulado e zera. Chamado pelo laço, não pela view."""
    with _lock:
        if not _contagem:
            return {}
        saida = dict(_contagem)
        _contagem.clear()
    return {e: min(q, TETO_POR_DESPEJO) for e, q in saida.items()}


def limpar():
    """Zera o balde (teste e começo de leilão)."""
    with _lock:
        _contagem.clear()
