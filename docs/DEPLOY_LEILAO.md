# Deploy do módulo de Leilão (`/leilao/`)

> O leilão roda como um **segundo serviço**, ao lado do `pinhaljunior2`, na mesma base de código.
> Banco próprio, porta própria, processo próprio. Plano e justificativas em
> `docs/PLANEJAMENTO_LEILAO.md`.

```
pinhaljunior.com.br/sistema-novo/  → pinhaljunior2.service        → gunicorn sync      → db.sqlite3
pinhaljunior.com.br/leilao/        → pinhaljunior_leilao.service  → uvicorn (1 worker) → leilao.sqlite3
pinhaljunior.com.br/leilao/audio/  → mediamtx.service             → WebRTC (voz do locutor)
```

---

## 1. Por que um worker só (não mude isso)

O hub de eventos e o relógio do leilão vivem **na memória do processo**. Dois workers seriam dois
leilões paralelos, cada um com o seu cronômetro, e metade das pessoas veria um pregão e metade veria
outro. **`--workers 1` é requisito, não economia.**

Um worker aguenta com folga: as conexões SSE ficam paradas quase o tempo todo e só custam CPU quando
alguém dá lance.

## 2. Dependência nova

```bash
/var/www/pinhaljunior2/.venv/bin/pip install -r /var/www/pinhaljunior2/current/requirements-leilao.txt
```

É só o **uvicorn** (autorizado pelo usuário ao escolher SSE). Ficou num arquivo separado para o
ambiente do sistema do clube não mudar.

## 3. Variáveis de ambiente — `/etc/pinhaljunior_leilao.env`

```ini
DJANGO_SETTINGS_MODULE=config.settings_leilao
DJANGO_SECRET_KEY=<gerar uma chave só para o leilão>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=pinhaljunior.com.br,www.pinhaljunior.com.br
DJANGO_CSRF_TRUSTED_ORIGINS=https://pinhaljunior.com.br,https://www.pinhaljunior.com.br

DJANGO_LEILAO_SCRIPT_NAME=/leilao
DJANGO_LEILAO_SQLITE_PATH=/var/www/pinhaljunior2/data/leilao.sqlite3
DJANGO_LEILAO_MEDIA_ROOT=/var/www/pinhaljunior2/media_leilao
DJANGO_LEILAO_STATIC_ROOT=/var/www/pinhaljunior2/staticfiles_leilao
DJANGO_LEILAO_MEDIA_URL=/leilao/media/
DJANGO_LEILAO_STATIC_URL=/leilao/static/
```

> **`DJANGO_SECRET_KEY` própria**: com a mesma chave dos dois lados, um cookie assinado de um app
> valeria no outro. São sistemas separados — as chaves também.

Permissões, como no outro serviço:

```bash
chown root:www-data /etc/pinhaljunior_leilao.env && chmod 640 /etc/pinhaljunior_leilao.env
mkdir -p /var/www/pinhaljunior2/media_leilao /var/www/pinhaljunior2/staticfiles_leilao
chown -R www-data:www-data /var/www/pinhaljunior2/media_leilao /var/www/pinhaljunior2/staticfiles_leilao
```

## 4. Serviço — `/etc/systemd/system/pinhaljunior_leilao.service`

```ini
[Unit]
Description=Leilao online - Pinhal Junior (ASGI/uvicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/pinhaljunior2/current
EnvironmentFile=/etc/pinhaljunior_leilao.env
ExecStart=/var/www/pinhaljunior2/.venv/bin/uvicorn config.asgi_leilao:application \
    --host 127.0.0.1 --port 8011 --workers 1 --timeout-keep-alive 75 --proxy-headers
Restart=always
RestartSec=3

# O pregão é tempo real: se o áudio e o leilão disputarem CPU com os outros 11
# sites, quem perde é quem está dando lance. No dia do evento, subir estes pesos
# (ou parar os outros serviços) é o combinado.
CPUWeight=300
IOWeight=300

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now pinhaljunior_leilao.service
systemctl status pinhaljunior_leilao.service
```

## 5. Nginx

No site `sitepinhal`, ao lado do bloco `/sistema-novo/`:

```nginx
location /leilao/static/ { alias /var/www/pinhaljunior2/staticfiles_leilao/; expires 30d; }
location /leilao/media/  { alias /var/www/pinhaljunior2/media_leilao/;     expires 7d;  }

# O stream de eventos. SEM `proxy_buffering off` o Nginx segura os pedaços e o
# "tempo real" vira entrega em lotes — o leilão parece travado.
location /leilao/stream/ {
    proxy_pass http://127.0.0.1:8011;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    chunked_transfer_encoding off;
}

# Sinalização do áudio (WHIP/WHEP) → MediaMTX. Só o SDP passa por aqui;
# a voz em si vai por UDP direto ao servidor.
location /leilao/audio/ {
    proxy_pass http://127.0.0.1:8889/;
    proxy_set_header Host $host;
    proxy_read_timeout 60s;
}

location /leilao/ {
    proxy_pass http://127.0.0.1:8011;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    client_max_body_size 25M;   # foto de celular
}
```

