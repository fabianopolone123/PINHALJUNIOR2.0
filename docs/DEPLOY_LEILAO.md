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

## 7. Áudio — MediaMTX

Binário Go único, sem npm e sem compilar:

```bash
cd /opt && mkdir -p mediamtx && cd mediamtx
# baixar o release para linux_amd64 e extrair aqui
```

`/opt/mediamtx/mediamtx.yml` (o essencial):

```yaml
logLevel: info
api: no
rtsp: no
rtmp: no
hls: no
srt: no

webrtc: yes
webrtcAddress: 127.0.0.1:8889          # atrás do Nginx
webrtcLocalUDPAddress: :8189           # a VOZ passa por aqui (abrir no firewall)
webrtcAdditionalHosts: [SEU.IP.PUBLICO.AQUI]

paths:
  leilao:
    publishUser: locutor
    publishPass: <senha forte, a mesma da tela de configuração>
```

Serviço `/etc/systemd/system/mediamtx.service`:

```ini
[Unit]
Description=MediaMTX - audio ao vivo do leilao
After=network.target

[Service]
ExecStart=/opt/mediamtx/mediamtx /opt/mediamtx/mediamtx.yml
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
e o usuário/senha de publicação.

## 8. Antes do evento — a prova

**Obrigatório, e não no dia.**

```bash
# De OUTRA máquina (medir de dentro do VPS esconde o que o teste procura):
python manage.py leilao_carga --url https://pinhaljunior.com.br/leilao --ouvintes 100
```

Passa se: nenhuma conexão cair e o atraso p95 do lance ficar **abaixo de 1 s**.

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
