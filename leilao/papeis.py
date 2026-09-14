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
    return [
        {"chave": a, "rotulo": AREAS[a][0], "icone": AREAS[a][1], "rota": AREAS[a][2]}
        for a in ORDEM
        if a in meus
    ]


def exige(*areas):
    """Decorator: a view só abre para quem tem **alguma** das áreas.

    Sem papel nenhum, a pessoa volta para o hub da equipe com um aviso — nunca
    uma tela em branco nem um 403 seco no meio de um evento.
    """

    def decorador(view):
        @login_required
        @wraps(view)
        def _wrap(request, *args, **kwargs):
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
