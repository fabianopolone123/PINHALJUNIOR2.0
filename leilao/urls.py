"""Rotas do leilão.

Duas metades:

- **Público** (sem login): a porta, a tela do pregão, o stream e as ações do
  participante.
- **Equipe** (login + papel): `preparacao/`, `locutor/` e `caixa/` — uma pasta
  por área, para ficar óbvio na URL de quem é cada tela. Quem protege é o
  decorator `papeis.exige` na view, nunca o menu.
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
    # --- Equipe: entrada comum ---
    path("equipe/entrar/", views.entrar_equipe_view, name="entrar_equipe"),
    path("equipe/sair/", views.sair_equipe_view, name="sair_equipe"),
    path("equipe/", views.equipe_view, name="equipe"),
    path("equipe/acao/", views.locutor_acao_view, name="acao"),
    # --- Área do locutor ---
    path("locutor/", views.locutor_view, name="locutor"),
    path("locutor/dados/", views.locutor_dados_view, name="locutor_dados"),
    # --- Área do caixa ---
    path("caixa/", views.caixa_view, name="caixa"),
    # --- Área da preparação ---
    path("preparacao/", views.preparacao_view, name="preparacao"),
    path("preparacao/config/", views.config_view, name="config"),
    path("preparacao/<int:pk>/status/", views.leilao_status_view, name="leilao_status"),
    path("preparacao/<int:leilao_id>/itens/", views.lotes_view, name="lotes"),
    path("preparacao/<int:leilao_id>/itens/novo/", views.lote_form_view, name="lote_novo"),
    path("preparacao/itens/<int:pk>/editar/", views.lote_form_view, name="lote_editar"),
    path("preparacao/itens/<int:pk>/excluir/", views.lote_excluir_view, name="lote_excluir"),
]
