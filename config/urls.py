"""
Configuração de URLs do projeto.

Clube de Aventureiros Pinhal Júnior
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]
