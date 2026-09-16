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
import time

# Poucos e claros. Emoji demais vira paleta de pintura e ninguém usa.
EMOJIS = ["❤️", "👏", "🔥", "😮", "🎉", "👍"]

# Quantos emojis sobem na tela por TOQUE. Um só some no meio do pregão — e o
# efeito existe justamente para a sala parecer cheia.
#
# Isto não custa requisição nenhuma: o que viaja é a **contagem** dentro do
# resumo que já ia de meio em meio segundo. Sai mais emoji na tela pelo mesmo
# preço de rede, que é o ponto do desenho agregado.
EMOJIS_POR_TOQUE = 4

# Teto por despejo — **do resumo inteiro**, não de cada emoji.
#
# Por emoji parecia a mesma coisa e não era: são seis emojis, então um resumo
# podia mandar 240 desenhos para um celular que só mostra 30. O excedente não
# ia para lugar nenhum — só engordava a mensagem e dava trabalho ao aparelho
# mais fraco da sala, que é justamente quem não pode travar.
TETO_POR_DESPEJO = 40

# --- O freio da porta de entrada -------------------------------------------
#
# No dia do evento este processo não está fazendo só emoji: ele carrega o
# pregão (lance), o stream de todo mundo e divide o vCPU com o MediaMTX, que
# precisa entregar um pacote de voz a cada 20 ms. A ordem de importância é
# clara e não é opinião: **voz e lance são o leilão; emoji é enfeite.**
#
# Por isso a reação é a primeira coisa a ser descartada quando aperta — e é
# descartada **calada**, sem erro na tela de ninguém: quem tocou já viu o
# próprio emoji subir (a tela desenha na hora), então ele não perde nada.
#
# Duas travas, nesta ordem:
#
# 1. **Por pessoa**: o `reacoes.js` já manda no máximo 2 por segundo, mas o
#    servidor não pode acreditar no cliente — um `fetch` num console faria 200.
# 2. **Do processo inteiro**: um teto de requisições por segundo somando todo
#    mundo. Passou disso, o resto do segundo é descartado. É o que garante que
#    uma sala eufórica não roube o processador de quem está dando lance.
INTERVALO_MIN_POR_PESSOA = 0.4   # segundos
TETO_POR_SEGUNDO = 150

_contagem = {}
_lock = threading.Lock()
_ultimo_toque = {}
_janela = [0.0, 0]               # [segundo, quantas neste segundo]
_freio = threading.Lock()


def aceitar(participante_id):
    """A porta: esta reação entra ou é descartada?

    Fica **fora** do `registrar` de propósito: `registrar` é a regra do balde
    (e é o que os testes exercitam); isto aqui é proteção de tráfego, e vale só
    para quem chega pela rede.
    """
    agora = time.monotonic()
    with _freio:
        ultimo = _ultimo_toque.get(participante_id, 0.0)
        if agora - ultimo < INTERVALO_MIN_POR_PESSOA:
            return False
        segundo = int(agora)
        if _janela[0] != segundo:
            _janela[0] = segundo
            _janela[1] = 0
        if _janela[1] >= TETO_POR_SEGUNDO:
            # A sala inteira martelando ao mesmo tempo. O pregão vem primeiro.
            return False
        _janela[1] += 1
        _ultimo_toque[participante_id] = agora
    return True


def limpar_freio():
    """Zera o freio (teste e começo de leilão, como o `limpar_limites` do lance)."""
    with _freio:
        _ultimo_toque.clear()
        _janela[0] = 0.0
        _janela[1] = 0


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
    """Devolve o acumulado e zera. Chamado pelo laço, não pela view.

    O teto é aplicado ao **resumo inteiro** e repartido entre os emojis na
    proporção em que foram tocados — quem reagiu mais aparece mais. Cada emoji
    que alguém tocou sai com **pelo menos 1**: a tela precisa mostrar que a
    sala mandou seis coisas diferentes, e não só a mais votada.
    """
    with _lock:
        if not _contagem:
            return {}
        saida = dict(_contagem)
        _contagem.clear()

    total = sum(saida.values())
    if total <= TETO_POR_DESPEJO:
        return saida

    resumo = {}
    for emoji, quantos in saida.items():
        resumo[emoji] = max(1, round(quantos * TETO_POR_DESPEJO / total))
    return resumo


def limpar():
    """Zera o balde **e o freio** (teste e começo de leilão).

    O freio guarda o último toque por id de participante, em memória do
    processo. Entre um teste e outro (onde os ids se repetem) isso viraria
    estado velho descartando reação legítima — o mesmo cuidado que o
    `servicos.limpar_limites` tem com o lance.
    """
    with _lock:
        _contagem.clear()
    limpar_freio()
