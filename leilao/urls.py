"""Rotas do leilão.

Público (sem login): a porta, a tela do pregão, o stream e as ações do
participante. Restrito ao `is_staff`: tudo em `locutor/`.
"""

from django.urls import path

from . import views

app_name = "leilao"

urlpatterns = [
    # --- Participante ---
    path("", views.leilao_view, name="leilao"),
    path("entrar/", views.entrar_view, name="entrar"),
    path("sair/", views.sair_view, name="sair"),
    path("stream/", views.stream_view, name="stream"),
    path("lance/", views.lance_view, name="lance"),
    path("chat/enviar/", views.chat_enviar_view, name="chat_enviar"),
    path("meus-arremates/", views.meus_arremates_view, name="meus_arremates"),
    path("arremate/<int:pk>/pix/", views.arremate_pix_view, name="arremate_pix"),
    path("arremate/<int:pk>/conferir/", views.arremate_conferir_view, name="arremate_conferir"),
    # --- Webhook público ---
    path("webhooks/mercadopago/", views.webhook_mp_view, name="webhook_mp"),
    # --- Locutor ---
    path("locutor/entrar/", views.entrar_locutor_view, name="entrar_locutor"),
    path("locutor/sair/", views.sair_locutor_view, name="sair_locutor"),
    path("locutor/", views.locutor_view, name="locutor"),
    path("locutor/dados/", views.locutor_dados_view, name="locutor_dados"),
    path("locutor/acao/", views.locutor_acao_view, name="locutor_acao"),
    path("locutor/lotes/", views.lotes_view, name="lotes"),
    path("locutor/lotes/novo/", views.lote_form_view, name="lote_novo"),
    path("locutor/lotes/<int:pk>/editar/", views.lote_form_view, name="lote_editar"),
    path("locutor/lotes/<int:pk>/excluir/", views.lote_excluir_view, name="lote_excluir"),
    path("locutor/leiloes/", views.leiloes_view, name="leiloes"),
    path("locutor/leiloes/<int:pk>/status/", views.leilao_status_view, name="leilao_status"),
    path("locutor/config/", views.config_view, name="config"),
]
