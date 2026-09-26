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

  // O martelo bate com o locutor FORA do ar de propósito: a janela "O som
  // parou" não pode abrir (ela abria 1,5 s depois do martelo e ficava por
  // cima do item seguinte). Achado da revisão final de 26/09.
  function acao(corpo) {
    var csrf = (document.querySelector("[data-csrf]") || {}).dataset.csrf;
    corpo.leilao = 1;
    return fetch("/equipe/acao/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: JSON.stringify(corpo)
    }).then(function (x) { return x.json(); });
  }
  C.p11_martelo_com_locutor_parado_sem_janela = async function () {
    if (!(await entrarComSom())) return r(false, "não ouviu: " + resumo());
    await vozServidor(false);
    await dormir(400);
    __sim.whep.status = 404;
    __sim.ultima().faixa.onmute();
    await dormir(1500);
    // o martelo: dou-lhe uma, duas, VENDIDO (a sessão é também de locutor)
    var d = await (await fetch("/locutor/dados/?leilao=1", { headers: { "X-Requested-With": "XMLHttpRequest" } })).json();
    var lote = d.estado && d.estado.ativo ? d.estado.lote : null;
    if (!lote) return r(false, "sem item em pregão no banco de demonstração");
    if (lote.tem_lance) {
      await acao({ acao: "dou_lhe", vez: 1, lote: lote.id });
      await acao({ acao: "dou_lhe", vez: 2, lote: lote.id });
    }
    var f = await acao({ acao: "fechar", lote: lote.id, valor: lote.tem_lance ? String(lote.valor_atual) : "" });
    await dormir(2500);                                   // a janela abria ~1,5 s depois
    var abriu = modalAberto();
    await acao({ acao: "abrir", atual: 0 });              // deixa um item em pregão para a próxima vez
    __sim.whep.status = 201;
    await vozServidor(true);
    return r(f.ok && !abriu, "fechou=" + f.ok + " janela_abriu=" + abriu + " " + resumo());
  };
})();
