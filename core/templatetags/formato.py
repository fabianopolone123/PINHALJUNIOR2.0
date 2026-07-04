"""Filtros de formatação para os templates."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def moeda(value):
    """Formata um número no padrão de moeda brasileira, sem o "R$".

    Ex.: 1500 -> "1.500,00"; 1234.5 -> "1.234,50"; -1500 -> "-1.500,00".
    """
    try:
        valor = Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return value
    # Formata no padrão en (1,500.00) e troca os separadores para o pt-BR.
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto
