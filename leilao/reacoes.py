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

# Teto por despejo: mais que isto não cabe na tela e só derruba o celular
# fraco. O contador segue somando; o que passa disso é descartado no desenho.
TETO_POR_DESPEJO = 40

_contagem = {}
_lock = threading.Lock()


def registrar(emoji, quantos=1):
    """Soma toques ao balde. Chamado pela view — barato de propósito."""
    if emoji not in EMOJIS:
        return False
    quantos = max(1, min(int(quantos or 1), 10))
    with _lock:
        _contagem[emoji] = _contagem.get(emoji, 0) + quantos
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
