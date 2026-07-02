from django.contrib import admin

from .models import Aventureiro, AutorizacaoImagem, FichaMedica


@admin.register(Aventureiro)
class AventureiroAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "usuario", "cidade", "data_inscricao")
    search_fields = ("nome_completo", "cpf", "usuario__username")
    list_filter = ("sexo", "data_inscricao")


@admin.register(FichaMedica)
class FichaMedicaAdmin(admin.ModelAdmin):
    list_display = ("aventureiro", "tipo_sanguineo", "possui_plano_saude")
    search_fields = ("aventureiro__nome_completo",)


@admin.register(AutorizacaoImagem)
class AutorizacaoImagemAdmin(admin.ModelAdmin):
    list_display = ("aventureiro", "nome_menor", "resp_nome")
    search_fields = ("nome_menor", "resp_nome")
