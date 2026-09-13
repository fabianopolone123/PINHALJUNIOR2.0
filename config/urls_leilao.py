"""URLs do **serviço do leilão**.

O prefixo `/leilao/` vem do `FORCE_SCRIPT_NAME` (Nginx), como no sistema do
clube — por isso aqui as rotas nascem na raiz.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("leilao.urls")),
]

if settings.DEBUG:
    # Em produção quem serve estático e mídia é o Nginx.
    #
    # Em desenvolvimento, este serviço roda em **uvicorn**, não no `runserver` —
    # e o handler de estáticos é coisa que só o `runserver` acrescenta sozinho.
    # Sem estas duas linhas, `uvicorn config.asgi_leilao:application` sobe a
    # página sem CSS nenhum e sem as fotos dos lotes.
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
