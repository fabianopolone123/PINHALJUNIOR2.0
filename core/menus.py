"""
Registro central dos itens de menu e do acesso por perfil.

Fonte ÚNICA da verdade de "quem vê / acessa o quê". Hoje o acesso é decidido só
pelo `ACESSO_PADRAO` (por perfil). Quando existir o **módulo de permissões**
(ligar/desligar botões por perfil/usuário), basta consultar as regras do banco
ANTES do padrão dentro de `_ids_liberados` — o menu (`_menu.html`) e as views
NÃO mudam. Esse é o "encaixe" que evita reescrever tudo depois.

Uso:
- `itens_menu_para(user)` → itens visíveis no menu (na ordem de `ITENS_MENU`).
- `pode_acessar(user, "loja")` → guarda de view (True/False).
- `perfil_do_usuario(user)` → "Diretor" | "Responsável" | None (anônimo).
"""

from .permissoes import eh_diretor

PERFIL_DIRETOR = "Diretor"
PERFIL_RESPONSAVEL = "Responsável"
PERFIL_PROFESSOR = "Professor"
PERFIL_TESOUREIRO = "Tesoureiro"
PERFIL_SECRETARIO = "Secretário"

# Ordem de exibição dos perfis (no seletor do menu).
ORDEM_PERFIS = [
    PERFIL_DIRETOR, PERFIL_RESPONSAVEL, PERFIL_PROFESSOR,
    PERFIL_TESOUREIRO, PERFIL_SECRETARIO,
]
# Ícone de cada perfil (para o seletor).
ICONE_PERFIL = {
    PERFIL_DIRETOR: "🧭", PERFIL_RESPONSAVEL: "👨‍👩‍👧", PERFIL_PROFESSOR: "🎓",
    PERFIL_TESOUREIRO: "💵", PERFIL_SECRETARIO: "🗂️",
}

# Cada item: `id` estável, `rotulo`, `icone`, `url` (name completo) e `ativas`
# (url_names que deixam o item "ativo" no menu).
ITENS_MENU = [
    {"id": "inicio", "rotulo": "Meus Dados", "icone": "👤",
     "url": "core:inicio", "ativas": ["inicio", "editar_responsavel"]},
    {"id": "usuarios", "rotulo": "Usuários", "icone": "👥",
     "url": "core:usuarios", "ativas": ["usuarios"]},
    {"id": "eventos", "rotulo": "Eventos", "icone": "📅",
     "url": "core:eventos", "ativas": [
         "eventos", "evento_novo", "evento_complexo_novo", "evento_painel",
         "evento_produto_novo", "evento_produto_editar", "evento_pdv",
         "evento_pdv_inscricao", "evento_operadores", "evento_dia"]},
    {"id": "loja", "rotulo": "Loja", "icone": "🛍️",
     "url": "core:loja", "ativas": [
         "loja", "loja_produto", "loja_produto_novo", "loja_produto_editar",
         "loja_pagamento", "loja_sucesso"]},
    {"id": "mensalidades", "rotulo": "Mensalidades", "icone": "💰",
     "url": "core:mensalidades", "ativas": ["mensalidades"]},
    {"id": "financeiro", "rotulo": "Financeiro", "icone": "📈",
     "url": "core:financeiro", "ativas": ["financeiro"]},
    {"id": "presenca", "rotulo": "Presença", "icone": "✅",
     "url": "core:presenca", "ativas": ["presenca", "presenca_evento"]},
    {"id": "whatsapp", "rotulo": "WhatsApp", "icone": "💬",
     "url": "core:whatsapp", "ativas": ["whatsapp"]},
    {"id": "mercadopago", "rotulo": "Mercado Pago", "icone": "💳",
     "url": "core:mercadopago", "ativas": ["mercadopago"]},
]

# Acesso PADRÃO por perfil (lista de ids de `ITENS_MENU`). É o "perfil tal tem
# acesso a tal" — sobreponível no futuro pelo módulo de permissões.
ACESSO_PADRAO = {
    PERFIL_DIRETOR: [i["id"] for i in ITENS_MENU],           # Diretor vê tudo
    PERFIL_RESPONSAVEL: ["inicio", "mensalidades", "loja", "presenca"],
    # Perfis ainda sem telas próprias: por ora só "Meus Dados" (serão liberados
    # à medida que forem construídos — ver o encaixe em `_ids_liberados`).
    PERFIL_PROFESSOR: ["inicio"],
    PERFIL_TESOUREIRO: ["inicio"],
    PERFIL_SECRETARIO: ["inicio"],
}


# Chave de sessão do perfil ATIVO (seletor de perfil no menu). Vazio/ausente =
# perfil padrão do usuário.
PERFIL_ATIVO_KEY = "perfil_ativo"


def perfil_do_usuario(user):
    """Perfil PADRÃO (real) do usuário. Diretor pelo grupo nativo; qualquer outro
    membro logado é tratado como Responsável. Anônimo → None."""
    if not getattr(user, "is_authenticated", False):
        return None
    if eh_diretor(user):
        return PERFIL_DIRETOR
    return PERFIL_RESPONSAVEL


def perfis_do_usuario(user):
    """Perfis que o usuário PODE assumir (grupos nativos ∩ perfis conhecidos), na
    ordem de `ORDEM_PERFIS`. Sem grupo → só o perfil padrão."""
    if not getattr(user, "is_authenticated", False):
        return []
    nomes = set(user.groups.values_list("name", flat=True))
    perfis = [p for p in ORDEM_PERFIS if p in nomes]
    return perfis or [perfil_do_usuario(user)]


def perfil_efetivo(request):
    """Perfil em uso: o do seletor (sessão) se o usuário pode assumi-lo; senão, o
    perfil padrão. É o que decide o menu e a ramificação das telas."""
    padrao = perfil_do_usuario(request.user)
    escolhido = request.session.get(PERFIL_ATIVO_KEY)
    if escolhido and escolhido in perfis_do_usuario(request.user):
        return escolhido
    return padrao


def pode_trocar_perfil(user):
    """True se o usuário tem mais de um perfil (mostra o seletor no menu)."""
    return len(perfis_do_usuario(user)) > 1


def atua_como_responsavel(request):
    """True se a tela deve se comportar como Responsável (perfil efetivo)."""
    return perfil_efetivo(request) == PERFIL_RESPONSAVEL


def itens_menu_do_perfil(perfil):
    """Itens de menu de um perfil (nome), na ordem de `ITENS_MENU`."""
    liberados = set(ACESSO_PADRAO.get(perfil, []))
    return [i for i in ITENS_MENU if i["id"] in liberados]


def _ids_liberados(user):
    """Ids de itens que o usuário pode ver/acessar.

    HOJE: só o `ACESSO_PADRAO` do perfil.
    FUTURO (módulo de permissões): consultar aqui os overrides do banco ANTES de
    cair no padrão. Nada mais no sistema precisa mudar.
    """
    perfil = perfil_do_usuario(user)
    if perfil is None:
        return []
    return ACESSO_PADRAO.get(perfil, [])


def itens_menu_para(user):
    """Itens de menu visíveis para o usuário (perfil real), na ordem de
    `ITENS_MENU`. O menu que respeita o modo preview usa `perfil_efetivo` +
    `itens_menu_do_perfil` (ver context processor)."""
    liberados = set(_ids_liberados(user))
    return [i for i in ITENS_MENU if i["id"] in liberados]


def pode_acessar(user, item_id):
    """True se o usuário pode acessar a tela do item (guarda de view)."""
    return item_id in _ids_liberados(user)
