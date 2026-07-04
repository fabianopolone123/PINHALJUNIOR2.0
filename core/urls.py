from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("sair/", views.sair_view, name="sair"),
    path("inicio/", views.inicio_view, name="inicio"),
    path(
        "meus-dados/responsavel/editar/",
        views.editar_responsavel_view,
        name="editar_responsavel",
    ),
    path("usuarios/", views.usuarios_view, name="usuarios"),
    path("eventos/", views.eventos_view, name="eventos"),
    path("eventos/novo/", views.evento_novo_view, name="evento_novo"),
    path("eventos/complexo/novo/", views.evento_complexo_novo_view, name="evento_complexo_novo"),
    path("eventos/<int:pk>/", views.evento_painel_view, name="evento_painel"),
    path("eventos/<int:pk>/pagina/", views.evento_pagina_view, name="evento_pagina"),
    path("eventos/<int:pk>/inscrever/", views.evento_inscrever_view, name="evento_inscrever"),
    path(
        "eventos/<int:pk>/inscrever/sucesso/",
        views.evento_inscricao_sucesso_view,
        name="evento_inscricao_sucesso",
    ),
    path(
        "eventos/<int:pk>/inscricoes/<int:inscricao_id>/cancelar/",
        views.evento_inscricao_cancelar_view,
        name="evento_inscricao_cancelar",
    ),
    path(
        "eventos/<int:pk>/produtos/novo/",
        views.evento_produto_novo_view,
        name="evento_produto_novo",
    ),
    path(
        "eventos/<int:pk>/produtos/<int:produto_id>/editar/",
        views.evento_produto_editar_view,
        name="evento_produto_editar",
    ),
    path(
        "eventos/<int:pk>/produtos/<int:produto_id>/excluir/",
        views.evento_produto_excluir_view,
        name="evento_produto_excluir",
    ),
    path("eventos/<int:pk>/loja/", views.evento_loja_view, name="evento_loja"),
    path("eventos/<int:pk>/loja/pagamento/", views.evento_pagamento_view, name="evento_pagamento"),
    path("eventos/<int:pk>/pdv/", views.evento_pdv_view, name="evento_pdv"),
    path("eventos/<int:pk>/pdv/inscricao/", views.evento_pdv_inscricao_view, name="evento_pdv_inscricao"),
    path("eventos/<int:pk>/operar/", views.evento_operar_view, name="evento_operar"),
    path("eventos/<int:pk>/operadores/", views.evento_operadores_view, name="evento_operadores"),
    path("eventos/<int:pk>/operadores/diretoria/", views.evento_operador_add_diretoria_view, name="evento_operador_add_diretoria"),
    path("eventos/<int:pk>/operadores/externo/", views.evento_operador_add_externo_view, name="evento_operador_add_externo"),
    path("eventos/<int:pk>/operadores/<int:operador_id>/reset/", views.evento_operador_reset_view, name="evento_operador_reset"),
    path("eventos/<int:pk>/operadores/<int:operador_id>/remover/", views.evento_operador_remover_view, name="evento_operador_remover"),
    path(
        "eventos/<int:pk>/loja/sucesso/",
        views.evento_pedido_sucesso_view,
        name="evento_pedido_sucesso",
    ),
    path(
        "eventos/<int:pk>/pedidos/<int:pedido_id>/cancelar/",
        views.evento_pedido_cancelar_view,
        name="evento_pedido_cancelar",
    ),
    path("eventos/<int:pk>/custos/novo/", views.evento_custo_novo_view, name="evento_custo_novo"),
    path(
        "eventos/<int:pk>/custos/<int:custo_id>/excluir/",
        views.evento_custo_excluir_view,
        name="evento_custo_excluir",
    ),
    path(
        "eventos/<int:pk>/inscricoes/config/",
        views.evento_inscricao_config_view,
        name="evento_inscricao_config",
    ),
    path(
        "eventos/<int:pk>/inscricoes/faixa/novo/",
        views.evento_faixa_nova_view,
        name="evento_faixa_nova",
    ),
    path(
        "eventos/<int:pk>/inscricoes/faixa/<int:faixa_id>/excluir/",
        views.evento_faixa_excluir_view,
        name="evento_faixa_excluir",
    ),
    path(
        "eventos/<int:pk>/inscricoes/campo/novo/",
        views.evento_campo_novo_view,
        name="evento_campo_novo",
    ),
    path(
        "eventos/<int:pk>/inscricoes/campo/<int:campo_id>/excluir/",
        views.evento_campo_excluir_view,
        name="evento_campo_excluir",
    ),
    path(
        "eventos/<int:pk>/inscricoes/campo/<int:campo_id>/mover/",
        views.evento_campo_mover_view,
        name="evento_campo_mover",
    ),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path(
        "cadastro/novo-aventureiro/",
        views.cadastro_novo_aventureiro_view,
        name="cadastro_novo_aventureiro",
    ),
    path("cadastro/sucesso/", views.cadastro_sucesso_view, name="cadastro_sucesso"),
    path("trocar-senha/", views.trocar_senha_view, name="trocar_senha"),
]
