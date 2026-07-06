"""Storage de arquivos estáticos com cache-busting tolerante.

`ManifestStaticFilesStorage` renomeia cada arquivo com um hash do conteúdo
(ex.: `mensalidades.abc123.js`), forçando o navegador a baixar a versão nova a
cada deploy. `manifest_strict = False` faz o `{% static %}` cair no nome original
(sem hash) quando a entrada não está no manifesto — assim os testes (que rodam
com DEBUG=False e sem `collectstatic`) e eventuais referências fora do manifesto
não quebram a página.
"""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class CacheBustingStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False
