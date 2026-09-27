window.__cenarios = {};
(function () {
  var C = window.__cenarios;
  function $(id) { return document.getElementById(id); }
  function estado() { return ($("microEstado") || {}).textContent || ""; }
  function dormir(ms) { return window.__sim.dormir(ms); }
  async function esperar(cond, ms) {
    var t = Date.now();
    while (Date.now() - t < ms) { try { if (cond()) return true; } catch (e) {} await dormir(40); }
    try { return !!cond(); } catch (e) { return false; }
  }
  function r(ok, detalhe) { return { ok: !!ok, detalhe: detalhe }; }
  function mic() { var s = __sim.streams[__sim.streams.length - 1]; return s && s.getAudioTracks()[0]; }
  function vozes(v) { return __sim.acoes.filter(function (a) { return a.acao === "voz" && a.no_ar === v; }).length; }
  async function noAr() {
    $("btnMicrofone").click();
    return esperar(function () { return __sim.vivas(true).length === 1 && /No ar|MUDO/.test(estado()); }, 4000);
  }
  function resumo() {
    return "vivas=" + __sim.vivas(true).length + " mics=" + __sim.microfonesVivos() + " estado='" + estado().slice(0, 50) + "'";
  }

  C.m01_transmitir = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar: " + resumo());
    var auth = (__sim.fetches[0] || {}).auth || "";
    return r(__sim.microfonesVivos() === 1 && /^Basic /.test(auth) && vozes(true) >= 1,
      resumo() + " auth=" + (auth ? "sim" : "não") + " voz_no_ar=" + vozes(true));
  };

  C.m02_mudo_nao_derruba = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    var pc = __sim.ultima(), n = __sim.pcs.length;
    $("btnMudo").click();
    var mudo = mic().enabled === false && /MUDO/.test(estado());
    await dormir(2500);                                 // ~25 s no relógio acelerado
    var firme = !pc.fechada && pc.connectionState === "connected" && __sim.pcs.length === n && vozes(false) === 0;
    $("btnMudo").click();
    var volta = mic().enabled === true && /No ar/.test(estado());
    return r(mudo && firme && volta, "mudo=" + mudo + " conexao_firme=" + firme + " voltou=" + volta + " " + resumo());
  };

  C.m03_mudo_armado_antes = async function () {
    $("btnMudo").click();
    var armado = /MUDO armado/.test(estado()) && __sim.microfonesVivos() === 0;
    if (!(await noAr())) return r(false, "não entrou no ar");
    return r(armado && mic().enabled === false && /MUDO/.test(estado()),
      "armado=" + armado + " track_enabled=" + mic().enabled + " " + resumo());
  };

  C.m04_parar_com_mudo = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    $("btnMudo").click();
    $("btnMicrofone").click();                          // Parar
    await dormir(300);
    var desligou = __sim.vivas(true).length === 0 && __sim.microfonesVivos() === 0;
    var armado = /MUDO armado/.test(estado()) && $("btnMudo").classList.contains("ativo");
    var avisou = vozes(false) >= 1;
    if (!(await noAr())) return r(false, "não voltou ao ar");
    return r(desligou && armado && avisou && mic().enabled === false,
      "desligou=" + desligou + " armado=" + armado + " avisou_sala=" + avisou + " volta_muda=" + (mic().enabled === false));
  };

  C.m05_queda_religa = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    var velha = __sim.ultima();
    __sim.cair(velha);
    var viuQueda = await esperar(function () { return /caiu/.test(estado()); }, 1500);
    var voltou = await esperar(function () { var v = __sim.vivas(true); return v.length === 1 && v[0] !== velha && /No ar/.test(estado()); }, 6000);
    return r(viuQueda && voltou && __sim.microfonesVivos() === 1, "viu_queda=" + viuQueda + " voltou=" + voltou + " " + resumo());
  };

  C.m06_queda_preserva_mudo = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    $("btnMudo").click();
    var velha = __sim.ultima();
    __sim.cair(velha);
    var voltou = await esperar(function () { var v = __sim.vivas(true); return v.length === 1 && v[0] !== velha; }, 6000);
    await dormir(100);
    return r(voltou && mic().enabled === false && /MUDO/.test(estado()),
      "voltou=" + voltou + " track_enabled=" + mic().enabled + " " + resumo());
  };

  C.m07_queda_e_parar = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    __sim.whip.status = 503;                            // a religação vai falhar
    __sim.cair();
    await esperar(function () { return /caiu/.test(estado()); }, 1500);
    $("btnMicrofone").click();                          // Parar no meio da religação
    var nParar = __sim.pcs.length;
    __sim.whip.status = 201;
    await dormir(3000);                                  // ~30 s
    return r(__sim.vivas(true).length === 0 && __sim.microfonesVivos() === 0 && __sim.pcs.length === nParar && /Desligado/.test(estado()),
      "pcs_depois_do_parar=" + (__sim.pcs.length - nParar) + " " + resumo());
  };

  C.m08_queda_parar_transmitir_rapido = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    __sim.cair();
    await esperar(function () { return /caiu/.test(estado()); }, 1500);
    $("btnMicrofone").click();                          // Parar
    $("btnMicrofone").click();                          // Transmitir de novo, na hora
    var ok = await esperar(function () { return __sim.vivas(true).length === 1 && /No ar/.test(estado()); }, 5000);
    var viva = __sim.vivas(true)[0];
    await dormir(3000);                                  // a religação velha não pode derrubar a nova
    var firme = viva && !viva.fechada && __sim.vivas(true).length === 1 && __sim.microfonesVivos() === 1;
    return r(ok && firme, "no_ar=" + ok + " firme=" + firme + " " + resumo());
  };

  C.m09_queda_religacao_em_voo_parar_transmitir = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    __sim.whip.atraso = 1500;                           // a religação fica "no meio do caminho"
    __sim.cair();
    await esperar(function () { return __sim.fetches.length >= 2; }, 3000);   // religação já mandou o WHIP
    __sim.whip.atraso = 60;
    $("btnMicrofone").click();                          // Parar
    $("btnMicrofone").click();                          // Transmitir
    var ok = await esperar(function () { return __sim.vivas(true).length === 1 && /No ar/.test(estado()); }, 5000);
    var boa = __sim.vivas(true)[0], nPcs = __sim.pcs.length;
    await dormir(3500);
    // A conexão boa tem de ser a MESMA no fim: derrubá-la e refazer (mesmo que
    // volte) é a sala inteira perdendo a voz e reconectando.
    var mesma = boa && !boa.fechada && __sim.vivas(true)[0] === boa && __sim.pcs.length === nPcs;
    return r(ok && mesma && __sim.microfonesVivos() === 1 && /No ar/.test(estado()),
      "no_ar=" + ok + " mesma_conexao=" + mesma + " pcs_novas=" + (__sim.pcs.length - nPcs) + " " + resumo());
  };

  C.m10_senha_recusada = async function () {
    __sim.whip.status = 401;
    $("btnMicrofone").click();
    var viu = await esperar(function () { return /Não consegui/.test(estado()); }, 3000);
    await dormir(1500);
    return r(viu && __sim.vivas(true).length === 0 && __sim.microfonesVivos() === 0 && /Transmitir/.test($("btnMicrofone").textContent),
      "avisou=" + viu + " " + resumo());
  };

  C.m11_duplo_clique = async function () {
    $("btnMicrofone").click();
    $("btnMicrofone").click();
    await esperar(function () { return /No ar/.test(estado()); }, 4000);
    await dormir(500);
    return r(__sim.vivas(true).length === 1 && __sim.microfonesVivos() === 1, resumo() + " pcs=" + __sim.pcs.length);
  };

  C.m12_microfone_negado = async function () {
    __sim.negarMic = true;
    $("btnMicrofone").click();
    var viu = await esperar(function () { return /Não consegui/.test(estado()); }, 3000);
    return r(viu && __sim.vivas(true).length === 0 && !$("btnMicrofone").disabled, "avisou=" + viu + " " + resumo());
  };

  C.m13_religa_depois_de_falhas = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    var avisosAntes = vozes(true);
    __sim.whip.status = 503;
    __sim.cair();
    await dormir(2000);
    __sim.whip.status = 201;
    var voltou = await esperar(function () { return __sim.vivas(true).length === 1 && /No ar/.test(estado()); }, 8000);
    return r(voltou && vozes(true) > avisosAntes, "voltou=" + voltou + " avisou_a_sala=" + (vozes(true) > avisosAntes) + " " + resumo());
  };

  C.m14_sem_vazamento_em_ciclos = async function () {
    var base = __sim.intervalosVivos();
    for (var i = 0; i < 6; i++) {
      if (!(await noAr())) return r(false, "ciclo " + i + " não entrou no ar");
      $("btnMicrofone").click();
      await esperar(function () { return /Desligado/.test(estado()); }, 2000);
    }
    await dormir(300);
    var depois = __sim.intervalosVivos();
    return r(depois <= base && __sim.microfonesVivos() === 0 && __sim.vivas(true).length === 0,
      "intervalos_antes=" + base + " depois=" + depois + " " + resumo());
  };

  C.m15_mudo_durante_religacao = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    __sim.whip.status = 503;
    __sim.cair();
    await esperar(function () { return /caiu/.test(estado()); }, 1500);
    $("btnMudo").click();                               // muta com a voz caída
    __sim.whip.status = 201;
    var voltou = await esperar(function () { return __sim.vivas(true).length === 1; }, 8000);
    await dormir(200);
    return r(voltou && mic().enabled === false && /MUDO/.test(estado()),
      "voltou=" + voltou + " track_enabled=" + (mic() && mic().enabled) + " " + resumo());
  };

  C.m16_mudo_na_religacao_nao_diz_no_ar = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    __sim.whip.status = 503;
    __sim.cair();
    await esperar(function () { return /caiu/.test(estado()); }, 1500);
    $("btnMudo").click();
    var t1 = estado();
    $("btnMudo").click();
    var t2 = estado();
    return r(!/No ar/.test(t1) && !/No ar/.test(t2), "depois_do_mudo='" + t1.slice(0, 45) + "' depois_de_voltar='" + t2.slice(0, 45) + "'");
  };

  C.m17_rede_que_barra_a_midia = async function () {
    __sim.naoConecta = true;
    $("btnMicrofone").click();
    await dormir(14000);                                // o limite de 12 s é em tempo real
    var falsoNoAr = /No ar/.test(estado()) || vozes(true) > 0;
    return r(!falsoNoAr && __sim.vivas(true).length === 0,
      "disse_no_ar_ou_avisou_a_sala=" + falsoNoAr + " tentativas_whip=" + __sim.fetches.length + " estado='" + estado().slice(0, 50) + "'");
  };

  C.m18_microfone_que_desconecta = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    var velho = mic();
    velho.stop();                                       // Bluetooth/USB saiu, bateria acabou
    velho.dispatchEvent(new Event("ended"));            // (stop() sozinho não dispara o evento)
    var viu = await esperar(function () { return /caiu/.test(estado()); }, 1500);
    var voltou = await esperar(function () { return mic() !== velho && __sim.vivas(true).length === 1 && /No ar/.test(estado()); }, 6000);
    return r(viu && voltou, "percebeu=" + viu + " religou_com_mic_novo=" + voltou + " " + resumo());
  };

  C.m19_soluco_de_rede_reaproveita = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    var pc = __sim.ultima(), n = __sim.pcs.length;
    pc._estado("disconnected");
    await esperar(function () { return /caiu/.test(estado()); }, 1500);   // passou dos 4 s
    pc._estado("connected");                            // voltou sozinha antes da religação
    await dormir(2500);
    var mesma = !pc.fechada && __sim.pcs.length === n && __sim.vivas(true)[0] === pc && /No ar/.test(estado());
    return r(mesma, "mesma_conexao=" + mesma + " pcs_novas=" + (__sim.pcs.length - n) + " " + resumo());
  };

  C.m20_servidor_de_audio_nao_responde = async function () {
    __sim.whip.atraso = 60000;                          // o servidor nunca responde
    $("btnMicrofone").click();
    var liberou = await esperar(function () { return /Não consegui/.test(estado()) && !$("btnMicrofone").disabled; }, 4000);
    return r(liberou && __sim.microfonesVivos() === 0, "botao_liberado=" + liberou + " " + resumo());
  };
  // ---- Qual microfone (27/09) -----------------------------------------
  function usando() { return ($("microUsando") || {}).textContent || ""; }
  function envio() { var pc = __sim.vivas(true)[0]; return pc && pc.getSenders()[0]; }
  function pedidoDe(i) { var p = __sim.pedidos[i]; return p && p.audio && p.audio.deviceId && p.audio.deviceId.exact; }
  async function listaComNomes() {
    $("btnMicrofones").click();
    return esperar(function () { return $("microEscolha").options.length >= 3 && !/🔄/.test($("microEscolha").textContent); }, 3000);
  }
  function escolherNaLista(i) {
    var sel = $("microEscolha");
    sel.value = sel.options[i].value;
    sel.dispatchEvent(new Event("change"));
    return sel.options[i];
  }

  C.m21_escolhe_o_microfone_antes = async function () {
    if (!(await listaComNomes())) return r(false, "a lista não mostrou os microfones: " + $("microEscolha").textContent);
    var op = escolherNaLista(2);
    await dormir(100);
    var n = __sim.pedidos.length;
    if (!(await noAr())) return r(false, "não entrou no ar: " + resumo());
    var pediu = pedidoDe(n) === op.value;
    var mostra = usando().indexOf(op.textContent) >= 0;
    var guardou = localStorage.getItem("leilao_microfone") === op.value;
    return r(pediu && mostra && guardou && __sim.microfonesVivos() === 1,
      "pediu_o_escolhido=" + pediu + " mostra_em_uso=" + mostra + " guardou=" + guardou + " usando='" + usando() + "' " + resumo());
  };

  C.m22_troca_no_ar_sem_derrubar = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    if (!(await listaComNomes())) return r(false, "sem lista");
    var pc = __sim.ultima(), n = __sim.pcs.length, velho = mic();
    var op = escolherNaLista(2);
    var trocou = await esperar(function () { return mic() !== velho && envio() && envio().track === mic(); }, 3000);
    await dormir(300);
    var firme = !pc.fechada && pc.connectionState === "connected" && __sim.pcs.length === n && vozes(false) === 0;
    var velhoDesligado = velho.readyState === "ended";
    var mostra = usando().indexOf(op.textContent) >= 0;
    return r(trocou && firme && velhoDesligado && mostra && __sim.microfonesVivos() === 1 && /No ar/.test(estado()),
      "trocou=" + trocou + " mesma_conexao=" + firme + " velho_desligado=" + velhoDesligado + " mostra=" + mostra + " " + resumo());
  };

  C.m23_escolhido_sumiu_usa_o_padrao = async function () {
    localStorage.setItem("leilao_microfone", "microfone-que-saiu");
    window.AudioFalar.escolher("microfone-que-saiu");
    if (!(await noAr())) return r(false, "ficou sem voz com o microfone escolhido fora: " + resumo());
    var avisa = $("microUsando").classList.contains("reserva") && /não foi achado/.test(usando());
    return r(avisa && __sim.microfonesVivos() === 1, "no_ar_pelo_padrao=true avisa_reserva=" + avisa + " usando='" + usando() + "'");
  };

  C.m24_troca_no_mudo_continua_muda = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    $("btnMudo").click();
    if (!(await listaComNomes())) return r(false, "sem lista");
    var velho = mic();
    escolherNaLista(2);
    var trocou = await esperar(function () { return mic() !== velho && envio().track === mic(); }, 3000);
    await dormir(100);
    return r(trocou && mic().enabled === false && /MUDO/.test(estado()),
      "trocou=" + trocou + " nova_faixa_muda=" + (mic().enabled === false) + " " + resumo());
  };

  C.m25_duas_trocas_seguidas_fica_a_ultima = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    if (!(await listaComNomes())) return r(false, "sem lista");
    __sim.atrasoTroca = 300;                         // a 1ª troca ainda no meio quando vem a 2ª
    var sel = $("microEscolha");
    var a = sel.options[1].value, b = sel.options[2].value;
    window.AudioFalar.escolher(a);
    var fim = await window.AudioFalar.escolher(b);
    await dormir(200);
    var faixa = envio().track;
    var certa = faixa.readyState === "live" && faixa.getSettings().deviceId === b;
    return r(certa && __sim.microfonesVivos() === 1 && window.AudioFalar.escolhido() === b,
      "no_ar_o_ultimo=" + certa + " faixa_viva=" + (faixa.readyState === "live") + " fim=" + JSON.stringify(fim) + " " + resumo());
  };

  C.m26_parar_no_meio_da_troca = async function () {
    if (!(await noAr())) return r(false, "não entrou no ar");
    if (!(await listaComNomes())) return r(false, "sem lista");
    __sim.atrasoTroca = 300;
    var troca = window.AudioFalar.escolher($("microEscolha").options[2].value);
    await dormir(20);
    $("btnMicrofone").click();                       // Parar com a troca a caminho
    await troca;
    await dormir(300);
    return r(__sim.microfonesVivos() === 0 && __sim.vivas(true).length === 0,
      "microfone_quente=" + __sim.microfonesVivos() + " " + resumo());
  };
})();
