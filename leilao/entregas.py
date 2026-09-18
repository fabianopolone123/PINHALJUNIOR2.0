"""Divisão das entregas entre os voluntários que vão rodar a cidade.

**O que este módulo NÃO faz: ele não consulta mapa nenhum.** O sistema guarda
rua, número, bairro e cidade — não guarda coordenada, e buscar uma seria
dependência externa nova (e uma chamada por endereço, na noite do evento).

O que ele faz é o que uma pessoa faria com o mapa aberto: **junta por bairro** e
divide os bairros entre os entregadores equilibrando a quantidade de paradas.
Bairro é o dado que o clube tem e é o recorte que as pessoas usam para falar de
região — "fica lá pro Centro", "isso é tudo no mesmo lado".

A honestidade sobre o limite é parte do recurso: a tela diz que a divisão é por
bairro, para ninguém supor uma otimização de rota que não existe. Dois bairros
vizinhos podem cair com entregadores diferentes; quem conhece a cidade ajusta em
dez segundos, e isso é melhor do que uma precisão inventada.
"""

import re
import unicodedata


def _chave_regiao(participante):
    """Bairro + cidade, normalizados, como identidade da região.

    Sem acento e sem caixa porque cada pessoa digita o bairro de um jeito
    ("Centro", "centro", "CENTRO", " Jardim  Exemplo ") e o mesmo bairro escrito
    de dois modos viraria duas regiões — o entregador faria a mesma rua duas
    vezes.

    **O que isto NÃO resolve: abreviação.** "Jd. Paulista" e "Jardim Paulista"
    continuam sendo duas regiões, porque adivinhar abreviação é adivinhar
    (e "Sto." pode ser Santo ou Santos). Quem arruma isso é o quadro de
    entregas, onde a equipe arrasta as duas para o mesmo entregador.
    """
    def limpar(texto):
        texto = (texto or "").strip().lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", texto)

    bairro = limpar(participante.bairro)
    cidade = limpar(participante.cidade)
    return (cidade, bairro)


def _rotulo_regiao(participante):
    """Como a região aparece na tela — com a grafia que a pessoa cadastrou."""
    bairro = (participante.bairro or "").strip()
    cidade = (participante.cidade or "").strip()
    if bairro and cidade:
        return f"{bairro} — {cidade}"
    return bairro or cidade or "Sem bairro informado"


def _uniformizar_rotulos(paradas):
    """UM rótulo por região, para todas as paradas dela.

    O rótulo é a grafia de quem cadastrou, e o mesmo bairro chega escrito de
    vários jeitos ("Centro", "centro", "CENTRO"). Agrupar por chave normalizada
    resolve a **divisão**, mas cada parada continuava carregando a sua grafia —
    e a rota impressa abria um cabeçalho de região por variação, como se fossem
    três bairros diferentes. Quem entrega lê isso como três regiões.

    Vence a grafia **mais usada**. No empate, a que está escrita como nome
    próprio — "Centro" ganha de "centro" e de "CENTRO", que numa lista impressa
    parecem descuido ou grito. Só depois disso desempata pelo texto, para a
    escolha nunca depender da ordem em que as paradas chegaram.
    """
    def preferencia(par):
        rotulo, quantas = par
        # Palavra inteira em maiúscula é grito numa lista impressa. Conta por
        # PALAVRA porque o rótulo junta bairro e cidade, e o descuido costuma
        # estar só em um dos dois ("CENTRO — Rio Negrinho").
        gritos = sum(1 for w in rotulo.split() if len(w) > 1 and w.isupper())
        return (-quantas, gritos, rotulo)

    contagem = {}
    for parada in paradas:
        chave = parada["regiao"]
        contagem.setdefault(chave, {})
        contagem[chave][parada["rotulo"]] = contagem[chave].get(parada["rotulo"], 0) + 1
    escolhido = {
        chave: min(rotulos.items(), key=preferencia)[0]
        for chave, rotulos in contagem.items()
    }
    for parada in paradas:
        parada["rotulo"] = escolhido[parada["regiao"]]
    return paradas


def paradas_de(pendentes):
    """Uma parada por PESSOA, com os itens dela juntos.

    É a unidade de todo o módulo: dois itens da mesma casa são **uma visita**, e
    contá-los como duas faria um entregador parecer sobrecarregado sem estar.
    Serve tanto para a divisão automática quanto para o quadro manual.
    """
    paradas_por_pessoa = {}
    for a in pendentes:
        p = a.participante
        if p.id not in paradas_por_pessoa:
            paradas_por_pessoa[p.id] = {
                "pessoa": p,
                "itens": [],
                "regiao": _chave_regiao(p),
                "rotulo": _rotulo_regiao(p),
            }
        paradas_por_pessoa[p.id]["itens"].append(a)
    return _uniformizar_rotulos(list(paradas_por_pessoa.values()))


