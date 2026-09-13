"""Admin do leilão — leitura e socorro.

A operação de verdade é na mesa do locutor. O admin fica para conferência e
para o caso de precisar corrigir algo na unha durante o evento.
"""

from django.contrib import admin

from .models import (
    Arremate,
    ConfigLeilao,
    Lance,
    Leilao,
    Lote,
    MensagemChat,
    PagamentoLeilao,
    Participante,
)


@admin.register(Leilao)
class LeilaoAdmin(admin.ModelAdmin):
    list_display = ("nome", "status", "criado_em")
    list_filter = ("status",)
    search_fields = ("nome",)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ("ordem", "nome", "leilao", "status", "valor_atual", "lider", "voltas")
    list_filter = ("leilao", "status")
    search_fields = ("nome",)


@admin.register(Participante)
class ParticipanteAdmin(admin.ModelAdmin):
    list_display = ("nome", "whatsapp", "cidade", "bloqueado", "criado_em")
    list_filter = ("bloqueado",)
    search_fields = ("nome", "whatsapp")


@admin.register(Lance)
class LanceAdmin(admin.ModelAdmin):
    list_display = ("lote", "participante", "valor", "origem", "cancelado", "criado_em")
    list_filter = ("cancelado", "origem")


@admin.register(Arremate)
class ArremateAdmin(admin.ModelAdmin):
    list_display = ("lote", "participante", "valor", "status", "criado_em", "expira_em")
    list_filter = ("status",)


@admin.register(PagamentoLeilao)
class PagamentoLeilaoAdmin(admin.ModelAdmin):
    list_display = ("referencia", "status", "valor_bruto", "taxa", "criado_em")
    list_filter = ("status",)
    search_fields = ("referencia", "mp_payment_id")
    readonly_fields = ("payload",)


@admin.register(MensagemChat)
class MensagemChatAdmin(admin.ModelAdmin):
    list_display = ("leilao", "autor", "texto", "removida", "criado_em")
    list_filter = ("removida",)


@admin.register(ConfigLeilao)
class ConfigLeilaoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "modo", "audio_ativo", "atualizado_em")
