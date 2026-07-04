from django.contrib import admin

from .models import (
    Aventureiro,
    AutorizacaoImagem,
    CustoEvento,
    Evento,
    FaixaEtariaPreco,
    FichaMedica,
)


@admin.register(Aventureiro)
class AventureiroAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "usuario", "resp_nome", "cidade", "criado_em")
    search_fields = ("nome_completo", "cpf", "usuario__username", "resp_nome")
    list_filter = ("sexo", "data_inscricao")


@admin.register(FichaMedica)
class FichaMedicaAdmin(admin.ModelAdmin):
    list_display = ("aventureiro", "tipo_sanguineo", "possui_plano_saude")
    search_fields = ("aventureiro__nome_completo",)


@admin.register(AutorizacaoImagem)
class AutorizacaoImagemAdmin(admin.ModelAdmin):
    list_display = ("aventureiro", "nome_menor", "resp_nome")
    search_fields = ("nome_menor", "resp_nome")


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "data", "horario_inicio", "local", "criado_por")
    search_fields = ("nome", "local")
    list_filter = ("tipo", "data")


@admin.register(CustoEvento)
class CustoEventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "evento", "valor", "criado_por", "criado_em")
    search_fields = ("nome", "evento__nome")
    list_filter = ("evento",)


@admin.register(FaixaEtariaPreco)
class FaixaEtariaPrecoAdmin(admin.ModelAdmin):
    list_display = ("evento", "rotulo", "idade_min", "idade_max", "valor", "ordem")
    search_fields = ("rotulo", "evento__nome")
    list_filter = ("evento",)
