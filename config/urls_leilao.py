"""URLs do **serviço do leilão**.

O prefixo `/leilao/` vem do `FORCE_SCRIPT_NAME` (Nginx), como no sistema do
clube — por isso aqui as rotas nascem na raiz.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

# O /admin/ deste serviço é **só de superusuário**.
#
# O padrão do Django abre o admin para qualquer `is_staff` — e `is_staff` é
# exatamente o que toda conta da equipe do leilão tem (é ele que faz os papéis
# valerem). Sem isto, a conta de um voluntário, criada com a senha padrão `1234`,
# entraria no admin do leilão por uma porta que nenhuma tela mostra e que a troca
# obrigatória de senha não protege.
#
# Vale só neste processo: o sistema do clube roda em outro serviço, com o seu
# próprio `urls.py`.
admin.site.has_permission = lambda request: bool(
    request.user.is_active and request.user.is_superuser
)

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
