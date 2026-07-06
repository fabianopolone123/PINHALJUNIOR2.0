/* =========================================================
   Cadastro de produto da Loja do Clube:
   - alternar entre produto simples e composto (grupos);
   - adicionar/remover grupos e opções (índices únicos nos names);
   - mostrar/ocultar a coluna "Estoque" conforme "Controlar estoque";
   - por grupo, o modo (escolha única / itens) controla a coluna "obrig.".
   JS puro, sem bibliotecas.
   ========================================================= */
(function () {
    "use strict";

    var form = document.getElementById("produtoLojaForm");
    if (!form) return;
    var lista = document.getElementById("loja-grupos");
    var grupoModelo = document.getElementById("loja-grupo-modelo");
    var varModelo = document.getElementById("loja-var-modelo");
    var addGrupoBtn = document.getElementById("lojaAddGrupo");

    function proxIndice(inputs) {
        var max = -1;
        Array.prototype.forEach.call(inputs, function (inp) {
            var n = parseInt(inp.value, 10);
            if (!isNaN(n) && n > max) max = n;
        });
        return max + 1;
    }

    function fragmento(html) {
        var temp = document.createElement("div");
        temp.innerHTML = html.trim();
        return temp.firstElementChild;
    }

    function conectarGrupo(grupo) {
        var modoSel = grupo.querySelector(".loja-grupo-modo");
        function aplicarModo() {
            grupo.dataset.modo = modoSel ? modoSel.value : "itens";
        }
        if (modoSel) {
            modoSel.addEventListener("change", aplicarModo);
        }
        aplicarModo();
    }

    // Adicionar opção (variação) dentro de um grupo.
    if (lista && varModelo) {
        lista.addEventListener("click", function (e) {
            var add = e.target.closest(".loja-add-var");
            if (!add) return;
            var gidx = add.dataset.gidx;
            var grupo = lista.querySelector('.loja-grupo[data-gidx="' + gidx + '"]');
            if (!grupo) return;
            var vars = grupo.querySelector(".loja-grupo-vars");
            var vidx = proxIndice(grupo.querySelectorAll('input[name="var_idx_' + gidx + '"]'));
            var html = varModelo.innerHTML.replace(/__G__/g, gidx).replace(/__V__/g, vidx);
            var nova = fragmento(html);
            if (nova) vars.appendChild(nova);
        });

        // Remover opção / remover grupo (delegação).
        lista.addEventListener("click", function (e) {
            var remVar = e.target.closest(".loja-var-remover");
            if (remVar) {
                var grupo = remVar.closest(".loja-grupo");
                var linhas = grupo.querySelectorAll(".loja-var-linha");
                var linha = remVar.closest(".loja-var-linha");
                if (linhas.length > 1) {
                    linha.remove();
                } else {
                    linha.querySelectorAll("input").forEach(function (c) {
                        if (c.type === "checkbox") c.checked = false;
                        else if (!/^var_idx_/.test(c.name) && !/^var_id_/.test(c.name)) c.value = "";
                    });
                }
                return;
            }
            var remGrupo = e.target.closest(".loja-grupo-remover");
            if (remGrupo) {
                var grupos = lista.querySelectorAll(".loja-grupo");
                if (grupos.length > 1) {
                    remGrupo.closest(".loja-grupo").remove();
                }
            }
        });
    }

    // Adicionar grupo.
    if (addGrupoBtn && grupoModelo && lista) {
        addGrupoBtn.addEventListener("click", function () {
            var gidx = proxIndice(lista.querySelectorAll('input[name="grupo_idx"]'));
            var html = grupoModelo.innerHTML.replace(/__G__/g, gidx);
            var novo = fragmento(html);
            if (!novo) return;
            lista.appendChild(novo);
            conectarGrupo(novo);
        });
    }

    Array.prototype.forEach.call(
        lista ? lista.querySelectorAll(".loja-grupo") : [],
        conectarGrupo
    );

    // Produto simples x composto.
    var chkComposto = form.querySelector('input[name="composto"]');
    function aplicarComposto() {
        form.classList.toggle("loja-simples", !(chkComposto && chkComposto.checked));
    }
    if (chkComposto) {
        chkComposto.addEventListener("change", aplicarComposto);
        aplicarComposto();
    }

    // Controlar estoque (mostra/oculta a coluna Estoque).
    var chkEstoque = form.querySelector('input[name="controla_estoque"]');
    function aplicarEstoque() {
        form.classList.toggle("oculta-estoque", !(chkEstoque && chkEstoque.checked));
    }
    if (chkEstoque) {
        chkEstoque.addEventListener("change", aplicarEstoque);
        aplicarEstoque();
    }
})();
