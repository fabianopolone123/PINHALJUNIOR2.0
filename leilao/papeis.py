"""Papéis da equipe do leilão — quem enxerga o quê.

Três funções diferentes numa noite de leilão, e raramente a mesma pessoa:

- **Preparação** — cadastra os itens, monta a fila, configura o leilão. Trabalho
  de antes, com calma.
- **Locutor** — conduz o pregão: abre lote, bate o martelo, fala ao microfone.
  Durante o evento, com as duas mãos ocupadas.
- **Caixa** — confere quem pagou e cuida da entrega. Mexe em dinheiro.

O **Diretor** enxerga as três áreas e é quem distribui os papéis.

Decisões que este arquivo aplica:

- **Papéis acumulam.** No evento pequeno o mesmo voluntário faz duas coisas, e
  fazer a pessoa trocar de login no meio do pregão seria pior do que não ter
  separação nenhuma.
- **O locutor não mexe em dinheiro.** Dar baixa de pagamento é do Caixa (e do
  Diretor): quem bate o martelo não é quem confirma o recebimento, e o locutor
  já tem trabalho suficiente falando e olhando o cronômetro.

A implementação são **grupos nativos do Django**, no banco do leilão — mesmo
conceito dos perfis do sistema do clube, sem model novo.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

# Nome do grupo → (rótulo, ícone, rota inicial daquela área)
AREAS = {
    "preparacao": ("Preparação", "📦", "leilao:preparacao"),
    "locutor": ("Locutor", "🎤", "leilao:locutor"),
    "caixa": ("Caixa", "💰", "leilao:caixa"),
}

DIRETOR = "diretor"

# A tela de Usuários é do **diretor**, e por isso não entra em `AREAS`: ela não
# é um papel que se distribua (ninguém é "o usuário de usuários"), é o que o
# diretor faz por ser diretor. Fica aqui para aparecer na barra e no hub pelo
# mesmo caminho das áreas — o template itera o menu, nunca chumba `{% if %}`.
ITEM_USUARIOS = {
    "chave": "usuarios",
    "rotulo": "Usuários",
    "icone": "👤",
    "rota": "leilao:usuarios",
}

# Ordem em que as áreas aparecem no menu e em que se escolhe a tela inicial de
# quem tem mais de um papel: quem prepara chega antes; quem conduz, durante.
ORDEM = ["preparacao", "locutor", "caixa"]


def papeis_do(user):
    """Conjunto de áreas que a pessoa pode abrir.

    `is_superuser` e o grupo **diretor** abrem tudo — é quem distribui os papéis
    e quem socorre quando falta alguém no dia.
    """
    if not user.is_authenticated or not user.is_staff:
        return set()
    if user.is_superuser or user.groups.filter(name=DIRETOR).exists():
        return set(AREAS) | {DIRETOR}

    nomes = set(user.groups.values_list("name", flat=True))
    return {a for a in AREAS if a in nomes}


def eh_diretor(user):
    return DIRETOR in papeis_do(user)


def pode(user, area):
    return area in papeis_do(user)


def area_inicial(user):
    """Para onde mandar a pessoa depois do login."""
    meus = papeis_do(user)
    for a in ORDEM:
        if a in meus:
            return AREAS[a][2]
    return None


def menu_do(user):
    """Itens de menu da pessoa — só as áreas que ela realmente abre."""
    meus = papeis_do(user)
    itens = [
        {"chave": a, "rotulo": AREAS[a][0], "icone": AREAS[a][1], "rota": AREAS[a][2]}
        for a in ORDEM
        if a in meus
    ]
    # Usuários vem por último: é trabalho de antes e de socorro, não do pregão.
    if DIRETOR in meus:
        itens.append(dict(ITEM_USUARIOS))
    return itens


def senha_pendente(user):
    """A pessoa ainda está com a senha que o diretor entregou?

    Import tardio de propósito: `equipe.py` importa daqui (papéis válidos), e
    importar de volta no topo fecharia o ciclo.
    """
    from .equipe import precisa_trocar_senha

    return precisa_trocar_senha(user)


def exige(*areas):
    """Decorator: a view só abre para quem tem **alguma** das áreas.

    Sem papel nenhum, a pessoa volta para o hub da equipe com um aviso — nunca
    uma tela em branco nem um 403 seco no meio de um evento.
    """

    def decorador(view):
        @login_required
        @wraps(view)
        def _wrap(request, *args, **kwargs):
            # A senha padrão vale para UMA entrada. Enquanto ela não for
            # trocada, a única tela que abre é a da troca — senão a conta
            # continuaria funcionando com a senha que a mesa inteira ouviu.
            if senha_pendente(request.user):
                return redirect("leilao:trocar_senha")
            meus = papeis_do(request.user)
            if not meus:
                messages.error(request, "Sua conta ainda não tem papel no leilão.")
                return redirect("leilao:entrar_equipe")
            if not meus.intersection(areas):
                rotulos = " ou ".join(AREAS[a][0] for a in areas if a in AREAS)
                messages.error(request, f"Esta área é de {rotulos}.")
                return redirect("leilao:equipe")
            return view(request, *args, **kwargs)

        return _wrap

    return decorador


def exige_diretor(view):
    """Decorator das telas que só o **diretor** abre (hoje: Usuários).

    Separado do `exige(...)` porque `diretor` não é uma das `AREAS`: é quem
    distribui as áreas. A guarda da senha provisória vale aqui também.
    """

    @login_required
    @wraps(view)
    def _wrap(request, *args, **kwargs):
        if senha_pendente(request.user):
            return redirect("leilao:trocar_senha")
        if not eh_diretor(request.user):
            messages.error(request, "Esta tela é só do diretor.")
            return redirect("leilao:equipe")
        return view(request, *args, **kwargs)

    return _wrap
