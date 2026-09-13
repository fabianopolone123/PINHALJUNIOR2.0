"""Quem é o participante deste navegador.

Sem senha, de propósito: pedir cadastro com senha na porta de um leilão de uma
noite espanta gente. A pessoa preenche o formulário de entrada uma vez e passa a
ser reconhecida pelo **token guardado na sessão**.

O token também fica no model (`Participante.token`), então a sessão guarda só o
token — nunca o id cru. Trocar o cookie na mão não vira "ser outra pessoa": o
token tem 43 caracteres aleatórios.
"""

CHAVE_SESSAO = "leilao_participante"


def participante_atual(request):
    """O `Participante` desta sessão, ou `None`. Cacheia por requisição."""
    if not hasattr(request, "_leilao_participante"):
        from .models import Participante

        token = request.session.get(CHAVE_SESSAO) or ""
        participante = None
        if token:
            participante = Participante.objects.filter(token=token).first()
            if participante is None:
                # Token órfão (banco recriado, participante removido): limpa em
                # vez de deixar a pessoa num limbo em que nada funciona.
                request.session.pop(CHAVE_SESSAO, None)
        request._leilao_participante = participante
    return request._leilao_participante


def entrar(request, participante):
    request.session[CHAVE_SESSAO] = participante.token
    request.session.set_expiry(60 * 60 * 24 * 30)
    request._leilao_participante = participante


def sair(request):
    request.session.pop(CHAVE_SESSAO, None)
    request._leilao_participante = None
