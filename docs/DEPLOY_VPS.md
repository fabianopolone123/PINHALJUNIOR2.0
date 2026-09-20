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

> **Atenção ao nome.** Existem **dois** atalhos parecidos no servidor:
>
> | Comando | Projeto | Caminho | Porta |
> |---|---|---|---|
> | `pinhaljunior2-deploy` | **este sistema** | `/var/www/pinhaljunior2` | 8010 |
> | `pinhaljunior-deploy` (sem o "2") | sistema **antigo** | `/srv/sitepinhal` | 8000 |
>
> Rodar o de baixo por engano **reativa o `sitepinhal.service`**, que deve ficar parado — ele volta a consumir
> memória sem servir tráfego (o Nginx aponta o domínio para a porta 8010). Não quebra o site, mas passa
> despercebido. Para conferir e parar:
>
> ```bash
> systemctl is-active sitepinhal.service
> systemctl stop sitepinhal.service
> ```
>
> Como distinguir na saída: o nosso mostra `[pinhaljunior2]` em cada linha, aplica migrations do app `core` e
> faz healthcheck na porta 8010.

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

## Quando o deploy falha: o rollback NÃO refaz as permissões

Descoberto em 12/09/2026, com o site **502 por ~2 minutos**. O atalho valida `makemigrations --check` **antes**
de aplicar migrations; faltando uma migration ele aborta e chama o rollback, que volta o código (`git reset`) e
restaura o SQLite — mas o passo de **permissões** (`chown -R root:www-data` + `chmod -R g+rX`) vem **depois**, no
caminho feliz, e não é refeito. O código volta como `root:root` e o Gunicorn não lê nem o `config/__init__.py`:

```text
PermissionError: [Errno 13] Permission denied: '/var/www/pinhaljunior2/current/config/__init__.py'
```

O serviço fica em `activating (auto-restart)` e o Nginx responde **502**. Para levantar na hora:

```bash
chown -R root:www-data /var/www/pinhaljunior2/current
chmod -R g+rX /var/www/pinhaljunior2/current
systemctl restart pinhaljunior2.service
```

Melhor ainda: **corrigir a causa e rodar o `pinhaljunior2-deploy` de novo** — o deploy que dá certo refaz as
permissões no fim e devolve o site sozinho (foi o que se fez). E, antes de qualquer push que mexa em model
(inclusive em `default=`, como o texto padrão de uma mensagem), rode localmente:

```bash
python manage.py makemigrations --check --dry-run
```

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

## Cron — reengajamento do WhatsApp

O reengajamento de contatos inativos (WhatsApp) roda pelo comando `reengajar_inativos`. **Quantos dias sem
resposta** disparam o reengajamento é configurável **na tela** (WhatsApp → aba Liberação → "Reengajar após quantos
dias"); o cron só executa a verificação. O comando já pausa **10s entre cada envio** e não reenvia para quem já
foi reengajado dentro da janela.

Agendar (ex.: **todo dia às 09:00**) com `crontab -e`:

```cron
0 9 * * * cd /var/www/pinhaljunior2/current && set -a && . /etc/pinhaljunior2.env && set +a && /var/www/pinhaljunior2/.venv/bin/python manage.py reengajar_inativos >> /var/www/pinhaljunior2/backup/reengajar.log 2>&1
```

- Roda **independente de acesso** ao site (é o cron do servidor).
- Ajuste o horário (`0 9`) se quiser; o fuso é o do servidor.
- Para **pausar**, basta comentar/remover a linha do crontab (o comando também não faz nada se o WhatsApp não
  estiver configurado ou a mensagem de reengajamento estiver vazia).
- Rodar na mão para testar: use o mesmo bloco sem o `>> ...log`.

## O VPS é compartilhado com outros projetos

Este servidor **não é exclusivo** do Pinhal Júnior. Levantamento de **2026-09-19**: **11 sites** habilitados no
Nginx e ~50 serviços ativos no total (o número de *sites* é menor que o de *serviços* — há worker, scheduler e
API que não têm domínio próprio).

| Site (Nginx) | Domínio | Back-end |
|---|---|---|
| `sitepinhal` | pinhaljunior.com.br | **este sistema** → 8010 (e `/leilao/` → 8011) |
| `compraquerende` | compraquerende.com.br | Flask/gunicorn → 8131 (`compraquerende-api.service`) |
| `docuras-ana` | docurasdaana.com.br | 8125 |
| `gm3d` | gm3d.com.br | 8113 |
| `site_idiomas` | fabianopolone.com.br | 8121 |
| `advministerioesperanca` | advministerioesperanca.com.br | estático |
| `ppm` | fabianopolloni.com.br | estático |
| `procuroprofissional` | api.fabianopolone.com.br | estático |
| `samelapolloni` | samelapolloni.com.br | estático |
| `site_inscricao` | inscriçãoandrews.com.br (punycode `xn--inscriaoandrews-jmb`) | estático |
| `sitemissao` | missaoandrewsc.com.br | estático |

> O nome do arquivo do Nginx **não** é o nome do serviço systemd. O nosso domínio é servido pelo site
> `sitepinhal` (nome herdado do sistema antigo) e atendido pelo `pinhaljunior2.service`; o
> `sitepinhal.service` é outra coisa e deve continuar **parado** (conferido inativo em 19/09).

Outros serviços ativos sem site próprio: `beezap`, `italiano`/`italiano-ti`, `polloniflow`, `tradeanalise`,
`treinartrade`, `madson`, `marcelochaveiros`, `missaoesperanca`, `zappoint`, `searchwork`(+`-scheduler`),
`form-desenv`, `site_inscricao_africa`, `site_inscricao_v2`, `mediamtx` (áudio do leilão), além de
`postgresql@16`, `redis-server` e os agentes `beszel`.

**Recursos:** 1 vCPU, 3,8 GB de RAM, **2 GB de swap**, ~72 processos gunicorn. Disco em 42% de 48 GB.
Implicações práticas:

- Nunca parar/reiniciar serviço que não seja o `pinhaljunior2` sem saber a quem pertence. Para descobrir de
  quem é uma porta: `ss -ltnp | grep <porta>` e depois
  `grep -rl "<porta>" /etc/systemd/system/*.service`.
- **Já existe swap** (não existia em 07/2026), então um pico de memória agora degrada em vez de matar o
  processo. Ainda assim a margem é curta: ~1,3 GB disponíveis com 254 MB de swap já em uso.
- Um `systemctl restart` de um serviço é seguro; um `reboot` derruba os 11 sites e precisa de janela.
- **Ao inspecionar o Nginx, use `grep -R` (maiúsculo).** O `sites-enabled` é só de symlinks e o `grep -r`
  **não os segue** — uma busca por `server_name` ali volta vazia e dá a impressão de que o site não existe.

## Dependências externas que expiram

Coisas que param sozinhas e **não** geram alerta — quando algo "parou de funcionar sem ninguém mexer", comece por aqui:

| Dependência | Como falha | Onde renovar |
|---|---|---|
| **W-API** (WhatsApp) | `Erro 403: para continuar usando essa instância, você deve assinar novamente` | painel da w-api.app — assinatura da instância |
| **Sessão do WhatsApp** | `Erro 401: Whatsapp não conectado` | ler o QR Code de novo no painel da W-API |
| **Certificado SSL** | site fora do ar por HTTPS | automático (`certbot.timer`); só conferir se o timer está ativo |
| **Senha de app do Gmail** | `SMTPAuthenticationError` na tela de E-mail | Conta do Google → Segurança → Senhas de app |

Quando a W-API cai, **tudo** que depende dela para: cobrança por WhatsApp, as notificações automáticas nesse
canal, o código de recuperação de senha e o reengajamento. O sistema não quebra (as falhas viram mensagem na
tela), mas nada sai. O canal de **e-mail é independente** e continua funcionando.

Diagnóstico rápido da W-API, sem incomodar ninguém (envia para o próprio número do clube):

```bash
set -a; . /etc/pinhaljunior2.env; set +a
cd /var/www/pinhaljunior2/current
/var/www/pinhaljunior2/.venv/bin/python -c "
import django; django.setup()
from core.models import WhatsappConfig
from core import wapi
print(wapi.listar_grupos(WhatsappConfig.get_solo())[:2])
"
```

## Acesso bloqueado em redes corporativas (FortiGate)

O domínio é novo (registrado em 2026-01-18) e pequeno, então o **FortiGuard** pode não tê-lo classificado — e
muitos perfis de FortiGate bloqueiam categoria "não classificada" por padrão. O site fica inacessível na rede
da empresa e normal em todo o resto.

- **Conserto definitivo (gratuito):** pedir reclassificação em `fortiguard.com/webfilter` → *Request
  Reclassification*. Categoria sugerida: **Education** ou **Charitable Organizations**.
- **Paliativo por rede:** exceção no FortiGate. O caminho que resolve todos os perfis de uma vez é
  **Security Profiles → Web Rating Overrides**, não a lista de URLs (que vale só para o perfil ao qual a
  tabela está amarrada).
- Não é problema do servidor: o site responde 200 normalmente da internet aberta.

## Cron — mensagens de aniversário

O disparo das mensagens de aniversário roda pelo comando `enviar_aniversarios`, que manda para quem faz
aniversário **naquele dia**, pelos canais ligados no template de cada perfil (WhatsApp e/ou e-mail).

É **idempotente**: o `EnvioAniversario` trava um envio por pessoa/ano/canal, então rodar duas vezes no mesmo
dia não duplica — e rodar depois de um envio manual pela tela também não. Pausa **10s entre cada pessoa**.

Agendar (ex.: **todo dia às 09:00**) com `crontab -e`:

```cron
0 9 * * * cd /var/www/pinhaljunior2/current && set -a && . /etc/pinhaljunior2.env && set +a && /var/www/pinhaljunior2/.venv/bin/python manage.py enviar_aniversarios >> /var/www/pinhaljunior2/backup/aniversarios.log 2>&1
```

- Para ver quem receberia **sem enviar nada**: acrescente `--dry-run`.
- Para mudar a pausa: `--pausa 5` (segundos).
- Nada sai enquanto a mensagem do perfil estiver **desligada** na tela (todas nascem assim).

## Cuidados

- Não copiar código manualmente para o VPS. Código sempre por GitHub + `pinhaljunior2-deploy`.
- **Deploy só traz o que já está no GitHub.** Se `Commit anterior` e `Commit atual` saírem iguais na saída do
  atalho, é sinal de que o `git push` não foi feito — não adianta rodar de novo.
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
