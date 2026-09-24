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
    # A tela clássica, de backup desde que a "show" virou a padrão (24/09).
    path("classico/", views.leilao_classico_view, name="leilao_classico"),
    # Endereço da show enquanto ela estava em teste: agora leva à padrão.
    path("nova/", views.leilao_nova_view, name="leilao_nova"),
    path("entrar/", views.entrar_view, name="entrar"),
    path("sair/", views.sair_view, name="sair"),
    path("stream/", views.stream_view, name="stream"),
    path("lance/", views.lance_view, name="lance"),
    path("chat/enviar/", views.chat_enviar_view, name="chat_enviar"),
    path("reagir/", views.reagir_view, name="reagir"),
    path("meus-arremates/", views.meus_arremates_view, name="meus_arremates"),
    # O pagamento é da PESSOA, pelo total — não de um item. As rotas com
    # `<pk>` ficam porque uma aba antiga ainda pode chamá-las; a view ignora o
    # id em vez de devolver 404 na cara de quem está pagando.
    path("conta/pix/", views.arremate_pix_view, name="conta_pix"),
    path("conta/conferir/", views.arremate_conferir_view, name="conta_conferir"),
    path("arremate/<int:pk>/pix/", views.arremate_pix_view, name="arremate_pix"),
    path("arremate/<int:pk>/conferir/", views.arremate_conferir_view, name="arremate_conferir"),
    # --- Webhook público ---
    path("webhooks/mercadopago/", views.webhook_mp_view, name="webhook_mp"),
    # --- Equipe: entrada comum ---
    path("equipe/entrar/", views.entrar_equipe_view, name="entrar_equipe"),
    path("equipe/sair/", views.sair_equipe_view, name="sair_equipe"),
    path("equipe/", views.equipe_view, name="equipe"),
    path("equipe/acao/", views.locutor_acao_view, name="acao"),
    path("equipe/senha/", views.trocar_senha_view, name="trocar_senha"),
    # --- Equipe: contas (só diretor) ---
    path("equipe/usuarios/", views.usuarios_view, name="usuarios"),
    path("equipe/usuarios/<int:pk>/", views.usuario_acao_view, name="usuario_acao"),
    # --- Área do locutor ---
    # A tela de equipe trabalha sobre UM leilão, e ele vem na URL. A rota sem
    # id continua existindo (link antigo, favorito, atalho do hub): ela escolhe
    # o padrão e **redireciona** para a URL com o id, em vez de ficar
    # trabalhando sobre um palpite — que é como o locutor abria a mesa sem
    # saber qual leilão estava conduzindo.
    path("locutor/", views.locutor_view, name="locutor"),
    path("locutor/<int:leilao_id>/", views.locutor_view, name="locutor_leilao"),
    path("locutor/dados/", views.locutor_dados_view, name="locutor_dados"),
    # --- Área do caixa ---
    path("caixa/", views.caixa_view, name="caixa"),
    path("caixa/<int:leilao_id>/", views.caixa_view, name="caixa_leilao"),
    # O Pix é da PESSOA, pelo total — não de um item. A rota por arremate fica
    # por compatibilidade (aba já aberta na mesa) e só descobre de quem é.
    path("caixa/pessoa/<int:pk>/pix/", views.caixa_pix_pessoa_view, name="caixa_pix_pessoa"),
    path("caixa/arremate/<int:pk>/pix/", views.caixa_pix_view, name="caixa_pix"),
    path("caixa/entregas/", views.entregas_quadro_view, name="entregas_quadro"),
    path("caixa/<int:leilao_id>/entregas/", views.entregas_quadro_view,
         name="entregas_quadro_leilao"),
    path("caixa/entregas/redistribuir/", views.entregas_redistribuir_view,
         name="entregas_redistribuir"),
    # --- Área da preparação ---
    path("preparacao/", views.preparacao_view, name="preparacao"),
    path("preparacao/config/", views.config_view, name="config"),
    path("preparacao/<int:pk>/status/", views.leilao_status_view, name="leilao_status"),
    path("preparacao/<int:pk>/editar/", views.leilao_editar_view, name="leilao_editar"),
    path("preparacao/<int:leilao_id>/itens/", views.lotes_view, name="lotes"),
    path("preparacao/<int:leilao_id>/itens/novo/", views.lote_form_view, name="lote_novo"),
    path("preparacao/itens/<int:pk>/editar/", views.lote_form_view, name="lote_editar"),
    path("preparacao/itens/<int:pk>/excluir/", views.lote_excluir_view, name="lote_excluir"),
]
