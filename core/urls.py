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
    path("eventos/<int:pk>/custos/novo/", views.evento_custo_novo_view, name="evento_custo_novo"),
    path(
        "eventos/<int:pk>/custos/<int:custo_id>/excluir/",
        views.evento_custo_excluir_view,
        name="evento_custo_excluir",
    ),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path(
        "cadastro/novo-aventureiro/",
        views.cadastro_novo_aventureiro_view,
        name="cadastro_novo_aventureiro",
    ),
    path("cadastro/sucesso/", views.cadastro_sucesso_view, name="cadastro_sucesso"),
]
