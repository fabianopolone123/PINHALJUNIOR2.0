"""Context processors: disponibilizam dados de perfil em todos os templates."""

from django.db.models import Q
from django.utils import timezone

from .models import Evento
from .permissoes import eh_diretor


def _eventos_menu(user):
    """Eventos com inscrição ainda **não encerrados** (data futura ou em
    andamento), para aparecerem no menu de todos os perfis logados. Eventos
    passados somem sozinhos."""
    if not getattr(user, "is_authenticated", False):
        return []
    hoje = timezone.localdate()
    return list(
        Evento.objects.filter(tipo="inscricao")
        .filter(Q(data_fim__gte=hoje) | Q(data_fim__isnull=True, data__gte=hoje))
        .order_by("data", "horario_inicio")
    )


def perfis(request):
    """Adiciona `is_diretor` e `eventos_menu` ao contexto de todos os templates."""
    return {
        "is_diretor": eh_diretor(request.user),
        "eventos_menu": _eventos_menu(request.user),
    }
