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

O hub de eventos vive **na memória do processo**. Dois workers seriam dois leilões paralelos, cada um
com o seu estado e o seu `HUB`: metade das pessoas veria um pregão e metade veria outro, e o lance
dado numa metade não chegaria na outra. **`--workers 1` é requisito, não economia.**

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

> O `createsuperuser` cria o **Diretor** do leilão (vê as três áreas). A conta do sistema do clube
> **não serve** aqui — bancos diferentes, de propósito.

### Distribuir os papéis da equipe

`is_staff` **não basta**: sem papel, a pessoa entra e não vê tela nenhuma.

```bash
python manage.py leilao_papel --listar
python manage.py leilao_papel maria --dar preparacao --senha   # cria e mostra a senha uma vez
python manage.py leilao_papel joao  --dar locutor --senha
python manage.py leilao_papel ana   --dar caixa --senha
python manage.py leilao_papel joao  --dar caixa                # papéis acumulam
python manage.py leilao_papel joao  --tirar caixa
```

| Papel | Abre | Faz |
|---|---|---|
| `preparacao` | `/leilao/preparacao/` | cadastra itens, monta a fila, cria leilões, configura |
| `locutor` | `/leilao/locutor/` | conduz o pregão, chat, microfone |
| `caixa` | `/leilao/caixa/` | confere pagamento e registra a entrega |
| `diretor` | as três | distribui os papéis |

Todos entram pelo mesmo endereço, `/leilao/equipe/entrar/`. Quem tem **uma** área só cai direto nela.

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

> **Espere o intervalo entre um item e outro para reiniciar.** Nada é corrompido e **nada fecha
> sozinho**: o estado do pregão está no banco, não há cronômetro (quem bate o martelo é o locutor) e
> as conexões SSE voltam em segundos por conta própria — o `EventSource` reconecta e o servidor
> remanda o estado inteiro.
>
> O que se perde são **os segundos do blecaute**: com uma disputa quente rolando, quem tocar o botão
> nesse intervalo leva erro e precisa tocar de novo. Por isso a regra é **item em pregão, não
> reinicie** — confira antes com `Lote.objects.filter(status="aberto")`. Com o leilão no ar mas
> nenhum item aberto, pode.
>
> *(Este aviso já descreveu outro risco — o laço central subir com o cronômetro vencido e bater o
> martelo sozinho. Isso **não existe mais** desde 21/09/2026, quando o cronômetro e o prazo de
> pagamento saíram.)*

## 8. Antes do evento — a prova

**Obrigatório, e não no dia.**

```bash
# De OUTRA máquina (medir de dentro do VPS esconde o que o teste procura):
python manage.py leilao_carga --url https://pinhaljunior.com.br/leilao --ouvintes 100
```

Passa se: nenhuma conexão cair e o atraso p95 do lance ficar **abaixo de 1 s**.

**Meça COMBINADO, não uma coisa de cada vez.** A noite tem voz ao vivo, lances e emoji ao mesmo tempo,
disputando um vCPU compartilhado — medir cada coisa isolada esconde exatamente isso:

```bash
python manage.py leilao_carga --url https://pinhaljunior.com.br/leilao \
    --ouvintes 100 --lote <id> \
    --cookie "leilao_sessionid=..." --cookie "leilao_sessionid=..." \
    --lances 40 --reacoes 20
```

…com o **MediaMTX transmitindo** e alguém falando ao microfone. O que olhar, nesta ordem: o **áudio
picotou?** (é o mais sensível); o **p95 do lance** passou de 1 s?; e só então o número das reações — se
elas apertarem, o que se ajusta é o `INTERVALO_ENVIO` do `reacoes.js`, **não** o `EMOJIS_POR_TOQUE` (que
não muda quantas requisições chegam). O servidor já descarta reação sozinho quando o processo aperta
(`reacoes.TETO_POR_SEGUNDO`): o pregão vem primeiro.

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

**Medido de novo em 21/09/2026**, de outra máquina, com o VPS ocioso (load 0,04) e os outros sites
atendendo — desta vez subindo até o **dobro** do teto de projeto:

| | 100 conexões | 200 conexões |
|---|---|---|
| Abertas / mantidas | **100/100** | **200/200** |
| Quedas | 0 | 0 |
| Eventos recebidos | 5.183 | 19.854 |
| CPU ocupada em regime | ~5-10% | **~2-7%** |
| CPU no pico de entrada | ~35% | **84%** (1 s) |
| Memória do uvicorn | 60,8 → 65,5 MB | → 68,5 MB |

> **O custo é a pessoa CHEGANDO, não a conectada.** Com 200 gente dentro, o servidor fica 90-98% ocioso —
> SSE parado quase não custa nada. O aperto foi o instante dos handshakes TLS simultâneos, e o teste é mais
> duro que a realidade: ele abre 50 conexões por segundo, e gente de verdade chega pingando ao longo de
> minutos. Sobra vCPU de sobra para o MediaMTX (estimado em 10-20% para 100 ouvintes).
>
> **A voz continua sem prova.** Estas medições foram feitas **sem** o MediaMTX transmitindo: publicar exige
> um cliente WHIP (o ffmpeg do VPS é 6.1.1; WHIP só a partir do 7.1) e simular ouvintes exige uma pilha
> WebRTC, que seria dependência nova. O gasto do áudio é proporcional ao número de **assinantes**, então não
> há atalho: é o ensaio com 10-15 aparelhos reais, com alguém falando e ouvido humano julgando, medindo
> `mpstat 1` e `nload` no servidor ao mesmo tempo.

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