```bash
cp /etc/nginx/sites-available/sitepinhal /etc/nginx/sites-available/sitepinhal.bak_$(date +%Y%m%d_%H%M%S)
nginx -t && systemctl reload nginx
```

## 6. Primeira carga

```bash
cd /var/www/pinhaljunior2/current
export $(grep -v '^#' /etc/pinhaljunior_leilao.env | xargs)
/var/www/pinhaljunior2/.venv/bin/python manage.py migrate
/var/www/pinhaljunior2/.venv/bin/python manage.py collectstatic --noinput
/var/www/pinhaljunior2/.venv/bin/python manage.py createsuperuser   # o locutor
chown -R www-data:www-data /var/www/pinhaljunior2/data /var/www/pinhaljunior2/staticfiles_leilao
```

> O `createsuperuser` cria quem entra em `/leilao/locutor/`. O acesso é pelo `is_staff` — a conta do
> sistema do clube **não serve** aqui (bancos diferentes, de propósito).

O `collectstatic` do leilão usa o mesmo cache-busting do clube (`core.storages`, que é importável sem o
app `core` instalado) — conferido localmente: 188 arquivos, todos pós-processados.

O `manage.py check --deploy` deste serviço mostra **as mesmas três** advertências do sistema do clube, e
elas são **esperadas**: `W004` (HSTS ainda sem valor — dívida conhecida do projeto), `W008` (quem
redireciona HTTP→HTTPS é o Nginx) e `W009`, que só aparece se faltar a `DJANGO_SECRET_KEY` no `.env`.
**Essa terceira, em produção, tem de sumir** — se ela aparecer, o segredo não foi configurado.

## 7. Áudio — MediaMTX

Binário Go único, sem npm e sem compilar:

```bash
cd /opt && mkdir -p mediamtx && cd mediamtx
# baixar o release para linux_amd64 e extrair aqui
```

Config própria em `/opt/mediamtx/leilao.yml` (**não** edite o `mediamtx.yml` que vem no pacote — assim
uma atualização do binário não apaga a sua configuração):

```yaml
logLevel: info
api: false
metrics: false
playback: false
rtsp: false
rtmp: false
hls: false
srt: false
moq: false          # sem isto ele abre 8892/8893 sem necessidade

webrtc: true
webrtcAddress: 127.0.0.1:8889     # atrás do Nginx
webrtcLocalUDPAddress: :8189      # a VOZ passa por aqui (abrir no firewall)
webrtcAdditionalHosts: [145.223.93.162]

# ATENÇÃO: do MediaMTX v1.x em diante a autenticação é GLOBAL (`authInternalUsers`).
# O `publishUser`/`publishPass` por caminho, que aparece em tutoriais antigos, não
# existe mais — a config carrega e a proteção simplesmente não vale.
authInternalUsers:
  # Ouvir é liberado: quem está no leilão escuta o locutor, sem senha.
  - user: any
    pass:
    ips: []
    permissions:
      - action: read
        path: leilao

  # Falar exige senha: só o locutor publica.
  - user: locutor
    pass: <senha forte, a MESMA da tela /leilao/locutor/config/>
    ips: []
    permissions:
      - action: publish
        path: leilao
      - action: read
        path: leilao

paths:
  leilao:
```

```bash
chmod 600 /opt/mediamtx/leilao.yml     # tem senha dentro
```

Serviço `/etc/systemd/system/mediamtx.service`:

```ini
[Unit]
Description=MediaMTX - audio ao vivo do leilao
After=network.target

[Service]
ExecStart=/opt/mediamtx/mediamtx /opt/mediamtx/leilao.yml
WorkingDirectory=/opt/mediamtx
Restart=always
RestartSec=3
CPUWeight=500

[Install]
WantedBy=multi-user.target
```

Firewall:

```bash
ufw allow 8189/udp comment "MediaMTX - audio do leilao"
```

Depois, na tela `/leilao/locutor/config/`: ligar **"Transmitir a voz do locutor"**, caminho `leilao`,
e o usuário/senha de publicação — **os mesmos** do `authInternalUsers`.

Conferência rápida, sem precisar de navegador:

```bash
# ouvir: 204 no OPTIONS; 404 no POST enquanto ninguém estiver falando (correto)
curl -s -o /dev/null -w "%{http_code}
" -X OPTIONS https://pinhaljunior.com.br/leilao/audio/leilao/whep
# falar sem senha: tem de dar 401
curl -s -o /dev/null -w "%{http_code}
" -X POST -H "Content-Type: application/sdp"      --data x https://pinhaljunior.com.br/leilao/audio/leilao/whip
```

