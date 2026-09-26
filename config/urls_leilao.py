"""URLs do **serviço do leilão**.

O prefixo `/leilao/` vem do `FORCE_SCRIPT_NAME` (Nginx), como no sistema do
clube — por isso aqui as rotas nascem na raiz.
"""

from django import forms
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
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


class _LoginDoAdmin(AdminAuthenticationForm):
    """O LOGIN do admin também é só de superusuário — e tem o freio da equipe.

    O `has_permission` acima barra o índice, mas a tela de login usa o
    `AdminAuthenticationForm`, que aceita qualquer `is_staff`: uma conta de
    voluntário com a senha padrão entrava por aqui, SEM o freio de tentativas
    da porta da equipe, e caía na troca de senha — dava para varrer
    `nome/1234` e tomar a conta (revisão de 26/09).
    """

    def clean(self):
        from leilao import equipe
        from leilao.views import _ip_do

        ip = _ip_do(self.request) if self.request else "?"
        nome = (self.data.get("username") or "").strip().lower()
        chave, chave_ip = f"admin:{ip}|{nome}", f"admin-ip:{ip}"
        if equipe.login_barrado(chave) or equipe.login_barrado(
            chave_ip, limite=equipe.MAX_TENTATIVAS_POR_IP
        ):
            raise forms.ValidationError("Muitas tentativas. Espere alguns minutos.")
        try:
            dados = super().clean()
        except forms.ValidationError:
            equipe.registrar_erro_de_login(chave)
            equipe.registrar_erro_de_login(chave_ip)
            raise
        equipe.limpar_tentativas(chave)
        return dados

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise forms.ValidationError(
                "O admin do leilão é só de superusuário. A equipe entra por /equipe/.",
                code="invalid_login",
            )


admin.site.login_form = _LoginDoAdmin

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
