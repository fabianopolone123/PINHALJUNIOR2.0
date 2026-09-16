"""Teste de carga do leilão: N ouvintes SSE + lances de verdade.

**Rode isto ANTES do evento, não no dia.** É a prova combinada no planejamento:
o VPS é compartilhado (1 vCPU, 11 aplicações), e a única forma honesta de saber
se aguenta 100 pessoas é medir.

    python manage.py leilao_carga --url https://pinhaljunior.com.br/leilao \\
        --ouvintes 100 --lances 40

O que ele mede:

- **atraso do lance** — do `POST` sair até o evento chegar nas conexões abertas;
  é ele que diz se o leilão "parece ao vivo" (alvo: p95 abaixo de 1 s);
- **conexões que caíram** no meio;
- **lances recusados** pelo servidor;
- **rajada de reações** (`--reacoes`) — a sala inteira martelando emoji ao mesmo
  tempo, que é o único momento em que o sistema recebe **muitas** requisições
  por segundo. O lance é raro (um por vez, e a pessoa pensa antes); o emoji é o
  contrário. Se alguma coisa vai apertar o servidor, é isto.

Rode de **outra máquina**, não do próprio VPS: medir de dentro esconde
exatamente o que o teste procura (a rede e a disputa de CPU).

Não usa dependência nova — `urllib` e threads da biblioteca padrão, como o resto
das integrações do projeto.
"""

import json
import re
import statistics
import threading
import time
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand


