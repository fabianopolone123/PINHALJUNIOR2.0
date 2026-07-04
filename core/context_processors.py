"""Context processors: disponibilizam dados de perfil em todos os templates."""

from django.db.models import Q
from django.utils import timezone

from .models import Evento, OperadorEvento
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
    """Adiciona ao contexto de todos os templates: `is_diretor`, `eventos_menu`,
    e as informações de operador (`operador_eventos`, `eh_operador_externo`)."""
    user = request.user
    contexto = {
        "is_diretor": eh_diretor(user),
        "eventos_menu": _eventos_menu(user),
        "operador_eventos": [],
        "eh_operador_externo": False,
    }
    if getattr(user, "is_authenticated", False):
        contexto["operador_eventos"] = list(
            Evento.objects.filter(operadores__usuario=user).distinct().order_by("data")
        )
        if not contexto["is_diretor"]:
            contexto["eh_operador_externo"] = OperadorEvento.objects.filter(
                usuario=user, externo=True
            ).exists()
    return contexto
