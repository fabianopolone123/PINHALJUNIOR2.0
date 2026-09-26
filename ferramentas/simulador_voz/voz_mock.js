/* Simulador da voz: roda ANTES dos scripts da página (addScriptToEvaluateOnNewDocument).
   Troca só o que precisa de rede de áudio de verdade: RTCPeerConnection, o
   servidor WHIP/WHEP (fetch) e o relógio (acelerado). O resto é o código real. */
(function () {
  // Cada cenário começa limpo: o mudo guardado na aba não vaza entre eles.
  try { sessionStorage.removeItem("leilao_mudo"); } catch (e) {}
  var sim = window.__sim = {
    escala: 0.1,                    // setTimeout/setInterval 10x mais rápidos
    whip: { status: 201, atraso: 60 },
    whep: { status: 201, atraso: 60 },
    pcs: [], fetches: [], acoes: [], streams: [],
    recusarPlay: false, bytesParados: false, log: [],
    intervalos: 0
  };

  // ---- relógio acelerado (conta intervalos vivos para achar vazamento)
  var _st = window.setTimeout, _si = window.setInterval, _ci = window.clearInterval;
  var vivos = new Set();
  window.setTimeout = function (fn, ms) { return _st(fn, Math.max(0, (ms || 0) * sim.escala)); };
  window.setInterval = function (fn, ms) { var id = _si(fn, Math.max(1, (ms || 0) * sim.escala)); vivos.add(id); return id; };
  window.clearInterval = function (id) { vivos.delete(id); return _ci(id); };
  sim.intervalosVivos = function () { return vivos.size; };
  sim.dormir = function (ms) { return new Promise(function (r) { _st(r, ms); }); };

  // ---- microfone: registra toda stream entregue (para achar "microfone quente")
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    var _gum = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = function (c) {
      if (sim.negarMic) return Promise.reject(new DOMException("negado", "NotAllowedError"));
      return _gum(c).then(function (s) { sim.streams.push(s); return s; });
    };
  }
  sim.microfonesVivos = function () {
    return sim.streams.reduce(function (n, s) {
      return n + s.getAudioTracks().filter(function (t) { return t.readyState === "live"; }).length;
    }, 0);
  };

  // ---- play() controlável
  var _play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    if (sim.recusarPlay) return Promise.reject(new DOMException("autoplay", "NotAllowedError"));
    try { var p = _play.call(this); if (p && p.catch) p.catch(function () {}); } catch (e) {}
    return Promise.resolve();
  };

  // ---- a faixa de áudio que o "servidor" manda para quem escuta
  var ctx = null;
  function faixaNova() {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    var dest = ctx.createMediaStreamDestination();
    return dest.stream;
  }

  // ---- RTCPeerConnection falso
  function FakePC() {
    this.id = sim.pcs.length + 1;
    this.connectionState = "new";
    this.iceConnectionState = "new";
    this.iceGatheringState = "complete";
    this.localDescription = null;
    this.fechada = false;
    this.publica = false;
    this.bytes = 0;
    this._ouvintes = {};
    sim.pcs.push(this);
  }
  FakePC.prototype.addEventListener = function (n, fn) { (this._ouvintes[n] = this._ouvintes[n] || []).push(fn); };
  FakePC.prototype.removeEventListener = function (n, fn) {
    this._ouvintes[n] = (this._ouvintes[n] || []).filter(function (f) { return f !== fn; });
  };
  FakePC.prototype.addTrack = function () { this.publica = true; };
  FakePC.prototype.addTransceiver = function () { this.publica = false; };
  FakePC.prototype.createOffer = function () {
    if (this.fechada) return Promise.reject(new DOMException("closed", "InvalidStateError"));
    return Promise.resolve({ type: "offer", sdp: "v=0 falso" });
  };
  FakePC.prototype.setLocalDescription = function (d) {
    if (this.fechada) return Promise.reject(new DOMException("closed", "InvalidStateError"));
    this.localDescription = d; return Promise.resolve();
  };
  FakePC.prototype.setRemoteDescription = function () {
    var self = this;
    if (self.fechada) return Promise.reject(new DOMException("closed", "InvalidStateError"));
    _st(function () {
      if (self.fechada) return;
      if (sim.naoConecta) { self._estado("connecting"); return; }   // rede que barra a mídia
      self._estado("connected");
      if (!self.publica && self.ontrack) {
        var stream = faixaNova();
        self.faixa = stream.getAudioTracks()[0];
        self.ontrack({ streams: [stream], track: self.faixa });
      }
    }, 20);
    return Promise.resolve();
  };
  FakePC.prototype._estado = function (s) {
    this.connectionState = s;
    this.iceConnectionState = s === "connected" ? "connected" : s;
    if (this.onconnectionstatechange) this.onconnectionstatechange();
    if (this.oniceconnectionstatechange) this.oniceconnectionstatechange();
  };
  // Como o navegador de verdade: close() NÃO dispara connectionstatechange.
  FakePC.prototype.close = function () { this.fechada = true; this.connectionState = "closed"; this.iceConnectionState = "closed"; };
  FakePC.prototype.getStats = function () {
    if (!sim.bytesParados && this.connectionState === "connected") this.bytes += 1000;
    var b = this.bytes;
    return Promise.resolve(new Map([["x", { type: "inbound-rtp", kind: "audio", bytesReceived: b }]]));
  };
  window.RTCPeerConnection = FakePC;
  sim.vivas = function (publica) {
    return sim.pcs.filter(function (p) { return !p.fechada && p.connectionState === "connected" && (publica === undefined || p.publica === publica); });
  };
  sim.ultima = function () { return sim.pcs[sim.pcs.length - 1]; };
  sim.cair = function (pc) { (pc || sim.ultima())._estado("failed"); };

  // ---- servidor WHIP/WHEP falso + registro das ações da mesa
  var _fetch = window.fetch.bind(window);
  window.fetch = function (url, op) {
    url = String(url);
    op = op || {};
    if (/\/whip$|\/whep$/.test(url)) {
      var cfg = /whip$/.test(url) ? sim.whip : sim.whep;
      var h = op.headers || {};
      sim.fetches.push({ url: url, auth: h.Authorization || h.authorization || "", em: Date.now() });
      return new Promise(function (ok, falha) {
        var sinal = op.signal;
        if (sinal) sinal.addEventListener("abort", function () { falha(new DOMException("abortado", "AbortError")); });
        _st(function () { ok(new Response(cfg.status < 300 ? "v=0 resposta" : "erro", { status: cfg.status })); }, cfg.atraso);
      });
    }
    if (/equipe\/acao\/$/.test(url) && op.body) {
      try { sim.acoes.push(JSON.parse(op.body)); } catch (e) {}
    }
    return _fetch(url, op);
  };
})();
