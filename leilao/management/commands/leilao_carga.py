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
- **lances recusados** pelo servidor.

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
        parser.add_argument("--cookie", default="",
                            help="Cookie de sessão de um participante já cadastrado "
                                 "(leilao_sessionid=...). Sem ele, só mede as conexões.")
        parser.add_argument("--lote", type=int, default=0, help="Id do lote em pregão.")

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

        if o["cookie"] and o["lote"]:
            self.stdout.write(f"Disparando {o['lances']} lances…")
            for _ in range(o["lances"]):
                antes = len(chegadas)
                t0 = time.monotonic()
                ok = self._lance(url, o["cookie"], o["lote"])
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
