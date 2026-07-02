"""
Configuração de URLs do projeto.

Clube de Aventureiros Pinhal Júnior
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

# Em desenvolvimento (DEBUG), o Django serve os arquivos de mídia (uploads).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
