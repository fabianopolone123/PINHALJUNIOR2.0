from django.contrib import admin

from .models import (
    Aventureiro,
    AutorizacaoImagem,
    CampoInscricao,
    CompraLoja,
    CupomDesconto,
    CustoEvento,
    Evento,
    FaixaEtariaPreco,
    FichaMedica,
    GrupoLoja,
    Inscricao,
    ItemCompraLoja,
    ItemPedidoLoja,
    OperadorEvento,
    ParticipanteInscricao,
    PedidoLoja,
    PerfilUsuario,
    ProdutoEvento,
    ProdutoLoja,
    RespostaInscricao,
    VariacaoLoja,
    VariacaoProduto,
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


@admin.register(CupomDesconto)
class CupomDescontoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "evento", "percentual", "usado", "usado_por", "valor_desconto", "criado_em")
    search_fields = ("codigo", "evento__nome", "usado_por")
    list_filter = ("evento",)


@admin.register(CampoInscricao)
class CampoInscricaoAdmin(admin.ModelAdmin):
    list_display = ("evento", "rotulo", "tipo", "obrigatorio", "ordem")
    search_fields = ("rotulo", "evento__nome")
    list_filter = ("evento", "tipo")


class ParticipanteInscricaoInline(admin.TabularInline):
    model = ParticipanteInscricao
    extra = 0


class RespostaInscricaoInline(admin.TabularInline):
    model = RespostaInscricao
    extra = 0


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "evento", "responsavel_nome", "origem", "forma_pagamento", "status", "valor_total", "criado_em")
    search_fields = ("codigo", "responsavel_nome", "evento__nome")
    list_filter = ("evento", "status", "origem")
    inlines = [ParticipanteInscricaoInline, RespostaInscricaoInline]


class VariacaoProdutoInline(admin.TabularInline):
    model = VariacaoProduto
    extra = 1


@admin.register(ProdutoEvento)
class ProdutoEventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "evento", "controla_estoque", "ativo", "ordem")
    search_fields = ("nome", "evento__nome")
    list_filter = ("evento", "ativo")
    inlines = [VariacaoProdutoInline]


@admin.register(OperadorEvento)
class OperadorEventoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "evento", "externo", "criado_em")
    search_fields = ("usuario__username", "evento__nome")
    list_filter = ("evento", "externo")


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "precisa_trocar_senha")
    search_fields = ("usuario__username",)


class ItemPedidoLojaInline(admin.TabularInline):
    model = ItemPedidoLoja
    extra = 0


@admin.register(PedidoLoja)
class PedidoLojaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "evento", "comprador_nome", "origem", "forma_pagamento", "status", "valor_total", "criado_em")
    search_fields = ("codigo", "comprador_nome", "evento__nome")
    list_filter = ("evento", "status", "origem", "forma_pagamento")
    inlines = [ItemPedidoLojaInline]


# --- Loja do Clube (loja oficial) ---
class VariacaoLojaInline(admin.TabularInline):
    model = VariacaoLoja
    extra = 1


@admin.register(GrupoLoja)
class GrupoLojaAdmin(admin.ModelAdmin):
    list_display = ("nome", "produto", "modo", "obrigatorio", "ordem")
    search_fields = ("nome", "produto__nome")
    list_filter = ("modo", "obrigatorio")
    inlines = [VariacaoLojaInline]


class GrupoLojaInline(admin.TabularInline):
    model = GrupoLoja
    extra = 1


@admin.register(ProdutoLoja)
class ProdutoLojaAdmin(admin.ModelAdmin):
    list_display = ("nome", "composto", "controla_estoque", "ativo", "ordem")
    search_fields = ("nome",)
    list_filter = ("composto", "ativo")
    inlines = [GrupoLojaInline]


class ItemCompraLojaInline(admin.TabularInline):
    model = ItemCompraLoja
    extra = 0


@admin.register(CompraLoja)
class CompraLojaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "comprador_nome", "forma_pagamento", "status", "valor_total", "criado_em")
    search_fields = ("codigo", "comprador_nome")
    list_filter = ("status", "forma_pagamento")
    inlines = [ItemCompraLojaInline]
