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
    path(
        "usuarios/aventureiro/<int:pk>/ativo/",
        views.aventureiro_toggle_ativo_view,
        name="aventureiro_toggle_ativo",
    ),
    path(
        "usuarios/conta/<int:conta_id>/principal/",
        views.usuario_principal_view,
        name="usuario_principal",
    ),
    path("eventos/", views.eventos_view, name="eventos"),
    path("eventos/novo/", views.evento_novo_view, name="evento_novo"),
    path("eventos/complexo/novo/", views.evento_complexo_novo_view, name="evento_complexo_novo"),
    path("eventos/<int:pk>/excluir/", views.evento_excluir_view, name="evento_excluir"),
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
    path("eventos/<int:pk>/dia/", views.evento_dia_view, name="evento_dia"),
    path("eventos/<int:pk>/dia/checkin/", views.evento_checkin_view, name="evento_checkin"),
    path("eventos/<int:pk>/dia/entrega/", views.evento_entrega_view, name="evento_entrega"),
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
    path("eventos/<int:pk>/descontos/novo/", views.evento_cupom_novo_view, name="evento_cupom_novo"),
    path(
        "eventos/<int:pk>/descontos/<int:cupom_id>/excluir/",
        views.evento_cupom_excluir_view,
        name="evento_cupom_excluir",
    ),
    path(
        "eventos/<int:pk>/cupom/validar/",
        views.evento_cupom_validar_view,
        name="evento_cupom_validar",
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
    path("whatsapp/", views.whatsapp_view, name="whatsapp"),
    path("whatsapp/config/", views.whatsapp_config_view, name="whatsapp_config"),
    path("whatsapp/enviar/", views.whatsapp_enviar_view, name="whatsapp_enviar"),
    path("presenca/", views.presenca_view, name="presenca"),
    path("presenca/<int:pk>/", views.presenca_evento_view, name="presenca_evento"),
    path("presenca/<int:pk>/marcar/", views.presenca_marcar_view, name="presenca_marcar"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path(
        "cadastro/novo-aventureiro/",
        views.cadastro_novo_aventureiro_view,
        name="cadastro_novo_aventureiro",
    ),
    path("cadastro/sucesso/", views.cadastro_sucesso_view, name="cadastro_sucesso"),
    path("trocar-senha/", views.trocar_senha_view, name="trocar_senha"),
    path("recuperar-senha/", views.recuperar_senha_view, name="recuperar_senha"),
    path(
        "recuperar-senha/codigo/",
        views.recuperar_senha_codigo_view,
        name="recuperar_senha_codigo",
    ),
    path(
        "recuperar-senha/reenviar/",
        views.recuperar_senha_reenviar_view,
        name="recuperar_senha_reenviar",
    ),
    path(
        "recuperar-senha/nova-senha/",
        views.recuperar_senha_nova_view,
        name="recuperar_senha_nova",
    ),
]
