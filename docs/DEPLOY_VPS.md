# Deploy no VPS

Este documento registra como o **PINHALJUNIOR2.0** está publicado no VPS e como fazer novos deploys.

## Estado atual

- URL principal: `https://pinhaljunior.com.br/`
- URL legada temporária: `https://pinhaljunior.com.br/sistema-novo/` (mantida por compatibilidade; reescreve para a raiz no Nginx)
- VPS: Ubuntu 24.04, Nginx, systemd e Gunicorn.
- Deploy de código: sempre via GitHub, usando o atalho global `pinhaljunior2-deploy`.

## Estrutura no servidor

- Código: `/var/www/pinhaljunior2/current`
- Ambiente virtual: `/var/www/pinhaljunior2/.venv`
- Banco SQLite: `/var/www/pinhaljunior2/data/db.sqlite3`
- Uploads/media: `/var/www/pinhaljunior2/media`
- Staticfiles coletados: `/var/www/pinhaljunior2/staticfiles`
- Backups: `/var/www/pinhaljunior2/backup`
- Variáveis de ambiente: `/etc/pinhaljunior2.env`
- Serviço systemd: `pinhaljunior2.service`
- Gunicorn interno: `127.0.0.1:8010`
- Nginx: bloco do site `sitepinhal`, agora apontando a raiz `/`, `/static/` e `/media/` para o sistema novo.
- Sistema antigo arquivado: `/srv/sitepinhal-archive/sitepinhal_20260711_221836.tar.gz`
- Sistema antigo desativado: `sitepinhal.service` parado e desabilitado.

## Atalho de deploy

Depois de commitar e fazer push no GitHub:

```bash
pinhaljunior2-deploy
```

O atalho faz:

- lock para impedir dois deploys simultâneos;
- backup do SQLite em `/var/www/pinhaljunior2/backup`;
- `git fetch` e `git reset --hard origin/main`;
- instalação/atualização de dependências;
- `manage.py check`;
- `makemigrations --check --dry-run`;
- `migrate --noinput`;
- `collectstatic --noinput`;
- ajuste de permissões;
- restart de `pinhaljunior2.service`;
- reload do Nginx;
- healthcheck em `127.0.0.1:8010`.

## Variáveis de produção

O arquivo `/etc/pinhaljunior2.env` define:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SQLITE_PATH=/var/www/pinhaljunior2/data/db.sqlite3`
- `DJANGO_STATIC_URL=/static/`
- `DJANGO_STATIC_ROOT=/var/www/pinhaljunior2/staticfiles`
- `DJANGO_MEDIA_URL=/media/`
- `DJANGO_MEDIA_ROOT=/var/www/pinhaljunior2/media`

Opcionais (têm padrão no código; só defina para sobrescrever):

- `DJANGO_SESSION_COOKIE_NAME` (padrão `pinhaljunior2_sessionid`) e `DJANGO_CSRF_COOKIE_NAME` (padrão
  `pinhaljunior2_csrftoken`) — nomes de cookie próprios para **não colidir** com o sistema antigo no mesmo
  domínio (senão o login de um derruba o do outro).

Não versionar esse arquivo.

## Dados importados

Em 2026-07-06, o `db.sqlite3` local e a pasta `media/` local foram importados uma vez para a instalação nova.

Em 2026-07-07, após testes que sujaram o banco online, o banco do VPS foi restaurado novamente a partir do
`db.sqlite3` local. O banco online anterior foi salvo em:

```text
/var/www/pinhaljunior2/backup/db_before_local_restore_20260707_002006.sqlite3
```

Validação após importação:

- 37 usuários;
- 39 aventureiros;
- 36 aventureiros ativos;
- 87 arquivos em `media/`;
- mídia servindo com HTTP 200 via `/sistema-novo/media/`.

Pacotes temporários com dados sensíveis foram removidos após a importação.

## Validações úteis

```bash
systemctl status pinhaljunior2.service
systemctl is-active pinhaljunior2.service nginx sitepinhal.service
curl -I https://pinhaljunior.com.br/
curl -I https://pinhaljunior.com.br/cadastro/
curl -I https://pinhaljunior.com.br/recuperar-senha/
curl -I https://pinhaljunior.com.br/static/css/login.css
curl -I https://pinhaljunior.com.br/sistema-novo/
```

Rodar comandos Django no ambiente do VPS:

```bash
set -a
source /etc/pinhaljunior2.env
set +a
cd /var/www/pinhaljunior2/current
/var/www/pinhaljunior2/.venv/bin/python manage.py check
```

## Cuidados

- Não copiar código manualmente para o VPS. Código sempre por GitHub + `pinhaljunior2-deploy`.
- O deploy padrão (`pinhaljunior2-deploy`) hoje sobe o sistema novo para a **raiz** do domínio.
- O serviço antigo `sitepinhal.service` está desativado; só reativar em rollback explícito.
- Não versionar banco, uploads, tokens, `.env` ou backups.
- Antes de mudanças em Nginx, criar backup do arquivo e rodar `nginx -t` antes de `systemctl reload nginx`.
- Para mudanças que alterem models, criar migration, commitar e deixar o deploy aplicar `migrate`.

## Virada para o domínio raiz

Feita em **2026-07-11**:

- backup do Nginx: `/etc/nginx/sites-available/sitepinhal.bak_20260711_221836`
- backup do env: `/etc/pinhaljunior2.env.bak_20260711_221836`
- compactação do sistema antigo: `/srv/sitepinhal-archive/sitepinhal_20260711_221836.tar.gz`
- Nginx alterado para apontar `/` para `127.0.0.1:8010`
- `DJANGO_FORCE_SCRIPT_NAME` removido do env do novo
- `DJANGO_STATIC_URL` e `DJANGO_MEDIA_URL` ajustados para `/static/` e `/media/`
- rota legada `/sistema-novo/` mantida por compatibilidade, com rewrite para a raiz antes do proxy
- `sitepinhal.service` parado e desabilitado

Validação após a virada:

- `manage.py check` OK
- `collectstatic --noinput` OK
- `nginx -t` OK
- `https://pinhaljunior.com.br/` 200
- `https://pinhaljunior.com.br/cadastro/` 200
- `https://pinhaljunior.com.br/recuperar-senha/` 200
- `https://pinhaljunior.com.br/static/css/login.css` 200
- `https://pinhaljunior.com.br/sistema-novo/` 200
