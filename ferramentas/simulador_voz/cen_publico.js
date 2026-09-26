window.__cenarios = {};
(function () {
  var C = window.__cenarios;
  function $(id) { return document.getElementById(id); }
  function dormir(ms) { return window.__sim.dormir(ms); }
  async function esperar(cond, ms) {
    var t = Date.now();
    while (Date.now() - t < ms) { try { if (cond()) return true; } catch (e) {} await dormir(40); }
    try { return !!cond(); } catch (e) { return false; }
  }
  function r(ok, detalhe) { return { ok: !!ok, detalhe: detalhe }; }
  function ouvindo() { return window.AudioLeilao && window.AudioLeilao.ouvindo() === true; }
  function caiu() { return $("btnSom").classList.contains("caiu"); }
  function modalAberto() { var m = $("modalSomCaiu"); return !!m && !m.hidden; }
  function abertas() { return __sim.pcs.filter(function (p) { return !p.fechada; }).length; }
  function resumo() {
    return "ouvindo=" + (window.AudioLeilao && window.AudioLeilao.ouvindo()) + " abertas=" + abertas() +
      " pcs=" + __sim.pcs.length + " caiu=" + caiu() + " modal=" + modalAberto();
  }
  // O aviso de voz sai pelo servidor de verdade (a sessão é também de locutor),
  // e chega aqui pelo stream — o caminho real.
  function vozServidor(noAr) {
    var csrf = (document.querySelector("[data-csrf]") || {}).dataset.csrf;
    return fetch("/equipe/acao/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: JSON.stringify({ acao: "voz", no_ar: noAr, leilao: 1 })
    });
  }
  async function entrarComSom() {
    await vozServidor(true);
    await dormir(300);
    var porta = $("btnPortaSom");
    if (porta && porta.offsetParent !== null) porta.click();
    else $("btnSom").click();
    return esperar(ouvindo, 4000);
  }

  C.p01_ouve = async function () {
    var ok = await entrarComSom();
    return r(ok && abertas() === 1 && !caiu() && !modalAberto(), resumo());
  };

  C.p02_mute_curto_nao_religa = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    var pc = __sim.ultima(), n = __sim.pcs.length;
    pc.faixa.onmute();
    await dormir(150);                                   // ~1,5 s: soluço
    pc.faixa.onunmute();
    await dormir(1500);
    return r(!pc.fechada && __sim.pcs.length === n && ouvindo(), resumo());
  };

  C.p03_mute_longo_religa_sem_cobrir_o_lance = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    var pc = __sim.ultima();
    pc.faixa.onmute();
    var pediu = await esperar(caiu, 1500);               // no pregão: o 🔊 pisca
    var semModal = !modalAberto();
    var voltou = await esperar(function () { return __sim.ultima() !== pc && ouvindo() && !caiu(); }, 5000);
    return r(pediu && semModal && voltou, "pediu_toque=" + pediu + " sem_modal=" + semModal + " voltou=" + voltou + " " + resumo());
  };

  C.p04_bytes_parados_religa = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    var pc = __sim.ultima();
    __sim.bytesParados = true;
    var religou = await esperar(function () { return __sim.ultima() !== pc; }, 4000);
    __sim.bytesParados = false;
    var voltou = await esperar(ouvindo, 3000);
    return r(religou && voltou && abertas() === 1, "religou=" + religou + " voltou=" + voltou + " " + resumo());
  };

  C.p05_locutor_parou_de_proposito_sem_alarme = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    await vozServidor(false);                            // o locutor apertou Parar
    await dormir(400);
    __sim.whep.status = 404;                             // não há ninguém publicando
    __sim.ultima().faixa.onmute();
    await dormir(2000);
    var alarmou = caiu() || modalAberto();
    var tentando = __sim.fetches.length > 1;             // segue tentando, em silêncio
    __sim.whep.status = 201;
    await vozServidor(true);                             // o locutor voltou
    var voltou = await esperar(function () { return ouvindo() && !caiu(); }, 6000);
    return r(!alarmou && tentando && voltou, "alarme_falso=" + alarmou + " seguiu_tentando=" + tentando + " voltou=" + voltou + " " + resumo());
  };

  C.p06_navegador_recusa_tocar_pede_toque = async function () {
    __sim.recusarPlay = true;                            // o iPhone não deixou tocar
    await vozServidor(true);
    await dormir(300);
    var porta = $("btnPortaSom");
    if (porta && porta.offsetParent !== null) porta.click(); else $("btnSom").click();
    var pediu = await esperar(function () { return caiu() || modalAberto(); }, 3000);
    __sim.recusarPlay = false;
    $("btnSom").click();                                 // o toque que o navegador queria
    var voltou = await esperar(function () { return ouvindo() && !caiu(); }, 4000);
    return r(pediu && voltou, "pediu_toque=" + pediu + " voltou_com_o_toque=" + voltou + " " + resumo());
  };

  C.p07_desligar_para_tudo = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    var base = __sim.intervalosVivos();
    $("btnSom").click();                                 // desliga de propósito
    var n = __sim.pcs.length;
    await dormir(3000);                                  // ~30 s
    return r(abertas() === 0 && __sim.pcs.length === n && !caiu() && !modalAberto() && __sim.intervalosVivos() <= base,
      "pcs_novas=" + (__sim.pcs.length - n) + " intervalos=" + base + "->" + __sim.intervalosVivos() + " " + resumo());
  };

  C.p08_servidor_fora_espera_crescente = async function () {
    __sim.whep.status = 404;
    await vozServidor(true);
    await dormir(300);
    var porta = $("btnPortaSom");
    if (porta && porta.offsetParent !== null) porta.click(); else $("btnSom").click();
    await dormir(4000);                                  // ~40 s
    var n = __sim.fetches.length;
    return r(n >= 3 && n <= 12 && abertas() <= 1, "tentativas_em_40s=" + n + " " + resumo());
  };

  C.p09_oscilacao_curta_nao_derruba = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    var pc = __sim.ultima(), n = __sim.pcs.length;
    pc._estado("disconnected");
    await dormir(120);                                   // ~1,2 s
    pc._estado("connected");
    await dormir(1500);
    return r(!pc.fechada && __sim.pcs.length === n, "mesma_conexao=" + (!pc.fechada) + " pcs_novas=" + (__sim.pcs.length - n) + " " + resumo());
  };

  C.p10_noite_longa_sem_vazamento = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    var base = __sim.intervalosVivos();
    for (var i = 0; i < 12; i++) {
      var pc = __sim.ultima();
      __sim.cair(pc);
      if (!(await esperar(function () { return __sim.ultima() !== pc && ouvindo(); }, 5000))) return r(false, "ciclo " + i + " não voltou: " + resumo());
    }
    await dormir(300);
    return r(abertas() === 1 && __sim.intervalosVivos() <= base + 1,
      "intervalos=" + base + "->" + __sim.intervalosVivos() + " " + resumo());
  };
})();
