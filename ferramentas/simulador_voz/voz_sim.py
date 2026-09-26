"""Roda os cenários de voz no Chrome, com o simulador injetado antes da página.

Ver LEIAME.md nesta pasta.

Uso: python voz_sim.py <sessao> <url> <arquivo_cenarios.js> [nome ...]
Cada cenário roda numa página recém-carregada (um não contamina o outro).
"""
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
CHROME = os.environ.get("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
sessao, url, arq = sys.argv[1], sys.argv[2], sys.argv[3]
filtro = sys.argv[4:]
mock = open(os.path.join(AQUI, "voz_mock.js"), encoding="utf-8").read()
cenarios = open(os.path.join(AQUI, arq), encoding="utf-8").read()
porta = 9344
perfil = os.path.join(AQUI, "chrome_voz")

proc = subprocess.Popen([
    CHROME, "--headless=new", f"--remote-debugging-port={porta}", f"--user-data-dir={perfil}",
    "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
    "--autoplay-policy=no-user-gesture-required", "--no-first-run", "about:blank",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ws_conectar():
    for _ in range(60):
        try:
            alvos = json.load(urllib.request.urlopen(f"http://127.0.0.1:{porta}/json"))
            return [a for a in alvos if a["type"] == "page"][0]["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.2)
    raise SystemExit("chrome não subiu")


ws_url = ws_conectar()
hp, caminho = ws_url[len("ws://"):].split("/", 1)
h, p = hp.split(":")
sock = socket.create_connection((h, int(p)))
chave = base64.b64encode(os.urandom(16)).decode()
sock.send((f"GET /{caminho} HTTP/1.1\r\nHost: {hp}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           f"Sec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
r = b""
while b"\r\n\r\n" not in r:
    r += sock.recv(1)


def enviar(obj):
    d = json.dumps(obj).encode()
    cab = bytearray([0x81])
    n = len(d)
    if n < 126:
        cab.append(0x80 | n)
    elif n < 65536:
        cab.append(0x80 | 126); cab += struct.pack(">H", n)
    else:
        cab.append(0x80 | 127); cab += struct.pack(">Q", n)
    m = os.urandom(4)
    cab += m
    sock.send(bytes(cab) + bytes(b ^ m[i % 4] for i, b in enumerate(d)))


def exato(n):
    b = b""
    while len(b) < n:
        b += sock.recv(n - len(b))
    return b


def receber():
    partes = b""
    while True:
        b1, b2 = exato(2)
        n = b2 & 0x7F
        if n == 126:
            n = struct.unpack(">H", exato(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", exato(8))[0]
        partes += exato(n)
        if b1 & 0x80:
            return json.loads(partes.decode())


seq = [0]
erros_js = []


def chamar(metodo, **params):
    seq[0] += 1
    meu = seq[0]
    enviar({"id": meu, "method": metodo, "params": params})
    while True:
        m = receber()
        if m.get("method") == "Runtime.exceptionThrown":
            d = m["params"]["exceptionDetails"]
            erros_js.append((d.get("exception") or {}).get("description", d.get("text", ""))[:300])
        if m.get("id") == meu:
            return m.get("result", m)


try:
    chamar("Network.enable")
    chamar("Runtime.enable")
    chamar("Network.setCookie", name="leilao_sessionid", value=sessao, domain="127.0.0.1", path="/")
    chamar("Page.enable")
    chamar("Page.addScriptToEvaluateOnNewDocument", source=mock + "\n" + cenarios)
    chamar("Page.navigate", url=url)
    time.sleep(3)
    nomes = chamar("Runtime.evaluate", expression="Object.keys(window.__cenarios)", returnByValue=True)["result"]["value"]
    if filtro:
        nomes = [n for n in nomes if n in filtro]
    resultados = []
    for nome in nomes:
        erros_js.clear()
        chamar("Page.navigate", url=url)
        time.sleep(2.5)
        r = chamar("Runtime.evaluate", expression=f"window.__cenarios[{json.dumps(nome)}]()",
                   awaitPromise=True, returnByValue=True, timeout=120000)
        v = (r.get("result") or {}).get("value")
        if v is None:
            v = {"ok": False, "detalhe": "sem retorno: " + json.dumps(r)[:400]}
        if erros_js:
            v.setdefault("erros_js", list(erros_js))
        resultados.append((nome, v))
        marca = "OK  " if v.get("ok") else "FALHA"
        print(f"{marca} {nome}: {v.get('detalhe', '')}" + (f"  ERROS_JS={v['erros_js']}" if v.get("erros_js") else ""))
        sys.stdout.flush()
    falhas = [n for n, v in resultados if not v.get("ok")]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} cenários passaram")
finally:
    proc.kill()
