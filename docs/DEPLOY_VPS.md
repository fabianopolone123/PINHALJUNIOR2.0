# Deploy no VPS

Este documento registra como o **PINHALJUNIOR2.0** está publicado no VPS e como fazer novos deploys.

## Estado atual

- URL temporária: `https://pinhaljunior.com.br/sistema-novo/`
- Domínio raiz `https://pinhaljunior.com.br/`: continua apontando para o sistema antigo (`sitepinhal`).
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
- Nginx: bloco do site `sitepinhal`, apenas nas rotas `/sistema-novo/`, `/sistema-novo/static/` e `/sistema-novo/media/`.

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
- `DJANGO_FORCE_SCRIPT_NAME=/sistema-novo`
- `DJANGO_STATIC_URL=/sistema-novo/static/`
- `DJANGO_STATIC_ROOT=/var/www/pinhaljunior2/staticfiles`
- `DJANGO_MEDIA_URL=/sistema-novo/media/`
- `DJANGO_MEDIA_ROOT=/var/www/pinhaljunior2/media`

Não versionar esse arquivo.

## Dados importados

Em 2026-07-06, o `db.sqlite3` local e a pasta `media/` local foram importados uma vez para a instalação nova.

Validação após importação:

- 37 usuários;
- 39 aventureiros;
- 36 aventureiros ativos;
- 86 arquivos em `media/`;
- mídia servindo com HTTP 200 via `/sistema-novo/media/`.

Pacotes temporários com dados sensíveis foram removidos após a importação.

## Validações úteis

```bash
systemctl status pinhaljunior2.service
systemctl is-active pinhaljunior2.service nginx sitepinhal.service
curl -I https://pinhaljunior.com.br/sistema-novo/
curl -I https://pinhaljunior.com.br/sistema-novo/static/css/login.css
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
- Não mexer no serviço antigo `sitepinhal.service` sem pedido explícito.
- Não substituir o domínio raiz ainda; a nova versão fica em `/sistema-novo/`.
- Não versionar banco, uploads, tokens, `.env` ou backups.
- Antes de mudanças em Nginx, criar backup do arquivo e rodar `nginx -t` antes de `systemctl reload nginx`.
- Para mudanças que alterem models, criar migration, commitar e deixar o deploy aplicar `migrate`.

## Quando for virar produção no domínio raiz

Ainda não feito. Quando chegar a hora, será necessário planejar a troca do Nginx para apontar `/` para o
novo serviço, revisar `DJANGO_FORCE_SCRIPT_NAME`, URLs de static/media, integrações de pagamento e eventuais
webhooks externos.
