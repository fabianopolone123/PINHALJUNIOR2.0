"""Context processors: disponibilizam dados de perfil em todos os templates."""

from .permissoes import eh_diretor


def perfis(request):
    """Adiciona `is_diretor` ao contexto (para exibir/ocultar itens por perfil)."""
    return {"is_diretor": eh_diretor(request.user)}