## 7.1 Atualizar o leilão depois de um deploy — ARMADILHA

O `pinhaljunior2-deploy` faz `git reset --hard` em `/var/www/pinhaljunior2/current`, que é a pasta dos
**dois** serviços. Ou seja: ele **troca o código do leilão junto**, mas reinicia só o
`pinhaljunior2.service` e roda `collectstatic` só com as settings do clube.

**Consequência:** depois de um deploy, o leilão continua rodando o **código velho** em memória, e os
estáticos novos dele não foram coletados. Num dia comum isso passa despercebido; na véspera do evento,
não.

Então, **sempre depois do `pinhaljunior2-deploy`** (ou quando só o leilão mudou):

```bash
cd /var/www/pinhaljunior2/current
export $(grep -v '^#' /etc/pinhaljunior_leilao.env | xargs)
/var/www/pinhaljunior2/.venv/bin/python manage.py migrate --noinput
/var/www/pinhaljunior2/.venv/bin/python manage.py collectstatic --noinput
chown -R www-data:www-data /var/www/pinhaljunior2/data /var/www/pinhaljunior2/staticfiles_leilao
systemctl restart pinhaljunior_leilao.service
```

> **Não reinicie o serviço com um pregão acontecendo.** O estado em si sobrevive: `fecha_em` é uma
> data/hora **gravada no banco**, então o cronômetro é retomado no ponto certo e as conexões SSE voltam
> sozinhas em segundos (o `EventSource` reconecta e o servidor remanda o estado inteiro).
>
> O risco é o **tempo**: se o reinício demorar mais do que faltava no cronômetro, o laço central sobe
> com o prazo **já vencido** e fecha o lote **no mesmo instante** — batendo o martelo no valor em que
> estava, sem os últimos segundos de disputa. Espere o intervalo entre um lote e outro.

## 8. Antes do evento — a prova

**Obrigatório, e não no dia.**

```bash
# De OUTRA máquina (medir de dentro do VPS esconde o que o teste procura):
python manage.py leilao_carga --url https://pinhaljunior.com.br/leilao --ouvintes 100
```

Passa se: nenhuma conexão cair e o atraso p95 do lance ficar **abaixo de 1 s**.

**Medido em produção em 13/09/2026**, de outra máquina, pela internet, com o VPS atendendo os outros
11 sites normalmente:

| | Resultado |
|---|---|
| Conexões abertas / mantidas | **100 / 100** (zero quedas) |
| Lances disparados / recusados | 40 / **0** |
| Atraso do lance (p50) | **135 ms** |
| Atraso do lance (p95) | **254 ms** |
| Atraso do lance (máximo) | **261 ms** |
| Memória do processo depois | 65 MB |
| Carga do servidor depois | 0,05 |

> O `--cookie` é **repetível, e precisa ser**: a regra do pregão recusa quem tenta cobrir o próprio
> lance, então com um cookie só tudo é recusado do segundo lance em diante. Use 2 ou 3 participantes.

> **Ruído esperado no log:** ao fim de um teste (ou quando muita gente fecha a página de uma vez) o
> uvicorn registra `socket.send() raised exception.` — é ele tentando escrever num socket que o cliente
> já fechou. **Não é falha**: conferido que as conexões saem do hub (0 conexões estabelecidas na 8011
> depois do pico) e a memória não cresce.

Para o áudio não há simulação fiel: junte **10-15 aparelhos reais**, acompanhe
`mpstat 1` e `nload` no servidor e extrapole pela conta de pacotes (é linear — ~50 pacotes/s por
ouvinte). É **estimativa, não prova**; se não convencer, a saída já está pronta: preencher
"link de live externa" na configuração, e a tela passa a apontar para lá sem tocar no resto.

**No dia:** parar os serviços que puderem parar e conferir `systemctl status pinhaljunior_leilao mediamtx`.

## 9. Conferência rápida

```bash
systemctl is-active pinhaljunior_leilao.service mediamtx.service nginx
curl -sI https://pinhaljunior.com.br/leilao/entrar/ | head -1
curl -sN --max-time 3 https://pinhaljunior.com.br/leilao/stream/ | head -3   # tem de sair "event: estado"
```

## 10. O que NÃO fazer

- **Não subir com mais de um worker** (dois cronômetros — ver §1).
- **Não apontar o leilão para `db.sqlite3`**: bancos separados é o que protege mensalidades, eventos e
  loja de uma rajada de lances.
- **Não repetir o nome do cookie** do sistema do clube: um derruba a sessão do outro no navegador.
- **Não ligar `proxy_buffering`** no `/leilao/stream/`.
- **Não usar as credenciais do Mercado Pago do clube por variável de ambiente**: o leilão tem a tela
  de configuração dele, e o webhook precisa apontar para `/leilao/webhooks/mercadopago/`.