class Ouvinte(threading.Thread):
    """Uma conexão SSE aberta, como a de um celular no leilão."""

    def __init__(self, url, parar, chegadas):
        super().__init__(daemon=True)
        self.url = url.rstrip("/") + "/stream/"
        self.parar = parar
        self.chegadas = chegadas
        self.eventos = 0
        self.caiu = False

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={"Accept": "text/event-stream"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                for linha in resp:
                    if self.parar.is_set():
                        return
                    texto = linha.decode("utf-8", "replace").strip()
                    if texto.startswith("data:"):
                        self.eventos += 1
                        # Só o evento de lance interessa para o atraso.
                        if '"valor"' in texto:
                            self.chegadas.append(time.monotonic())
        except Exception:  # noqa: BLE001 — queda é resultado, não erro do teste
            self.caiu = True


class Command(BaseCommand):
    help = "Mede o leilão sob carga: N conexões SSE + lances cronometrados."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="Raiz pública do leilão.")
        parser.add_argument("--ouvintes", type=int, default=50)
        parser.add_argument("--lances", type=int, default=30)
        parser.add_argument("--intervalo", type=float, default=1.0,
                            help="Segundos entre um lance e o próximo.")
        parser.add_argument("--cookie", action="append", default=[],
                            help="Cookie de sessão de um participante já cadastrado "
                                 "(leilao_sessionid=...). Pode repetir: um leilão de "
                                 "verdade tem vários disputando, e a regra do pregão "
                                 "recusa quem tenta cobrir o próprio lance — com um "
                                 "cookie só, do segundo lance em diante tudo é recusado. "
                                 "Sem nenhum, só mede as conexões.")
        parser.add_argument("--lote", type=int, default=0, help="Id do lote em pregão.")
        parser.add_argument("--reacoes", type=int, default=0,
                            help="Segundos de rajada de emoji: todos os --cookie "
                                 "martelando ao mesmo tempo. É o pior caso de "
                                 "requisições por segundo do módulo.")

    def handle(self, *args, **o):
        url = o["url"].rstrip("/")
        parar = threading.Event()
        chegadas = []

        self.stdout.write(f"Abrindo {o['ouvintes']} conexões em {url}/stream/ …")
        ouvintes = [Ouvinte(url, parar, chegadas) for _ in range(o["ouvintes"])]
        for x in ouvintes:
            x.start()
            time.sleep(0.02)   # não abrir tudo no mesmo milissegundo
        time.sleep(3)

        vivos = sum(1 for x in ouvintes if not x.caiu)
        self.stdout.write(f"  conectadas: {vivos}/{len(ouvintes)}")
        if vivos < len(ouvintes):
            self.stdout.write(self.style.WARNING(
                f"  {len(ouvintes) - vivos} caíram só de conectar — investigue antes de seguir."
            ))

        atrasos = []
        recusados = 0

        cookies = [c for c in (o["cookie"] or []) if c.strip()]
        if cookies and o["lote"]:
            if len(cookies) == 1:
                self.stdout.write(self.style.WARNING(
                    "Só um --cookie: do 2º lance em diante o servidor recusa "
                    "(ninguém cobre o próprio lance). Passe 2 ou mais."
                ))
            self.stdout.write(f"Disparando {o['lances']} lances com {len(cookies)} participantes…")
            for i in range(o["lances"]):
                antes = len(chegadas)
                t0 = time.monotonic()
                ok = self._lance(url, cookies[i % len(cookies)], o["lote"])
                if not ok:
                    recusados += 1
                # Espera o evento voltar para as conexões abertas.
                limite = t0 + 5
                while len(chegadas) <= antes and time.monotonic() < limite:
                    time.sleep(0.01)
                if len(chegadas) > antes:
                    atrasos.append((chegadas[antes] - t0) * 1000)
                time.sleep(o["intervalo"])
        else:
            self.stdout.write(self.style.WARNING(
                "Sem --cookie/--lote: medindo só as conexões (nenhum lance disparado)."
            ))
            time.sleep(10)

        reacoes_enviadas = 0
        reacoes_recusadas = 0
        reacoes_ms = []
        if o["reacoes"] and cookies:
            self.stdout.write(
                f"Rajada de emoji: {len(cookies)} participantes martelando por {o['reacoes']} s…"
            )
            reacoes_enviadas, reacoes_recusadas, reacoes_ms = self._rajada(
                url, cookies, o["reacoes"]
            )

        parar.set()
        time.sleep(0.5)

        caidos = sum(1 for x in ouvintes if x.caiu)
        total_eventos = sum(x.eventos for x in ouvintes)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Resultado ==="))
        self.stdout.write(f"Conexões abertas ........ {len(ouvintes)}")
        self.stdout.write(f"Conexões que caíram ..... {caidos}")
        self.stdout.write(f"Eventos recebidos ....... {total_eventos}")
        self.stdout.write(f"Lances recusados ........ {recusados}")

        if reacoes_enviadas:
            reacoes_ms.sort()
            p95r = reacoes_ms[min(len(reacoes_ms) - 1, int(len(reacoes_ms) * 0.95))]
            por_segundo = reacoes_enviadas / max(1, o["reacoes"])
            self.stdout.write(f"Reações enviadas ........ {reacoes_enviadas} ({por_segundo:.0f}/s)")
            self.stdout.write(f"Reações recusadas ....... {reacoes_recusadas}")
            self.stdout.write(f"Tempo da reação (p50) ... {statistics.median(reacoes_ms):.0f} ms")
            self.stdout.write(f"Tempo da reação (p95) ... {p95r:.0f} ms")
            if p95r > 800 or reacoes_recusadas:
                self.stdout.write(self.style.ERROR(
                    "ATENÇÃO: a rajada de emoji está apertando o servidor. "
                    "Baixe `EMOJIS_POR_TOQUE` não — ele não muda o nº de requisições; "
                    "aumente `INTERVALO_ENVIO` no reacoes.js, que é o que espaça os envios."
                ))

        if atrasos:
            atrasos.sort()
            p50 = statistics.median(atrasos)
            p95 = atrasos[min(len(atrasos) - 1, int(len(atrasos) * 0.95))]
            self.stdout.write(f"Atraso do lance (p50) ... {p50:.0f} ms")
            self.stdout.write(f"Atraso do lance (p95) ... {p95:.0f} ms")
            self.stdout.write(f"Atraso do lance (máx) ... {max(atrasos):.0f} ms")
            if p95 < 1000 and caidos == 0:
                self.stdout.write(self.style.SUCCESS(
                    "\nPASSOU: o pregão chega em menos de 1 s para todo mundo."
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    "\nATENÇÃO: acima de 1 s no p95 ou com conexões caindo. "
                    "No dia, pare os outros serviços do VPS e meça de novo."
                ))
        else:
            self.stdout.write("Atraso do lance ......... (não medido)")

    def _rajada(self, url, cookies, segundos):
        """Todo mundo martelando emoji ao mesmo tempo.

        Cada participante manda **uma** requisição a cada 0,5 s com a contagem
        de toques — é exatamente o que o `reacoes.js` faz no celular. Martelar
        mais rápido do que isso não gera mais requisição, e é justamente esse o
        desenho que se quer provar aqui.
        """
        enviadas = []
        recusadas = []
        tempos = []
        trava = threading.Lock()
        fim = threading.Event()

        def martelar(cookie, emoji):
            locais, meus_erros, meus_ms = 0, 0, []
            corpo = json.dumps({"emoji": emoji, "quantos": 10}).encode("utf-8")
            csrf = ""
            achado = re.search(r"leilao_csrftoken=([^;]+)", cookie)
            if achado:
                csrf = achado.group(1)
            while not fim.is_set():
                t0 = time.monotonic()
                try:
                    req = urllib.request.Request(
                        url + "/reagir/", data=corpo,
                        headers={
                            "Content-Type": "application/json",
                            "Cookie": cookie,
                            "X-CSRFToken": csrf,
                            "X-Requested-With": "XMLHttpRequest",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if resp.status != 200:
                            meus_erros += 1
                    locais += 1
                    meus_ms.append((time.monotonic() - t0) * 1000)
                except Exception:  # noqa: BLE001 — recusa é resultado
                    meus_erros += 1
                time.sleep(0.5)
            with trava:
                enviadas.append(locais)
                recusadas.append(meus_erros)
                tempos.extend(meus_ms)

        # Emojis diferentes de propósito: o resumo real tem várias chaves, e é
        # com várias que o teto do despejo precisa ser repartido.
        lista = ["❤️", "👏", "🔥", "😮", "🎉", "👍"]
        threads = [
            threading.Thread(target=martelar, args=(c, lista[i % len(lista)]), daemon=True)
            for i, c in enumerate(cookies)
        ]
        for t in threads:
            t.start()
        time.sleep(segundos)
        fim.set()
        for t in threads:
            t.join(timeout=5)
        return sum(enviadas), sum(recusadas), tempos

    def _lance(self, url, cookie, lote):
        corpo = json.dumps({"lote": lote}).encode("utf-8")
        csrf = ""
        achado = re.search(r"leilao_csrftoken=([^;]+)", cookie)
        if achado:
            csrf = achado.group(1)
        req = urllib.request.Request(
            url + "/lance/",
            data=corpo,
            headers={
                "Content-Type": "application/json",
                "Cookie": cookie,
                "X-CSRFToken": csrf,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": url + "/",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8")).get("ok", False)
        except urllib.error.HTTPError:
            return False
        except Exception:  # noqa: BLE001
            return False