def ordenar_paradas(paradas):
    """Região primeiro, rua depois: é como quem entrega lê a lista."""
    return sorted(paradas, key=lambda x: (x["rotulo"].lower(),
                                          (x["pessoa"].logradouro or "").lower(),
                                          (x["pessoa"].nome or "").lower()))


def dividir(pendentes, quantos):
    """Divide os arremates a entregar entre `quantos` entregadores.

    Devolve uma lista de listas de "paradas": cada parada é uma PESSOA com os
    itens dela juntos. A unidade da divisão é a pessoa, não o item — dois itens
    da mesma casa são uma visita só, e contá-los como duas paradas faria um
    entregador parecer sobrecarregado sem estar.

    A divisão é gulosa: a região com mais paradas vai para quem está mais leve.
    É o LPT clássico, que é simples de conferir a olho (a equipe precisa
    confiar no resultado numa mesa de evento) e fica perto do equilíbrio ideal.
    **Região nunca é partida**: dividir um bairro entre dois entregadores é
    exatamente o que a divisão existe para evitar.
    """
    quantos = max(1, int(quantos or 1))

    # 1. Uma parada por PESSOA, com os itens dela juntos.
    # 2. Paradas agrupadas por região.
    regioes = {}
    for parada in paradas_de(pendentes):
        regioes.setdefault(parada["regiao"], []).append(parada)

    # Dentro da região, ordena por rua: quem entrega anda por rua, não por nome.
    for paradas in regioes.values():
        paradas.sort(key=lambda x: ((x["pessoa"].logradouro or "").lower(),
                                    (x["pessoa"].nome or "").lower()))

    # 3. Regiões maiores primeiro — é o que faz a divisão gulosa ficar boa.
    ordenadas = sorted(
        regioes.values(), key=lambda paradas: (-len(paradas), paradas[0]["rotulo"])
    )

    rotas = [[] for _ in range(quantos)]
    for paradas in ordenadas:
        # Vai para quem está mais leve; empate desempata pelo índice, para a
        # divisão ser sempre a mesma nas mesmas entradas (a equipe reabre a tela
        # e precisa ver o mesmo resultado).
        i = min(range(quantos), key=lambda k: (len(rotas[k]), k))
        rotas[i].extend(paradas)

    return rotas


def texto_da_rota(leilao, numero, paradas, total_rotas, nome=""):
    """A rota de UM entregador, pronta para copiar e mandar para ele.

    Vem pronta do servidor (convenção do projeto: o JS só copia). Leva nome,
    telefone e endereço — é documento de trabalho de quem entrega, não texto
    para grupo aberto.

    Com `nome`, o cabeçalho chama o voluntário pelo nome: a mensagem vai para
    ele no particular, e "ENTREGAS 2/4" não diz a quem ela pertence quando a
    pessoa reabre a conversa dois dias depois.
    """
    itens = sum(len(p["itens"]) for p in paradas)
    quem = (nome or "").strip()
    cabecalho = f"*ENTREGAS {numero}/{total_rotas} — {leilao.nome}*"
    if quem:
        cabecalho = f"*ENTREGAS DE {quem.upper()} — {leilao.nome}*"
    linhas = [
        cabecalho,
        f"{len(paradas)} parada(s) · {itens} item(ns)",
        "",
    ]

    regiao_atual = None
    for i, parada in enumerate(paradas, start=1):
        if parada["rotulo"] != regiao_atual:
            regiao_atual = parada["rotulo"]
            linhas.append(f"— {regiao_atual} —")
        p = parada["pessoa"]
        linhas.append(f"*{i}. {p.nome}*")
        linhas.append(f"📱 {p.whatsapp}")
        endereco = p.endereco_uma_linha
        if endereco:
            linhas.append(f"📍 {endereco}")
        for a in parada["itens"]:
            # O número na frente: quem separa as caixas procura a etiqueta.
            linhas.append(f"   • nº {a.lote.numero} — {a.lote.nome}")
        linhas.append("")

    return "\n".join(linhas).strip()


def quadro(pendentes, atribuicoes, quantos):
    """As colunas do quadro manual: `{0: [a distribuir], 1: [...], ...}`.

    `atribuicoes` é `{participante_id: numero_do_entregador}` — o que a equipe
    já arrastou. Quem não está lá (pagou depois de o quadro ser montado) cai na
    coluna **0**, "a distribuir": entrar sozinho na rota de alguém seria pior,
    porque ninguém repara no que aparece já resolvido.

    Coluna que não existe mais (a equipe diminuiu o número de entregadores)
    também volta para a 0 — a atribuição no banco é preservada, mas a tela nunca
    mostra uma parada num entregador que não está lá.
    """
    quantos = max(0, int(quantos or 0))
    colunas = {i: [] for i in range(quantos + 1)}
    for parada in paradas_de(pendentes):
        numero = atribuicoes.get(parada["pessoa"].id, 0)
        if numero not in colunas:
            numero = 0
        colunas[numero].append(parada)
    for numero in colunas:
        colunas[numero] = ordenar_paradas(colunas[numero])
    return colunas
