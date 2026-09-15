"""Contas da equipe do leilão — criar, dar função, entregar a senha.

O que esta tela resolve: no dia do evento aparecem voluntários para ajudar, e
até aqui a única forma de dar acesso a eles era o comando `leilao_papel`, no
terminal do servidor. O diretor precisa conseguir criar a conta **da mesa**, em
dez segundos, falando o usuário e a senha em voz alta para a pessoa ao lado.

Daí as três decisões deste arquivo:

- **Senha padrão `1234`, igual para todo mundo.** Ela não é um segredo: é um
  bilhete. Serve para a pessoa entrar uma vez.
- **Trocar a senha é obrigatório no primeiro acesso** (`ContaEquipe.senha_provisoria`).
  É isso que faz a senha padrão não ser um buraco: ela vale de uma entrada só, e
  a conta passa a ter uma senha que só a pessoa sabe.
- **A senha nova pode ser fraca.** Os validadores do Django ficam de fora de
  propósito (decisão do clube): é um voluntário digitando no celular, no meio de
  um evento, numa conta que abre telas de leilão. Exigir 8 caracteres com
  número e símbolo ali produziria senha anotada em papel — que é pior.

O `leilao_papel` continua existindo e **não** passa por aqui: ele sorteia uma
senha forte, então as contas dele nunca ficam com senha provisória.
"""

import re
import unicodedata

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import ContaEquipe
from .papeis import AREAS, DIRETOR

# O bilhete. Curta de propósito: é ditada em voz alta e digitada no celular.
SENHA_PADRAO = "1234"

# Mínimo da senha nova. Três caracteres é quase nada — e é o combinado: o que
# não pode é continuar com a senha que todo mundo da mesa ouviu.
TAMANHO_MINIMO_SENHA = 3

PAPEIS_VALIDOS = list(AREAS) + [DIRETOR]

ROTULOS = {
    "preparacao": "📦 Preparação — cadastra itens, monta a fila, configura",
    "locutor": "🎤 Locutor — conduz o pregão, abre item, bate o martelo",
    "caixa": "💰 Caixa — confere pagamento e cuida da entrega",
    DIRETOR: "👑 Diretor — enxerga tudo e cadastra a equipe",
}


def escolhas_de_papel():
    """As funções, na ordem em que a noite acontece."""
    return [(p, ROTULOS[p]) for p in PAPEIS_VALIDOS]


# ---------------------------------------------------------------------------
# Usuário de acesso
# ---------------------------------------------------------------------------
def _sem_acento(texto):
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c))


def limpar_usuario(bruto):
    """Deixa só o que serve como login: minúsculas, sem acento, sem espaço."""
    limpo = _sem_acento(bruto).lower()
    return re.sub(r"[^a-z0-9._-]", "", limpo)


def usuario_sugerido(nome, ocupado=None):
    """Um login a partir do nome da pessoa — **primeiro nome**, quando dá.

    É ditado em voz alta ("seu usuário é maria"), então o curto vale mais que o
    único. Repetiu, tenta `maria.silva`; repetiu de novo, entra o número.

    `ocupado` é injetável para o teste não precisar do banco.
    """
    if ocupado is None:
        User = get_user_model()

        def ja_existe(u):
            return User.objects.filter(username__iexact=u).exists()

        ocupado = ja_existe

    partes = [limpar_usuario(p) for p in (nome or "").split()]
    partes = [p for p in partes if p]
    if not partes:
        partes = ["equipe"]

    candidatos = [partes[0]]
    if len(partes) > 1:
        candidatos.append(f"{partes[0]}.{partes[-1]}")

    for candidato in candidatos:
        if not ocupado(candidato):
            return candidato

    base = candidatos[-1]
    n = 2
    while ocupado(f"{base}{n}"):
        n += 1
    return f"{base}{n}"


# ---------------------------------------------------------------------------
# Criar e manter a conta
# ---------------------------------------------------------------------------
def definir_papeis(user, escolhidos):
    """Deixa a pessoa **exatamente** com as funções escolhidas.

    Mexe só nos grupos do leilão: um grupo que exista por outro motivo (o admin
    do Django, por exemplo) não é removido por esta tela.
    """
    escolhidos = [p for p in (escolhidos or []) if p in PAPEIS_VALIDOS]
    for papel in PAPEIS_VALIDOS:
        grupo, _ = Group.objects.get_or_create(name=papel)
        if papel in escolhidos:
            user.groups.add(grupo)
        else:
            user.groups.remove(grupo)
    return escolhidos


def criar_conta(nome, papeis, *, usuario="", criado_por=None):
    """Cria a conta da pessoa com a senha padrão. Devolve o `User`.

    `is_staff` é o que separa a equipe de quem só dá lance — sem ele os papéis
    não valem nada (ver `papeis.papeis_do`).
    """
    User = get_user_model()
    nome = " ".join((nome or "").split())
    login = limpar_usuario(usuario) or usuario_sugerido(nome)

    user = User.objects.create(username=login, is_staff=True, is_active=True)
    user.set_password(SENHA_PADRAO)
    user.save()

    ContaEquipe.objects.create(
        usuario=user, nome=nome, senha_provisoria=True, criado_por=criado_por
    )
    definir_papeis(user, papeis)
    return user


def resetar_senha(user):
    """Volta para a senha padrão — e volta a exigir a troca.

    É o socorro de quem esqueceu a senha no meio do evento: o diretor devolve o
    bilhete, e a pessoa escolhe outra ao entrar.
    """
    user.set_password(SENHA_PADRAO)
    user.save(update_fields=["password"])
    ContaEquipe.objects.update_or_create(
        usuario=user, defaults={"senha_provisoria": True}
    )
    return SENHA_PADRAO


def definir_senha(user, senha):
    """A pessoa escolheu a senha dela. Encerra a senha provisória."""
    user.set_password(senha)
    user.save(update_fields=["password"])
    ContaEquipe.objects.update_or_create(
        usuario=user, defaults={"senha_provisoria": False}
    )


def precisa_trocar_senha(user):
    """Esta pessoa ainda está com o bilhete na mão?

    **Sem registro, não precisa.** Conta criada antes desta tela (ou pelo
    `leilao_papel`, que sorteia senha forte) nunca teve senha padrão — cobrar a
    troca dela seria inventar um problema.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    conta = ContaEquipe.objects.filter(usuario=user).first()
    return bool(conta and conta.senha_provisoria)


def equipe():
    """Todo mundo que tem conta de equipe, com o que a lista precisa mostrar."""
    User = get_user_model()
    return (
        User.objects.filter(is_staff=True)
        .select_related("conta_leilao")
        .prefetch_related("groups")
        .order_by("username")
    )


def nome_de(user):
    conta = getattr(user, "conta_leilao", None)
    return (conta.nome if conta and conta.nome else "") or user.get_username()


def recado_de_acesso(user, site_url=""):
    """O bilhete pronto para colar no WhatsApp da pessoa.

    Vem **pronto do servidor**, como manda a convenção do projeto — o botão só
    copia. **Sem o nome de ninguém mais e sem link de tela interna**: é o acesso
    de uma pessoa.
    """
    base = (site_url or "").rstrip("/")
    link = f"{base}/equipe/entrar/" if base else "(link da equipe do leilão)"
    return "\n".join(
        [
            "*Leilão do clube — seu acesso*",
            f"Link: {link}",
            f"Usuário: {user.get_username()}",
            f"Senha: {SENHA_PADRAO}",
            "",
            "No primeiro acesso o sistema pede para você trocar a senha.",
        ]
    )
