from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.login_view, name="login"),
    path("inicio/", views.inicio_view, name="inicio"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path(
        "cadastro/novo-aventureiro/",
        views.cadastro_novo_aventureiro_view,
        name="cadastro_novo_aventureiro",
    ),
    path("cadastro/sucesso/", views.cadastro_sucesso_view, name="cadastro_sucesso"),
]
