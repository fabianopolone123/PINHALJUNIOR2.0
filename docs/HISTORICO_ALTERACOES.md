# Histórico de Alterações

Registro cronológico das alterações do projeto Clube de Aventureiros Pinhal Júnior.

Formato de cada entrada:

```
## YYYY-MM-DD - Título da alteração

### Resumo
Descrição curta do que foi feito.

### Arquivos criados/alterados
- arquivo: explicação

### Decisões tomadas
- decisão técnica importante

### Pendências
- item ainda não feito
```

---

## 2026-07-11 - Mercado Pago: sinal visível de "credenciais salvas"

### Resumo
Na tela `/mercadopago/` (só Diretor), cada par de credenciais — **Teste** e **Produção** — ganhou um
**badge no cabeçalho** ("✓ Configurado" / "Não configurado"), no mesmo padrão do card de Modo. Além disso, os
campos que guardam segredo (Access Token e Assinatura do webhook, de teste e de produção) agora mostram os
**últimos 4 dígitos** do valor salvo (ex.: `••••••1234`), como já fazia a assinatura do webhook de teste.
Assim dá pra confirmar, batendo o olho, que as credenciais estão gravadas — sem precisar colar de novo. Nada
é exposto por inteiro e nenhum segredo é reenviado ao navegador.

### Arquivos alterados
- `core/models.py` (`MercadoPagoConfig`): propriedades novas `teste_configurado`/`prod_configurado` (bool pelo
  access token do par) e mascaradas `access_token_teste_mascarado`/`access_token_prod_mascarado`/
  `webhook_secret_teste_mascarado`/`webhook_secret_prod_mascarado` (reusam `_mascarar_segredo`).
- `templates/core/mercadopago.html`: badge de status em cada card (Teste/Produção) e troca do texto "Salvo
  (oculto por segurança)" por "Atual: **••••••1234** (salvo)" nos campos de segredo.

### Decisões tomadas
- Sinal de "configurado" = ter o **Access Token** do par (é a credencial obrigatória para cobrar).
- Sem migration: só propriedades derivadas, nenhum campo novo no banco.

### Pendências
- Operacionais (inalteradas): cadastrar a URL do webhook + secret no painel do MP e confirmar a taxa real em
  produção com um pagamento de verdade.

---

## 2026-07-11 - Revisão geral dos pagamentos (cartão) + fix do pagamento recusado

### Resumo
Revisão dos pagamentos (Pix e **cartão/Checkout Pro**) nas 3 áreas — **loja**, **mensalidades** e **eventos**.
Conclusão: a engine está consistente (cartão disponível nos 6 pontos: lojinha de evento, inscrição, Loja do
Clube, mensalidades do Diretor, mensalidades do responsável e acerto público; gross-up da taxa correto;
webhook valida assinatura e usa o MP como fonte da verdade; página genérica trata cartão com "confirmando +
polling"). **Corrigido um problema:** quando o cartão (ou Pix) era **recusado/cancelado**, a página de
pagamento ficava **girando para sempre** — o polling só reagia a "aprovado". Agora, em `rejeitado`/`cancelado`,
a tela para o spinner, mostra um aviso de **recusa** e um botão **"Voltar e tentar de novo"** (destino por tipo:
mensalidades/loja/página do evento/início).

### Arquivos alterados
- `static/js/pagamento_mp.js`: trata `rejeitado`/`cancelado` no polling (mostra recusa, para o spinner, toast).
- `templates/core/pagamento.html`: bloco `#pixRejeitado` (aviso de recusa + voltar).
- `core/views.py` (`pagamento_view`): novo `voltar_url` por tipo de pagamento.
- `core/tests.py`: teste `test_pagamento_rejeitado_mostra_recusa_sem_redirecionar`.

### Pendências (operacionais — do lado do usuário, não código)
- Cadastrar a **URL do webhook** + a **secret** no painel do Mercado Pago (produção) e confirmar a **taxa real**
  do cartão com uma venda de produção (ajustar `taxa_cartao_pct` se o "termômetro" na tela do MP ficar > 0).
- Deixar o parcelamento como **"Parcelado comprador"** no painel do MP (juros por conta do comprador).

---

## 2026-07-11 - Validação do cadastro usa o toast padrão do sistema

### Resumo
Ao clicar "Próximo"/"Finalizar" com campos obrigatórios vazios, o aviso agora é o **toast clássico** do
sistema (`window.mostrarToast`), com **uma notificação só** listando o(s) campo(s) que faltam (ex.:
"Preencha os campos obrigatórios: Usuário, Senha, Confirmar senha"; acima de 4, resume com "e mais N").
Removida a caixa `#avisoValidacao`.

### Arquivos alterados
- `static/js/wizard_validacao.js`: `mostrarAviso` monta uma mensagem e chama `window.mostrarToast(msg, "error")`.
- `templates/core/cadastro.html` e `cadastro_diretoria.html`: carregam `inicio.js` (expõe `mostrarToast`;
  CSS do toast já está em `base.css`) e removem a caixa de aviso.

---

## 2026-07-11 - Ajustes na ficha médica e no visual do Sim/Não

### Resumo
Refinamentos após revisão:
- **Doenças e Deficiência física:** a lista agora fica **sempre visível** (antes só aparecia depois do "Sim",
  e a pessoa não via as opções). Viraram o padrão das classes: mostra a lista + opção **"Nenhuma"** e exige
  ao menos uma marcação (doença/deficiência OU "Nenhuma"). Removidos os gates `teve_doencas`/`tem_deficiencia`.
- **Número da Carteira do SUS:** agora **obrigatório**.
- **Sim/Não:** deixado **menor** (padrão de todos os cadastros), sem o "quadrado azul" de foco ao clicar do
  mouse (mantido no teclado via `:focus-visible`), com destaque discreto da opção escolhida (`:has(input:checked)`).
- **Tipo sanguíneo:** confirmado que "Não sabe" já é uma das opções.

### Arquivos alterados
- `core/forms.py`: `FichaMedicaCamposMixin` — `sem_doencas`/`sem_deficiencia` (em vez dos gates), `cartao_sus`
  obrigatório, `clean()` exige ao menos uma marcação.
- `templates/core/_ficha_medica_campos.html`: listas visíveis + "Nenhuma".
- `static/css/cadastro.css`: `.simnao-opcao` menor + foco/checked ajustados.

---

## 2026-07-11 - Cadastros: obrigatoriedade dos campos + Sim/Não + validação com aviso

### Resumo
Revisão da obrigatoriedade dos campos nos dois cadastros (diretoria e aventureiro), com asterisco automático,
perguntas **Sim/Não obrigatórias** e **aviso listando os campos que faltam** ao tentar avançar/finalizar.
- **Ficha médica (ambos):** cada pergunta virou **Sim/Não obrigatório**; o detalhe ("qual/medicamentos") só é
  exigido quando "Sim". As listas de doenças e de deficiência ganharam um Sim/Não obrigatório na frente
  (`teve_doencas`/`tem_deficiencia`); se "Sim", exige marcar ao menos um; tipo sanguíneo obrigatório.
- **Diretoria:** obrigatórios foto, nacionalidade, data nasc., igreja, distrito, RG, estado civil, e-mail,
  endereço completo e escolaridade; "Tem filhos?" Sim/Não (+ qtd se Sim); cônjuge obrigatório se casado/união.
- **Aventureiro:** obrigatórios foto, sexo, data nasc., colégio/série/ano, tamanho da camiseta, endereço
  completo, grau de parentesco e e-mail do responsável; **Bolsa Família** vira Sim/Não; **classes** com opção
  **"Nenhuma"** (exige ao menos uma marcação); **pai/mãe** com "Tem os dados? Sim/Não" (se Sim, todos os campos
  daquele responsável obrigatórios); termo de imagem exige nacionalidade do menor e nacionalidade/estado civil/
  RG do responsável. Cidade da inscrição segue opcional.
- **Reaproveitamento:** o termo de imagem agora é **pré-preenchido** com os dados já digitados (nome do menor,
  nome/CPF/endereço do responsável) — sem redigitar.

### Arquivos criados/alterados
- `core/forms.py`: helper `campo_sim_nao` + `FichaMedicaCamposMixin` (compartilhado pelas duas fichas);
  obrigatórios e `clean()` condicionais em `MembroDiretoriaForm`, `AventureiroForm`, `AutorizacaoImagemForm`.
- Templates: `_campo_simnao.html` (novo), `_ficha_medica_campos.html` (novo, corpo da ficha compartilhado),
  ajustes em `cadastro.html` e `cadastro_diretoria.html` (caixa `#avisoValidacao`, Sim/Não, classes, pai/mãe).
- Estáticos: `static/js/wizard_validacao.js` (novo, valida e lista faltantes), `cadastro.js` e
  `cadastro_diretoria.js` (condicionais por grupo de radios `data-depende-nome`, validação por etapa/envio,
  reaproveitamento do termo de imagem); estilos `.campo-simnao`/`.simnao-*` em `cadastro.css`.
- Removido `_campo_check_livre.html` (não usado). **Sem migration** (obrigatoriedade é no form).

### Decisões (confirmadas com o Fabiano)
- Ficha médica "tudo com Sim/Não"; pai/mãe "todos os campos" quando tem os dados; "endereço completo";
  classes com opção "Nenhuma". Foto obrigatória (atenção: em erro de servidor o arquivo precisa ser
  reanexado — a validação no cliente evita isso na maioria dos casos).

---

## 2026-07-11 - Comandos de migração: diretoria + assinaturas antigas

### Resumo
Dois comandos de importação (rodam **localmente**, lendo o ZIP de exportação git-ignored; depois db/media
sincronizam para o VPS). Ambos idempotentes e com `--dry-run`.
- **`importar_diretoria`**: cria `MembroDiretoria` (+ `FichaMedicaDiretoria` + foto) por integrante, vincula ao
  perfil **Diretoria** e trata as **mesclagens** (quem tem diretoria e responsável em logins diferentes é
  anexado ao login que tem o aventureiro → 1 login com 2 perfis). Cria o `User` (preservando username + hash da
  senha) para os só-diretoria que ainda não existiam. Pula teste e Fabiano.
- **`importar_assinaturas`**: importa as assinaturas desenhadas antigas casando **por CPF**:
  `aventureiroficha` → `AssinaturaDocumento` (inscrição/declaração médica/imagem);
  `diretoriaficha` → `AssinaturaDocumentoDiretoria` (compromisso/imagem + **declaração médica = cópia do
  compromisso**, pois o antigo não tinha). As imagens vêm dos arquivos de assinatura do ZIP.

### Resultado local (validado)
- Diretoria: **10 membros** (6 logins novos criados; 3 mesclagens; Lediani no login dela); 10 fotos, 10 fichas.
- Assinaturas: **96** de aventureiro (32 fichas × 3) e **21** de diretoria (7 × 3). Cobertura: 32/46
  aventureiros e 7/10 membros (os demais não tinham ficha assinada no antigo).

### Arquivos criados/alterados
- `core/management/commands/importar_diretoria.py`, `core/management/commands/importar_assinaturas.py`.
- `.gitignore`: ignora `migracao_mesclagem.json` (config local com logins reais — não versionar).

### Decisões
- A config de **skip/mesclagem** (com logins/nomes reais) fica em `migracao_mesclagem.json` **local**
  (git-ignored); o comando é genérico. Sem o arquivo, só pula o registro de teste e não faz mesclagens.
- Migração roda local; o db/media resultantes é que vão para o VPS (padrão já usado no projeto).

---

## 2026-07-11 - Levantamento da migração da diretoria (doc local)

### Resumo
Análise **somente leitura** dos dados do sistema antigo (zip de exportação) para planejar a migração da
diretoria: quem é diretoria, quem é só-diretoria e quem tem duas contas (diretoria + responsável) e precisa
de **mesclagem** (um login com 2 perfis). Resultado registrado em `docs/MIGRACAO_DIRETORIA.md`.

### Arquivos alterados
- `docs/MIGRACAO_DIRETORIA.md`: **novo, mantido LOCAL** (contém nomes/logins reais da diretoria).
- `.gitignore`: ignora `docs/MIGRACAO_DIRETORIA.md` (não versionar dados pessoais).

### Decisões
- Não versionar o levantamento (privacidade). Nenhum dado/código alterado — só análise + doc local.

### Atualização (mesmo dia)
- Investigado o **formato das assinaturas antigas** (só leitura): NÃO foram migradas; existem no export como
  base64 por documento em `aventureiroficha`/`diretoriaficha` (batem 1:1 com o novo) + arquivos PNG únicos.
  Mapeamento para `AssinaturaDocumento`/`AssinaturaDocumentoDiretoria` registrado no doc local.
- Decisão: aventureiro tem 3 assinaturas (inscrição, declaração médica, imagem) — a ficha médica entra sob a
  declaração médica. Diretoria (antigo) só tinha 2 (compromisso + imagem) → na migração, a declaração médica
  da diretoria recebe uma **cópia** da assinatura do compromisso, para ficar com as 3.

---

## 2026-07-11 - Diretor atribui o papel dos integrantes da diretoria

### Resumo
Nova tela (Diretor) para **atribuir o papel** de cada integrante da diretoria: Diretor, Secretário,
Tesoureiro, Professor ou "Diretoria (sem papel definido)". A atribuição ajusta os **grupos** do usuário
(remove os demais papéis e aplica o escolhido), então o perfil/menu passa a refletir o papel. Acessível por
um botão **"Gerenciar diretoria (papéis)"** na tela Usuários.

### Arquivos alterados
- `core/views.py`: `diretoria_equipe_view` (lista) e `diretoria_papel_view` (POST); constantes
  `PAPEIS_DIRETORIA_OPCOES`/`GRUPOS_PAPEL_DIRETORIA` e helper `_papel_atual_diretoria`.
- `core/urls.py`: `usuarios/diretoria/` e `usuarios/diretoria/<id>/papel/`.
- `templates/core/diretoria_equipe.html`: nova tela (lista + seletor de papel por integrante).
- `templates/core/usuarios.html`: botão "Gerenciar diretoria (papéis)".

### Decisões tomadas
- O papel é guardado como **grupo** do Django (fonte da verdade dos perfis). Atribuir um papel específico
  **remove** o grupo genérico "Diretoria" e os demais papéis, deixando só o escolhido.
- Atenção: atribuir "Diretor" concede acesso total (é o propósito do controle).

### Pendências
- Módulo de permissões por botão (fino) segue como futuro; hoje o acesso é por perfil.

---

## 2026-07-11 - "Meus Dados" mostra os dados do membro da diretoria

### Resumo
Quando um voluntário/integrante da diretoria (ex.: Secretário) acessa "Meus Dados", agora aparece um
**card "Diretoria"** com os dados do cadastro dele: identificação (nome, nacionalidade, CPF, RG, nascimento,
estado civil, cônjuge, filhos, igreja, distrito, escolaridade), contato, endereço e um resumo da ficha
médica. Mostra também o **papel** (Diretor/Secretário/Tesoureiro/Professor ou "Diretoria (papel a definir)").

### Arquivos alterados
- `core/views.py`: `inicio_view` carrega o `MembroDiretoria` do usuário (foto/idade/iniciais + `_preparar_ficha`)
  e o papel via novo helper `_papel_diretoria`; contexto `membro_diretoria`.
- `templates/core/inicio.html`: card "Diretoria" (painel expansível), entre o card do responsável e a lista
  de aventureiros.
- `static/css/inicio.css`: `.resp-avatar-img` (foto redonda) e `.painel-corpo .bloco-rotulo`.

### Pendências
- Próximo: UI do Diretor para atribuir o papel específico da diretoria.

---

## 2026-07-11 - Diretoria: assinatura desenhada dos 3 documentos (substitui os checkboxes)

### Resumo
No cadastro de diretoria, os aceites por checkbox (compromisso de voluntário, declaração médica e
autorização de imagem) viraram **assinatura desenhada** (dedo/mouse), no mesmo padrão do cadastro de
aventureiro. Cada documento tem a sua assinatura própria, gravada como imagem PNG + snapshot do texto do
termo preenchido. Responsividade mobile verificada (Chrome headless, 490px): etapa de Termos e modal de
assinatura OK. Corrigido, de quebra, um bug cosmético do preview de assinatura (imagem quebrada no estado
vazio) que afetava também o cadastro de aventureiro.

### Arquivos alterados
- `core/models.py`: `AssinaturaDocumentoBase` (molde abstrato) + `AssinaturaDocumento` (aventureiro, refatorado
  para herdar da base, tabela inalterada) + novo `AssinaturaDocumentoDiretoria` (membro + documento).
- `core/migrations/0042_...`: cria AssinaturaDocumentoDiretoria.
- `core/termos.py`: textos dos 3 documentos da diretoria (`montar_texto_diretoria`) — compromisso, declaração
  médica e autorização de imagem do adulto.
- `core/views.py`: `cadastro_diretoria_view` valida e grava as 3 assinaturas (`_validar_aceites_diretoria`
  agora exige assinatura; `_salvar_assinaturas_diretoria`); reusa `_decode_signature`.
- `core/admin.py`: registra `AssinaturaDocumentoDiretoria`.
- `templates/core/cadastro_diretoria.html`: blocos `_assinatura_doc.html` + modal de assinatura + `assinatura.js`.
- `static/js/cadastro_diretoria.js`: validação por assinatura (não mais checkbox) + revisão "Assinado".
- `static/css/cadastro.css`: `.assinatura-doc-preview img[hidden] { display:none }` (fix da imagem quebrada).
- Removido `templates/core/_campo_check_livre.html` (não é mais usado).

### Pendências
- Próximos: exibir o membro da diretoria em "Meus Dados"/"Usuários" e a UI do Diretor para atribuir o papel.

---

## 2026-07-11 - .gitignore: ignora PDFs soltos na raiz

### Resumo
Adiciona `/*.pdf` ao `.gitignore` para não versionar documentos de referência escaneados soltos na raiz
(ex.: `Fichas-Secretaria-Padrão (1).pdf`), seguindo a regra de "arquivos soltos na raiz não são versionados".

### Arquivos alterados
- `.gitignore`: novo padrão `/*.pdf` (PDFs no diretório-raiz).

---

## 2026-07-11 - Cadastro de Diretoria (Compromisso para Voluntários) + tela de escolha + 2 perfis

### Resumo
Implementado o **cadastro de diretoria** (voluntários), o novo ponto de entrada do "Cadastre-se"
(escolha de tipo) e a **alternância de 2 perfis** (Diretoria + Responsável). Fluxos:
- **Tela "Cadastre-se"** (`/cadastro/`) agora oferece **3 opções**: Aventureiro, Diretoria,
  Diretoria + Aventureiro. (Antes ia direto ao cadastro de aventureiro.)
- **Cadastro de diretoria** (`/cadastro/diretoria/`): wizard com Conta, Identificação (com cônjuge
  condicional ao estado civil e qtd. de filhos), Contato/Endereço, **ficha médica completa** (igual à do
  aventureiro), Escolaridade e **3 termos** (compromisso de voluntário, declaração médica e **autorização
  de imagem do adulto**, adaptada da versão do menor). Cria a conta + `MembroDiretoria` + `FichaMedicaDiretoria`,
  adiciona ao perfil **Diretoria** e loga.
- **Diretoria + Aventureiro** (`?com_aventureiro=1`): após a diretoria, emenda no cadastro de aventureiro
  (pré-preenchendo o responsável com os dados da diretoria) → 1 login com **2 perfis**.

### Arquivos criados/alterados
- `core/models.py`: `FichaMedicaBase` (abstract, campos médicos compartilhados); `FichaMedica` passa a herdar
  dela (tabela inalterada); novos `MembroDiretoria` e `FichaMedicaDiretoria`; choices `ESTADO_CIVIL`/`ESCOLARIDADE`.
- `core/migrations/0041_...`: cria MembroDiretoria e FichaMedicaDiretoria (FichaMedica intacta).
- `core/menus.py`: novo perfil **Diretoria** (ORDEM/ícone/acesso); `perfil_do_usuario`/`perfis_do_usuario`
  ajustados — "Responsável" é **implícito** (quem tem aventureiro não-demo) e convive com "Diretoria"
  (habilita a alternância). `configurar_perfis` cria o grupo "Diretoria".
- `core/forms.py`: `MembroDiretoriaForm` e `FichaMedicaDiretoriaForm`.
- `core/views.py`: `cadastro_view` vira a **tela de escolha**; `cadastro_aventureiro_view` (fluxo antigo);
  `cadastro_diretoria_view` (+ `_validar_aceites_diretoria`); prefill do responsável a partir da diretoria
  (`_dados_diretoria_para_responsavel`/`_dados_anteriores_ou_diretoria`); `cadastro_sucesso_view` com `tipo`.
- `core/urls.py`: rotas `cadastro_aventureiro` e `cadastro_diretoria`.
- `core/admin.py`: registra `MembroDiretoria` e `FichaMedicaDiretoria`.
- Templates: `cadastro_escolha.html`, `cadastro_diretoria.html`, `_campo_check_livre.html`,
  `cadastro_sucesso.html` (variante diretoria). Estáticos: `static/js/cadastro_diretoria.js`,
  estilos `.escolha-*` em `static/css/cadastro.css`.

### Decisões tomadas
- Ficha médica da diretoria = **completa** (reusa o molde abstrato, sem duplicar campos).
- Papel específico (Diretor/Secretário/Tesoureiro/Professor) **não** é escolhido no cadastro — a pessoa entra
  como "Diretoria" genérica e o Diretor define depois (a UI de atribuição fica para o próximo passo).
- Assinatura desenhada dos termos fica para depois; por ora, **aceite por checkbox** com o texto do termo.
- Textos dos termos = fiéis ao PDF oficial DSA: o "Compromisso para Voluntários" é o formulário + um aceite
  curto; a autorização de imagem é a da pág. 5 adaptada para maior de idade.

### Pendências
- **Próximo passo:** exibir os dados do membro da diretoria em "Meus Dados"/"Usuários" e a **UI do Diretor
  para atribuir o papel** específico. Assinatura desenhada dos termos da diretoria. Substituir o texto do
  compromisso pelo oficial, se/quando o clube fornecer um texto de juramento formal.

---

## 2026-07-11 - Ficha médica: 6 doenças e bloco de deficiência física (alinha ao formulário oficial DSA)

### Resumo
Completa a **Ficha Médica** para bater com o formulário oficial da DSA (PDF `Fichas-Secretaria-Padrão`).
Adicionadas as **6 doenças** que faltavam na lista "Já teve ou tem" — **Varíola, Coqueluche, Difteria,
Caxumba, Rinite e Bronquite** — e um **bloco novo "Deficiência física"** (Cadeirante, Visual, Auditiva e
Fala/mudez), que não existia. O telefone fixo de pai/mãe do formulário oficial foi deliberadamente deixado
de fora (decisão do Fabiano).

### Arquivos criados/alterados
- `core/models.py`: `FichaMedica` ganhou 6 BooleanField de doença (após `tetano`) e 4 BooleanField de
  deficiência física (`deficiente_cadeirante/_visual/_auditivo/_fala`, após as alergias).
- `core/migrations/0040_...`: migration dos 10 campos novos (todos `default=False`).
- `core/views.py` (`_preparar_ficha`): as 6 doenças entram em `doencas_lista`; nova `deficiencias_lista`
  para exibição.
- `templates/core/cadastro.html`: 6 checkboxes novos na etapa da ficha médica + bloco "Deficiência física".
- `templates/core/_aventureiro_detalhe.html`: linha "Deficiência física" na seção Ficha médica
  (usada em "Meus Dados" e no modal de Usuários).

### Decisões tomadas
- `FichaMedicaForm` usa `exclude=["aventureiro"]`, então os campos novos entram no form automaticamente
  (sem alterar o form). Admin idem (só `list_display`).
- Campos `default=False` → `criar_dados_teste`/`importar_migracao` não precisam mudar.
- Telefone fixo de pai/mãe **não** foi adicionado (fora do escopo pedido).

### Pendências
- Próximo passo combinado: iniciar o **cadastro de diretoria** (ficha "Compromisso para Voluntários",
  pág. 7 do PDF oficial). Especialidades (págs. 8-10) seguem sem módulo.

---

## 2026-07-07 - Perfil Responsável: Loja, Mensalidades e Presença próprias + registro central de menu

### Resumo
Início do trabalho nos **perfis**. Criado o **registro central de menu/acesso por perfil**
(`core/menus.py`) — fonte única da verdade de "quem vê/acessa o quê", pronta para o futuro módulo de
permissões encaixar sem reescrever menu nem views. O menu (`_menu.html`) deixou de ser chumbado
(`{% if is_diretor %}`) e passa a **iterar `menu_itens`** (vindo do context processor). O **perfil
Responsável** ganhou telas próprias, separadas das do Diretor, na **mesma URL** (a view ramifica por
perfil):
- **Loja** (`loja_view`): só a **vitrine** (comprar) + aba **"Meus pedidos"** (acompanhar). Sem
  Gerenciar/Vendas. Vitrine extraída para o parcial `_loja_vitrine.html` (reusado pelo Diretor e pelo
  responsável). Pagamento igual (Pix/cartão).
- **Mensalidades** (`mensalidades_view`): **resumo** (pago no ano × em aberto), lista das **em aberto
  vencidas** (mês atual + atrasados) para **selecionar e pagar** (uma cobrança Pix/cartão via
  `minhas_mensalidades_pagar`), botão **"adiantar meses"** (`?frente=1` mostra os futuros) e **texto de
  apelo** configurável pelo Diretor.
- **Presença** (`presenca_view`): **relatório só-leitura** dos próprios filhos — por criança, em quantos
  eventos com chamada esteve/faltou e em quais (o responsável **não marca** presença).

O Diretor ganhou, na aba **Cobranças**, um 2º campo: a **mensagem de apelo** (`ConfigMensalidade.mensagem_apelo`,
migration **0038**), exibida ao responsável na tela de Mensalidades dele.

### Arquivos criados/alterados
- `core/menus.py` (novo): `ITENS_MENU`, `ACESSO_PADRAO`, `perfil_do_usuario`, `itens_menu_para`,
  `pode_acessar`. Comentário marca o "encaixe" do futuro módulo de permissões (`_ids_liberados`).
- `core/context_processors.py`: expõe `menu_itens` e `perfil_atual`.
- `templates/core/_menu.html`: itera `menu_itens` (mantém o caso do operador externo e "Operar (PDV)").
- `core/models.py`: `ConfigMensalidade.mensagem_apelo` + `MENSAGEM_APELO_PADRAO`.
- `core/migrations/0038_configmensalidade_mensagem_apelo.py` (novo).
- `core/views.py`: `loja_view`/`mensalidades_view`/`presenca_view` passam a `@login_required` e ramificam
  por perfil; helpers `_loja_responsavel`, `_mensalidades_responsavel`, `_mensalidades_familia_abertas`,
  `_presenca_responsavel`; view `minhas_mensalidades_pagar_view`; `mensalidade_cobranca_config_view`
  salva também a mensagem de apelo.
- `core/urls.py`: rota `mensalidades/pagar-selecionadas/` (`minhas_mensalidades_pagar`).
- Templates novos: `_loja_vitrine.html`, `loja_responsavel.html`, `mensalidades_responsavel.html`,
  `presenca_responsavel.html`. `mensalidades.html`: 2ª textarea (apelo) na aba Cobranças.
- CSS: blocos do responsável em `static/css/mensalidades.css` e `static/css/presenca.css`.
- `core/tests.py`: `PerfilResponsavelTests` (menu por perfil, loja/mensalidades/presença do responsável,
  pagamento escopo-família e bloqueio de família alheia, responsável não marca presença) + apelo salvo.

### Decisões tomadas
- **Mesma URL, view ramifica por perfil** (uma entrada de menu por item), em vez de URLs separadas —
  menu simples e consistente.
- Gating por perfil resolvido em **um único lugar** (`core/menus.py`); o Diretor continua vendo tudo.
- Segurança do pagamento: `minhas_mensalidades_pagar` filtra por `aventureiro__usuario=request.user` —
  ninguém paga mensalidade de outra família.
- Presença do responsável é **só-leitura** (a tela do Diretor, que marca qualquer criança, segue só dele).

### Pendências
- Módulo de permissões (liga/desliga por perfil/usuário) — encaixa em `core/menus.py` sem reescrever.
- Demais perfis (Professor, Tesoureiro, Secretário) ainda sem telas.

---

## 2026-07-07 - Seletor de perfil vira cartão do usuário no topo do menu

### Resumo
A pedido, o seletor de perfil saiu da lista do menu e virou o **cartão do usuário no topo** (logo abaixo do
título "Clube de Aventureiros Pinhal Júnior"): mostra o **nome** + o **perfil selecionado** (chip verde) e,
quando o usuário tem 2+ perfis, é um **dropdown** (`<details>` nativo) que abre a lista para trocar de perfil.
O **nome do usuário foi removido do rodapé** (lá ficou só o botão Sair + copyright). Ocupa menos espaço no menu
e deixa claro "em que perfil estou".

### Arquivos alterados
- `templates/core/_menu.html`: cartão `perfil-box` (dropdown `<details>` quando `perfis_disponiveis`, senão
  estático) no topo; removida a seção "Ver como" que ficava no fim.
- `templates/core/*.html` (26 arquivos): removido o bloco `barra-usuario` do rodapé (nome subiu para o menu).
- `static/css/inicio.css`: estilos `.perfil-box`/`.perfil-atual`/`.perfil-lista`/`.perfil-opcao` (substituem
  os antigos `.menu-perfil*`).

### Decisões
- Dropdown com `<details>` nativo (sem JS): o auto-fechar do `inicio.js` é escopado a `.conteudo-interno`, então
  não interfere no menu; clicar num perfil já navega (fecha sozinho).

---

## 2026-07-07 - Seletor de perfil ("Ver como") + dados fictícios (demo) do Fabiano

### Resumo
Generaliza o preview do Diretor para um **seletor de perfil** de verdade e permite o Fabiano testar o perfil
Responsável **com dados**, sem poluir o clube.
- **Seletor "Ver como"** no menu: lista os perfis que o usuário **possui de fato** (grupos nativos) e troca a
  visão (menu + telas) ao clicar. Só aparece com 2+ perfis. Substitui o botão binário "Ver como responsável".
- **Fabiano ganha os 5 perfis** (Diretor, Responsável, Professor, Tesoureiro, Secretário). Professor/Tesoureiro/
  Secretário ainda **sem telas** → por ora só "Meus Dados" (placeholder no `ACESSO_PADRAO`).
- **Dados fictícios isolados:** flag **`demo`** em `Aventureiro` e `Evento` (migration **0039**). Tudo `demo=True`
  fica **fora de todas as contagens do clube** (Usuários, Mensalidades e Presença do Diretor, Financeiro, menu de
  eventos). A presença do responsável **casa a demo-ness** (família fictícia só enxerga eventos fictícios; a real,
  só reais — os demos não viram "falta" para ninguém).
- **Comando `dados_demo_fabiano`** (idempotente): dá os perfis ao Fabiano e cria **2 aventureiros fictícios**
  (foto/ficha/autorização), suas **mensalidades** (2 pagas + o resto em aberto/atrasado) e **2 eventos fictícios**
  com **presença** — para as telas do responsável aparecerem cheias.

### Arquivos alterados
- `core/menus.py`: perfis Professor/Tesoureiro/Secretário + `ORDEM_PERFIS`/`ICONE_PERFIL`; `PERFIL_ATIVO_KEY`,
  `perfis_do_usuario`, `perfil_efetivo` (via seletor), `pode_trocar_perfil`.
- `core/context_processors.py`: `perfis_disponiveis` (seletor) + menu do perfil efetivo; `_eventos_menu` exclui demo.
- `core/views.py`: `preview_responsavel_view` → `trocar_perfil_view`; **exclusão de `demo`** em usuarios,
  mensalidades (lista/totais/taxa), reajustar, gerar, cobranças, financeiro, presença (marcar/selecionar),
  recuperação por CPF, eventos e `_presenca_responsavel` (casa demo-ness).
- `core/models.py`: `Aventureiro.demo`, `Evento.demo`. `core/migrations/0039_*`.
- `core/urls.py`: `trocar-perfil/` (era `preview-responsavel/`). `templates/core/_menu.html`: seletor.
- `static/css/inicio.css`: estilo `.menu-perfil`. `core/management/commands/dados_demo_fabiano.py` (novo).
- `core/tests.py`: `DemoIsolamentoTests` + testes do seletor (substituem os de preview).

### Como usar
`python manage.py dados_demo_fabiano` → entrar como Fabiano → menu **"Ver como" → Responsável**.

---

## 2026-07-07 - Preview do Diretor: "Ver como responsável" (substituído pelo seletor de perfil)

### Resumo
Para o Diretor testar/conferir a visão do responsável sem outra conta, o menu do Diretor ganhou o botão
**"Ver como responsável"** (e **"Voltar ao Diretor"**). Liga/desliga uma flag na sessão (`PREVIEW_KEY`);
enquanto ligada, o menu e as telas Loja/Mensalidades/Presença se comportam como responsável.

### Arquivos alterados
- `core/menus.py`: `PREVIEW_KEY`, `perfil_efetivo(request)`, `atua_como_responsavel(request)`,
  `itens_menu_do_perfil(perfil)`.
- `core/context_processors.py`: menu usa `perfil_efetivo`; expõe `preview_responsavel`.
- `core/views.py`: `loja_view`/`mensalidades_view`/`presenca_view` passam a ramificar por
  `atua_como_responsavel`; nova `preview_responsavel_view` (só Diretor, POST).
- `core/urls.py`: rota `preview-responsavel/`. `templates/core/_menu.html`: botão (form POST).
- `static/css/inicio.css`: estilo `.menu-preview`. `core/tests.py`: 2 testes de preview.

### Observação
A conta do Diretor (Fabiano) não tem aventureiros, então em preview as telas aparecem **vazias**. Para ver
**com dados**, logar como um responsável real (ex.: `teste_responsavel` / `123456`).

---

## 2026-07-07 - Cobranças: busca também por aventureiro

### Resumo
A busca da aba Cobranças (que só achava por responsável) agora acha **também pelo nome do aventureiro**: o
`data-busca` de cada família passou a incluir o nome do responsável **e** os nomes das crianças. Placeholder
atualizado para "Buscar por responsável ou aventureiro…".

### Arquivos alterados
- `templates/core/mensalidades.html`: `data-busca` inclui `{{ f.resp_nome }}` + os `c.nome` das crianças;
  placeholder do campo de busca.

---

## 2026-07-07 - Cobranças: detalhe por criança + só cobra meses já vencidos

### Resumo
Dois ajustes: **(1)** cada família na aba Cobranças (e no cálculo) agora mostra o **detalhe por criança** —
nome do aventureiro, **valor em aberto dele** e os **meses**; **(2)** a cobrança e a página de acerto passam a
considerar **apenas meses já vencidos** (competência ≤ mês atual): cobra o **mês atual e os anteriores** em
aberto, **nunca meses à frente** (as mensalidades do ano inteiro já nascem geradas).

### Arquivos alterados
- `core/views.py`: `_cobrancas_familias` monta `criancas` (nome/total/meses por aventureiro); novo
  `_q_mens_vencidas()` (competência ≤ hoje) aplicado em `_mensalidades_abertas_familia` (acerto) e em
  `_cobrancas_familias` (aba Cobranças). A cobrança por aventureiro do Diretor (modal) segue manual (ele escolhe).
- `templates/core/mensalidades.html`: bloco por criança em cada família. `static/css/mensalidades.css`: estilos.
- `core/tests.py`: render com 2 crianças; `test_acerto_ignora_meses_futuros`; setups usam o mês atual.

---

## 2026-07-07 - Cobranças: busca, envio em lote com delay/progresso/cancelar, aviso como toast

### Resumo
Refinos na aba Cobranças, a pedido: **(1)** campo de **busca** por responsável (filtra ao digitar); **(2)**
**"Enviar a todos"** agora é **sequencial pelo navegador**, com **10s entre cada envio**, **barra de progresso**
e **botão cancelar** (evita bloqueio por spam do WhatsApp); **(3)** o aviso "configure o WhatsApp" **deixou de
ser um banner fixo** e passa a aparecer como **toast** (notificação lateral) só **quando se tenta enviar** (vem
da resposta do endpoint).

### Detalhes
- O lote envia **uma família por vez** (POST individual), atualiza a barra e o status inline, e respeita o filtro
  "só quem não recebeu este mês". Cancelar interrompe entre um envio e outro; se o WhatsApp não estiver
  configurado, o lote aborta no 1º retorno com o toast.
- Botões não ficam mais desabilitados por "WhatsApp não configurado" (só por família sem número) — o toast
  orienta ao tentar.

### Arquivos alterados
- `templates/core/mensalidades.html`: campo de busca, bloco de progresso (barra + cancelar), `data-*` nos itens
  (busca/cobrado/tem-numero); removido o banner fixo.
- `static/js/mensalidade_cobranca.js`: busca ao vivo; envio individual (atualiza inline); **lote com 10s +
  progresso + cancelar** (estado compartilhado, sem duplo encerramento).
- `static/css/mensalidades.css`: estilos da busca e da barra de progresso.

---

## 2026-07-07 - Cobrança de mensalidades (parte 2): aba "Cobranças" (WhatsApp)

### Resumo
Nova aba **"Cobranças"** no módulo Mensalidades (ao lado de Resumo/Aventureiros): dispara a **cobrança das
mensalidades por WhatsApp** (reusa a W-API), com **mensagem personalizável**, **envio a um ou a todos**,
**histórico do mês** e **filtro "só quem não recebeu este mês"**. A mensagem leva o **link de acerto** (parte 1).

### Como funciona
- **Mensagem configurável** (`ConfigMensalidade.mensagem_cobranca`) com marcadores `{nome}`, `{itens}`, `{total}`,
  `{link}` — interpolados por família no envio. Padrão em `MENSAGEM_COBRANCA_PADRAO`.
- **Agrupada por família** (conta): lista as famílias com mensalidade em aberto, com responsável, total, WhatsApp
  principal (reusa `_whatsapp_principal`), status do mês (📤 cobrado Nx / ⏳ não) e o link (`token_acerto`).
- **Envio**: `mensalidade_cobranca_enviar_view` (JSON) manda a um (`usuario_id`) ou a todos, com filtro
  `so_nao_enviados`; cada envio grava um `CobrancaEnviada` (mês/ano/quem) para o histórico e o filtro.
- Sem WhatsApp configurado (W-API) ou sem número da família → o envio avisa/pula.

### Arquivos criados/alterados
- `core/models.py`: `ConfigMensalidade.mensagem_cobranca` + `MENSAGEM_COBRANCA_PADRAO`; model `CobrancaEnviada`
  (histórico do mês). Migration **0037**.
- `core/views.py`: `_cobrancas_familias`, `_montar_mensagem_cobranca`, `_moeda_txt`,
  `mensalidade_cobranca_config_view` e `mensalidade_cobranca_enviar_view`; contexto da aba em `mensalidades_view`.
- `core/urls.py`: `mensalidades/cobrancas/config/` e `.../enviar/`.
- `templates/core/mensalidades.html`: aba/painel **Cobranças** (editor da mensagem + lista + enviar a um/todos +
  filtro). `static/js/mensalidade_cobranca.js` (envio AJAX). `static/css/mensalidades.css` (estilos).
- `core/tests.py`: `CobrancaWhatsappTests` (envio registra histórico; render da aba).

### Observações
- Envio "a todos" é síncrono (um POST por família na W-API); para o porte do clube, ok.
- Fecha a feature de cobrança (parte 1 = página de acerto; parte 2 = aba Cobranças).

---

## 2026-07-07 - Cobrança de mensalidades (parte 1): página pública de acerto (link do WhatsApp)

### Resumo
Primeira parte do sistema de cobrança de mensalidades: a **página pública de acerto** — o destino do link que
vai na mensagem de cobrança. Sem login: um **token fixo e secreto por família** (conta) abre uma página que
mostra as **mensalidades em aberto de todos os aventureiros da família** e permite **pagar na hora** (Pix ou
cartão), reusando a engine. O **Pix é gerado só no clique** (nada "vence" se a pessoa demorar a abrir o link) e a
página sempre reflete o que está em aberto **no momento**. É, na prática, a "visualização do responsável" numa
versão enxuta e pública.

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario.token_acerto` (+ `get_token_acerto()`; uuid fixo). Migration **0036**.
- `core/views.py`: `acerto_view` (pública, por token) e `acerto_cobrar_view` (pública; cobra TODAS as
  mensalidades em aberto da família, Pix/cartão) + helpers `_mensalidades_abertas_familia`/`_responsavel_da_familia`.
- `core/urls.py`: `/acerto/<token>/` e `/acerto/<token>/cobrar/`.
- `templates/core/acerto.html`: **nova** página pública (em aberto + total + pagar; "tudo em dia"/"link inválido").
- `core/tests.py`: `AcertoPublicoTests` (mostra em aberto, token inválido, cobrar Pix → simular → quita a família).

### Próximo (parte 2)
- Aba **"Cobranças"** no Mensalidades: template de mensagem configurável (com `{nome}`/`{itens}`/`{total}`/`{link}`),
  envio pelo WhatsApp (todos/um a um), **histórico por mês** de quem já recebeu e **filtro** "só quem não recebeu".

---

## 2026-07-07 - Pagamentos Mercado Pago (Etapa 6, parte 2): cartão nos 4 pontos

### Resumo
O cartão (Checkout Pro + gross-up da taxa + parcelado-comprador) foi replicado nos demais pontos: **Loja do
Clube**, **Inscrição de evento** e **Mensalidades**. Agora os quatro pontos aceitam **Pix e cartão**.

### Como ficou por ponto
- **Loja do Clube** (`loja_pagamento_view`): ramo de cartão espelhando o do Pix (já tinha o seletor Pix/Cartão).
- **Inscrição** (`evento_inscrever_view` + `evento_inscrever.html`): novo **seletor Pix/Cartão** no formulário
  (só quando o MP está configurado); cartão → Checkout Pro. Grátis segue criando na hora.
- **Mensalidades** (`mensalidade_cobrar_view` + modal em `mensalidades.html`): **seletor Pix/Cartão** no modal de
  cobrança; cartão → Checkout Pro (baixa múltipla no webhook, igual ao Pix).

### Arquivos alterados
- `core/views.py`: ramos de cartão em `loja_pagamento_view`, `evento_inscrever_view` e `mensalidade_cobrar_view`
  (+ `mp_configurado` no contexto da inscrição).
- `templates/core/`: seletor de forma em `evento_inscrever.html` e no modal de `mensalidades.html`.
- `core/tests.py`: cartão gera preferência em mensalidade e inscrição (sem criar/quitar antes de aprovar).

### Pendências
- No painel do MP, deixar o parcelamento como **"Parcelado comprador"** (config da conta).
- (Opcional) checkout transparente no site, se um dia não quiserem o redirecionamento.

---

## 2026-07-07 - Pagamentos Mercado Pago (Etapa 6, parte 1): cartão via Checkout Pro (lojinha de evento)

### Resumo
Início do **cartão de crédito**, reusando a engine. Modelo: **Checkout Pro** (redireciona ao MP; sem SDK, sem
dado de cartão no servidor, sem dependência nova). **Todas as taxas vão pro cliente**: o **juro do parcelamento**
é do comprador (config "Parcelado comprador" na conta MP, até 12x) e a **taxa de intermediação** (fixa) é
**embutida no preço** do cartão via *gross-up* (`cobrado = venda ÷ (1 − taxa%)`). Ligado 1º na **lojinha de
evento** para validar; os outros pontos vêm em seguida.

### Como funciona
- Config nova: **`MercadoPagoConfig.taxa_cartao_pct`** (padrão 4,98% = crédito na hora) + **termômetro** na tela
  (mostra a taxa residual média que o clube arcou nas vendas de cartão; ideal ≈ 0, senão aumentar o %).
- `mercadopago.criar_preferencia` (Checkout Pro, via `urllib`): cria a preferência (só cartão, `installments=12`,
  `back_urls`, `notification_url`) e devolve o `init_point` para redirecionar.
- `_criar_pagamento_cartao`: gross-up + cria `Pagamento(forma="cartao", valor_bruto=venda)` + preferência.
- **Taxa unificada**: `_aprovar_pagamento` calcula `taxa = valor_bruto − líquido` (o que o clube arcou). No Pix o
  clube absorve → taxa ≈ 1%; no cartão o repasse cobre → **líquido volta a bater com a venda → taxa ≈ 0**.
- Webhook e finalização já existentes servem; a forma (pix/cartão) do pedido/compra/mensalidade/inscrição passou
  a vir do `pagamento.forma` (antes fixava "pix").
- Página de pagamento genérica trata cartão (tela "confirmando pagamento" + polling, sem QR).

### Arquivos alterados
- `core/models.py`: `taxa_cartao_pct` (migration **0035**).
- `core/mercadopago.py`: `criar_preferencia`.
- `core/views.py`: `_grossar_cartao`, `_criar_pagamento_cartao`, `_aprovar_pagamento` (taxa = bruto − líquido),
  ramo de cartão na `evento_pagamento_view`, termômetro na `mercadopago_view`, `taxa_cartao_pct` no salvar, e as
  finalizações usando `pagamento.forma`.
- `templates/core/mercadopago.html` (config do cartão + termômetro), `pagamento.html` (modo cartão).
- `core/tests.py`: cartão gera preferência + webhook confirma com taxa repassada (≈ 0); teste do gross-up.

### Pendências
- Replicar o cartão em **Loja do Clube**, **Inscrição** e **Mensalidades**.
- No painel do MP, deixar o parcelamento como **"Parcelado comprador"** (config da conta, não do sistema).

---

## 2026-07-07 - Loja/Vendas: Custos, Taxa e Resultado como cards no Resumo

### Resumo
No Resumo da aba Vendas da Loja, **Custos**, **Taxa Mercado Pago** e **Resultado líquido** viraram **KPIs
próprios** (cards), ao lado de **Arrecadado** (que já era card). Removidos o card "Resultado da loja" (com a
linha Vendas/Custos/Taxa/Resultado) e a nota explicativa — a informação agora está nos cards. Ordem dos KPIs:
Arrecadado · Custos · Taxa Mercado Pago · Resultado líquido · Compras · Média por compra · Itens a entregar.

### Arquivos alterados
- `templates/core/loja.html`: KPIs de Custos/Taxa/Resultado no Resumo; remove o card "Resultado da loja".

---

## 2026-07-07 - Financeiro: remove "Onde está o dinheiro" e ajusta resultado do caixa

### Resumo
Removido da tela Financeiro o card/modal **"Onde está o dinheiro"** (banco + espécie), a pedido do usuário.
Também foi ajustado o banco local para o resultado líquido do Financeiro bater com o valor informado da conta do
clube: **R$ 3.353,00**.

### Arquivos alterados
- `templates/core/financeiro.html`: remove o card "Onde está o dinheiro" e o modal de edição do caixa.
- `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: documentação atualizada.

### Dados ajustados
- Mensalidades reabertas: IDs `744`, `675`, `611`, `610`, `695` (R$ 30,00 cada) e `482` (R$ 27,00).
- Mensalidade mantida paga com ajuste fino: ID `581`, `valor_pago` de R$ 30,00 para R$ 28,00.
- Resultado financeiro recalculado: **R$ 3.353,00**.

### Validação
- `python manage.py check` OK.
- Busca no template confirma que `Onde está o dinheiro`, `modalCaixa`, `btnEditarCaixa`, `caixa.saldo_banco` e
  `caixa_especie` não aparecem mais em `templates/core/financeiro.html`.
- Recalculo local do Financeiro: mensalidades recebidas R$ 2.995,00 e resultado R$ 3.353,00.
- Deploy no VPS com `pinhaljunior2-deploy` OK; banco online substituído pelo `db.sqlite3` local ajustado.
- Backup do banco online anterior: `/var/www/pinhaljunior2/backup/db_before_caixa_mensalidades_20260707_003251.sqlite3`.
- Recalculo no VPS: mensalidades recebidas R$ 2.995,00, resultado R$ 3.353,00, 100 pagas e 288 abertas.
- `https://pinhaljunior.com.br/sistema-novo/` respondeu `200`; serviços `pinhaljunior2`, `nginx` e `sitepinhal`
  ativos.

### Pendências
- Sem novas pendências.

---

## 2026-07-07 - Restaura banco local no VPS

### Resumo
Após testes manuais no ambiente online sujarem o banco do VPS, o banco da instalação nova (`pinhaljunior2`) foi
restaurado a partir do `db.sqlite3` local. A mídia do VPS foi mantida, pois a solicitação era restaurar o banco.
O sistema antigo (`sitepinhal`) não foi alterado.

### Arquivos/configurações envolvidos
- Local: `db.sqlite3` enviado temporariamente para `/tmp/pinhaljunior2-db-local.sqlite3`.
- VPS: `/var/www/pinhaljunior2/data/db.sqlite3` substituído pelo banco local.
- Backup criado antes da troca: `/var/www/pinhaljunior2/backup/db_before_local_restore_20260707_002006.sqlite3`.
- `docs/DEPLOY_VPS.md`, `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: documentação atualizada.

### Validação
- `manage.py check` OK no VPS.
- `migrate --noinput` sem pendências.
- Serviço `pinhaljunior2.service` ativo.
- `https://pinhaljunior.com.br/sistema-novo/` respondeu `200`.
- Contagem do banco restaurado: 37 usuários, 39 aventureiros, 36 ativos e 0 pagamentos.
- Serviços `pinhaljunior2.service`, `nginx` e `sitepinhal.service` ativos.

### Decisões tomadas
- Parar apenas `pinhaljunior2.service` durante a troca.
- Remover o arquivo temporário `/tmp/pinhaljunior2-db-local.sqlite3` após restaurar.
- Manter a pasta `media/` do VPS, que já continha os uploads.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Loja/Vendas: resumo financeiro no Resumo; Custos só com a lista

### Resumo
Ajuste de organização: o resumo financeiro (Vendas − Custos − Taxa MP = Resultado) saiu da sub-aba **Custos** e
virou um card **"💰 Resultado da loja"** na sub-aba **Resumo** (junto do Arrecadado) — é onde a taxa e o
resultado líquido fazem sentido. A sub-aba **Custos** ficou só com a **lista de custos** ("Custos da loja") +
um **Total de custos**.

### Arquivos alterados
- `templates/core/loja.html`: card "Resultado da loja" no Resumo; Custos retitulada ("Custos da loja"), sem a
  linha de resultado, com total ao final.
- `static/css/loja.css`: `.loja-custos-total`.

---

## 2026-07-06 - Loja/Vendas dividida em sub-abas

### Resumo
A aba **Vendas** da Loja (que estava com tudo empilhado) foi dividida em **4 sub-abas** para facilitar a
visualização: **Resumo** (KPIs + mais vendidos + por forma de pagamento), **Custos** (resultado líquido +
custos/pagamentos da loja), **Pedido ao fornecedor** (o que falta entregar) e **Todas as compras** (lista
buscável com entrega). Mesmo padrão visual das abas principais da Loja.

### Arquivos alterados
- `templates/core/loja.html`: barra de sub-abas + cada seção envolvida numa `.loja-subsecao` (Resumo visível
  por padrão; demais `hidden`).
- `static/js/loja.js`: alterna as sub-abas (`.loja-subaba` → `.loja-subsecao`).
- `static/css/loja.css`: estilo das sub-abas.

### Nota
- Fecha a pendência adiada da revisão anterior.

---

## 2026-07-06 - Taxa sempre visível na Loja/Vendas + nota na lojinha do evento

### Resumo
Ajuste de visibilidade da taxa (o cálculo já estava certo desde a Etapa 5). Na **Loja → Vendas**, a linha da
**taxa do Mercado Pago** só aparecia quando havia taxa > 0, dando a impressão de que o resultado "não refletia" a
taxa. Agora a linha **aparece sempre** (mesmo R$ 0,00) e há uma nota explicando que o Resultado já é líquido
(sem custos e sem taxa). Na **aba Lojinha do painel do evento**, uma nota esclarece que os valores dos pedidos
são brutos e que a taxa/resultado líquido ficam na aba **Financeiro**.

### Arquivos alterados
- `templates/core/loja.html`: linha de taxa sempre visível no resultado da aba Vendas + nota.
- `templates/core/evento_painel.html`: nota na sub-aba Pedidos da Lojinha.
- `core/tests.py`: `test_vendas_loja_resultado_reflete_taxa` (resultado da loja desconta a taxa).

### Pendências
- **Adiado (a pedido)**: dividir a aba **Vendas** da Loja em sub-abas (Custos / Pedido ao fornecedor / Todas as
  compras) para facilitar a visualização.

---

## 2026-07-06 - Correção: 500 no Financeiro (extrato com data+hora × custo do clube)

### Resumo
Após passar o extrato a exibir **data+hora** (`|date:"d/m/y H:i"`), a página `/financeiro/` dava **erro 500** em
produção: o lançamento de **custo do clube** usava `cc.data` (um `date`, sem hora) e o filtro `|date` com `H`
**quebra em objetos `date`** (`TypeError: ...may not contain time-related format specifiers`). Os testes não
tinham custo do clube, por isso não pegou.

### Correção
- `core/views.py`: o lançamento de custo do clube no extrato agora carrega um **datetime** (`cc.data` combinado
  com meia-noite) em vez de um `date`. Todos os itens do extrato passam a ser datetime → o `H:i` não quebra.
- `core/tests.py`: `test_financeiro_desconta_taxa_do_liquido` cria um `CustoClube` (exercita o render do extrato)
  — regressão coberta.

---

## 2026-07-06 - Financeiro: extrato ordenado por data E hora (com hora na tela)

### Resumo
O extrato consolidado do Financeiro ordenava só por **data** (`_dt_data` truncava o horário), então lançamentos
do mesmo dia ficavam na ordem de inserção, não do mais recente. Agora ordena por **data + hora** (mais recente
no topo) e a tela mostra o **horário** de cada lançamento. Isso também deixa a linha **"Taxa Mercado Pago"**
adjacente à venda que a gerou.

### Arquivos alterados
- `core/views.py`: `_dt_data` preserva o datetime; novo `_ordem_extrato` (chave aware date+hora, normaliza
  date/datetime/None); `extrato.sort` usa essa chave.
- `templates/core/financeiro.html`: data do extrato exibida como `d/m/y H:i`.
- `core/tests.py`: confirma a linha "Taxa Mercado Pago" no extrato.

### Nota
- A taxa (1%) aparece como linha própria no extrato **a partir da Etapa 5** — se não apareceu, faltou o deploy.

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 5): taxa/líquido nos relatórios

### Resumo
Os relatórios financeiros passaram a mostrar o **valor líquido que caiu no banco** (bruto − custos − **taxa do
Mercado Pago**). O clube absorve a taxa (não repassa ao cliente), mas ela agora aparece descontada em **todos os
relatórios**: **Financeiro geral**, **painel financeiro do evento**, **Mensalidades** e **Loja (Vendas)**. Usa a
`taxa` real gravada em cada `Pagamento` aprovado (fallback 1% já vem da engine).

### Como a taxa é somada (sem contagem dupla)
- **Geral**: soma `Pagamento.taxa` por **tipo** aprovado (mensalidade / loja_clube / loja_evento+inscricao) —
  cada Pagamento tem uma taxa e é contado uma vez.
- **Evento**: soma sobre os **Pagamentos distintos** ligados às inscrições/pedidos confirmados do evento (uma
  inscrição e o pedido de lojinha que veio junto **compartilham** o mesmo Pagamento → `set` evita duplicar).
- **Mensalidades/Loja**: soma a taxa dos Pagamentos das mensalidades do ano / das compras da loja.

### Arquivos alterados
- `core/views.py`:
  - `financeiro_view`: taxa por fonte (`resumo.*.taxa`), líquido de cada fonte já **sem taxa**, `saidas` e
    `resultado` incluem a taxa, `disponivel`/`reservado_loja` recalculados, e **linhas de "Taxa Mercado Pago"**
    no extrato consolidado.
  - `_montar_financeiro` (evento): `taxa` + `saidas_total` (custos + taxa), `resultado` líquido, taxa no extrato;
    `evento_painel_view` reflete no `resumo`.
  - `loja_view`: `taxa_loja` e `loja_resultado` já sem taxa.
  - `mensalidades_view`: `totais.taxa_gateway` e `totais.liquido`.
- Templates: `financeiro.html` (cards por fonte com linha de taxa + textos), `evento_painel.html` (Saídas =
  custos + taxa), `loja.html` (linha de taxa nas Vendas), `mensalidades.html` (líquido no KPI Recebido).
- `core/tests.py`: taxa refletida no geral (`test_financeiro_desconta_taxa_do_liquido`) e no painel do evento
  (`test_painel_evento_desconta_taxa_no_resultado`).

### Pendências
- Próxima: **cartão de crédito** (Etapa 6). Pagamentos manuais/dinheiro/importados têm taxa zero (líquido = bruto).

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 4): Inscrição de evento via Pix

### Resumo
Quarta etapa: a **inscrição online** de evento passou a cobrar por **Pix real** quando há valor a pagar. Antes a
inscrição nascia **confirmada sem pagar**; agora, com MP configurado e total &gt; 0, os dados validados são
**serializados** e a inscrição só é criada **na aprovação** do Pix (webhook/simular). Inscrição **gratuita**
(total 0 — diretoria/faixa sem valor) ou **sem MP** continua criando na hora. O **balcão/PDV** não muda.

### Como funciona
- `evento_inscrever_view`: valida como antes (responsável + participantes com preço/cupom + campos + lojinha) e
  monta um **payload serializável** (responsável; participantes com `valor` já calculado/descontado, `faixa_id`,
  respostas e cupom; campos extra; itens da lojinha). Se MP configurado e total &gt; 0 → cria `Pagamento`
  (`tipo="inscricao"`) e vai à página de pagamento genérica; senão → cria na hora.
- `_criar_inscricao_de_payload` (usado pela criação imediata **e** pela finalização): cria a Inscrição
  confirmada + participantes + respostas + pedido de lojinha vinculado; **marca os cupons** (uso único revalidado
  no ato — no Pix, isso acontece só no pagamento). Preços vêm prontos do payload (o desconto do cupom foi fixado
  na cobrança), evitando divergência de valor após pagar. `_finalizar_inscricao` chama esse helper na aprovação.
- Inscrição paga por Pix fica `forma_pagamento="pix"` e com FK `pagamento` (idem o pedido de lojinha junto).

### Arquivos alterados
- `core/models.py`: FK `Inscricao.pagamento`. Migration **0034**.
- `core/views.py`: `_criar_inscricao_de_payload` + `_finalizar_inscricao` + dispatch; `_sucesso_url_e_sessao`
  trata `inscricao`; bloco de criação da `evento_inscrever_view` reescrito (payload + branch Pix/imediato).
- `core/tests.py`: `InscricaoPixTests` (paga → Pix → simular → inscrição confirmada + taxa + FK; grátis cria na hora).

### Decisões tomadas
- Preço fixado na cobrança (payload) e cupom marcado só na aprovação (best-effort): se o cupom for usado por
  outro entre a geração do Pix e o pagamento, a pessoa mantém o preço que pagou (não falha após o pagamento).
- Balcão/PDV de inscrição inalterado (pagamento presencial).

### Pendências
- Próximas: **taxa/líquido nos relatórios** (Etapa 5) e **cartão** (Etapa 6).

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 3): Loja do Clube via Pix

### Resumo
Terceira etapa: a **Loja do Clube** passou a cobrar por **Pix real** (Mercado Pago), reaproveitando a engine e a
**página de pagamento genérica** da Etapa 2. Sem MP configurado, mantém o fluxo simulado antigo. A **compra só
nasce na aprovação** (o carrinho fica na sessão/no payload até lá). De quebra, o "Marcar pago/Desfazer" das
mensalidades agora mostra **toast de sucesso**.

### Como funciona
- `loja_pagamento_view`: com MP configurado + Pix, cria um `Pagamento` (`tipo="loja_clube"`, `payload` com o
  **carrinho** serializado + comprador) e **redireciona para a página genérica** de pagamento (`/pagamento/<ref>/`).
- Na aprovação, `_finalizar_loja_clube` reconstrói os itens do carrinho (`_loja_resolver_kits`, extraído de
  `_loja_cart_detalhado`) e cria a `CompraLoja` (forma Pix, FK `pagamento`, baixa de estoque). O sucesso volta
  para `loja_sucesso` (limpa carrinho/checkout da sessão).

### Arquivos alterados
- `core/models.py`: FK `CompraLoja.pagamento`. Migration **0033**.
- `core/views.py`: `_loja_resolver_kits` (resolvedor puro do carrinho) + `_loja_cart_detalhado` refatorado;
  `_finalizar_loja_clube` + dispatch; `_sucesso_url_e_sessao` trata `loja_clube`; `loja_pagamento_view` usa o Pix
  real quando configurado.
- `static/js/mensalidades.js`: toast de sucesso no marcar pago/desfazer.
- `core/tests.py`: `LojaClubePixTests` (carrinho → Pix → simular → compra criada + taxa + FK).

### Pendências
- Próximas: **Inscrição de evento** (Etapa 4), **taxa/líquido nos relatórios** (Etapa 5), **cartão** (Etapa 6).

---

## 2026-07-06 - Cache-busting dos estáticos (JS/CSS antigo preso no navegador)

### Resumo
**Causa-raiz** de "corrigi e não resolveu": as correções de JavaScript (caminho do fetch, leitura do cookie de
CSRF) eram entregues ao servidor, mas o **navegador continuava usando o `mensalidades.js`/`loja.js` antigos em
cache** — então o "Desfazer"/"Marcar pago" seguia batendo no endereço errado (raiz = sistema antigo), que não
devolve JSON → "não foi possível atualizar". Correções **server-side** (deslogar) pegavam na hora; as que
dependiam de JS novo ficavam mascaradas pelo cache. Confirmado por teste automatizado: o Desfazer no servidor
funciona (`MensalidadePixTests.test_desfazer_mensalidade_paga_via_pix`).

### Solução
Ativado **cache-busting** em produção: `STORAGES` usa `core.storages.CacheBustingStaticFilesStorage`
(subclasse de `ManifestStaticFilesStorage`, `manifest_strict=False`), que renomeia cada estático com um hash do
conteúdo (`mensalidades.<hash>.js`). Quando o arquivo muda, a URL muda e o navegador **sempre** baixa a versão
nova; arquivos inalterados mantêm o hash (seguem em cache). Em `DEBUG` continua o storage simples.

### Arquivos criados/alterados
- `config/settings.py`: `STORAGES` com o storage de cache-busting quando `DEBUG=False`.
- `core/storages.py`: **novo** — `CacheBustingStaticFilesStorage` (`manifest_strict=False`, para não quebrar
  testes/páginas quando falta o manifesto ou uma entrada).

### Notas
- `collectstatic --noinput` (roda no deploy) valida e gera o manifesto; testado localmente (168 arquivos, ok).
- Depois do deploy, basta **recarregar a página** — o HTML passa a apontar para o JS com hash novo; não precisa
  mais de "atualização forçada" (Ctrl+F5) a cada correção.

---

## 2026-07-06 - Correção: "deslogou sozinho" — cookies compartilhados com o sistema antigo

### Resumo
No VPS o sistema novo e o antigo estão no **mesmo domínio** (`pinhaljunior.com.br`) e os dois são Django usando
o **mesmo nome de cookie** de sessão (`sessionid`) e de CSRF (`csrftoken`). Cookie é do domínio inteiro → **um
sobrescreve o do outro**, derrubando o login do sistema novo ("deslogou ao clicar em Mercado Pago"). Como efeito,
o **Desfazer** das mensalidades (AJAX) recebia o redirecionamento para o login em vez de JSON → "não foi possível
atualizar". Resolvido dando **cookies com nome próprio** ao sistema novo.

### Arquivos alterados
- `config/settings.py`: `SESSION_COOKIE_NAME=pinhaljunior2_sessionid` e `CSRF_COOKIE_NAME=pinhaljunior2_csrftoken`
  (ambos via env: `DJANGO_SESSION_COOKIE_NAME` / `DJANGO_CSRF_COOKIE_NAME`).
- `static/js/mensalidades.js` e `static/js/loja.js`: o leitor de CSRF passa a ler o novo nome de cookie (com
  fallback para o token do formulário `csrfmiddlewaretoken`, que independe do nome).

### Efeito colateral esperado
- Ao subir, todas as sessões atuais do sistema novo caem uma vez (o cookie antigo `sessionid` é ignorado); é só
  logar de novo. Depois disso o login do sistema novo não briga mais com o do antigo.

---

## 2026-07-06 - Correção: fetch com caminho absoluto quebrava sob o prefixo do VPS

### Resumo
Bug **pré-existente** exposto pelo deploy no VPS (app sob `/sistema-novo/`): dois JS faziam `fetch` com
**caminho absoluto fixo**, que no VPS resolvia para a raiz do domínio (sistema antigo) e falhava. Sintoma
relatado: em Mensalidades, **"Desfazer"** (e o "Marcar pago") não funcionava. Também afetava a **marcação de
entrega** da Loja do Clube (mesmo bug, ainda não percebido).

### Arquivos alterados
- `static/js/mensalidades.js`: usa a URL de `#mensLista[data-pagar-url]` (via `{% url %}`, que inclui o prefixo)
  em vez de `"/mensalidades/pagar/"` fixo. `templates/core/mensalidades.html`: adiciona `data-pagar-url`.
- `static/js/loja.js`: usa `#lojaComprasLista[data-entrega-url|data-entrega-compra-url]` em vez de
  `"/loja/entrega/..."` fixo. `templates/core/loja.html`: adiciona os dois `data-`.

### Decisões tomadas
- Padrão a seguir dali em diante: **toda URL usada em JS vem do template via `{% url %}`** (num `data-`), nunca
  caminho absoluto fixo — senão quebra sob `FORCE_SCRIPT_NAME`. O código novo dos pagamentos já seguia isso.
- Mantido um fallback para o caminho local. Varredura confirmou que não há outros `fetch` absolutos.

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 2): Mensalidades online + admin do Pagamento

### Resumo
Segunda etapa da integração. **(1)** `Pagamento` agora aparece no **/admin/** (lista só-leitura, para auditoria).
**(2)** **Mensalidades online via Pix**: o Diretor seleciona os meses em aberto de um aventureiro e gera **uma
única cobrança Pix**; quando o pagamento é aprovado (webhook ou "Simular" no teste), **todos os meses escolhidos
são quitados automaticamente**. Reaproveita a engine da Etapa 1 e já fica pronto para a futura tela do
responsável (mesmo fluxo: selecionar em aberto → pagar → baixa tudo). Criada também uma **página de pagamento
genérica** (QR + polling + simular) e uma **tela de sucesso genérica**, reaproveitáveis pelas próximas etapas.

### Como funciona
- Na aba **Aventureiros** das Mensalidades, cada aventureiro com valor em aberto ganha o botão **"💳 Cobrar em
  aberto via Pix"** → abre um modal com os meses em aberto (checkbox, total ao vivo) → **"Gerar cobrança Pix"**.
- `mensalidade_cobrar_view` cria um `Pagamento` (`tipo="mensalidade"`, `payload` com os ids dos meses) + o Pix, e
  leva à página de pagamento genérica.
- Na aprovação, `_finalizar_mensalidade` marca cada mensalidade do payload como **paga** (forma Pix, `valor_pago`,
  `pago_em`, `registrado_por`, FK `pagamento`). Idempotente (só mexe nas que ainda estão em aberto). O webhook
  "sabe quem pagou e o quê" pelo `payload`.

### Arquivos criados/alterados
- `core/admin.py`: `PagamentoAdmin` (só-leitura: sem add/change/delete).
- `core/models.py`: FK `Mensalidade.pagamento`. Migration **0032**.
- `core/views.py`: `_finalizar_mensalidade` + dispatch; `_sucesso_url_e_sessao` para os tipos genéricos;
  `pagamento_view` (página genérica), `pagamento_sucesso_view` (sucesso genérico), `mensalidade_cobrar_view`.
- `core/urls.py`: `mensalidades/cobrar/`, `pagamento/<ref>/` e `pagamento/<ref>/sucesso/`.
- `templates/core/pagamento.html` e `pagamento_sucesso.html`: **novas** (genéricas, reaproveitáveis).
  `templates/core/mensalidades.html`: botão + modal de cobrança; `data-valor`/`data-nome` nos meses.
- `static/js/mensalidade_pix.js`: **novo** (monta o modal com os meses em aberto + total ao vivo).
  `static/css/mensalidades.css`: estilos do modal de cobrança.
- `core/tests.py`: `MensalidadePixTests` (renderização da tela; cobrança → simular → baixa múltipla + taxa + FK).

### Decisões tomadas
- Uma cobrança Pix por **aventureiro** (a view garante que todas as mensalidades são do mesmo).
- Por ora quem dispara é o **Diretor** (para testar); a engine já serve a futura tela do responsável.
- Páginas de pagamento/sucesso **genéricas** (por `referencia` do pagamento) para reuso nas Etapas 3 e 4.

### Pendências
- Próximas: **Loja do Clube** (Etapa 3), **Inscrição de evento** (Etapa 4), **taxa/líquido nos relatórios**
  (Etapa 5) e **cartão** (Etapa 6). Tela do responsável para pagar as próprias mensalidades: futura.

---

## 2026-07-06 - Pagamentos Mercado Pago (Etapa 1): engine Pix + webhook + lojinha de evento

### Resumo
Início da integração real de pagamentos (Mercado Pago), começando **só por Pix**. Criada uma **engine única
reaproveitável** para os 4 pontos de venda (lojinha de evento, Loja do Clube, mensalidades e inscrição) e
**ligada primeiro na lojinha de evento**, substituindo o QR simulado pela cobrança Pix real. O clube **absorve a
taxa** (não repassa), mas o sistema grava a **taxa real** informada pelo Mercado Pago e o **líquido** que caiu no
banco (fallback de 1% quando o dado não vier) — base para os relatórios financeiros mostrarem o líquido (Etapa 5).

### Componentes
- **Config** `MercadoPagoConfig` (singleton, só Diretor, tela `/mercadopago/`): guarda **dois pares** de
  credenciais — teste e produção — + `modo` ativo. Segredos mascarados; trocam só se um novo for digitado
  (espelha o `WhatsappConfig`). Mostra a **URL do webhook** para cadastrar no painel do MP.
- **Cliente** `core/mercadopago.py` (só `urllib`, sem dependência nova): `criar_pix`, `consultar_pagamento`
  (extrai **taxa real** de `fee_details` e o **líquido** de `net_received_amount`), `validar_assinatura`
  (HMAC-SHA256 do `x-signature`) e `mapear_status`. Usa a API clássica `/v1/payments`.
- **Model** `Pagamento` (genérico): `tipo`, `forma`, `referencia` (external_reference), `mp_payment_id`,
  `status`, `valor_bruto`/`taxa`/`valor_liquido`, `payload` (JSON = o que está sendo pago), dados do Pix (QR),
  `finalizado` (idempotência). FK `PedidoLoja.pagamento` (nulo em balcão/dinheiro/importados → taxa zero).
- **Webhook** `/webhooks/mercadopago/` (público, `csrf_exempt`, idempotente): valida a assinatura, **consulta o
  pagamento no MP (fonte da verdade)**, e ao aprovar grava taxa/líquido e **finaliza** (cria o objeto pago
  conforme o `tipo`). Despacho por tipo — só `loja_evento` implementado nesta etapa.
- **Fluxo na lojinha**: `evento_pagamento_view` usa Pix real quando o MP está configurado (QR do MP +
  **polling** de status + botão **"Simular aprovação" só no modo teste**); sem config, mantém o simulado antigo.
  O `PedidoLoja` só nasce na aprovação (webhook/simulação), preservando "sem estoque reservado por carrinho
  abandonado".

### Arquivos criados/alterados
- `core/models.py`: `MercadoPagoConfig`, `Pagamento`, `STATUS_PAGAMENTO_CHOICES`/`TIPO_PAGAMENTO_CHOICES`,
  `PedidoLoja.pagamento`; import `uuid`. Migration **0031**.
- `core/mercadopago.py`: **novo** cliente do gateway (urllib).
- `core/views.py`: engine (`_criar_pagamento_pix`, `_aprovar_pagamento`, `_finalizar_pagamento`/
  `_finalizar_loja_evento`, `_sucesso_url_e_sessao`), views de config, webhook, status (polling) e simulação;
  `evento_pagamento_view` passa a usar o MP quando configurado (`_evento_pagamento_pix_mp`).
- `core/urls.py`: rotas `mercadopago`, `mercadopago_config`, `mercadopago_webhook`, `pagamento_status`,
  `pagamento_simular`.
- `templates/core/mercadopago.html`: **nova** tela de config. `templates/core/evento_pagamento.html`: modo Pix
  real (QR base64 + copia e cola + polling + simular) com fallback ao simulado. `templates/core/_menu.html`:
  item "Mercado Pago" (💳, Diretor).
- `static/js/pagamento_mp.js`: **novo** (polling + botão simular + copiar). `static/css/eventos.css`: estilos do
  Pix (spinner/aguardando/erro/teste).
- `core/tests.py`: `MercadoPagoClienteTests` (assinatura + extração de taxa) e `PagamentoLojinhaTests` (fluxo
  pendente→aprovado, simulação só em teste, webhook com **taxa real**, assinatura inválida, retrocompat sem MP).

### Decisões tomadas
- **Taxa real do MP** (não 1% fixo), com fallback de 1% no Pix quando o dado não vier — bate com o extrato do banco.
- **Dois pares de credenciais** (teste/produção) num só singleton: valida no teste e vira a chave sem redigitar.
- **Engine genérica com `payload`**: o webhook sabe "quem pagou e o quê" sem depender da sessão do navegador.
- **Sem dependência nova**: cliente via `urllib`, como a W-API.
- Objeto pago só nasce na aprovação (mantém o padrão "não reserva estoque de carrinho abandonado").

### Pendências
- **Confirmar a taxa real com um pagamento de verdade**: no sandbox não dá para "pagar" um Pix de teste; o botão
  "Simular" usa 1% estimado. O caminho da taxa real (webhook → `fee_details`) já está testado com dado mockado;
  confirmar o **valor real** exige um Pix pequeno em produção (ou o fluxo de cartão de teste, na fase de cartão).
- Cadastrar a **URL do webhook** e a **assinatura secreta** no painel do MP e colar a secret na tela de config.
- Próximas etapas: **Mensalidades online** (seleção múltipla → uma cobrança → baixa automática), **Loja do
  Clube**, **Inscrição de evento**, **taxa/líquido nos relatórios financeiros** e, por fim, **cartão de crédito**.

---

## 2026-07-06 - Documentação dedicada de deploy no VPS

### Resumo
Criado um documento específico para o deploy no VPS, reunindo em um só lugar a URL temporária, estrutura do
servidor, atalho global, variáveis de ambiente, dados importados, validações e cuidados para não afetar o sistema
antigo.

### Arquivos criados/alterados
- `docs/DEPLOY_VPS.md`: novo guia de deploy e operação do VPS.
- `README.md`: adiciona link para o guia de deploy.
- `docs/README_PROJETO.md`: aponta para o guia dedicado na seção "Deploy no VPS".
- `docs/ESTADO_ATUAL.md`: referencia `docs/DEPLOY_VPS.md` no resumo do deploy.
- `docs/HISTORICO_ALTERACOES.md`: esta entrada.

### Decisões tomadas
- Manter o guia operacional separado do histórico para facilitar continuidade.
- Registrar explicitamente que código vai por GitHub + `pinhaljunior2-deploy`, e que o sistema antigo não deve
  ser alterado sem pedido.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Preparação para deploy no VPS

### Resumo
Preparado o projeto para rodar em produção no VPS sem alterar o comportamento local. As configurações sensíveis
e específicas do servidor agora podem vir de variáveis de ambiente, permitindo usar SQLite persistente fora do
repositório, `DEBUG=False`, hosts/CSRF corretos, arquivos estáticos coletados e publicação em subcaminho com
`DJANGO_FORCE_SCRIPT_NAME`.

### Arquivos criados/alterados
- `config/settings.py`: lê `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SQLITE_PATH`, `DJANGO_FORCE_SCRIPT_NAME`, `DJANGO_STATIC_URL`,
  `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_URL` e `DJANGO_MEDIA_ROOT`; adiciona `STATIC_ROOT` e proxy HTTPS.
- `requirements.txt`: adiciona `gunicorn` para execução via systemd/Gunicorn no VPS.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md` e `docs/README_PROJETO.md`: documentação atualizada.

### Decisões tomadas
- Manter os padrões locais quando as variáveis não existem, para não atrapalhar o desenvolvimento.
- Usar configuração por ambiente no VPS, sem versionar segredo, banco ou uploads.

### Pendências
- Concluir a configuração no VPS: clone via GitHub, env file, serviço systemd, Nginx no subcaminho temporário e
  atalho global de deploy.

---

## 2026-07-06 - WhatsApp: preserva ID e token salvos

### Resumo
Reforçada a persistência da configuração do WhatsApp/W-API. A configuração já ficava no banco via
`WhatsappConfig`, mas o ID da instância podia ser apagado se o formulário fosse enviado com o campo vazio. Agora
ID da instância e token seguem a mesma regra: só são substituídos quando um novo valor é digitado.

### Arquivos criados/alterados
- `core/views.py`: `whatsapp_config_view` preserva `instance_id` quando o POST vem vazio, assim como já fazia
  com o token.
- `templates/core/whatsapp.html`: texto da tela deixa claro que novo ID/token só devem ser digitados para troca.
- `core/tests.py`: teste automatizado garantindo que campos vazios não apagam ID/token salvos, chamando a view
  diretamente para não depender do prefixo `/sistema-novo` do ambiente de produção.
- `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: documentação atualizada.

### Validação
- `python manage.py test core.tests.WhatsappConfigTests` OK.
- `python manage.py check` OK.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Importação inicial do banco e mídias locais no VPS

### Resumo
Enviado para o novo sistema online o banco SQLite local e todos os arquivos da pasta `media/`, já que esses dados
não passam pelo GitHub. A importação foi feita apenas na instalação nova (`pinhaljunior2`), sem tocar no sistema
antigo do domínio raiz.

### Arquivos/configurações envolvidos
- Local: `db.sqlite3` e `media/` empacotados temporariamente para transferência.
- VPS: `/var/www/pinhaljunior2/data/db.sqlite3` substituído pelo banco local.
- VPS: `/var/www/pinhaljunior2/media` substituída pela pasta `media/` local.
- VPS: backup prévio salvo em `/var/www/pinhaljunior2/backup/local_before_import_<timestamp>/`.

### Validação
- `manage.py check` OK no VPS.
- `migrate --noinput` sem migrations pendentes.
- Serviço `pinhaljunior2.service` reiniciado e ativo.
- Contagem validada no banco importado: 37 usuários, 39 aventureiros e 36 aventureiros ativos.
- Arquivo de mídia validado com HTTP 200 em `/sistema-novo/media/`.

### Decisões tomadas
- Remover os pacotes temporários com dados sensíveis após a importação.
- Manter backup do banco/media anteriores do VPS, mesmo sendo a instalação nova.

### Pendências
- Sem novas pendências.

---

## 2026-07-06 - Deploy inicial no VPS em /sistema-novo

### Resumo
Publicado o sistema novo no VPS, sem substituir o sistema antigo do domínio principal. A nova versão responde em
`https://pinhaljunior.com.br/sistema-novo/`, usando serviço, banco, media, staticfiles e comando de deploy próprios.
O sistema antigo continua no domínio raiz e no serviço `sitepinhal.service`.

### Arquivos/configurações criados ou alterados no VPS
- `/var/www/pinhaljunior2/current`: clone do repositório GitHub.
- `/var/www/pinhaljunior2/.venv`: ambiente virtual Python do novo sistema.
- `/var/www/pinhaljunior2/data/db.sqlite3`: banco SQLite persistente da nova versão.
- `/var/www/pinhaljunior2/media` e `/var/www/pinhaljunior2/staticfiles`: uploads e estáticos coletados.
- `/etc/pinhaljunior2.env`: variáveis de produção, incluindo prefixo `/sistema-novo`.
- `/etc/systemd/system/pinhaljunior2.service`: Gunicorn em `127.0.0.1:8010`.
- `/usr/local/bin/pinhaljunior2-deploy`: deploy global via GitHub, com backup do SQLite, migrations,
  collectstatic, restart e healthcheck.
- `/etc/nginx/sites-available/sitepinhal`: adicionadas apenas as rotas `/sistema-novo/`,
  `/sistema-novo/static/` e `/sistema-novo/media/`; backup criado antes da alteração.

### Validação
- `pinhaljunior2-deploy` concluiu com healthcheck OK.
- `nginx -t` OK e reload aplicado.
- `https://pinhaljunior.com.br/sistema-novo/` respondeu `200`.
- `https://pinhaljunior.com.br/sistema-novo/static/css/login.css` respondeu `200`.
- Login real com `Fabiano` retornou `302` para `/sistema-novo/inicio/`.
- Serviços `pinhaljunior2.service`, `nginx` e `sitepinhal.service` ficaram ativos.

### Pendências
- Trocar a senha inicial do usuário diretor `Fabiano`.
- Configurar dados reais de produção e integrações de pagamento quando a etapa de gateway começar.

---

## 2026-07-06 - Cadastro: assinatura desenhada dos 3 documentos da inscrição

### Resumo
Voltou (do sistema antigo) a **assinatura desenhada** (dedo/mouse, estilo Canva) na inscrição do aventureiro.
O responsável assina **3 documentos** — ficha de inscrição, declaração médica e termo de autorização de imagem
— e a **assinatura substitui o checkbox de aceite** (assinar = aceitar). Cada assinatura vira um **documento de
assinatura** guardado (imagem PNG + **texto do termo preenchido no momento**), para que o **Diretor** consiga
depois gerar/imprimir o **termo assinado** de cada pessoa. O responsável **não** vê a própria assinatura depois
(só o status "assinado em ..."); a imagem/termo assinado é acessível **só pelo Diretor**.

### Arquivos criados/alterados
- `core/termos.py` (novo): textos canônicos dos 3 termos, já preenchidos com os dados (fonte única).
- `core/models.py`: model **`AssinaturaDocumento`** (aventureiro, documento, imagem, titulo/texto snapshot,
  assinante_nome/cpf, assinado_em; único por aventureiro+documento). Migration `0030_assinaturadocumento`.
- `core/views.py`: `_decode_signature` (base64→PNG), `_validar_aceites` agora exige as 3 assinaturas,
  `_salvar_aventureiro`/`_salvar_assinaturas` criam os 3 registros; `_preparar_assinaturas` anota status;
  nova view `aventureiro_termos_view` (Diretor) para o termo assinado; `prefetch_related("assinaturas")`.
- `core/urls.py`: rota `usuarios/aventureiro/<pk>/termos/`.
- `core/forms.py`: `mensalidade_isento`/`mensalidade_desconto_pct` deixam de ser obrigatórios no cadastro
  público (Diretor define depois em Mensalidades) — **corrige** um travamento pré-existente do cadastro.
- `core/admin.py`: registro de `AssinaturaDocumento`.
- Templates: `_assinatura_doc.html` (novo, bloco reutilizável), `aventureiro_termos.html` (novo, pág. de
  impressão do Diretor), `cadastro.html` (blocos de assinatura nas etapas 5, 6 e revisão; termo de imagem
  interpolado com os dados), `_aventureiro_detalhe.html` (status assinado + link só Diretor),
  `usuarios.html` (passa `pode_ver_termos=True`).
- Estáticos: `static/js/assinatura.js` (novo, pad em canvas com pointer events, sem lib),
  `static/js/cadastro.js` (validação por assinatura + revisão + interpolação do termo), `static/css/cadastro.css`
  (pad/modal/preview), `static/css/inicio.css` (link "Ver termos assinados").

### Decisões tomadas
- **Sem biblioteca**: canvas + pointer events (dedo e mouse), como no sistema antigo.
- Snapshot do texto do termo no ato da assinatura → o termo assinado é reconstruível mesmo se o cadastro mudar.
- Imagens em `media/assinaturas/` (git-ignored, dado pessoal) — nunca versionar.
- Página do Diretor pronta para impressão (`@media print`) — salva PDF pelo navegador, sem lib de PDF.

### Pendências
- Assinatura na diretoria (quando o cadastro de diretoria for implementado) pode reusar o mesmo padrão.

---

## 2026-07-06 - Loja/Vendas: relatório "Pedido para o fornecedor" (só o que falta entregar)

### Resumo
Nova seção na aba **Vendas** da Loja: **"📦 Pedido para o fornecedor"** — por **produto → variação**
(tamanho/item), mostra **só o que falta entregar** (= exatamente o que pedir ao fornecedor). Variações e
produtos **já 100% entregues não aparecem**; quando não há nada pendente, mostra "✅ Tudo entregue — nada a
pedir". (Primeira versão trazia colunas Vendido/Entregue + toggle; a pedido do usuário ficou só "A entregar",
sem dados desnecessários.) Ex.: Camiseta por tamanho, Uniforme de Gala por item, Laço.

### Arquivos alterados
- `core/views.py`: `_loja_relatorio` agrega `fornecedor` só com itens `falta_entregar > 0` (por produto/variação).
- `templates/core/loja.html`: seção "Pedido para o fornecedor" (antes de "Todas as compras"), coluna única
  "A entregar" + estado vazio.
- `static/css/loja.css`: estilos `.loja-forn-*`.

### Validação
- `manage.py check` OK. Render (test client): tudo entregue → mostra "Tudo entregue"; ao desmarcar 1 item, o
  relatório lista só aquela variação com a quantidade a entregar.

---

## 2026-07-06 - Financeiro: fim do "rateio" + contas Disponível × Reservado (loja)

### Resumo
A pedido do usuário, **removido o "rateio"** dos custos gerais (era confuso). Os **4 cards** do topo voltaram a
mostrar o **líquido de cada fonte** (Mensalidades, Loja, Eventos, Custos gerais) — visão de "quem gera mais
lucro/prejuízo". E entrou o modelo de **duas contas** que o usuário descreveu:
- **💚 Disponível pra gastar** = Mensalidades + **lucro dos eventos** − Custos gerais do clube (dinheiro livre).
- **🔒 Reservado da loja** = Vendas − pagamento a fornecedores (travado; não é lucro do clube).
As duas somam o resultado líquido. Custo **geral** sai do disponível; custo com destino **loja** sai do
reservado (usa o `destino` que já existe — sem rateio).

### Arquivos alterados
- `core/views.py`: `financeiro_view` remove o cálculo de contribuição/rateio; calcula `disponivel`,
  `reservado_loja` e `lucro_eventos`.
- `templates/core/financeiro.html`: 4 cards voltam ao líquido; novo bloco `.fin-contas` (Disponível × Reservado).
- `static/css/financeiro.css`: estilos `.fin-contas`/`.fin-conta*` (borda verde = livre, âmbar = travado).

### Validação
- `manage.py check` OK. Render (test client): cards Mensalidades R$ 3.174,00 · Loja R$ 808,50 · Eventos
  R$ 3.392,29 · Custos gerais −R$ 2.834,79; **Disponível R$ 3.731,50** + **Reservado (loja) R$ 808,50** =
  Resultado R$ 4.540,00.

### Pendências
- Filtro por período (hoje tudo é acumulado desde o início do clube).

---

## 2026-07-06 - Financeiro: "Onde está o dinheiro" simplificado (só banco + espécie)

### Resumo
A pedido do usuário, o card "Onde está o dinheiro" ficou com **duas linhas**: **na conta (banco)** e **em
espécie (caixa físico)**. Removida a linha **"a receber (empréstimos)"** — o valor do empréstimo entra **somado
no saldo do banco** (ex.: banco 2.808,00 + empréstimo 1.276,98 = **4.084,98** informado como banco), e a
**espécie** continua sendo o restante calculado (resultado − banco = **455,02**). O modal de edição passou a ter
só o campo do saldo do banco.

### Arquivos alterados
- `core/models.py`: remove `CaixaClube.a_receber` (migration **0029**). `core/forms.py`: `CaixaClubeForm` só com
  `saldo_banco`. `core/views.py`: `caixa_especie = resultado − saldo_banco`.
- `templates/core/financeiro.html`: card e modal sem a linha/campo "a receber".

### Validação
- `manage.py check` OK; `migrate` (0029). Render (test client): card com Banco R$ 4.084,98 + Espécie R$ 455,02
  = Resultado R$ 4.540,00; modal só com o saldo do banco; POST salva.

---

## 2026-07-06 - Financeiro: cards por contribuição + card "Onde está o dinheiro"

### Resumo
Reorganização do Resumo do Financeiro a pedido do usuário:
- **Cards do topo** (Mensalidades, Loja, Eventos) agora mostram **quanto cada fonte contribui no resultado**
  (o líquido **já com o rateio dos custos gerais**), com **% do resultado**, em vez do total de vendas/receita.
  As três **somam exatamente** o resultado líquido (resolve a confusão de "os cards não batem"). O card solto
  **"Custos gerais do clube"** saiu do topo (já entra rateado nas fontes e segue no quadro "Como o resultado se
  forma").
- **Removido** o card separado "Quanto cada fonte contribui no resultado" (o conteúdo virou os cards do topo);
  **mantido** o quadro "Como o resultado líquido se forma".
- **Novo card "Onde está o dinheiro"**: mostra **na conta (banco)** + **a receber (empréstimos/pendências)** +
  **em espécie (caixa físico)** = resultado líquido. O Diretor informa banco e a receber (modal ✏️ com máscara
  de moeda); a **espécie é calculada** (resultado − banco − a receber). Se ficar negativa, avisa pra conferir.

### Arquivos criados/alterados
- `core/models.py`: modelo **`CaixaClube`** (singleton `get_solo`: `saldo_banco`, `a_receber`). Migration **0028**.
- `core/forms.py`: `CaixaClubeForm` (banco/a_receber com `data-moeda`).
- `core/views.py`: `financeiro_view` agrega `contrib`/`rateio`/`pct` em cada fonte do `resumo` e calcula
  `caixa`/`caixa_especie`; nova `caixa_editar_view` (POST). `core/urls.py`: rota `financeiro/caixa/`.
- `templates/core/financeiro.html`: cards do topo por contribuição (3, sem o de custos gerais); remove o card
  de contribuição; card "Onde está o dinheiro" + modal de edição.
- `static/js/financeiro.js`: `ligarModal` genérico (custo + caixa). `static/css/financeiro.css`: `.fin-caixa*`
  e `.fin-fontes-intro` (remove `.fin-contrib*`).

### Validação
- `manage.py check` OK; `migrate` (0028). Render (test client, Diretor): cards mostram contribuição
  (Mensalidades R$ 1.953,95 · 43,0%, Loja R$ 497,72 · 11,0%, Eventos R$ 2.088,33 · 46,0%); card "Onde está o
  dinheiro" com Banco R$ 2.808,00 + A receber R$ 1.276,98 + Espécie R$ 455,02 = Resultado R$ 4.540,00. POST de
  edição do caixa salva (valores restaurados após o teste).

### Pendências
- Sem novas. (Rateio dos custos gerais é proporcional ao líquido; ajustável se quiserem outro critério.)

---

## 2026-07-06 - Financeiro: quadro "Quanto cada fonte contribui no resultado"

### Resumo
Os cards de "líquido por fonte" **não somavam** o resultado, porque os **custos gerais do clube** ficam num
balde à parte (não pertencem a nenhuma fonte) — então Mensalidades + Loja + Eventos dava mais que o resultado
líquido. Novo quadro na aba **Resumo** que **rateia os custos gerais** entre as fontes (proporcional ao líquido
de cada uma) e mostra, por fonte, **quanto ela contribui no resultado** (valor + **% do resultado** com barra),
de modo que as três **somam exatamente** o resultado líquido. O rateio é uma **escolha** (custo geral não é
"causado" por uma fonte); usei o critério proporcional, o mais comum.

### Arquivos alterados
- `core/views.py` (`financeiro_view`): calcula `contribuicao` (líquido de cada fonte − rateio dos custos gerais,
  contribuição, % e largura da barra) e `custos_gerais_total`; adiciona ao contexto.
- `templates/core/financeiro.html`: card `.fin-contrib` (3 fontes + barra de % + linha de total) após o quadro
  "Como o resultado líquido se forma".
- `static/css/financeiro.css`: estilos do card (barras nas cores das fontes: azul/verde/amarelo).

### Validação
- `manage.py check` OK. Render (test client, Diretor): quadro presente com Mensalidades **R$ 1.941,97 (47,5%)**,
  Loja **R$ 494,67 (12,1%)**, Eventos **R$ 1.648,34 (40,4%)**, somando **R$ 4.084,98**; barras 48/12/40%.

### Pendências
- Sem novas. (Critério de rateio dos custos gerais é ajustável se o clube preferir outro.)

---

## 2026-07-06 - Máscara de moeda pt-BR no "valor recebido" do PDV (troco corrigido)

### Resumo
Estende a máscara de moeda pt-BR ao campo **"Valor recebido (dinheiro)"** dos dois balcões — **PDV de venda**
(`evento_pdv.html`) e **PDV de inscrição** (`evento_pdv_inscricao.html`). Como o campo agora mostra
`1.234,56`, o **cálculo de troco ao vivo** foi ajustado: em vez de `parseFloat(value.replace(",","."))` — que
**quebraria** com o separador de milhar (`"1.234,56"` → `1.234`) — o JS passou a ler **os dígitos como
centavos** (`value.replace(/\D/g,"")/100`), batendo exatamente com o valor exibido. Back-end inalterado (já
fazia `replace(",",".")` e trata vazio/ inválido).

### Arquivos alterados
- `templates/core/evento_pdv.html` e `evento_pdv_inscricao.html`: `valor_recebido` vira `type=text data-moeda`;
  ambos carregam `moeda_br.js`.
- `static/js/evento_pdv.js` e `evento_insc_cupom.js`: leitura do recebido por dígitos/centavos (não `parseFloat`).

### Validação
- `manage.py check` OK. Render (test client, evento futuro temporário): ambos os PDVs carregam `moeda_br.js` e o
  recebido vem `type=text data-moeda`. Simulação do parse: `"1.234,56"` → `1234.56` (o antigo dava `1.234`).
  POST de venda em dinheiro (item R$ 35,00, recebido `50.00`): pedido criado com **total 35,00 · recebido 50,00
  · troco 15,00**. (Evento/produto temporários removidos após o teste.)

### Pendências
- Sem novas.

---

## 2026-07-06 - Máscara de moeda pt-BR nos preços de produto e custos de evento (fecha a pendência)

### Resumo
Fecha a pendência recorrente "aplicar a **máscara de moeda pt-BR** também aos **preços de produto da loja**
e aos **custos de evento** (ainda `type=number`)". Agora **todos** os campos de valor R$ do sistema usam o
padrão `moeda_br.js` (mostram `1.234,56` ao digitar e enviam o valor limpo `1234.56`). Migrados:
- **Loja do Clube** — preço da variação (`_loja_var_linha.html`).
- **Lojinha de evento** — preço da variação (`_variacao_linha.html`).
- **Evento** — **custo** (modal, `CustoEventoForm.valor`), **faixa etária** (`FaixaEtariaPrecoForm.valor`) e
  **valor da diretoria** (`EventoInscricaoConfigForm.valor_diretoria`).

Para cobrir os campos renderizados pelo Django e as **linhas de variação adicionadas por JS**, o
`moeda_br.js` ganhou um **modo inline**: um único `input[type=text] data-moeda` (sem campo oculto) formata
enquanto digita e é **normalizado para o valor limpo pouco antes do `submit`** (listener global em captura,
que ignora os campos do modo par visível+oculto, com `data-moeda-alvo`). Assim o back-end **não muda**
(continua recebendo `1234.56`; o parser das variações já fazia `replace(",", ".")`).

### Arquivos alterados
- `static/js/moeda_br.js`: modo inline (normalização no `submit`, em captura) + doc dos dois modos.
- `core/forms.py`: `CustoEventoForm.valor`, `FaixaEtariaPrecoForm.valor` e `EventoInscricaoConfigForm.valor_diretoria`
  passam de `NumberInput` para `TextInput` com `data-moeda`/`inputmode=decimal`/`placeholder=0,00`.
- `templates/core/_loja_var_linha.html` e `_variacao_linha.html`: preço vira `type=text data-moeda` (o
  `<template>` de clonagem usa os mesmos parciais, então linhas novas já nascem com a máscara).
- `templates/core/evento_painel.html`, `loja_produto_form.html`, `evento_produto_form.html`: carregam
  `moeda_br.js`.

### Decisões tomadas
- **Modo inline** em vez de par visível+oculto para os campos de formulário Django e as linhas repetíveis —
  evita ter de gerar um `<input hidden>` por linha e mantém a renderização padrão do Django (com erros do
  form). O modo par (com `data-moeda-alvo`) continua para os modais de custo do Financeiro/Loja.
- `valor_recebido` do PDV (troco ao vivo) e campos de **percentual/idade/estoque/quantidade** ficam como
  estão (não são preço em R$).

### Validação
- `manage.py check` OK. Render (test client, Diretor): as 3 telas carregam `moeda_br.js`; preço da loja e da
  lojinha de evento com `type=text data-moeda` (sem `type=number` sobrando); painel do evento com 3 campos
  `data-moeda` e nenhum `type=number step=0.01`. Forms validam com valor limpo: custo `1234.56`, faixa
  `40.00`, diretoria `25.50` (POST do custo gravou `1234.56`).

### Pendências
- Sem novas. (Todos os campos de valor R$ agora usam a máscara.)

---

## 2026-07-06 - Financeiro: quadro "Como o resultado líquido se forma" (esclarece a soma)

### Resumo
> Registro retroativo (o commit `d0fc5d8` foi feito sem atualizar os docs).

Os líquidos das 3 fontes não somavam sozinhos o resultado porque há os **custos gerais do clube** (que saem
do caixa comum). Adiciona um **quadro de composição** explícito na aba Resumo do Financeiro:
`mensalidades + loja + eventos − custos gerais = resultado líquido`, com nota explicativa. O rótulo dos cards
de fonte muda de "líquido no caixa" para **"líquido da fonte"**.

### Arquivos alterados
- `templates/core/financeiro.html`: quadro `.fin-composicao` (lista dos líquidos por fonte − custos gerais =
  resultado) + nota; rótulo dos cards → "líquido da fonte".
- `static/css/financeiro.css`: estilos do quadro de composição.

---

## 2026-07-06 - Financeiro: líquido por fonte + custos da loja + reclassificação + fluxo ao fundo

### Resumo
O clube tem **uma conta só**, então os cards de resumo agora mostram o **líquido de cada fonte** (quanto do
dinheiro no caixa é de cada uma): **Mensalidades** (recebido), **Loja** (vendas − custos da loja),
**Eventos** (entradas − custos de evento) e **Custos gerais do clube** (gastos que não são de loja/eventos).
Os líquidos **somam o Resultado líquido** total. Para isso, o **custo do clube ganhou `destino`** (Geral do
clube / Loja): custo com destino "loja" abate no líquido da loja. A **loja** ganhou, na aba Vendas, uma seção
**"Custos / pagamentos da loja"** (pagamento de fornecedores, ex.: uniformes) com o **resultado da loja** e um
botão **"Lançar custo da loja"** (modal, valor com máscara, comprovantes). **Reclassificados** os custos
importados: *Pagamento Uniformes de Gala* → **loja**; *Aluguel Decoração Acampamento* → **custo do evento**
Acampamento (movido para `CustoEvento`); os demais seguem como **gerais**. Ajuste visual: o gráfico de **fluxo
mensal** foi empurrado para a **base do card** (sem espaço em branco embaixo).

### Arquivos alterados
- `core/models.py`: `CustoClube.destino` (geral/loja; mig. **0027**). `core/forms.py`: campo `destino`.
- `core/views.py`: `financeiro_view` (líquido por fonte usando destino), `custo_clube_novo_view` (volta à
  loja quando destino/`de`=loja), `loja_view` (custos da loja + resultado).
- `templates/core/financeiro.html`: cards com líquido + tag; destino no modal de custo.
- `templates/core/loja.html`: seção "Custos/pagamentos da loja" + modal (máscara + comprovantes) na aba Vendas.
- `static/css/financeiro.css` (líquido/fluxo ao fundo) e `static/css/loja.css` (custos da loja).

### Decisões tomadas
- Custo de **evento** vira `CustoEvento` (aparece no painel do evento e no Financeiro); custo de **loja** é
  `CustoClube` com destino=loja; o resto é `CustoClube` geral. Os líquidos por fonte somam o resultado total.

### Pendências
- Máscara pt-BR nos **preços de produto da loja** e **custos de evento** (ainda `type=number`).

---

## 2026-07-06 - Financeiro: ajustes (custos importados, KPI, cards, custo em modal, máscara R$, extrato)

### Resumo
Vários ajustes no Financeiro: (1) KPI "Resultado" → **"Resultado líquido"**. (2) **Importados os custos do
clube** do sistema antigo (`financeirocomprovante`: 14 lançamentos, R$ 5.066,60, com comprovantes) — antes
estava zerado. (3) **Donut** de entradas por fonte **centralizado** no card e os dois cards de gráfico com a
**mesma altura**; nos cards de resumo por fonte, os botões "Ver …" ficam **fixos no rodapé**. (4) **Custos do
clube**: a aba agora tem só o botão **"➕ Lançar custo"** que abre um **modal**; sem campo de data (usa a data
do lançamento); permite **vários comprovantes** por custo (novo modelo `ComprovanteCustoClube`). (5) **Máscara
de moeda pt-BR** (`moeda_br.js`): campos de valor formatam `1.234,56` ao digitar e enviam o valor limpo —
aplicada ao custo do clube e aos valores de mensalidade (padrão documentado no CLAUDE.md). (6) **Corrigido o
extrato**: os **filtros por fonte** (chips) e a **busca** não escondiam nada — `.fin-lanc` tinha `display:flex`
sobrepondo o atributo `hidden`; corrigido com `.fin-lanc[hidden]{display:none}`.

### Arquivos criados/alterados
- `core/models.py`: `ComprovanteCustoClube` (mig. **0026**). `core/forms.py`: `CustoClubeForm` sem data/
  comprovante único. `core/admin.py`: inline de comprovantes.
- `core/views.py`: `custo_clube_novo_view` (data automática + múltiplos comprovantes); extrato usa 1º
  comprovante.
- `templates/core/financeiro.html`: KPI, custos via modal, comprovantes múltiplos; `mensalidades.html`: valores
  com máscara. `static/js/moeda_br.js` (novo); `financeiro.js` (abre modal); `financeiro.css` (donut/alturas/
  rodapé/`[hidden]`).

### Pendências
- Aplicar a máscara pt-BR também aos **preços de produto da loja** e **custos de evento** (ainda `type=number`).

---

## 2026-07-05 - Módulo Financeiro geral (mensalidades + loja + eventos + custos do clube)

### Resumo
Novo item **"Financeiro"** (📈, só Diretor) que **consolida as três frentes** — mensalidades, loja e eventos —
num só lugar. Tem **KPIs** (Entradas, Saídas, Resultado com selo positivo/negativo), **3 abas**:
- **Resumo**: **resumo por fonte** (cards de Mensalidades, Loja, Eventos com inscrições/lojinha/custos/
  resultado, e Custos do clube), **donut** de entradas por fonte e **gráfico de fluxo mensal** (entradas ×
  saídas por mês, CSS puro).
- **Extrato**: **extrato consolidado único** (mensalidades pagas, compras da loja, inscrições e lojinha de
  eventos como entradas; custos de evento e do clube como saídas), **cronológico**, com **filtro por fonte**
  (chips) + busca; cada lançamento com data, badge da fonte, valor (+verde/−vermelho) e link do comprovante.
- **Custos do clube**: **lançar** gastos gerais do clube (descrição, valor, data, **comprovante** anexo) e
  listar/remover — igual aos custos de evento, mas do clube.
Tudo responsivo (mobile/desktop). Números batem com cada módulo (entrada por lá para detalhes finos).

### Arquivos criados/alterados
- `core/models.py`: modelo **`CustoClube`** (nome, valor, data, comprovante). Migration **0025**.
- `core/forms.py`: `CustoClubeForm`. `core/admin.py`: `CustoClube`.
- `core/views.py`: `financeiro_view` (agrega as 3 fontes + custos, monta resumo/extrato/fluxo/donut),
  `custo_clube_novo_view`, `custo_clube_excluir_view`, helper `_dt_data`.
- `core/urls.py`: rotas `financeiro/…`. `templates/core/_menu.html`: item "Financeiro" (📈, Diretor).
- `templates/core/financeiro.html`; `static/js/financeiro.js`; `static/css/financeiro.css`.

### Decisões tomadas
- **Um extrato único** com filtro por fonte (em vez de extratos separados) — mais fácil de ver o todo e
  segmentar quando quiser. Entradas = mensalidades pagas + loja + (inscrições + lojinha de eventos); Saídas =
  custos de evento + custos do clube. Cancelados não entram. Custos do clube ficam em `media/` (git-ignored).

### Pendências
- Filtro por período/ano no extrato; exportar; gráficos por evento. Financeiro é consolidação — o detalhe fino
  fica em cada módulo.

---

## 2026-07-05 - Mensalidades: aventureiro inativo não interfere nos totais (mantém só dados anteriores)

### Resumo
Aventureiro **inativo** deixou de interferir no resumo/relatório de mensalidades — ficam só os **dados de
antes** de ele ficar inativo. Regra: **Recebido** conta **todas as cobranças pagas** (histórico, mesmo de
quem depois saiu); **Em aberto/Previsto** contam **só de aventureiros ativos**. Antes, os totais ignoravam os
pagamentos de inativos (some da lista) e o dashboard ainda somava as cobranças em aberto deles — agora está
consistente. O **reajuste em massa** também **pula inativos**. (Loja e eventos já respeitavam: a loja usa
registros históricos das compras; a cobertura/presença de eventos contam só ativos.) Os aventureiros da conta
de **teste** foram marcados **inativos** (a conta `teste_responsavel` segue ativa para os testes).

### Arquivos alterados
- `core/views.py`: `mensalidades_view` (totais: recebido = todos os pagos; em aberto = só ativos),
  `_mensalidades_dashboard` (idem por mês) e `mensalidade_reajustar_view` (só `aventureiro__ativo=True`).

---

## 2026-07-05 - Mensalidades: valores/reajuste viram botões+modais; oculta meses sem cobrança

### Resumo
A barra ficava poluída com os formulários de "Valores padrão" e "Reajustar" inline. Agora são **dois botões**
claros — **"💲 Valores da mensalidade"** e **"🔁 Reajustar mensalidades"** — que abrem **janelas (modais)**
com o respectivo formulário e um texto explicando o que faz (fechamento seguro mousedown+click). No dashboard,
os **cards de "Detalhe por mês"** deixam de mostrar os meses **sem cobrança** (ex.: Janeiro não aparece mais).

### Arquivos alterados
- `templates/core/mensalidades.html`: barra com 2 botões + modais "Valores"/"Reajustar"; cards só de meses
  com cobrança.
- `static/js/mensalidades.js`: `ligarModalBotao` (abre/fecha os modais por botão, com fechamento seguro).
- `static/css/mensalidades.css`: barra de ações e formulários dos modais.

---

## 2026-07-05 - Mensalidades: "Detalhe por mês" vira cards didáticos (corrige tabela sem estilo)

### Resumo
No dashboard, o "Detalhe por mês" era uma **tabela sem estilo** (usava classe da loja não carregada aqui).
Trocado por **cards mês a mês** mais didáticos: cada mês mostra a **% paga** com **barra de progresso
colorida** (verde ≥80%, amarelo ≥40%, vermelho abaixo), **nº de pagas / em aberto / isentos** e os valores
**recebido / a receber**. Meses sem cobrança aparecem esmaecidos ("Sem cobranças"). Nota deixando claro que o
resumo **conta inscrições + mensalidades**.

### Arquivos alterados
- `core/views.py`: `_mensalidades_dashboard` inclui `cor` (faixa de desempenho) por mês.
- `templates/core/mensalidades.html`: tabela → grade de cards mês a mês.
- `static/css/mensalidades.css`: estilos dos cards (barra de progresso colorida, contagens, valores).

---

## 2026-07-05 - Mensalidades: reajuste em massa a partir de um mês + modais não fecham ao arrastar

### Resumo
Dois pontos: (1) **Reajuste em massa** — na barra de valores há agora "🔁 Aplicar os valores atuais às
cobranças **em aberto** a partir de [mês]" + **Reajustar**: recalcula todas as cobranças **em aberto** do ano,
do mês escolhido em diante, com o **valor atual da configuração** (respeitando isenção/desconto de cada
aventureiro; **pagas não mudam**). Assim dá para "a partir do próximo mês a mensalidade passa a ser R$ X para
todos". (2) **Correção de modais**: o modal de editar mês (mensalidades) e os modais da loja (aviso de
obrigatórios e lightbox) fechavam ao **arrastar uma seleção de dentro para fora**; agora só fecham se o clique
**começar e terminar no fundo** (padrão `mousedown`+`click`, [[modais-fechamento-seguro]]).

### Arquivos alterados
- `core/views.py`: `mensalidade_reajustar_view`; contexto ganha `meses`/`mes_atual`. `core/urls.py`: rota.
- `templates/core/mensalidades.html`: form de reajuste na barra. `static/css/mensalidades.css`: estilo.
- `static/js/mensalidades.js` e `static/js/loja_produto.js`: fechamento seguro dos modais (mousedown+click).

---

## 2026-07-05 - Mensalidades: dashboard mês a mês (abas Resumo / Aventureiros)

### Resumo
A tela de Mensalidades ganhou **abas**: **Resumo** (dashboard) e **Aventureiros** (a lista operacional que já
existia). O **Resumo** mostra a visão geral do ano: um **donut de taxa de pagamento** (recebido ÷ previsto)
com a legenda recebido × em aberto, um **gráfico de barras mês a mês** (recebido em verde, em aberto em
amarelo, empilhados; CSS puro, sem libs; rolagem horizontal no celular) e uma **tabela "Detalhe por mês"**
(pagas, em aberto, recebido, a receber, % pago, com linha de total). Tudo respeita o **ano** selecionado.

### Arquivos alterados
- `core/views.py`: `_mensalidades_dashboard(mens)` (agrupa por mês: recebido/aberto/% + alturas das barras);
  `mensalidades_view` passa `dashboard`, `taxa` e `aba`.
- `templates/core/mensalidades.html`: abas + painel Resumo (donut, gráfico, tabela); lista vira painel
  "Aventureiros".
- `static/js/mensalidades.js`: alternância das abas (com `?aba=`). `static/css/mensalidades.css`: abas,
  donut (conic-gradient), gráfico de barras, tabela.

---

## 2026-07-05 - Mensalidades: edição por mês vira desconto % (com valor ao vivo) + remove "Gerar cobranças"

### Resumo
Refinos a pedido do usuário: (1) no modal de edição por mês, em vez de digitar o valor, agora se informa a
**% de desconto** e o **valor resultante aparece ao vivo** ("Ficará: R$ X — valor cheio: R$ Y"); "Isentar
este mês" = 100%. O servidor calcula o valor a partir do **valor cheio** (config) × (1 − %). (2) **Removido o
botão "Gerar cobranças <ano>"** do topo — desnecessário, pois o cadastro do aventureiro já gera as cobranças
do mês atual até dezembro automaticamente. (A geração por aventureiro sem cobranças continua disponível.)

### Arquivos alterados
- `core/views.py`: `mensalidade_editar_view` passa a receber `desconto_pct` e calcular o valor a partir da base.
- `templates/core/mensalidades.html`: modal com "% de desconto" + preview; `data-base` no botão ✏️; remove
  a barra "Gerar cobranças".
- `static/js/mensalidades.js`: preview ao vivo (base × desconto). `static/css/mensalidades.css`: preview.

---

## 2026-07-05 - Mensalidades: import do histórico + isenção/desconto por mês + valores visíveis

### Resumo
Três ajustes: (1) **Importado o histórico** de mensalidades do sistema antigo (352 cobranças de 2026, **104
pagas**, R$ 3.120 recebido; casadas pelo **nome** do aventureiro — pulou só 1 registro "teste"). As
cobranças respeitam os meses reais (ex.: quem entrou em fevereiro tem Fev=inscrição em diante). (2) **Isenção/
desconto por mês específico**: cada mês em aberto tem um botão **✏️** que abre um modal para **mudar o valor
daquele mês** (desconto pontual) ou **isentar só aquele mês** (endpoint `mensalidade_editar`). Continua
existindo a isenção/desconto do aventureiro inteiro. (3) **Valores padrão** agora aparecem preenchidos
(R$ 30,00) — antes o `<input type=number>` rejeitava o decimal localizado e ficava vazio; corrigido com
`stringformat`.

### Arquivos alterados
- `core/views.py`: `mensalidade_editar_view` (edita/isenta um mês; não mexe em pagas). `core/urls.py`: rota.
- `templates/core/mensalidades.html`: botão ✏️ por mês + modal de edição; inputs de valores padrão com
  `stringformat:'.2f'` (mostram o valor).
- `static/js/mensalidades.js`: abrir/preencher o modal de edição. `static/css/mensalidades.css`: botão e modal.

### Decisões tomadas
- Import é **fonte da verdade** de 2026 (apaga as cobranças e recria a partir do antigo). Dados ficam no
  banco local (não versionados). Edição por mês não altera cobranças **pagas** (desfazer o pagamento antes).

---

## 2026-07-05 - Módulo Mensalidades

### Resumo
Novo módulo **"Mensalidades"** (💰, só Diretor), separado do financeiro. Cada aventureiro tem, por mês do
ano, uma **cobrança**: o mês em que se inscreve nasce como **"inscrição"** e os meses seguintes como
**"mensalidade"** (gerado **automaticamente** no cadastro). **Valores configuráveis** (padrão R$ 30 cada, em
`ConfigMensalidade`). Aventureiros podem ser **isentos** ou ter **desconto %** — aplicável às cobranças em
aberto. Tela com **KPIs** (previsto/recebido/em aberto/isentos do ano), **seletor de ano**, botão **"Gerar
cobranças <ano>"** (todos ou um), e por aventureiro (card expansível) os **12 meses** com **marcar pago/
desfazer** (forma de pagamento, sem recarregar) + controle de isenção/desconto. **Busca** e filtro **"Só quem
deve"**. Contas de mensalidade ficam no banco local (não versionadas).

### Arquivos criados/alterados
- `core/models.py`: `ConfigMensalidade` (singleton) e `Mensalidade` (aventureiro, ano, mês, tipo, valor,
  isento, status, forma/valor_pago/pago_em); campos `Aventureiro.mensalidade_isento` e
  `mensalidade_desconto_pct`; constantes `MESES_PT`. Migration **0024**.
- `core/views.py`: `_gerar_mensalidades`/`_valor_mensalidade`/`_resumo_mensalidades`/`_fmt_moeda`;
  `mensalidades_view`, `mensalidade_config_view`, `mensalidades_gerar_view`, `mensalidade_pagar_view` (JSON),
  `mensalidade_isencao_view`; geração automática no `_salvar_aventureiro` (cadastro).
- `core/urls.py`: rotas `mensalidades/…`. `core/admin.py`: `Mensalidade`/`ConfigMensalidade`.
- `templates/core/_menu.html`: item "Mensalidades" (💰, Diretor).
- `templates/core/mensalidades.html`; `static/js/mensalidades.js`; `static/css/mensalidades.css`.

### Decisões tomadas
- Uma `Mensalidade` por (aventureiro, ano, mês) — controle simples de pago/aberto (sem agregador de
  pagamento por ora). Isenção/desconto ficam no aventureiro e são reaplicados às cobranças **em aberto**
  (as **pagas** não mudam). Geração é **idempotente**.

### Pendências
- Importar o **histórico de mensalidades** do sistema antigo (360 cobranças + pagamentos) — precisa mapear
  aventureiro antigo→novo. Cobrança/lembrete por WhatsApp. Financeiro geral consolidando as 3 áreas.

---

## 2026-07-05 - Loja/Vendas: remove os chips por produto (redundantes com a busca)

### Resumo
A pedido do usuário, os **chips por produto** em "Todas as compras" foram **removidos** — davam o mesmo
resultado de digitar o nome do produto na busca. Ficaram só o **campo de busca** e o **"Só a entregar"**.
Removidos a marcação `data-produtos`, o JS e o CSS dos chips. (As demais mudanças do relatório — "mais
vendidos" por pedido/unidade e "Média por compra" — foram mantidas.)

### Arquivos alterados
- `templates/core/loja.html`: remove a barra de chips e o `data-produtos`.
- `static/js/loja.js`: remove o filtro por chip (mantém busca + "só a entregar").
- `static/css/loja.css`: remove os estilos `.loja-chips`/`.loja-chip`.

---

## 2026-07-05 - Loja/Vendas: "Mais vendidos" por pedido (composto) + chips por produto + rótulo do ticket

### Resumo
Ajustes no relatório da aba Vendas: (1) **"Mais vendidos"** — produto **composto** (Uniforme de Gala) agora
conta **por pedido** (cada pedido que levou o produto = 1), pois tem vários itens obrigatórios; produtos
**simples** (Camiseta, Laço) seguem contando por **quantidade** de unidades (ex.: 2 tamanhos no mesmo pedido
= 2). A coluna mostra a **unidade** ("9 pedido(s)" / "14 un."). (2) **Chips por produto** ("Todos · <produto>…")
acima de "Todas as compras": clicar mostra só os pedidos que contêm aquele produto (um pedido misto aparece
em mais de um) — jeito leve de segmentar sem formulário de filtro. (3) O KPI "Ticket médio" virou **"Média por
compra"** com dica (arrecadado ÷ nº de compras).

### Arquivos criados/alterados
- `core/views.py`: `_loja_relatorio` recalcula "mais vendidos" (composto = por pedido; simples = por unidade),
  ordenado por total.
- `templates/core/loja.html`: coluna "Vendidos" com unidade; KPI "Média por compra" + dica; chips de produto
  (`#lojaChips`) e `data-produtos` em cada compra.
- `static/js/loja.js`: filtro por chip integrado à busca/"só a entregar".
- `static/css/loja.css`: estilos dos chips.

### Decisões tomadas
- Composto conta **por pedido** (via distintas compras que contêm o produto) — robusto mesmo com os pedidos
  importados; simples conta por unidade. Ordenação por **total (R$)** por serem unidades diferentes.

---

## 2026-07-05 - Loja/Vendas: entrega por pedido ("Entregar tudo") + filtro "Só a entregar"

### Resumo
Refino da entrega na aba **Vendas**, a pedido do usuário: a seção separada **"A entregar"** (que virava uma
lista enorme) foi **removida**. Agora tudo acontece dentro de **"Todas as compras"** (ordenadas por data):
cada compra mostra o **selo** de entrega e, ao expandir, tem os **toggles por item** e um botão **"Entregar
tudo"** (entrega/desfaz todas as variações do pedido de uma vez — ideal para o Uniforme de Gala). Adicionado
o filtro **"Só a entregar"** ao lado da busca, para achar rápido os pedidos pendentes. Os KPIs e o "Mais
vendidos"/"Por forma" continuam.

### Arquivos criados/alterados
- `core/views.py`: `loja_entrega_compra_view` (marca/desmarca todos os itens de uma compra; JSON).
- `core/urls.py`: rota `loja/entrega/compra/`.
- `templates/core/loja.html`: remove a seção "A entregar"; adiciona botão "Entregar tudo" por compra,
  `data-pendente` no card e o filtro "Só a entregar".
- `static/js/loja.js`: handler do "Entregar tudo" (atualiza selo, botão e todos os toggles) + filtro
  combinado (busca + só pendentes).
- `static/css/loja.css`: estilos do filtro e do botão "Entregar tudo" (verde quando há o que entregar).

### Decisões tomadas
- Entrega segue por **item** (toggle) **ou por pedido inteiro** ("Entregar tudo"); nada de lista global —
  o Diretor abre o pedido marcado como "A entregar" e resolve ali.

---

## 2026-07-05 - Loja: aba "Vendas" (relatório + entrega) + importação dos pedidos pagos do sistema antigo

### Resumo
Nova aba **"Vendas"** (📊, Diretor) na tela da Loja, com **relatório** e controle de entregas: **KPIs**
(arrecadado, nº de compras, ticket médio, itens a entregar), **Mais vendidos** (por produto: qtd + total),
**Por forma de pagamento**, uma seção **"A entregar"** (itens pendentes, com botão de entregar) e **Todas as
compras** — lista detalhada e **buscável** (nome/código/produto) com todos os dados (comprador, WhatsApp,
e-mail, login, data, forma) e **marcar entrega por item** (toggle sem recarregar, via JSON). As "compras
recentes" saíram do Gerenciar (que ficou só com produtos). Adicionado **controle de entrega** ao
`ItemCompraLoja` (`quantidade_entregue`/`entregue_em`/`entregue_por` + props; mig. **0023**) e ao
`CompraLoja` (props `status_entrega`/`falta_entregar_total`). Endpoint `loja_entrega` (POST/JSON, Diretor).

Também **importados os pedidos pagos** da loja oficial do sistema antigo (21 compras, R$ 3.083,50, todas Pix;
19 vinculadas a um login), com comprador, forma, **data original** e o **status de entrega** preservados
(código `LM<id>`, idempotente). Só pedidos **pagos**, **não-teste**, da **loja oficial** (evento=None) e com
produto do clube.

### Arquivos criados/alterados
- `core/models.py`: `ItemCompraLoja` ganha `quantidade_entregue`/`entregue_em`/`entregue_por` + props
  (`entregue`/`entrega_parcial`/`status_entrega`/`falta_entregar`); `CompraLoja` ganha `status_entrega` e
  `falta_entregar_total`. Migration **0023**.
- `core/views.py`: `_loja_relatorio()` (KPIs + mais vendidos + por forma + pendentes), `loja_entrega_view`
  (toggle JSON) e `loja_view` passa `relatorio`.
- `core/urls.py`: rota `loja/entrega/`.
- `templates/core/loja.html`: aba "Vendas" (KPIs, tabelas, "A entregar", "Todas as compras" com busca e
  entrega por item); Gerenciar sem a lista de compras.
- `static/js/loja.js`: toggle de entrega (fetch + `X-CSRFToken`, atualiza selo) e busca nas compras.
- `static/css/loja.css`: KPIs, tabelas do relatório, lista "a entregar", selos/botões de entrega, busca.

### Decisões tomadas
- Entrega por **item** com toggle total (entregar tudo/desfazer); parcial fica para depois (o histórico
  importado preserva a quantidade entregue original).
- Pedidos importados usam código **`LM<id>`** (idempotente) e status `confirmado`; **cancelados/pendentes**
  do antigo **não** entram. Fotos/produtos/pedidos são dados locais (`media/`+banco), não versionados.

### Pendências
- Entrega **parcial** pela tela (stepper), se necessário.
- Vincular item importado ao aventureiro/variação exatos (hoje é snapshot + produto por título).

---

## 2026-07-05 - Loja: galeria de fotos (com lightbox) + correção do estilo dos campos do carrinho

### Resumo
Dois ajustes na Loja do Clube: (1) **galeria de fotos por produto** — um produto pode ter **várias fotos**
(ex.: como fica o uniforme, tabela de tamanhos), com **miniaturas** e **ampliação em tela cheia (lightbox)**
no celular e no PC (setas/teclado/toque, fecha no X/fundo/Esc). No cadastro, **upload múltiplo** e remoção de
fotos; a 1ª é a capa (vitrine/gerenciar). (2) **Correção**: os campos "Dados do comprador" (nome/WhatsApp/
e-mail) no carrinho estavam **sem estilo** porque o CSS de campo é escopado em `.evento-form` e o form do
carrinho não tinha essa classe — adicionada nele e no form de configuração do produto.

Também foi **importado o "Uniforme de Gala - Aventureiro (Completo)"** do sistema antigo (produto 7): **61
variações** em 3 grupos (Camiseta escolha única/obrigatório; Calça/Saia escolha única/obrigatório — calça
meninos, saia meninas; Acessórios em itens, cada um obrigatório) + as **5 fotos** da galeria. Preços exatos.
As fotos ficam **só em `media/`** (git-ignored), como as fotos dos membros.

### Arquivos criados/alterados
- `core/models.py`: modelo **`FotoProdutoLoja`** (galeria) + property **`ProdutoLoja.capa`** (1ª foto/legado).
  Migration **0022**.
- `core/forms.py`: `ProdutoLojaForm` deixa de ter o campo único `foto` (galeria via upload múltiplo na view).
- `core/views.py`: `_produto_loja_form` trata upload/remoção de fotos (`_salvar_fotos_loja`); `loja_produto_view`
  e `loja_view` passam/prefetch as fotos.
- `core/admin.py`: inline `FotoProdutoLojaInline` em `ProdutoLoja`.
- `templates/core/loja_produto.html`: galeria (principal + miniaturas) + **lightbox**; form de config com `evento-form`.
- `templates/core/loja_produto_form.html`: seção "Fotos do produto" (existentes + remover + upload múltiplo).
- `templates/core/loja.html`: cards usam `capa`; badge "📷 N" na vitrine; form do carrinho com `evento-form` (fix).
- `static/js/loja_produto.js`: galeria + lightbox (miniaturas, setas, teclado, fechar).
- `static/css/loja.css`: galeria, miniaturas, lightbox, gerenciador de fotos e badge.

### Decisões tomadas
- Galeria em modelo próprio (`FotoProdutoLoja`), sem foto por variação por ora (as fotos do antigo eram
  `todas_variacoes=True`). A capa é a 1ª foto (ou o antigo `foto`, mantido só como fallback).
- Fotos reais do uniforme/tabelas ficam **apenas em `media/`** (git-ignored), nunca versionadas.

### Pendências
- Fotos por variação (se um dia quiserem foto por tamanho/cor) — hoje é galeria do produto.

---

## 2026-07-05 - Loja do Clube (loja oficial): cadastro, vitrine com carrinho e pagamento simulado

### Resumo
Novo módulo **Loja do Clube** (loja oficial — uniformes, lenços etc.), **independente** da lojinha de
evento e primeira das 3 áreas financeiras do clube (eventos ✅, mensalidades ⏳, loja ▶). Item novo
**"Loja"** (🛍️) no menu, **só Diretor** por ora. Tela com **2 abas**: **Gerenciar** (cadastro de produtos +
compras recentes) e **Loja** (vitrine com carrinho). Estrutura de produto em 3 níveis **Produto → Grupos →
Variações**: produto **simples** (uma lista de opções, como no evento) ou **composto** (vários grupos —
ex.: Uniforme de Gala = Camiseta [escolha única] + Calça/Saia [escolha única] + Acessórios [itens]). Cada
grupo é "escolha única" ou "itens", com **obrigatório** sim/não e **orientação**; itens podem ser
**obrigatórios** (aviso **soft** na vitrine — avisa o que falta e pergunta se já tem, mas **não bloqueia**).
**Carrinho na sessão** (não perde a seleção ao recarregar; o configurador ainda salva rascunho em
localStorage). A compra fica **vinculada ao login** e, opcional, a um **aventureiro** (1 = automático; 2+ =
escolher — útil pro bordado do Kit Nome). **Pagamento simulado** (Pix com QR/copia-e-cola + cartão com aviso
de Mercado Pago), reaproveitando os helpers da lojinha de evento; a `CompraLoja` só é criada após a
aprovação. Diretor pode **cancelar** compra (devolve estoque). Referência: produto 7 ("Uniforme de Gala")
do sistema antigo (flag `permite_multiplas_variacoes` + `obrigatoria_compra`).

### Arquivos criados/alterados
- `core/models.py`: novos modelos `ProdutoLoja`, `GrupoLoja`, `VariacaoLoja`, `CompraLoja`, `ItemCompraLoja`
  + `MODO_GRUPO_CHOICES`. Migration **0021**.
- `core/forms.py`: `ProdutoLojaForm`.
- `core/views.py`: bloco da Loja (cadastro de grupos/variações, vitrine, carrinho na sessão, finalizar,
  pagamento simulado, sucesso, cancelar) + helpers (`_parse_grupos_loja`, `_salvar_grupos_loja`,
  `_loja_cart_detalhado`, `_criar_compra_loja`, `_aventureiros_do_usuario`, `_comprador_padrao` etc.).
  Reaproveita `_qr_svg`/`_pix_copia_cola`/`FORMAS_PAGAMENTO_ONLINE`.
- `core/urls.py`: rotas `loja`, `loja_produto`, `loja_produto_novo/editar/excluir`, `loja_carrinho_add`,
  `loja_carrinho_remover`, `loja_finalizar`, `loja_pagamento`, `loja_sucesso`, `loja_compra_cancelar`.
- `core/admin.py`: `ProdutoLoja`/`GrupoLoja`/`CompraLoja` (com inlines).
- `templates/core/_menu.html`: item "Loja" (🛍️, só Diretor).
- Templates novos: `loja.html`, `loja_produto_form.html`, `loja_produto.html`, `loja_pagamento.html`,
  `loja_sucesso.html`, `_loja_grupo.html`, `_loja_var_linha.html`.
- Estáticos novos: `static/css/loja.css`; `static/js/loja.js`, `loja_produto_form.js`, `loja_produto.js`.

### Decisões tomadas
- Modelos **novos e independentes** dos da lojinha de evento (sem PDV/balcão/check-in nem FK de evento);
  nomes distintos (`CompraLoja`/`ItemCompraLoja`) para não colidir com `PedidoLoja`/`ItemPedidoLoja`.
- Item obrigatório é **aviso soft** (client-side, modal de confirmação) — a pessoa pode já ter o item.
- **Carrinho na sessão** (chave `loja_carrinho`); checkout na sessão (chave `loja_clube_checkout`, distinta
  da `loja_checkout` do evento). `CompraLoja` só nasce após a aprovação (sem "pendente" no banco).
- Menu **só para Diretor** por ora; as views da vitrine já são `@login_required` para abrir a responsáveis
  depois sem retrabalho.

### Pendências
- Abrir a loja aos **responsáveis** (mostrar o item no menu para eles) — hoje só Diretor.
- Pagamento **real** (gateway) — base pronta e simulada.
- Migrar o **Uniforme de Gala** e demais produtos reais do sistema antigo.
- **Financeiro geral** consolidando eventos + mensalidades + loja (futuro); **mensalidades** (a fazer).

---

## 2026-07-05 - Login por AJAX (senha errada só repete o toast) + componente genérico ajax_form.js

### Resumo
A pedido do usuário, o **login** passou a enviar por **AJAX** igual às telas de recuperação: com **senha
errada**, a notificação (toast) **repete a cada clique sem recarregar** a página; com senha certa, o JS
navega para o destino. O helper de AJAX virou um **componente genérico**: `recuperar.js` foi renomeado
para **`ajax_form.js`** e o atributo `data-ajax-recup` para **`data-ajax-toast`** (usado por login e
recuperação). Sem JS, tudo continua funcionando com POST normal.

### Arquivos criados/alterados
- `static/js/recuperar.js` → **renomeado** para `static/js/ajax_form.js` (agora genérico:
  `form[data-ajax-toast]`).
- `core/views.py`: `login_view` responde JSON quando AJAX (`{"redirect":url}` no sucesso, `{"msg","tipo"}`
  no erro). Helpers `_recup_ir`/`_recup_msg` renomeados para **`_ajax_redirect`/`_ajax_toast`**.
- `templates/core/login.html`: form com `data-ajax-toast` + carrega `ajax_form.js`.
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html`: atributo
  `data-ajax-toast` + `ajax_form.js`.

### Decisões tomadas
- O envio-por-AJAX-com-toast é um **componente reutilizável** (`ajax_form.js` + `data-ajax-toast`), não
  específico da recuperação — por isso o nome genérico.

### Pendências
- Sem novas.

## 2026-07-05 - Recuperação/Login: envio por AJAX (toast sem recarregar) + fim do vazamento de mensagem

### Resumo
Dois ajustes pedidos pelo usuário:
1. **Recuperação por AJAX**: os formulários das telas de recuperação (CPF, código, reenviar, nova senha)
   passam a enviar por **fetch**. Em caso de erro, a notificação (toast) **repete sem recarregar a
   página**; em caso de sucesso, o JS navega para a próxima etapa. Sem JS, os formulários continuam
   funcionando com POST normal (fallback).
2. **Login com o toast padrão + fim do vazamento**: o login agora **renderiza e consome** as mensagens
   (toast). Isso conserta um **vazamento**: a mensagem "Senha redefinida! Faça login…" era enfileirada e,
   como o login não a exibia, ficava **presa na store** e reaparecia depois (inclusive numa tentativa de
   login com senha errada). Agora ela aparece **uma vez** no login (correto) e some. O erro do próprio
   login ("Usuário ou senha inválidos.") também virou toast.

### Arquivos criados/alterados
- `core/views.py`: helpers `_eh_ajax`, `_recup_ir` (JSON `{"redirect":url}`), `_recup_msg`
  (JSON `{"msg","tipo"}`); as 4 views de recuperação respondem JSON quando AJAX (erro → toast; sucesso →
  redirect). `login_view` usa `messages.error` em vez do contexto `erro`.
- `static/js/recuperar.js` (novo): intercepta `form[data-ajax-recup]`, faz o fetch e trata
  `redirect`/`msg` (usa `window.mostrarToast`).
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html`: forms com
  `data-ajax-recup` + carregam `recuperar.js`.
- `templates/core/login.html`: bloco de `.mensagens` (toast) + carrega `inicio.js`; removido o aviso
  inline `.aviso-login`.

### Decisões tomadas
- Contrato JSON das telas de recuperação: `{"redirect": url}` (JS navega; mensagens enfileiradas
  aparecem no destino) ou `{"msg","tipo"}` (só toast, sem recarregar).
- Toda página que é **destino** de um redirect com mensagem precisa **renderizar `messages`** (senão a
  mensagem vaza). Por isso o login passou a renderizar.

### Pendências
- Sem novas. (O `.aviso-login` do `login.css` ficou sem uso; mantido no CSS por ora.)

## 2026-07-05 - Recuperação de senha: espaçamento do indicador de etapas

### Resumo
No indicador de etapas (CPF → Código → Nova senha), o número/✓ (círculo de 26px) estava encostando/
sobrepondo o texto abaixo. Aumentei o `padding-top` do `.recup-passos li` de 22px para **36px**
(26px do círculo + folga). Só CSS.

### Arquivos criados/alterados
- `static/css/recuperar.css`: `.recup-passos li { padding-top: 36px; }`.

## 2026-07-05 - Recuperação de senha: usar o toast padrão (não mais avisos inline)

### Resumo
A pedido do usuário, as telas de recuperação de senha passaram a usar as **notificações padrão do
sistema (toasts)**, e não os avisos inline. Para isso, o **CSS do toast** (`.mensagens`/`.mensagem`)
foi **movido do `inicio.css` para o `base.css`** (componente reutilizável, com fallback de cores),
ficando disponível em **qualquer página** — inclusive as públicas do login/recuperação. As telas de
recuperação agora carregam `inicio.js` (o módulo de toasts é seguro em qualquer página) e todo o
feedback passa pelo framework de `messages`.

### Arquivos criados/alterados
- `static/css/base.css`: recebeu o bloco de **notificações/toasts** (antes em `inicio.css`).
- `static/css/inicio.css`: removido o bloco de toasts (agora só um comentário apontando para o `base.css`).
- `static/css/recuperar.css`: removido o `.aviso-ok` (não é mais usado).
- `core/views.py`: `recuperar_senha_view`, `recuperar_senha_codigo_view`, `recuperar_senha_nova_view`
  usam `messages.error(...)` em vez do contexto `erro`.
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html`: usam o
  markup padrão `.mensagens`/`.mensagem` e carregam `inicio.js`.
- Removido `templates/core/_recup_avisos.html` (não é mais necessário).

### Decisões tomadas
- Toast é **um componente reutilizável** e deve morar no `base.css` (que já hospeda o modal), não no
  `inicio.css`. Confirmado que **toda** página que usa `inicio.css` também carrega `base.css`.

### Pendências
- Sem novas. (A tela de **login** em si continua com o aviso inline `.aviso-login` do jeito que já era.)

## 2026-07-05 - Recuperação de senha pelo WhatsApp (código de 4 dígitos)

### Resumo
O link **"Esqueci minha senha"** (login) passou a funcionar. Fluxo público em **3 etapas**
(guardadas na sessão):
1. **CPF** do responsável legal → identifica a conta (`Aventureiro.resp_cpf`) e envia um **código de
   4 dígitos** para o **WhatsApp principal** da conta (via módulo WhatsApp/W-API).
2. **Código** → validado com **limite de 5 tentativas** e **expiração de 10 min**; botão **reenviar**
   (espera mínima de 60 s).
3. **Nova senha** (2×) → grava e limpa a sessão; volta ao login.
O código é guardado **com hash** na sessão (nunca em texto puro). O número de destino aparece sempre
**mascarado** (`•••••-1234`).

Em **Usuários** (Diretor), no detalhe de cada responsável ligado a uma conta, há o controle
**"WhatsApp principal"**: escolher entre **pai / mãe / responsável legal** para onde o código será
enviado. Sem escolha, o padrão é o **WhatsApp do responsável legal**. (Mais pra frente o próprio
responsável logado poderá alterar.)

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario.whatsapp_principal_origem` (choices pai/mae/resp, blank).
- `core/migrations/0020_perfilusuario_whatsapp_principal_origem.py`.
- `core/views.py`: helpers `_so_digitos`, `_mascara_telefone`, `_numeros_conta`, `_whatsapp_principal`,
  `_conta_por_cpf_resp`, `_recup_gerar_e_enviar`, `_recup_expirado`; views `recuperar_senha_view`,
  `recuperar_senha_codigo_view`, `recuperar_senha_reenviar_view`, `recuperar_senha_nova_view`,
  `usuario_principal_view`; `usuarios_view` passou a anexar `conta_id`/`numeros_principal`/
  `principal_origem` a cada responsável (por CPF, só quando há **uma** conta). Constantes
  `RECUP_TTL_MIN=10`, `RECUP_MAX_TENTATIVAS=5`, `RECUP_REENVIO_ESPERA=60`.
- `core/urls.py`: `/recuperar-senha/`, `.../codigo/`, `.../reenviar/`, `.../nova-senha/` e
  `/usuarios/conta/<id>/principal/`.
- `templates/core/login.html`: link "Esqueci minha senha" aponta para o fluxo.
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html` e o parcial
  `_recup_avisos.html` (mensagens inline nas telas públicas).
- `templates/core/usuarios.html`: bloco **WhatsApp principal** no detalhe do responsável **+ bloco de
  `messages`** (que faltava — agora o toast do toggle ativo/inativo e do principal aparece).
- `static/css/recuperar.css` (indicador de etapas, campo do código, aviso verde, reenviar) e trecho novo
  em `static/css/usuarios.css` (bloco do principal).

### Decisões tomadas
- **Destino do código = WhatsApp principal** definido pelo Diretor (fallback: responsável legal).
  **Opções do principal**: pai, mãe ou responsável legal. **CPF aceito**: só o do responsável legal.
  (Confirmado com o usuário.)
- **Sem novas dependências**: reaproveita `normalizar_telefone` e `_enviar_whatsapp` do módulo WhatsApp
  (urllib). Código gerado com `secrets.randbelow`.
- **Estado na sessão** (não em modelo): simples e sem necessidade de limpeza; código sempre hasheado.
- **Anti-abuso**: expiração, limite de tentativas e espera entre reenvios.

### Pendências
- Permitir que o **responsável logado** altere o próprio WhatsApp principal (hoje só o Diretor).
- Se a conta tiver o mesmo CPF de responsável legal em mais de uma conta, o controle de principal em
  Usuários não aparece (fica a cargo do admin) — caso raro.

## 2026-07-05 - Módulo WhatsApp (W-API): configuração da instância + envio de mensagem

### Resumo
Novo item de menu **WhatsApp** (só Diretor) para integrar a **API da W-API**
(`https://api.w-api.app/v1`). A tela tem duas seções:
1. **Configuração da instância** — campos para o **ID da instância**, o **token** (exibido só com os
   **últimos 4 dígitos**, `••••••3456`; só é substituído se um novo for digitado) e a **URL base**
   (opcional, com o padrão já preenchido). No começo tudo vem em branco, pronto para cadastrar; um
   selo mostra "Não configurado" / "✓ Configurado".
2. **Enviar mensagem** — campos de **número** e **texto**. O número é **normalizado** (aceita espaços,
   traços, parênteses, `+55`, `00…`) para o formato que a API exige (só dígitos, com DDI 55); há uma
   **prévia ao vivo** ("Será enviado para: +55 (47) 99224-9708"). O envio é **AJAX** e usa o **toast
   padrão** do sistema para sucesso/erro. Os campos ficam desabilitados até a instância estar configurada.

### Arquivos criados/alterados
- `core/models.py`: novo model **`WhatsappConfig`** (singleton via `get_solo()`; `instance_id`, `token`,
  `base_url`, `atualizado_por/_em`; propriedades `configurado` e `token_mascarado`).
- `core/migrations/0019_whatsappconfig.py`: cria a tabela.
- `core/views.py`: `whatsapp_view` (tela), `whatsapp_config_view` (salvar — não apaga o token quando o
  campo vem vazio), `whatsapp_enviar_view` (envio AJAX/JSON), helper `normalizar_telefone` e
  `_enviar_whatsapp` (POST na W-API via **urllib** da stdlib, sem novas dependências).
- `core/urls.py`: rotas `/whatsapp/`, `/whatsapp/config/`, `/whatsapp/enviar/`.
- `templates/core/_menu.html`: item **WhatsApp** (💬) dentro de `{% if is_diretor %}`.
- `templates/core/whatsapp.html`: nova tela (mobile-first, cards do sistema).
- `static/js/whatsapp.js`: prévia do telefone, mostrar/ocultar token, envio AJAX + toast.
- `static/css/whatsapp.css`: estilos da tela (paleta azul/verde; inputs próprios; responsivo).

### Decisões tomadas
- **Sem novas dependências**: o POST na W-API usa `urllib.request` (regra do projeto).
- **Token nunca é exibido inteiro**: só os últimos 4 dígitos; para trocar, digita-se um novo (campo
  vazio mantém o token guardado). Botão "Mostrar" ajuda só na hora de colar o novo token.
- **Endpoint** (docs W-API): `POST {base_url}/message/send-text?instanceId=<id>`, header
  `Authorization: Bearer <token>`, body JSON `{"phone","message"}`.
- **Normalização de telefone** feita no back-end (fonte da verdade) e espelhada no JS só para a prévia.

### Pendências
- Envio de mensagem em lote / a partir dos cadastros (por ora é só teste de 1 número).
- Só o Diretor tem acesso (conforme pedido).

## 2026-07-05 - Usuários: contador "Vínculos" → "Ativos" (aventureiros ativos)

### Resumo
A pedido do usuário, o contador **"Vínculos"** (abstrato, pouco útil) na tela Usuários virou **"Ativos"** —
a quantidade de **aventureiros ativos**. Ficam: **Responsáveis · Aventureiros (total) · Ativos**.

### Arquivos alterados
- `core/views.py`: `usuarios_view` passa `total_ativos` (conta `ativo=True`); removido o cálculo de
  `total_vinculos`. `templates/core/usuarios.html`: card "Ativos".

### Validação
- `manage.py check` OK. Render: contadores **72 Responsáveis · 39 Aventureiros · 38 Ativos** (1 inativa).

---

## 2026-07-05 - Inativo: responsável aparece inativo + cobertura conta só ativos

### Resumo
Ajustes após o usuário testar (marcou a aventureira "Heloísa" inativa — a conta do responsável foi
desativada corretamente no banco, mas a tela não mostrava isso):
- **Responsável inativo na tela Usuários**: o card do pai/mãe/responsável agora aparece **Inativo** (selo +
  riscado) quando **todos os aventureiros vinculados a ele estão inativos** (mesma regra da conta). No modal
  do responsável, selo Ativo/Inativo + nota explicando. Vínculos inativos aparecem marcados na lista.
- **Cobertura do Resumo (dashboard)**: "Aventureiros do clube neste evento" passou a contar **só ativos**
  (`_montar_dashboard` filtra `Aventureiro.objects.filter(ativo=True)`) — inativos saem do total do clube.

### Arquivos alterados
- `core/views.py`: `usuarios_view` anota `ativo` em cada vínculo e `ativo` do responsável (any vínculo
  ativo); `_montar_dashboard` filtra aventureiros ativos na cobertura.
- `templates/core/usuarios.html`: selo/greyed no card e no modal do responsável + marca de vínculo inativo.
  `static/css/usuarios.css`: `.vinc-inativo`, strike no `.resp-nome-item`.

### Validação
- `manage.py check` OK. Verificado: conta da Heloísa (Mariane) `is_active=False` (cascata correta); os cards
  do pai (denner) e mãe (Mariane) agora vêm `av-inativo` com selo. Cobertura do evento 62: total caiu de 39
  → 38 (Heloísa fora) e cai +1 ao inativar um inscrito (testado e revertido).

### Observação
- "Heloísa Mendes carolino" foi marcada inativa pelo próprio usuário testando a feature (não é dado de teste
  meu). Fica como está.

---

## 2026-07-05 - Aventureiro inativo/desligado (com cascata na conta do responsável)

### Resumo
Alguns membros saem do clube no meio do ano e pedem para desligar. Agora, em **Usuários** (Diretor), ao
abrir o aventureiro (modal), há o botão **"Marcar como inativo"** (⛔) / **"Reativar"** (✅), com confirmação.

**Cascata na conta** (`Aventureiro.usuario`): ao inativar, se o responsável **não tiver mais nenhum
aventureiro ativo**, a **conta é desativada** (`is_active=False`, não loga mais). Se ainda tiver outro
ativo (ex.: dois irmãos, inativo só um), a conta **continua ativa** para gerenciar o que ficou. Reativar um
aventureiro reativa a conta. **Contas de Diretor/staff/superuser são protegidas** (nunca desativadas por
aqui, para não travar o acesso admin).

### Arquivos criados/alterados
- `core/models.py`: campo **`Aventureiro.ativo`** (default True). Migration **`0018`**.
- `core/views.py`: `aventureiro_toggle_ativo_view` (POST, Diretor; toggle + cascata com guarda de
  diretor/staff); `usuarios_view` anota `av.conta_ativa` (`select_related("usuario")`); `presenca_evento_view`
  passou a listar só `ativo=True`. Import de `eh_diretor`.
- `core/urls.py`: rota `aventureiro_toggle_ativo`.
- `templates/core/usuarios.html`: selo "Inativo" + card riscado; no modal, selo Ativo/Inativo, botão de
  ligar/desligar (form `data-confirmar`) e nota da cascata. `static/js/usuarios.js`: handler genérico de
  `form[data-confirmar]` (confirm antes de enviar). `static/css/usuarios.css`: `.pill-inativo`,
  `.av-inativo`, `.av-status-acao`, `.btn-inativar`/`.btn-reativar`.

### Validação
- `manage.py check` OK; `migrate` (0018). Teste (test client, Diretor): **irmãos** — inativar 1 → conta
  ativa; inativar o 2º → conta desativada; reativar 1 → conta volta. **Solo** — inativar único → conta
  desativada; reativar → volta. Diretor protegido. Registros de teste revertidos (0 aventureiros inativos).
  (A conta "Miguel Ferreira Mendes" está inativa desde a **importação** do sistema antigo — não é resíduo.)

---

## 2026-07-05 - Presença: toast ao marcar/desmarcar (confirmação)

### Resumo
Pedido do usuário: confirmar que a marcação deu certo. O `presenca.js` passou a mostrar o **toast padrão**
do sistema (`window.mostrarToast`) no **sucesso** de marcar/desmarcar — "<nome> — presente ✅" (success) ou
"<nome> — ausente" (info). Antes só havia toast em caso de erro. `inicio.js` (que expõe `mostrarToast`) já
é carregado antes do `presenca.js` na folha. `manage.py check` OK.

---

## 2026-07-05 - Módulo Presença do clube (+ guarda de exclusão por presença)

### Resumo
Novo módulo **Presença** (item no menu, Diretor), para marcar quais aventureiros do clube estiveram num
evento — pensado para **eventos simples** (reuniões, eventos fora), mas funciona para qualquer evento. É
**independente** do check-in de inscrição do evento complexo (`ParticipanteInscricao.presente`).

Fluxo (como no sistema antigo, com melhorias):
1. **Escolher o evento** (lista dos eventos cadastrados).
2. **Folha de presença**: lista de **todos os aventureiros** do clube, cada um com **foto grande**, nome +
   idade e um botão **Marcar** (toggle **presente ↔ ausente**, sem recarregar). Contador "presentes X de Y"
   ao vivo e **busca** por nome.
3. **Clicar na foto** abre a **foto ampliada** num modal (para conferir a pessoa no dia).

Também foi **ativada a guarda de exclusão** pendente da Fase 5.4: um evento com **presença marcada** não
pode mais ser excluído (junto de inscrições/pedidos).

### Arquivos criados/alterados
- `core/models.py`: model **`PresencaEvento`** (evento, aventureiro, marcado_em/por; `unique_together`;
  existência = presente). Migration **`0017`**.
- `core/views.py`: `presenca_view` (escolher evento), `presenca_evento_view` (folha), `presenca_marcar_view`
  (POST JSON toggle). `eventos_view`/`evento_excluir_view` passam a considerar `presencas` na guarda de
  exclusão. Import de `PresencaEvento`.
- `core/urls.py`: rotas `presenca`, `presenca_evento`, `presenca_marcar`.
- `templates/core/presenca_selecionar.html` e `presenca_evento.html` (novos); `_menu.html` (item
  "Presença", Diretor).
- `static/js/presenca.js` (novo: toggle fetch/JSON + modal da foto + busca). `static/css/presenca.css` (novo).

### Validação
- `manage.py check` OK; `migrate` aplicado. Teste (test client, Diretor): seletor 200; folha 200 (lista +
  modal); marcar → cria registro (presentes=1); desmarcar → remove (presentes=0); **guarda de exclusão**:
  evento com presença → `pode_excluir` False e POST excluir **bloqueado** (evento preservado). Registros de
  teste removidos. Visual do seletor conferido (headless); a folha **não** foi capturada para não expor
  fotos reais de menores (validada funcionalmente).

### Pendências / próximo passo
- (Opcional) abrir a presença a outros perfis além do Diretor. Migrar os eventos "Reunião do Clube" (2/4/5)
  do sistema antigo, onde a presença será usada.

---

## 2026-07-05 - Correção da migração do "Passaporte" (conferência com o relatório do sistema antigo)

### Resumo
O usuário baixou o **relatório PDF do evento no sistema antigo** para conferir, e havia diferenças grandes
vs a 1ª importação (evento 61). Investigado e **corrigido** (reimportado como **evento 62**; o 61 foi
apagado). Três causas:
1. **Inscrição contava como venda de loja**: no antigo, a inscrição é um **item do pedido** com título
   "Inscricao do evento: …". A 1ª importação somou essas linhas na lojinha → **R$ 4.505,50** em vez de
   **R$ 1.825,50**. Correção: itens com esse título **não** entram na loja; pedido que só tem a inscrição
   é ignorado (a inscrição já vem da `eventoinscricao`).
2. **Idade como texto**: 8 participantes tinham `Idade` = "6 anos" (texto). O parser antigo (`int`) falhava
   → caíam em "sem faixa". Correção: extrair o número por regex (`\d+`). Faixas passaram a 13 (1-4) / 58 → 56.
3. **Inscrição de teste**: 1 inscrição confirmada e **não paga** com nomes "teste/testee" (R$ 80) passou.
   Removida (heurística de nomes de teste).

Também, a pedido do usuário, a **taxa de cartão/Pix do Mercado Pago (R$ 423,73)** foi lançada como
**custo**, para o Resultado bater com o **"líquido"** do relatório.

### Resultado final (idêntico ao relatório antigo)
- Vendas lojinha **R$ 1.825,50** · Inscrições **R$ 2.500,00** (69 crianças: 13 na faixa 1-4 + 56 na 5-12)
- Bruto **R$ 4.325,50** · Custos **R$ 607,12** (R$ 183,39 + taxa R$ 423,73) · **Resultado R$ 3.718,38**

### Aprendizado (registrado p/ os próximos eventos com lojinha)
- Excluir itens "Inscricao do evento" da loja; parsear idade por regex; pular inscrições/pedidos de teste
  (`transacao_teste` + nomes de teste). Ver memória `migracao-eventos-conciliacao`.

---

## 2026-07-05 - Migração do evento "Passaporte da Diversão" (com lojinha completa)

### Resumo
Migrado o 2º evento do sistema antigo: **"Passaporte da Diversão"** (evento 6 → **evento 61**), agora com
**lojinha** (produtos, variações, fotos e vendas). Valores vieram **corretos do sistema antigo** — sem
conciliação bancária (a pedido do usuário).

- **Evento**: Colégio Adventista de São Carlos, 24/05/2026 13h–17h (1 dia), só membros. **Faixas**:
  1-4 anos R$ 20 · 5-12 anos R$ 40.
- **Inscrições**: **52** confirmadas (71 participantes), R$ 2.580,00. Puladas 6 não-confirmadas + 1
  cancelada. `valor_total` = valor gravado (correto); forma "online".
- **Lojinha**: **4 produtos** (Mini pizza, Bebidas, Pipoca, Açaí) com **fotos** + **13 variações** (preço
  por variação). Sem controle de estoque (evento histórico).
- **Vendas**: **141 pedidos** (R$ 4.505,50), só **status "pago" e não-teste** (puladas 23 canceladas +
  13 testes), com **226 itens** e a **retirada por item** (`quantidade_entregue`) preservada do antigo.
  Forma real (pix/dinheiro/cartão); dinheiro→balcão, resto→online; vínculo à inscrição via
  `evento_inscricao`.
- **Custos**: **3** (Pulseiras, pizzas, estorno) = R$ 183,39, **com comprovantes**.
- **Resultado**: receitas R$ 7.085,50 − custos R$ 183,39 = **R$ 6.902,11** (lucro).

### Como foi feito
- Script one-off (`importar_evento6.py` no scratchpad) lendo o export atualizado ("com_arquivos"): cria
  evento+faixas, produtos+variações (fotos extraídas para `media/eventos/produtos/`), inscrições
  (`criado_em` original), pedidos+itens (com mapa old→new de inscrição e variação) e custos (comprovantes
  em `media/eventos/custos/`). Mídia é **git-ignored**.
- Mapeamento de chaves flexível (o form do Passaporte usa "Nome do responsável"/"Nome da Criança", difere
  do Acampamento) via helpers de extração no script.

### Validação
- Render do evento 61 (Diretor): Inscritos 71, Arrecadação R$ 2.580, Vendas R$ 4.505,50, Custos R$ 183,39,
  **Resultado R$ 6.902,11**; "por forma" (Pix 131 / Online 52 / Dinheiro 8 / Cartão 2); faixas (5-12: 52,
  1-4: 11); **retiradas 192 de 287** (item-level); cobertura 25/39, 0 "a conferir"; 4 fotos de produto e
  3 comprovantes de custo existentes. Sem erros.

### Pendências / próximo passo
- Migrar os eventos restantes (ids 2/4/5 "Reunião do Clube" — simples, sem inscrição/lojinha).

---

## 2026-07-05 - Cobertura do clube: casamento de nomes mais esperto + lista de "a conferir"

### Resumo
No painel do evento, o card **"Aventureiros do clube neste evento"** (cobertura) casava mal os nomes: se a
inscrição abreviava o nome do meio (ex.: **"Alice Z Moreira"**), não casava com **"Alice Zanatta Moreira"**
(a regra exigia todos os tokens idênticos). Melhorias:
- **Casamento ciente de iniciais**: um token de 1 letra casa com um token que começa por ela — "Alice Z
  Moreira" → "Alice Zanatta Moreira". Mantém o subconjunto (ex.: "Beatriz Gonçalves" → "Beatriz Gonçalves
  Steinmeyer"). Helpers `_tokens_lista` + `_cobre_token` + `_nome_casa` (substituem o `_tokens_nome`/subset).
- **Desambiguação pelo sobrenome do responsável**: quando um nome curto casa com mais de um aventureiro,
  usa o sobrenome do responsável para escolher (ex.: "Beatriz" + responsável "…Staine" → "Beatriz Gonçalves
  Staine"; a outra Beatriz fica de fora). Só vira "a conferir" se ainda restar ambiguidade.
- **"A conferir" agora é uma lista** (participante + inscrição + candidatos), não só um contador — o
  Diretor vê exatamente quais nomes ficaram ambíguos.

Efeito no Acampamento 2026: cobertura subiu de **17 → 19 de 39** e **0 a conferir** (Alice e Beatriz
resolvidas). Os ~20 restantes são adultos/pais e crianças **não cadastradas** (corretamente fora).

### Arquivos alterados
- `core/views.py`: `_tokens_lista`/`_cobre_token`/`_nome_casa` (novos); `_montar_dashboard` usa o novo
  casamento + desambiguação por responsável e devolve `cobertura.ambiguos_lista`. Removido `_tokens_nome`.
- `templates/core/evento_painel.html`: lista `.cob-conferir` (os "a conferir"). `static/css/eventos.css`:
  estilo `.cob-conferir`.

### Validação
- `manage.py check` OK. Render do evento 60: cobertura **19 de 39**, sem "a conferir"; "Alice Zanatta
  Moreira" e "Beatriz Gonçalves Staine" passaram a casar. Casos legítimos fora (não-membros) seguem fora.

---

## 2026-07-05 - Migração do evento "Acampamento 2026" do sistema antigo (com conciliação bancária)

### Resumo
Migrado o primeiro evento do sistema antigo para o novo: **"ACAMPAMENTO AVENTUREIROS PINHAL JÚNIOR,
2026"** (era o evento 7 no antigo → **evento 60** no novo). Trazidos: dados do evento (nome, local,
descrição, datas 19–21/06 14h–17h), as **5 faixas etárias** (0-5 isento · 6-9 R$45 · 10-12 R$60 ·
13-17 R$80 · 18+ R$150) e as **24 inscrições reais confirmadas** (puladas as não confirmadas e um teste).

**Conciliação dos valores:** o sistema antigo gravava valores inconsistentes (taxa de cartão, campos
zerados, etc.). Os valores foram **conciliados contra o extrato bancário (Mercado Pago, abr–jun)** —
cruzando data + nome do pagador + valor — para registrar o **valor realmente recebido** em cada inscrição.
Resultado: **R$ 4.597,41** (14 Pix + 3 cartão + 7 cortesia/diretoria). Decisões de cortesia/diretoria e
casos de pagamento parcial confirmados com o usuário antes da importação.

### Como foi feito
- Análise/conciliação por **scripts one-off** no scratchpad (parser dos PDFs do extrato + matcher
  inscrição↔transação) + **relatório visual** (Artifact) para revisão do usuário. **Não** virou comando
  versionado porque a conciliação é bespoke (revisão manual do banco caso a caso).
- Importação direta no banco (SQLite): `Inscricao` + `ParticipanteInscricao` por inscrição, com
  `forma_pagamento` (pix/cartao/cortesia), `valor_total` = recebido conciliado e **`criado_em` = data
  original** da inscrição (para rastreabilidade). Sem tela de edição (decisão do usuário: subir já certo).

### Privacidade
- Os **PDFs do extrato** (`EXTRATOS/`) e os JSONs da exportação contêm dados financeiros/pessoais e
  **NÃO são versionados** (adicionado `EXTRATOS/`, `extratos/`, `*.ofx` ao `.gitignore`). Ficam só local.

### Custos (adicionado em seguida)
- Migrados os **9 custos** do evento 7 (nome, valor, data): Aluguel chácara R$ 2.000, comidas, lonas,
  pó de festa, pão, produtos vegetarianos, etc. — **total R$ 4.723,50**. Com isso o **Resultado do
  acampamento = R$ 4.597,41 − R$ 4.723,50 = −R$ 126,09**.
- **Comprovantes**: no primeiro export **não vieram** (só as assinaturas). O usuário **reexportou com
  arquivos** (`exportacao_migracao_..._com_arquivos.zip`, com `arquivos/media/eventos/custos/evento_7/`) e
  os **9 comprovantes foram anexados** (casados por nome+valor), copiados para `media/eventos/custos/`
  (git-ignored). O custo "Mini Lanterninhas" tinha 2 arquivos (screenshot + invoice); o principal
  (screenshot) ficou no campo comprovante e o invoice também foi copiado para `media/`.

### Pendências / próximo passo
- Migrar os **demais eventos** do sistema antigo (mesmo processo, um a um). Vínculo
  `Inscricao.usuario`→conta migrada não foi feito (histórico); dá para casar por nome/CPF se necessário.

### Arquivos alterados
- `.gitignore`: ignora `EXTRATOS/`, `extratos/`, `*.ofx`. (Dados do evento entram só no banco local.)

---

## 2026-07-05 - "Dia do evento": botão Voltar do balcão volta para o console (não para o painel)

### Resumo
Quando o atendente abre um atalho de balcão a partir do console **"Dia do evento"** (Nova inscrição /
Vender na lojinha), o botão **Voltar** dessas telas levava sempre ao painel. Agora ele **volta para o
"Dia do evento"**, de onde veio — para o atendente pesquisar/marcar entrega e vender na mesma tela sem
ficar navegando.

### Como
- Os atalhos no console apontam para o PDV com **`?de=dia`**.
- `evento_pdv_view` e `evento_pdv_inscricao_view` leem `de` (GET **ou** POST), passam ao template e
  **preservam** `?de=dia` no redirect após registrar (para continuar registrando e o Voltar seguir certo).
- As telas de PDV têm um **hidden `de`** no form e o link de Voltar passou a ter o ramo
  `{% if de == "dia" %}` → "← Voltar para o Dia do evento" (senão, mantém painel/operar como antes).

### Arquivos alterados
- `core/views.py`: `de` nas duas views de PDV (contexto + redirect com `?de=dia`).
- `templates/core/evento_dia.html`: atalhos com `?de=dia`.
- `templates/core/evento_pdv.html` e `evento_pdv_inscricao.html`: hidden `de` + ramo do Voltar.

### Validação
- `manage.py check` OK. Render (test client): `/pdv/?de=dia` e `/pdv/inscricao/?de=dia` mostram "Voltar
  para o Dia do evento" e o hidden `de=dia`; sem `?de=dia`, mantêm o Voltar para o painel.

---

## 2026-07-05 - Refinos de UX: abas do painel em card + atalhos de balcão no "Dia do evento"

### Resumo
Três ajustes pedidos pelo usuário:
1. **Lojinha só quando há produtos** (verificação): confirmado que a página do evento (botão "Comprar na
   loja", via `tem_loja`) e o formulário de inscrição (seção "Quer levar algo da lojinha?", via
   `produtos_loja`) **já** só aparecem quando existem produtos **ativos**. Testado com um evento sem
   produtos: nenhum dos dois aparece. Também conferido que não há produto ativo sem variação. **Sem
   mudança de código** (já estava correto).
2. **Barra de abas do painel em card**: a `.painel-abas` virou um **card/toolbar** (fundo branco, borda,
   cantos arredondados, sombra leve). A aba de seção **ativa** ficou **preenchida em azul** (antes era só
   sublinhado verde), e as **abas de ação** (Dia do evento / Vender no balcão / Operadores) ganharam um
   **divisor** à esquerda — deixando claro que o conjunto são os botões daquele painel.
3. **Atalhos de balcão no "Dia do evento"**: o topo do console ganhou **"Nova inscrição (balcão)"** e
   **"Vender na lojinha"**, para o atendente vender/inscrever **sem sair da tela** (pesquisa, marca entrega
   e vende no mesmo lugar). Gates: inscrição enquanto o evento não terminou; venda quando a loja está
   aberta e há produtos ativos.

### Arquivos alterados
- `static/css/eventos.css`: `.painel-abas` (card), `.painel-aba`/`.ativa` (pílula preenchida),
  `.painel-aba-acao::before` (divisor); `.dia-acoes` (linha de atalhos).
- `templates/core/evento_dia.html`: linha de atalhos (`.dia-acoes`) com os dois botões.
- `core/views.py`: `evento_dia_view` passa `pode_inscrever` (evento não terminou) e `pode_vender`
  (loja aberta + produtos ativos).

### Validação
- `manage.py check` OK. Teste (test client): evento sem produtos → "Comprar na loja"/"Quer levar algo da
  lojinha?" **ausentes**. **Visual (Chrome headless)**: abas do painel num card com "Resumo" ativo
  preenchido e divisor antes das ações; console "Dia do evento" com os dois atalhos no topo.

---

## 2026-07-05 - Evento complexo — Fase 5.4d: contadores do dia no painel (encerra a Fase 5.4)

### Resumo
Fecha a Fase 5.4 com a visão de acompanhamento no **painel do evento**. A aba **Resumo** ganhou um painel
**"📋 Dia do evento"** com os contadores ao vivo do dia — **Check-in** (presentes X/Y) e **Retiradas**
(itens entregues X/Y) — e um botão **"Abrir console"** que leva à tela "Dia do evento". Aparece só quando
há participantes ou itens (não polui eventos sem inscrição/lojinha). Reusa o helper `_resumo_dia`.

### Guarda de exclusão (esclarecimento)
O item "guarda de exclusão do evento simples" da Fase 5.4 **não exigiu código novo**: o evento **complexo**
já é protegido (`evento_excluir_view`/`eventos_view` bloqueiam a exclusão quando há inscrições ou pedidos,
o que cobre qualquer presença/entrega). O **evento simples** não tem módulo de presença (presença é do
evento complexo), então a guarda por presença em evento simples permanece como **item futuro** — ver
memória `exclusao-evento-presenca`. Nada a mudar por ora.

### Arquivos alterados
- `core/views.py`: `evento_painel_view` passa `dia = _resumo_dia(evento)` no contexto.
- `templates/core/evento_painel.html`: painel "Dia do evento" na aba Resumo (após os KPIs), com os
  contadores e o botão "Abrir console"; só renderiza se `dia.total_part` ou `dia.total_itens`.
- `static/css/eventos.css`: estilo `.dia-band` (+ `.dia-band-titulo`/`-nums`/`-num`).

### Validação
- `manage.py check` OK. Render do painel (test client, Diretor) com 2 presentes + 1 item entregue:
  o band aparece com **Check-in 2 de 4** e **Retiradas 1 de 12** + "Abrir console". **Visual (Chrome
  headless)**: band com gradiente azul/verde, entre os KPIs e os gráficos. Marcações de teste revertidas.

### Pendências / próximo passo
- **🎉 Fase 5.4 (Check-in + Retirada) CONCLUÍDA.** Futuro: presença em **evento simples** (aí a guarda de
  exclusão por presença passa a valer para eles). Depois: **pagamentos reais** (gateway) e **loja oficial
  do clube** (uniformes, separada da lojinha de evento).

---

## 2026-07-05 - Evento complexo — Fase 5.4c: "vai levar agora?" no balcão (entrega na hora da venda)

### Resumo
Fecha o fluxo do dia pelo lado do **balcão**: ao registrar uma venda, o atendente diz se o cliente **vai
levar os itens agora**. Um checkbox **"Entregar os itens agora"** (marcado por padrão) foi adicionado ao
**PDV de vendas** (`evento_pdv`) e ao **PDV de inscrição** (`evento_pdv_inscricao`):
- **Marcado** → o pedido já nasce **entregue** (`quantidade_entregue = quantidade`, registrando quem/quando).
- **Desmarcado** → os itens ficam **pendentes** e são retirados depois pelo console "Dia do evento" (5.4b).

Assim, a venda de balcão de consumo imediato não precisa ser marcada de novo no console, e a compra "para
levar depois" entra automaticamente na fila de retirada.

### Arquivos alterados
- `core/views.py`: `_criar_pedido` ganhou o parâmetro **`entregar_agora`** (nasce entregue, com
  `entregue_em`/`entregue_por`). `evento_pdv_view` e `evento_pdv_inscricao_view` leem o checkbox
  (`entregar_agora`, default marcado), passam ao helper e devolvem o estado ao template; a venda no PDV
  avisa "Itens entregues." quando aplicável.
- `templates/core/evento_pdv.html` e `evento_pdv_inscricao.html`: checkbox "Entregar os itens agora"
  (este só quando há itens da lojinha). `static/css/eventos.css`: estilo `.entregar-agora`.

### Decisões
- **Default marcado**: a maioria das vendas de balcão é retirada na hora; desmarca-se para "levar depois".
- Vale para venda avulsa **e** para a lojinha comprada junto da inscrição presencial. Cortesia também
  entrega (item físico), só não soma em dinheiro.

### Validação
- `manage.py check` OK. PDV de **vendas** (test client, Diretor): `entregar_agora` ausente → item **0/1**
  (pendente); marcado → **1/1** (entregue) + `entregue_por`. PDV de **inscrição**: idem no pedido vinculado
  (0/1 vs 1/1). Novos registros de teste **removidos** (banco limpo). **Visual (Chrome headless)**: checkbox
  em caixa verde, marcado por padrão, entre os itens e o vínculo/pagamento.

### Pendências / próximo passo
- **5.4d**: contadores de presença/retirada no painel + **guarda de exclusão do evento simples** (só
  exclui sem presença marcada).

---

## 2026-07-05 - Evento complexo — Fase 5.4b: marcar check-in e entrega no console "Dia do evento"

### Resumo
Continuação da Fase 5.4: o console **"Dia do evento"** (`/eventos/<id>/dia/`) deixou de ser só leitura —
agora o Diretor/operador **marca** o dia de fato, **sem recarregar a página**:
- **Check-in por participante**: cada participante tem um botão que alterna **Marcar chegada ↔ ✅ Chegou**.
- **Retirada por unidade**: o **selo** do item é clicável (entrega **tudo** ou **desfaz**); itens com mais
  de 1 unidade ganham um **stepper − x/y +** para **entrega parcial** (ex.: pegou 1 de 3 agora).
- **Resumo do dia ao vivo**: os contadores (check-in X/Y, retiradas X/Y, pendentes) atualizam na hora.
- Cada marcação guarda **quem** marcou e **quando** (`presente_por`/`presente_em`, `entregue_por`/`entregue_em`).

### Como funciona
- Endpoints JSON **`evento_checkin`** e **`evento_entrega`** (POST, `@operador_required`): validam que o
  participante/item pertence ao evento e a uma **inscrição/pedido confirmado**, limitam a entrega a
  **0..quantidade** do item e devolvem o novo status + o **resumo do dia** recalculado (helper único
  **`_resumo_dia`**, reusado pela tela e pelos endpoints). O JS envia via `fetch` com **`X-CSRFToken`** e
  atualiza a linha (selo/stepper) e o resumo. Toast só em caso de erro (marcar em massa não polui a tela).

### Arquivos criados/alterados
- `core/views.py`: helper `_resumo_dia`; views `evento_checkin_view` e `evento_entrega_view`;
  `evento_dia_view` passou a usar `_resumo_dia`. Import de `Count`/`Q`/`Sum`.
- `core/urls.py`: rotas `evento_checkin` (`.../dia/checkin/`) e `evento_entrega` (`.../dia/entrega/`).
- `templates/core/_dia_entrega.html` (novo): controle de retirada por unidade (selo clicável + stepper),
  reusado nas duas seções (inscrições e avulsos). `evento_dia.html`: botão de check-in, `#diaDados`
  (URLs + csrf), IDs no resumo, inclui o parcial de entrega nas duas seções, nota atualizada.
- `static/js/evento_dia.js`: ações de marcar (fetch/JSON, atualização inline dos selos/stepper e do
  resumo). `static/css/eventos.css`: `.selo-btn`, `.entrega`/`.entrega-stepper`/`.entrega-btn`/`.entrega-num`.

### Validação
- `manage.py check` OK. Endpoints (test client, Diretor): check-in ON→presente=True + `presente_por` +
  resumo.presentes=1; OFF→zera presente/em/por; entrega 1→entregue, 999→**clamp** para a quantidade,
  0→pendente + zera em/por; item inexistente→**404**; **GET**→**405**. Property `status_entrega` conferida.
  **Visual (Chrome headless, desktop)**: selos clicáveis "Marcar chegada"/"✅ Chegou" e "Não entregue", e
  item com qtd>1 mostrando selo **Parcial** + stepper **− 1/3 +** — consistente nas duas seções. Marcações
  de teste revertidas (banco limpo).

### Pendências / próximo passo
- **5.4c**: "vai levar agora?" no balcão (PDV venda e PDV inscrição) — já marcar a entrega na hora.
- **5.4d**: contadores no painel + guarda de exclusão do evento simples.

---

## 2026-07-05 - Evento complexo — Fase 5.4a: Check-in + Retirada (console "Dia do evento", só leitura)

### Resumo
Início da **Fase 5.4** (definida com o usuário): controle do **dia do evento** — **check-in** dos
participantes e **retirada/entrega** dos itens da lojinha. Escopo desta parte (**5.4a**): os **modelos** e
a **tela de consulta**, ainda **só leitura** (as marcações vêm na 5.4b).

- **Modelos**: `ParticipanteInscricao` ganhou **check-in por participante** (`presente`, `presente_em`,
  `presente_por`) e `ItemPedidoLoja` ganhou **retirada por unidade** (`quantidade_entregue`, `entregue_em`,
  `entregue_por`) — permite **entrega parcial** (props `entregue`/`entrega_parcial`/`status_entrega`).
  Migration **0016**.
- **Console "Dia do evento"** (`/eventos/<id>/dia/`, **Diretor + operadores**): por **família** (inscrição
  confirmada), mostra os **participantes** com o selo de check-in (✅ Chegou / Não chegou) e os **itens da
  lojinha comprados** com o selo de retirada (Não entregue / Parcial (x/y) / ✅ Entregue). Tem **resumo do
  dia** (check-in X/Y + retiradas X/Y), **busca** em tempo real (responsável/participante/código) e uma
  seção de **pedidos avulsos** (passantes sem inscrição). Os pedidos são casados à inscrição pela **mesma
  regra do painel** (vínculo direto ou mesma conta única) — helper `_casar_pedidos_inscricoes` (extraído
  para reuso).
- **Pontos de entrada**: aba-link **"📋 Dia do evento"** na barra do painel e card na landing **"Operar"**.

### Decisões (definidas com o usuário)
- **Entrega por unidade** (permite retirada parcial: pegou 1 de 3 agora, o resto depois).
- **Todos os itens** da lojinha entram no controle (sem marcar "entregável" por produto).
- **Check-in por participante** (cada criança), não por família — melhor para a presença.
- Escopo de "entregável" cobre também **pedidos avulsos** (passantes), em seção separada.

### Arquivos criados/alterados
- `core/models.py`: campos de check-in em `ParticipanteInscricao` e de retirada em `ItemPedidoLoja` (+
  props). `core/migrations/0016_itempedidoloja_entregue_em_and_more.py` (novo).
- `core/views.py`: `evento_dia_view` (`@operador_required`, só leitura) e helper `_casar_pedidos_inscricoes`.
- `core/urls.py`: rota `evento_dia` (`/eventos/<id>/dia/`).
- `templates/core/evento_dia.html` (novo); `evento_painel.html` (aba-link "Dia do evento");
  `evento_operar.html` (card "Dia do evento").
- `static/js/evento_dia.js` (novo: busca). `static/css/eventos.css`: estilos do console (`.dia-*`, `.selo-*`).

### Validação
- `manage.py check` OK; `migrate` aplicado. Render (test client, Diretor) do evento 4: **200**, com resumo
  (Check-in 1/4, Retiradas 0/12), busca, cards por inscrição (selos Chegou/Não chegou e Não entregue) e
  seção de pedidos avulsos. Property `status_entrega` conferida (0/3→pendente, 1/3→parcial, 3/3→entregue).
  **Visual (Chrome headless, desktop 900px e mobile 430px)** conferido — layout consistente com o padrão
  azul/verde. As marcações de teste feitas nos dados reais foram **revertidas** (banco limpo).

### Pendências / próximo passo
- **5.4b**: ações de marcar (check-in por participante + entrega por unidade, com status ao vivo).
- **5.4c**: "vai levar agora?" no balcão (PDV venda e PDV inscrição).
- **5.4d**: contadores no painel + guarda de exclusão do evento simples.

---

## 2026-07-05 - Lista de eventos: botões Duplicar/Excluir menores, consistentes e grudados na base

### Resumo
Ajuste visual dos botões dos cards da lista de **Eventos**:
- **Duplicar** passou a usar o mesmo estilo pequeno do "Abrir painel"/"Criar evento" (`btn-acao
  btn-acao-pequeno`, verde) — antes era o `btn-secundario` (grandão).
- **Excluir** virou um **botão pequeno vermelho** (fundo/borda suaves, mesmo tamanho) em vez de texto
  solto — mais bonito e do mesmo tamanho dos outros.
- **Bug corrigido**: os botões ficavam "no meio" do card. Havia **duas** regras `.evento-acoes` no
  `eventos.css` e a da página pública (`margin-top: 24px`) sobrescrevia a da lista (`margin-top: auto`).
  Escopei a da lista em **`.evento-card .evento-acoes`**, então os botões voltam a **grudar na base** do
  card (alinhados entre cards de alturas diferentes).

### Arquivos criados/alterados
- `templates/core/eventos.html`: "Duplicar" usa `btn-acao btn-acao-pequeno`.
- `static/css/eventos.css`: `.evento-card .evento-acoes` (escopo + `margin-top:auto`); `.btn-excluir-evento`
  menor e com fundo/borda (botão, não texto).

### Decisões tomadas
- Duplicar em verde (igual ao "Abrir painel"); Excluir em vermelho (destrutivo) — mesmo tamanho/forma.

---

## 2026-07-05 - Lista de eventos: etiqueta do tipo mais compacta e bonita

### Resumo
Na lista de **Eventos**, a etiqueta ao lado do título (antes o pill grande "Evento com inscrição" /
"Evento simples") virou uma **etiqueta compacta com ícone**: **🎟️ Com inscrição** (verde suave) e
**🗓️ Simples** (azul suave). Menor, com texto curto e sem quebrar linha.

### Arquivos criados/alterados
- `templates/core/eventos.html`: a etiqueta do tipo usa `.evento-tipo`/`.evento-tipo-<tipo>` com ícone +
  texto curto (em vez de `.pill` com `get_tipo_display`).
- `static/css/eventos.css`: estilos `.evento-tipo`, `.evento-tipo-inscricao`, `.evento-tipo-simples`.

### Decisões tomadas
- Texto curto ("Com inscrição" / "Simples") com ícone; o tipo completo continua no modal de detalhes.

---

## 2026-07-05 - Evento complexo — Fase 5.3b: cupom por participante + faixa + geração em lote + validação ao vivo

### Resumo
Evolução dos cupons de desconto (Fase 5.3), definida com o usuário. O cupom deixou de ser um campo
único da inscrição (que abatia "o participante de maior valor") e passou a ser **por participante**,
com **validação ao vivo** e **restrição por faixa etária**:
- **Cupom por participante**: cada participante da inscrição (online e balcão) tem seu **próprio campo
  de cupom**; o desconto vale **só para aquele participante** (o usuário escolhe em quem aplicar).
- **Validação ao vivo**: ao digitar/sair do campo, o sistema valida no servidor (endpoint JSON) e mostra
  o **toast padrão** — verde quando aplicado (com o **desconto em R$**) ou vermelho quando inválido.
  O **total** da inscrição já **abate** o desconto na hora e um resumo mostra **"Cupons: −R$ X"**.
- **Faixa etária no cupom**: ao gerar, o Diretor pode restringir o cupom a uma **faixa etária**. Se o
  participante não estiver na faixa, aparece o erro "**Cupom é só para <faixa>**" (no ao vivo e ao enviar).
- **Geração em lote**: a aba "Desconto" ganhou **Quantidade** (stepper − / +), gerando **até 5 cupons por
  vez** com o mesmo percentual e faixa; ao tentar passar de 5, toast "**No máximo 5 cupons por vez**".
- **Layout revisado** da aba "Desconto": o campo de **%** (que parecia sem estilo, pois o painel não
  carrega o CSS de formulário) agora é estilizado localmente, em uma **grade** (Desconto · Quantidade ·
  Faixa) dentro de um card.

### Arquivos criados/alterados
- `core/models.py`: `CupomDesconto` ganhou **`faixa`** (FK opcional a `FaixaEtariaPreco`) e **`participante`**
  (FK opcional a `ParticipanteInscricao`, quem usou). Migration **`0015`**.
- `core/views.py`: `_processar_cupons_participantes` (valida/aplica o cupom digitado na linha de cada
  participante: uso único, sem repetir código, casa a faixa) e `_marcar_cupons_usados`; **`evento_cupom_validar_view`**
  (endpoint JSON GET de validação ao vivo — não grava nada); `evento_inscrever_view` e
  `evento_pdv_inscricao_view` passaram a usar esses helpers (corrige a `_aplicar_desconto_cupom` removida);
  `evento_cupom_novo_view` aceita **`quantidade`** (1–5) e **`faixa`**; o painel anexa `i.cupons_aplicados`
  (lista) a cada inscrição (pode haver mais de um cupom por inscrição). `tem_cupons`/`faixas_json`/`diretoria_json`
  no contexto das duas telas de inscrição. Import de `JsonResponse`.
- `core/urls.py`: rota **`evento_cupom_validar`** (`.../cupom/validar/`).
- `templates/core/_participante_linha.html`: **campo de cupom por participante** (`part_cupom_<idx>`) +
  feedback inline, sob `tem_cupons`.
- `templates/core/evento_inscrever.html` e `evento_pdv_inscricao.html`: removido o campo de cupom único;
  passam `tem_cupons` e a URL de validação; JSON de faixas/diretoria; **total ao vivo** com resumo de cupons.
- `templates/core/evento_painel.html`: aba "Desconto" reformulada (grade % / quantidade-stepper / faixa) +
  nota atualizada + pílulas de faixa no cupom + pílula por cupom aplicado (loop).
- `static/js/evento_insc_cupom.js` (**novo**): total ao vivo + validação do cupom por participante + troco
  (PDV). Substitui `static/js/evento_pdv_inscricao.js` (**removido**).
- `static/js/evento_painel.js`: stepper de quantidade dos cupons (toast ao passar de 5).
- `static/css/eventos.css`: layout da geração de cupons (grade, campo de %, stepper), campo de cupom por
  participante (ok/erro) e caixa de total da inscrição.

### Decisões tomadas
- **Cupom por participante** (o usuário escolhe em quem aplicar), no lugar de "o de maior valor".
- **Validação ao vivo por GET** (endpoint JSON sem CSRF, não grava): o **uso único** só é gravado ao
  **confirmar** a inscrição (o servidor revalida). Assim não há cupom "reservado" por formulário aberto.
- **Cortesia** (balcão) ignora cupom (já é grátis) — sem erro de faixa nesse caso.
- Um script único (`evento_insc_cupom.js`) serve as duas telas (online e PDV), evitando duplicação.

### Pendências
- Presença/check-in (Fase 5.4) — próximo passo.

### Resumo
Nova frente da Fase 5: **cupons de desconto**, **somente para inscrição** (não valem na lojinha).
- **Aba "Desconto"** no painel (Diretor): gera cupom informando a **% de desconto** ("Gerar cupom" → cria
  um **código único**); a **lista** mostra cada cupom com **status** ("Disponível" / "Usado por FULANO ·
  −R$ X") e permite **remover** os não usados.
- **Campo "Cupom de desconto"** nos formulários de inscrição — **online** (`evento_inscrever`) e
  **balcão/PDV** (`evento_pdv_inscricao`). Código inválido ou já usado **bloqueia** com aviso.
- **Regra**: cupom de **uso único**; o desconto se aplica a **um participante só** — o de **maior valor**
  (decisão nossa; mais vantajoso). Reduz o valor desse participante e o total; marca o cupom como usado
  (quem usou, valor descontado e vínculo à inscrição). O cupom aparece na inscrição (painel) e na tela de
  sucesso.

### Arquivos criados/alterados
- `core/models.py`: model **`CupomDesconto`** (evento, codigo único, percentual, ativo, inscricao,
  usado_por, valor_desconto, usado_em, criado_por; property `usado`; `gerar_codigo_unico`). Migration
  `0014`.
- `core/views.py`: helpers `_buscar_cupom_valido` e `_aplicar_desconto_cupom` (aplica no participante de
  maior valor); `evento_inscrever_view` e `evento_pdv_inscricao_view` leem/validam/aplicam o cupom (num
  participante) e marcam o uso; novas `evento_cupom_novo_view` / `evento_cupom_excluir_view`; o painel
  passa `cupons` e anexa `i.cupom_aplicado` a cada inscrição.
- `core/urls.py`: rotas `evento_cupom_novo` / `evento_cupom_excluir`.
- `templates/core/evento_painel.html`: aba "Desconto" (topo) + seção (gerar + lista) + pílula do cupom
  na inscrição. `evento_inscrever.html` e `evento_pdv_inscricao.html`: campo "Cupom de desconto".
  `evento_inscricao_sucesso.html`: linha do desconto aplicado.
- `core/admin.py`: registra `CupomDesconto`. `static/css/eventos.css`: estilos do cupom (`.cupom-*`,
  `.pill-cupom`).

### Decisões tomadas
- **Um participante por cupom** (o de maior valor); **uso único**; **só inscrição**. Código
  case-insensitive.
- **Balcão**: o total ao vivo (JS) **não** reflete o cupom (precisaria validar o código no cliente); o
  **servidor** aplica o desconto e calcula o troco ao confirmar. Anotado como limitação.
- Cancelar a inscrição **não** libera o cupom (permanece usado) — simplicidade; revisitar se necessário.

### Validação
- `manage.py check` OK. Teste ponta a ponta: gerar cupom (50%); rejeitar 150% (não cria); inscrição
  online com cupom (2 participantes 30/50 → desconto no de 50 → 25; total 55); cupom marcado usado (por
  quem, −R$ 25, vínculo); **reusar** o cupom → bloqueado; **inexistente** → bloqueado; **balcão** aplica
  (20% de 40 → −R$ 8, total 32). Visual (headless): aba "Desconto" com gerar + lista (1 disponível, 1
  usado com "Usado por … · −R$ 8,00").

### Pendências / próximo passo
- **Fase 5.4 — presença/check-in** (também vira guarda de exclusão dos eventos simples). Melhoria
  possível: refletir o cupom no total ao vivo do balcão (validação via AJAX).

---

## 2026-07-04 - Barra de abas do painel unificada (ícones + mesmo estilo)

### Resumo
Ajuste visual: as abas de ação ("Vender no balcão", "Operadores") destoavam das abas de seção (tinham
ícone e cor diferente). A pedido do usuário, **todas as abas ficaram no mesmo estilo, com ícone**:
Resumo 📊 · Inscrições 🎟️ · Lojinha 🛒 · Custos 💸 · Financeiro 📈 · Vender no balcão 🧾 · Operadores 👥.
Cor base **azul** para todas; a **aba de seção ativa** ganha **sublinhado verde + fundo suave** (as de
ação, que navegam, não têm estado ativo).

### Arquivos alterados
- `templates/core/evento_painel.html`: ícone (`<span aria-hidden>`) nas 5 abas de seção.
- `static/css/eventos.css`: `.painel-aba` cor base → `--azul`; `.ativa` com fundo suave; `.painel-aba-acao`
  perdeu a cor especial (herda a base) — só mantém `text-decoration:none` + a margem separadora.

### Validação
- `manage.py check` OK. Visual (Chrome headless, desktop e mobile): as 7 abas com ícone, mesmo estilo; a
  ativa destacada (sublinhado verde). No mobile quebram em linhas mantendo a consistência.

---

## 2026-07-04 - Reorganização do painel — Etapa 4/4: cards clicáveis no Resumo (conclui a reorg)

### Resumo
**Etapa 4 (última)**: no **Resumo**, os cards de KPI (Inscritos, Arrecadação, Vendas, Receitas, Custos)
ficaram **clicáveis** — com um caret ▾. Ao clicar, abre **abaixo do grid** uma **lista simples** daquele
indicador (accordion: uma por vez; clicar de novo fecha):
- **Inscritos** → responsável + participantes (um por linha).
- **Arrecadação** → quem pagou e quanto.
- **Vendas (lojinha)** → uma linha por venda (comprador + valor).
- **Receitas** → uma linha por entrada (com etiqueta Inscrição/Lojinha).
- **Custos** → uma linha por custo.
O card **Resultado** não é clicável (é o número final). Os gráficos e a cobertura seguem abaixo.

**Com isso a reorganização do painel está completa** (Etapas 1–4): abas internas em Inscrições e Lojinha,
Balcão/Operadores no topo, e cards clicáveis no Resumo.

### Arquivos alterados
- `core/views.py`: `_montar_dashboard` agora recebe `pedidos_confirmados`/`custos` e monta
  `dashboard["listas"]` (inscritos, arrecadacao, vendas, receitas, custos) prontas para o template.
- `templates/core/evento_painel.html`: cards de KPI com `.kpi-clicavel` + `data-lista` + `role/tabindex`
  + caret; `#kpiListas` com 5 painéis `.kpi-lista` (hidden) renderizando cada lista.
- `static/js/evento_painel.js`: accordion dos cards (`.kpi-clicavel` → mostra o `.kpi-lista` do
  `data-lista`; teclado Enter/Espaço; fecha os outros).
- `static/css/eventos.css`: `.kpi-clicavel`/`.kpi-caret`/`.kpi-clicavel.ativo`, `#kpiListas`,
  `.kpi-lista`, `.lista-simples` e `.ls-*` (nome/valor/tag/sec).

### Validação
- `manage.py check` OK. Render (test client): 5 cards `.kpi-clicavel`; 5 painéis `hidden` por padrão;
  listas com os dados certos (arrecadação: quem pagou+quanto; inscritos: responsável+participantes;
  receitas com etiquetas Inscrição/Lojinha; custos). Visual (Chrome headless): ao abrir "Arrecadação", o
  card destaca e a lista aparece abaixo (Carlos R$ 30 / Maria R$ 60), um por linha.

### Pendências / próximo passo
- Reorganização concluída. Próximo da Fase 5: **5.3 códigos de desconto (cupons %)**; depois **5.4
  presença/check-in**.

---

## 2026-07-04 - Reorganização do painel — Etapa 3/4: Balcão e Operadores no topo

### Resumo
**Etapa 3**: os botões **PDV / Balcão** e **Operadores**, que ficavam no **cabeçalho da Lojinha**,
foram movidos para a **barra de abas do topo** (ao lado de Financeiro). Conforme combinado, **só mudou o
lugar do botão** — as páginas de balcão/operadores **não foram reescritas**. As duas novas abas são
**links** (`<a class="painel-aba painel-aba-acao">`) que abrem as páginas existentes; ficam em **azul**
(cor de link) + ícone, para se distinguir das abas de seção (que trocam conteúdo no cliente). O
**"PDV / Balcão"** foi renomeado para **"Vender no balcão"** (mais didático).

### Arquivos alterados
- `templates/core/evento_painel.html`: na `.painel-abas`, 2 abas-link novas ("🧾 Vender no balcão" →
  `evento_pdv`; "👥 Operadores" → `evento_operadores`); removida a `.secao-acoes` do cabeçalho da Lojinha.
- `static/js/evento_painel.js`: a troca de seção agora seleciona `.painel-aba[data-aba]` (os links
  `.painel-aba-acao`, sem `data-aba`, **não** entram no toggle — navegam para a página).
- `static/css/eventos.css`: `.painel-aba { text-decoration: none }` (para os `<a>`) e `.painel-aba-acao`
  (azul + margem separando das abas de seção).

### Decisões tomadas
- **Abas-link** (não reescrever as telas de operador, que são de tela cheia): só o ponto de entrada mudou
  de lugar. A "Nova inscrição (balcão)" segue na aba Inscrições (o usuário pediu para mover só os da
  Lojinha).

### Validação
- `manage.py check` OK. Render (test client): 2 abas-link no topo apontando para `…/pdv/` e
  `…/operadores/`; cabeçalho da Lojinha **sem** o "PDV / Balcão" antigo. Visual (desktop e mobile): abas
  de ação em azul ao lado/abaixo das abas de seção (quebram bem no responsivo).

### Pendências / próximo passo
- **Etapa 4** (última da reorg): **cards clicáveis no Resumo** → cada card abre uma lista simples.

---

## 2026-07-04 - Reorganização do painel — Etapa 2/4: abas internas na "Lojinha"

### Resumo
**Etapa 2** da reorganização: a aba **Lojinha** ganhou **sub-abas** (mesmo padrão da Etapa 1):
- **Produtos** (abre primeiro) — a lista de produtos + botão **"Novo produto"** (que saiu do cabeçalho).
- **Pedidos** — a lista de pedidos com uma **busca** (por comprador, código ou produto), igual à das
  inscrições; some quem não bate e mostra "Nenhum pedido encontrado".

Os botões **PDV / Balcão** e **Operadores** continuam **no cabeçalho da Lojinha por enquanto** — a
**Etapa 3** os move para a barra do topo (só troca de lugar, sem reescrever as páginas).

### Arquivos alterados
- `templates/core/evento_painel.html`: seção Lojinha em `.sub-abas` (Produtos/Pedidos) + 2 `.sub-secao`;
  "Novo produto" movido para a aba Produtos; busca (`#buscaPedidos`) + `.pedido-busca` nos itens +
  mensagem "pedidosVazio".
- `static/js/evento_painel.js`: `ligarBusca("buscaPedidos", ".pedido-busca", "pedidosVazio")` (reusa o
  helper de busca e o de sub-abas — ambos genéricos).

### Validação
- `manage.py check` OK. Render (test client): 2 sub-abas; Produtos visível, Pedidos `hidden`; busca de
  pedidos presente (2 itens `.pedido-busca`); "Novo produto" só na aba Produtos; `<div>` equilibrados.
  Visual (Chrome headless, desktop): Lojinha com sub-abas Produtos/Pedidos, "Novo produto" na aba.

### Pendências / próximo passo
- **Etapa 3**: mover **Balcão** e **Operadores** para a barra do topo (abas-link) + renomear "PDV /
  Balcão". Depois **Etapa 4** (cards clicáveis no Resumo).

---

## 2026-07-04 - Reorganização do painel — Etapa 1/4: abas internas em "Inscrições"

### Resumo
Início de uma **reorganização do painel do evento** (alinhada com o usuário) para dar responsabilidade
clara a cada aba e evitar rolagem. **Etapa 1 (esta)**: a aba **Inscrições** ganhou **sub-abas**:
**Lista de inscrições** (abre primeiro) · **Configuração** · **Faixas de preço** · **Formulário**. Assim
a lista (que cresce com o tempo) aparece de cara e as configurações ficam **minimizadas**, a um clique —
sem precisar rolar até o fim. O botão "Nova inscrição (balcão)" e o status/prazo ficam no topo da aba
(comuns). Removida uma nota desatualizada ("...entram nas próximas partes da Fase 2").

### Plano completo da reorganização (etapas)
1. **Etapa 1 — CONCLUÍDA ✅**: abas internas em Inscrições.
2. **Etapa 2**: abas internas em **Lojinha** (Produtos · Pedidos) + **busca** na lista de pedidos.
3. **Etapa 3**: mover os **botões** de **Balcão** (vender) e **Operadores** de dentro da Lojinha para a
   **barra do topo** (ao lado de Custos/Financeiro), como abas-link para as páginas atuais (**sem
   reescrever** as páginas — só muda o local do botão de entrada); renomear "PDV / Balcão" para algo
   didático (ex.: "Vender no balcão").
4. **Etapa 4**: no **Resumo**, tornar os **cards de KPI clicáveis** → cada um abre uma **lista simples**
   (Inscritos → responsável+participantes; Arrecadação → quem pagou+quanto; Vendas → 1/linha; Receitas →
   1/linha; Custos → 1/linha).

### Arquivos alterados
- `templates/core/evento_painel.html`: seção Inscrições envolvida em `.sub-abas` + 4 `.sub-secao`
  (`data-subsecao=lista|config|faixas|formulario`); "lista" visível, demais `hidden`.
- `static/js/evento_painel.js`: handler genérico de **sub-abas** (por `.sub-abas`, escopado à
  `.painel-secao` pai) — reutilizável na Etapa 2 (Lojinha).
- `static/css/eventos.css`: `.sub-abas`/`.sub-aba`/`.sub-aba.ativa` (pílulas) e `.sub-secao[hidden]`.

### Validação
- `manage.py check` OK. Render (test client): 4 sub-abas; "lista" sem `hidden`, Config/Faixas/Formulário
  `hidden`; `<div>` abrem == fecham (estrutura equilibrada). Visual (Chrome headless) em **desktop e
  mobile (~470px)**: sub-abas em pílula, "Lista de inscrições" ativa, configs escondidas.

### Pendências / próximo passo
- **Etapa 2**: abas na Lojinha + busca nos pedidos.

---

## 2026-07-04 - Inscrição: "nome completo" + botão "Ver detalhes"

### Resumo
Dois ajustes:
1. **Nome completo**: o formulário de inscrição passou a pedir **"Nome completo do responsável"**
   (placeholder "Nome e sobrenome" + dica "evite só o primeiro nome") e **"Nome completo do
   participante"** (placeholder). Assim a pessoa não põe só o primeiro nome e o **casamento** com o
   cadastro do clube (cobertura) funciona melhor. Vale para a inscrição online e a do PDV (mesmo form).
2. **Botão de expandir**: na lista de inscrições do painel, o `<summary>` mudou de "Ver participantes e
   respostas" para **"Ver detalhes"** — que agora cobre participantes, respostas **e** as compras na
   lojinha.

### Arquivos alterados
- `core/forms.py`: `InscricaoForm.responsavel_nome` → label "Nome completo do responsável" + placeholder
  + `help_text`.
- `templates/core/_participante_linha.html`: placeholder "Nome completo do participante".
- `templates/core/evento_painel.html`: `<summary>Ver detalhes</summary>`.

### Validação
- `manage.py check` OK. Render: o form de inscrição mostra "Nome completo do responsável" + placeholder +
  dica + "Nome completo do participante"; o painel (com inscrição) mostra "Ver detalhes" (antigo texto
  ausente).

---

## 2026-07-04 - Compras da lojinha por inscrição (o que cada pessoa comprou)

### Resumo
O usuário sentia falta de ver **o que cada pessoa comprou** na lojinha (casamento inscrição × pedidos).
Agora, na aba **Inscrições** do painel, cada inscrito mostra (ao expandir "Ver participantes…") um bloco
**"🛒 Compras na lojinha"** com os pedidos daquela pessoa e o **Total geral (inscrição + lojinha)**; o
topo do card ganha uma **pílula 🛒** com o valor gasto na lojinha.

**Como casa (do confiável ao menos):** (1) **vínculo direto** `PedidoLoja.inscricao` (comprou junto da
inscrição ou vinculado no PDV); (2) **mesma conta logada** — `pedido.usuario == inscricao.usuario`,
**somente** quando esse responsável tem **uma** inscrição no evento (evita atribuir a inscrição errada);
pedidos da mesma conta ganham a etiqueta "· mesma conta". Pedidos **avulsos** (sem conta e sem vínculo —
passante) **não** são atribuídos e seguem só na aba Lojinha. Não usa casamento por nome aqui (evita o
falso positivo).

### Arquivos alterados
- `core/views.py`: `evento_painel_view` calcula `compras_por_insc` (FK ou mesma conta única) e anexa a
  cada inscrição `i.compras`, `i.total_compras` e `i.total_geral`.
- `templates/core/evento_painel.html`: bloco "Compras na lojinha" no detalhe da inscrição + pílula
  `pill-loja` no topo + linha "Total geral".
- `static/css/eventos.css`: `.pill-loja`, `.inscrito-compras`, `.inscrito-compras-titulo`,
  `.inscrito-total-geral`.

### Decisões tomadas
- **Só sinais confiáveis** (FK + mesma conta logada única); nada de casar por nome para dinheiro.
- **Avulsos ficam na aba Lojinha** (são passantes/anônimos, sem dono).
- Divisão: **Inscrição** = o que aquela pessoa/família comprou; **Lojinha** = todos os pedidos (inclui
  avulsos).

### Validação
- `manage.py check` OK. Teste (render, test client): pedido **vinculado (FK)** + pedido da **mesma conta**
  aparecem no bloco (o 2º com "mesma conta"); **Total geral = R$ 94,00** (60 + 24 + 10), **excluindo** um
  pedido **avulso** de R$ 8; visual do card (pílula 🛒 + bloco + total) conferido em headless.

### Pendências / próximo passo
- (Opcional futuro) **vínculo exato na inscrição** (selecionar o aventureiro) melhoraria também a
  atribuição de compras de anônimos. Fase 5: **5.3 códigos de desconto**, depois **5.4 presença/check-in**.

---

## 2026-07-04 - Corrige edição de produto: preço e estoque não vinham preenchidos

### Resumo
Ao **editar** um produto da lojinha, as variações mostravam o **nome**, mas os campos de **preço** e
**estoque** vinham **vazios** (não reexibiam os últimos valores). **Causa**: a view passava o valor como
`Decimal`/`int` cru e o template, em **pt-BR**, **localizava** o número (ex.: `12,00` com vírgula); um
`<input type="number">` **não aceita vírgula** e descarta o valor → campo vazio. **Correção**: a view
passa `valor_raw`/`estoque_raw` como **string com ponto** (`str(v.valor)` / `str(v.estoque)`), que o
template não localiza.

### Arquivos alterados
- `core/views.py`: `_produto_form` (GET de edição) usa `str(v.valor)` e `str(v.estoque)` ao montar as
  linhas de variação.

### Validação
- `manage.py check` OK. Render da edição (test client): os inputs vêm com `value="12.00"` / `value="18.50"`
  (preço, com ponto) e `value="20"` / `value="15"` (estoque); sem vírgula; nomes preservados.

### Nota técnica
- **Ao reexibir número em `<input type="number">` cru**, passar **string com ponto** (ou `unlocalize`) —
  um `Decimal`/`float` é localizado no template (vírgula em pt-BR) e o input rejeita. Ver REGRAS.

---

## 2026-07-04 - Refinos do dashboard: busca (visual + bug) e cobertura inteligente

### Resumo
Ajustes pedidos após validar o dashboard:
1. **Caixas de busca repaginadas**: viraram um campo "pill" com **ícone de lupa** (SVG inline), foco
   azul e largura total (antes era um input cru com emoji no placeholder).
2. **Bug da busca corrigido**: ao pesquisar algo inexistente, a **lista continuava aparecendo** e a
   mensagem "nada encontrado" surgia embaixo. **Causa**: os itens têm `display:flex`, que **vence** o
   atributo `[hidden]` (do UA stylesheet). **Correção**: o JS passou a alternar a classe
   **`.busca-oculto { display:none !important }`** — agora a lista **some** e sobra só a mensagem; ao
   limpar a busca, tudo volta.
3. **Cobertura do clube — casamento inteligente**: antes exigia **nome exato**. Agora compara por
   **conjunto de nomes** (tokens sem acento/caixa e **sem conectores** de/da/do): o participante casa
   com um aventureiro quando **todos os nomes digitados estão contidos** no nome cadastrado **e** isso
   aponta para **um único** aventureiro. Se servir para mais de um → **"a conferir"** (não casa errado),
   com aviso "⚠️ N a conferir". Ex.: "Beatriz Gonçalves" casa com "Beatriz Gonçalves Steinmeyer"; "Beatriz"
   sozinho (duas Beatriz) fica a conferir.

### Arquivos alterados
- `core/views.py`: helpers `_tokens_nome`/`_CONECTORES_NOME`; `_montar_dashboard` refez a cobertura
  (subconjunto de tokens + unicidade + contagem de `ambiguos`).
- `static/js/evento_painel.js`: `ligarBusca` usa `classList.toggle("busca-oculto", …)` (não mais o
  atributo `hidden`).
- `templates/core/evento_painel.html`: buscas (Inscrições e cobertura) em `.busca-box` com lupa SVG;
  aviso "a conferir" na cobertura.
- `static/css/eventos.css`: `.busca-box`/`.busca-icone`/`.busca-input` (pill + foco), `.busca-oculto`
  (`display:none !important`) e `.cob-aviso`.

### Decisões / proposta
- **Casamento por tokens + unicidade** é conservador (prefere não casar a casar errado — como o usuário
  pediu no caso "Beatriz"). Continua sendo **melhor esforço**.
- **Proposta para o vínculo EXATO** (a combinar): no formulário de inscrição, quando o **responsável
  está logado**, oferecer para **escolher o participante entre os aventureiros DELE** (lista curta e
  privada — não expõe o clube todo). Cria `ParticipanteInscricao.aventureiro` (FK opcional) → cobertura
  100% exata. Para inscrição pública/sem login, mantém texto livre + o casamento por nome. Requer
  migration + mexer no form público — **não implementado ainda** (aguarda o "ok").

### Validação
- `manage.py check` OK. Teste do casamento (nomes fictícios p/ não colidir com dados reais): "Xbeatriz
  Xgoncalves" → casa com "...Xstein"; "Xbeatriz Xsilva" → casa com "...Xsilva"; "Xjoao Xalves" → casa;
  "Xbeatriz" sozinho → **ambíguo** (não casa; conta em "a conferir"). Visual (Chrome headless, dados
  fictícios): caixa de busca com lupa + aviso "a conferir" conferidos.

### Pendências / próximo passo
- Decidir o **vínculo exato na inscrição** (proposta acima). Fase 5: **5.3 códigos de desconto**, depois
  **5.4 presença/check-in**.

---

## 2026-07-04 - Evento complexo — Fase 5 (parte 2): Resumo vira dashboard

### Resumo
A aba **Resumo** do painel virou um **dashboard** visual e didático (pedido do usuário: "bem bonito,
fácil de entender"). Conteúdo:
1. **KPIs repaginados**: ícones por card; **Receitas em verde**, **Custos em vermelho**, **Resultado**
   em destaque (verde/vermelho); hover.
2. **Gráficos em CSS/SVG puro** (sem bibliotecas — regra do projeto): **Receitas × Custos** (barras
   verde/vermelho + resultado), **Entradas por forma de pagamento** e **Inscritos por faixa etária**
   (barras azul, com valor rotulado). Cor segue a boa prática: magnitude num **tom só** (azul), status
   (verde/vermelho) **sempre com rótulo** — a cor nunca é a única pista.
3. **Cobertura do clube** ("Aventureiros do clube neste evento"): **donut** ("X de Y inscritos", %) +
   duas listas — **Inscritos** e **Ainda não inscritos** — dos aventureiros cadastrados, **casadas por
   nome** (melhor esforço — a inscrição guarda nome livre, sem vínculo rígido com o cadastro), com
   **busca em tempo real**.
4. **Busca na aba Inscrições**: filtra a lista por responsável/participante ("fulano se inscreveu?" —
   se não aparece, não se inscreveu).

Divisão de responsabilidades (para não duplicar com o Financeiro): **gráfico/visual mora no Resumo;
número/tabela/extrato mora no Financeiro**.

### Arquivos criados/alterados
- `core/views.py`: helper **`_montar_dashboard`** (cobertura por nome via `_normaliza`/`Aventureiro`;
  séries dos gráficos: formas, faixas, receitas×custos com percentuais prontos); `evento_painel_view`
  passa `dashboard` no contexto (e `financeiro` como variável).
- `templates/core/evento_painel.html`: aba **Resumo** reconstruída (KPIs com ícone, gráficos de barra,
  donut e cobertura com busca); aba **Inscrições** ganhou a caixa de busca + `.inscricao-busca` nos itens
  e a mensagem "nenhuma inscrição encontrada".
- `static/js/evento_painel.js`: helper **`ligarBusca`** (normaliza + filtra, padrão do `usuarios.js`)
  ligado à cobertura (`#buscaCobertura`) e às inscrições (`#buscaInscricoes`).
- `static/css/eventos.css`: KPIs (ícone/cores), `.dash-graficos`/`.dash-card`, barras
  (`.barra-*`, verde/vermelho/azul), **donut** (`.donut*`, via `pathLength="100"` + `stroke-dasharray`),
  cobertura (`.cobertura-*`, `.cob-item`) e `.busca-input` (largura total). Responsivo.

### Decisões tomadas
- **Cobertura por nome (melhor esforço)**: não há vínculo rígido entre `ParticipanteInscricao` (nome
  livre) e `Aventureiro`; casa por nome normalizado (ignora caixa/acentos). Serve como referência; um dia
  pode virar vínculo real.
- **Charts sem lib** (CSS/SVG). Paleta: magnitude em tom único (azul); status verde/vermelho com rótulo.
- **Duas buscas**: cobertura (membros do clube, inscrito/não) e Inscrições (todos, inclusive público).

### Validação
- `manage.py check` OK. Teste do helper `_montar_dashboard` com dados fictícios: cobertura casa por nome
  **mesmo em minúsculo** (1 inscrito), não-membro fica **fora** da cobertura, faixas/formas/receitas×custos
  com contagens e percentuais corretos. **Visual (Chrome headless, dados fictícios — sem expor nomes
  reais de menores)**: KPIs, 3 gráficos de barra, donut de cobertura e listas com busca — conferidos em
  **desktop e mobile (~470px)**, sem overflow.

### Pendências / próximo passo
- **Fase 5 — parte 3: códigos de desconto** (cupons %). Depois: **presença/check-in**. Pagamento real
  (gateway) segue para depois.

---

## 2026-07-04 - Painel de evento inexistente redireciona (em vez de 404 cru)

### Resumo
Depois de excluir um evento, um **link/aba antigo** para o painel dele (`/eventos/<id>/`) mostrava um
**404 cru do Django**. Agora, se o evento não existe (ex.: foi excluído), o painel **redireciona** para a
lista de Eventos com um **toast**: "Esse evento não existe mais (pode ter sido excluído)." — UX
consistente com o resto do sistema (o 404 do evento 33/`_TESTE_PGTO`, já removido, foi o gatilho).

### Arquivos alterados
- `core/views.py`: `evento_painel_view` troca `get_object_or_404` por busca + redirect com `messages.info`
  para `core:eventos` quando o evento não existe.

### Validação
- `manage.py check` OK. Teste (Diretor): `GET /eventos/999999/` → **302** para `/eventos/`; seguindo o
  redirect, a página traz o **toast** "não existe mais".

### Observação
- As demais rotas de evento (loja/página/PDV/etc.) seguem com `get_object_or_404`; dá para estender o
  mesmo tratamento se algum link antigo delas incomodar.

---

## 2026-07-04 - Evento complexo — Fase 5 (parte 1): Financeiro (extrato completo)

### Resumo
A aba **Financeiro** do painel do evento deixou de ser "em breve" e virou o **extrato/prestação de
contas** do evento — a pedido do usuário, "bem completo, bonito e responsivo". Conteúdo:
1. **Resultado** em destaque: **Entradas − Saídas = Resultado** (banner verde/vermelho, com selo
   Lucro/Prejuízo/Zerado).
2. **Resumos** (cards): **por fonte** (inscrições × lojinha), **por forma de pagamento** (dinheiro/Pix/
   cartão/cortesia/online, com quantidade), **por canal** (online × balcão) e **saídas** (total de
   custos + botão "Gerenciar custos" que troca para a aba Custos).
3. **Vendidos por produto** (tabela **movida do Resumo** para o Financeiro).
4. **Extrato**: lista **cronológica** de **todos** os lançamentos — cada inscrição, pedido e custo — com
   data, tipo (badge), código, forma, canal e valor (**+** verde para entradas, **−** vermelho para
   saídas). **Cancelados aparecem** (riscados, selo "cancelado") para auditoria, mas **não entram nos
   totais** (só confirmados contam; cortesia soma R$ 0).

**Divisão de responsabilidades** (definida com o usuário, para não duplicar): **número/tabela** mora no
**Financeiro**; **gráfico** morará no **Resumo/dashboard** (próxima parte da Fase 5). O único indicador
repetido de propósito é o **Resultado**. Os **custos continuam sendo cadastrados na aba Custos** — o
Financeiro só **consolida** (não duplica o CRUD).

### Arquivos criados/alterados
- `core/views.py`: helper **`_montar_financeiro(...)`** (entradas por forma/canal, extrato de todos os
  lançamentos com flag `cancelado`, totais) e `evento_painel_view` passa `financeiro` no contexto.
- `templates/core/evento_painel.html`: aba **Financeiro** completa (banner de resultado, cards de
  resumo, "vendidos por produto" e extrato); o bloco "vendidos por produto" saiu do **Resumo** (que
  ficou com os KPIs + nota de que os gráficos vêm em breve).
- `static/js/evento_painel.js`: botões `[data-aba-ir]` trocam de aba (ex.: "Gerenciar custos →").
- `static/css/eventos.css`: estilos do Financeiro — `.fin-resultado` (banner), `.fin-cards`/`.fin-card`,
  `.tabela-extrato` e `.lanc-*` (badges por tipo, +/−, cancelado riscado). Responsivo (cards empilham no
  celular; extrato rola dentro de `.tabela-scroll`).

### Decisões tomadas
- **Financeiro = extrato/contabilidade** (números + extrato); **Resumo/dashboard = visual** (KPIs +
  gráficos, próxima parte). Evita duplicar responsabilidades.
- Só **confirmados** entram nos totais; **cancelados** ficam visíveis no extrato (auditoria). Cortesia
  conta como transação com valor R$ 0.
- **Custos** permanecem na aba Custos (com upload de comprovante); o Financeiro apenas consolida.

### Validação
- `manage.py check` OK. Render (test client + Chrome headless) com dados variados (1 inscrição online, 1
  pedido Pix, 1 pedido cancelado, 1 pedido cortesia, 1 custo): **Entradas R$ 54 − Saídas R$ 50 =
  Resultado R$ 4 (Lucro)**; "por forma" (Online 30 / Pix 24 / Cortesia 0), "por canal" (Online 54 /
  Balcão 0), "vendidos por produto" (qtd 3 / R$ 24), extrato com 5 lançamentos (3 entradas + 1 saída;
  cancelado riscado fora do total). Conferido em **mobile (~490px)** e **desktop** — sem overflow (extrato
  rola no próprio contêiner).

### Pendências / próximo passo
- **Fase 5 — parte 2: dashboard/gráficos** no Resumo (CSS/SVG puro, sem bibliotecas). Depois: **códigos
  de desconto** e **presença/check-in**. Pagamento real (gateway) segue para depois.

---

## 2026-07-04 - Excluir evento (Diretor) — só quando o evento está vazio

### Resumo
O Diretor agora pode **excluir um evento** pela lista de Eventos. Para proteger dados de pessoas e de
vendas, a exclusão é permitida **apenas quando o evento está "vazio"** — sem nenhuma **inscrição** e sem
nenhum **pedido** da lojinha. Assim dá para apagar eventos de **teste/erro** sem risco; eventos que já
têm gente inscrita ou vendas são **preservados** (independentemente da data). Decisão alinhada com o
usuário (a alternativa "só por data" foi descartada por permitir apagar um evento futuro que já tem
inscrições/pedidos). Também foi **removido** um evento de teste que sobrou de uma execução anterior
(`_TESTE_PGTO`, id 33 — vazio).

### Comportamento
- Na lista, cada evento **vazio** ganha um botão **🗑️ Excluir** (discreto/destrutivo). Eventos com
  inscrições/pedidos **não** exibem o botão. Ao excluir, pede **confirmação** e mostra **toast** de
  sucesso; a exclusão remove em cascata a configuração do evento (custos, produtos, faixas, campos,
  operadores). A regra é **revalidada no servidor** (não confia só na ausência do botão).

### Arquivos criados/alterados
- `core/views.py`: `eventos_view` anota `e.pode_excluir` (sem inscrições nem pedidos); nova
  `evento_excluir_view` (`@diretor_required` + `@require_POST`) — bloqueia com mensagem se houver
  inscrições/pedidos, senão apaga e redireciona para a lista com toast.
- `core/urls.py`: rota `evento_excluir` (`/eventos/<id>/excluir/`).
- `templates/core/eventos.html`: botão **Excluir** (form POST com `data-confirmar`) só quando
  `e.pode_excluir`.
- `static/js/eventos.js`: guarda genérica — `<form data-confirmar="...">` pede `confirm()` antes de
  enviar (reutilizável para ações destrutivas).
- `static/css/eventos.css`: estilo do `.btn-excluir-evento` (ghost destrutivo) + `align-items` no
  `.evento-acoes`.

### Decisões tomadas
- **Guardar por conteúdo, não por data**: só exclui evento sem inscrições e sem pedidos. É o que
  cobre com segurança o caso de "apagar evento de teste/erro" sem destruir dados reais.
- Confirmação via `data-confirmar` (JS puro em `eventos.js`), reaproveitável em outras exclusões.

### Validação
- Teste (test client, logado como Diretor): GET lista 200; **excluir evento vazio** → some (302);
  **excluir evento com pedido** → bloqueado (302, evento e pedido **preservados**); **GET** em
  `/excluir/` → **405** (`require_POST`); **não-diretor** → redirecionado, evento preservado; o **botão
  Excluir não aparece** no evento com dados. Todos passaram. `manage.py check` OK. **Visual (Chrome
  headless)**: na lista, o botão 🗑️ Excluir aparece só nos eventos vazios (Reunião e o de teste), e
  **não** no "ACAMPAMENTO…" (que tem pedidos).

---

## 2026-07-04 - Correções de notificação (toast) no fluxo de pagamento da loja

### Resumo
Ajustes pedidos após validar o fluxo de pagamento da lojinha pública:
1. **Toast "Pagamento aprovado!" na hora**: ao "Simular pagamento aprovado", a notificação aparecia só
   **na página seguinte** (ao clicar em "Fazer outro pedido"/"Voltar para o evento"). **Causa**: a tela
   de sucesso (`evento_pedido_sucesso.html`) **não renderizava** o bloco `{% if messages %}`, então a
   mensagem ficava pendente e só era exibida na próxima página que renderizava o bloco. **Correção**: a
   tela de sucesso passou a renderizar o bloco de mensagens → o toast aparece **na própria tela de
   sucesso**.
2. **Balão não sumia** nas páginas públicas: o toast ficava na tela mesmo depois da barrinha de
   progresso. **Causa**: as páginas públicas do evento (loja, página do evento, inscrição, e as novas de
   pagamento/sucesso) **não carregavam** o `inicio.js` (que faz mover para o `<body>` + auto-fechar).
   **Correção**: `inicio.js` passou a ser carregado nessas páginas (é seguro — cada bloco tem guarda de
   elemento).
3. **Copiar o Pix usa a notificação padrão**: o botão "Copiar" do código Pix mostrava um aviso próprio;
   agora dispara o **toast clássico** do sistema ("Código Pix copiado!").

Para isso, o **toast foi centralizado** no `inicio.js` (padrão único do sistema) e ganhou uma API
`window.mostrarToast(texto, tipo)` para criar toast pelo JS, reaproveitada pela cópia do Pix — sem
duplicar a lógica de toast em outro arquivo.

### Arquivos alterados
- `static/js/inicio.js`: bloco de toast reestruturado (helpers `garantirContainer`/`fechar`/`agendar`)
  + **`window.mostrarToast(texto, tipo)`** (cria o contêiner se faltar; mesmo visual/tempo — 4,5s).
- `templates/core/evento_pedido_sucesso.html`: renderiza o bloco `{% if messages %}` (toast na hora) e
  carrega `inicio.js`.
- `templates/core/evento_loja.html`, `evento_pagina.html`, `evento_inscrever.html`,
  `evento_pagamento.html`: passam a carregar `inicio.js` (no pagamento, **antes** do
  `evento_pagamento.js`, para `window.mostrarToast` já existir).
- `static/js/evento_pagamento.js`: o feedback de "copiado" usa `window.mostrarToast(...)` (com fallback
  no texto do botão). `evento_pagamento.html`: removido o aviso próprio `#pixCopiado`.
- `static/css/eventos.css`: removida a regra órfã `.pix-aviso`.

### Decisões tomadas
- **Um único módulo de toast** (`inicio.js`), carregado onde houver notificação (inclusive páginas
  públicas). Nada de segundo mecanismo — mantém o "padrão único" documentado nas REGRAS.
- Toast criado por JS usa o **mesmo** visual/tempo dos toasts do servidor (classe `.mensagem`/CSS).

### Validação
- Teste ponta a ponta (test client): fluxo Pix continua OK (POST sem WhatsApp/sem forma rejeitados;
  válido → pagamento sem criar pedido; aprovar cria confirmado, baixa estoque, limpa sessão; sucesso com
  código/"Pago com"; cartão com aviso Mercado Pago). A tela de sucesso agora **contém** o toast
  (`mensagem-success` "Pagamento aprovado! Pedido confirmado.") e carrega `inicio.js`. `manage.py check`
  OK. **Visual (Chrome headless ~490px)**: toast aparece no topo da tela de sucesso (auto-some em ~4,5s).

---

## 2026-07-04 - Lojinha pública: fluxo de pagamento (simulado) Pix/Cartão

### Resumo
Melhoria do fluxo de **compra na lojinha pela página pública** do evento (o cliente final — sem ser
atendente/diretoria — que compra para chegar já pago e **evitar fila** na retirada). Antes, ao
"Finalizar", o pedido era confirmado na hora, sem escolher forma de pagamento. Agora:
1. **WhatsApp obrigatório** (e-mail opcional) nos dados do comprador.
2. **Autopreenchimento**: os dados do comprador (nome/WhatsApp/e-mail) são lembrados no **localStorage**
   do próprio aparelho (celular e PC) e preenchem sozinhos em pedidos seguintes.
3. **Forma de pagamento** na loja: **Pix** ou **Cartão de crédito** (cards selecionáveis).
4. **Tela de pagamento** (`/eventos/<id>/loja/pagamento/`): no **Pix**, a tela clássica com **QR Code
   (simulado)** e **código "copia e cola"** com botão **Copiar**; no **cartão**, aviso de que **em
   produção** haverá **redirecionamento ao Mercado Pago** (integração futura). Botão **"Simular
   pagamento aprovado"**.
5. **Sucesso melhorado**: lista dos itens em linhas (qtd × produto/variação → subtotal), total e
   "**Pago com Pix/Cartão**".

O **pagamento é simulado** (só ilustra o processo). O **`PedidoLoja` só é criado no banco após a
aprovação**: enquanto pendente, o pedido fica na **sessão** (`loja_checkout`) — evita pedido "pendente"
e estoque reservado por carrinho abandonado; a baixa de estoque (revalidada) acontece só na aprovação.
Escopo: **apenas a loja pública** — o PDV/balcão e o fluxo de inscrição continuam como estavam.

### Arquivos criados/alterados
- `core/views.py`: `evento_loja_view` (WhatsApp obrigatório + forma de pagamento → guarda `loja_checkout`
  na sessão e redireciona para o pagamento, **sem** criar pedido); nova `evento_pagamento_view` (GET
  mostra Pix/cartão; POST simula a aprovação, revalida estoque, cria o pedido confirmado e vai ao
  sucesso). Helpers novos: `_erros_estoque`, `_pseudo_qr`, `_qr_svg` (SVG de QR **simulado**),
  `_pix_copia_cola` (payload Pix **simulado**). Constante `FORMAS_PAGAMENTO_ONLINE` (pix/cartão).
- `core/urls.py`: rota `evento_pagamento` (`/eventos/<id>/loja/pagamento/`).
- `templates/core/evento_loja.html`: WhatsApp `*`, e-mail "(opcional)", seção "Forma de pagamento",
  botão "Ir para o pagamento"; inclui `loja_comprador.js`.
- `templates/core/evento_pagamento.html` (novo): tela de pagamento (Pix: QR + copia e cola; cartão:
  aviso Mercado Pago) + botão "Simular pagamento aprovado".
- `templates/core/evento_pedido_sucesso.html`: lista de itens em linhas + forma de pagamento.
- `static/js/loja_comprador.js` (novo): autopreenchimento via localStorage. `static/js/evento_pagamento.js`
  (novo): botão "Copiar" do código Pix (com fallback `execCommand`).
- `static/css/eventos.css`: cards de forma de pagamento (`.pagamento-metodo`), tela de pagamento
  (`.pagamento-resumo`, `.pix-qr`, `.pix-copia`, `.cartao-mock`, `.pagamento-simulado`) e lista de
  sucesso (`.pedido-lista`).

### Decisões tomadas
- **Pedido só após a aprovação** (dados na sessão enquanto pendente): "só aparece pedido confirmado",
  sem lixo de pedidos abandonados nem estoque preso. Reaproveita `_criar_pedido` com
  `forma_pagamento` pix/cartão e `origem="online"`.
- **QR e "copia e cola" simulados**, gerados sem biblioteca externa (regra do projeto) — o QR é
  decorativo/determinístico (não escaneável) e o payload Pix é fictício. O QR/pagamento reais virão
  com a integração do gateway (**Mercado Pago**), a conversar depois.
- **Formas online = Pix e Cartão** apenas (dinheiro/cortesia continuam no PDV/balcão).

### Validação
- Teste ponta a ponta (test client): GET loja; POST **sem WhatsApp** e **sem forma** rejeitados (0
  pedidos); POST válido → redireciona ao pagamento **sem criar pedido** (dados na sessão); GET pagamento
  Pix (QR/`<svg>` + código Pix + botão simular); **POST aprovar** cria o pedido **confirmado**
  (forma=pix, origem=online, total correto), **baixa o estoque** (5→3) e **limpa a sessão**; GET sucesso
  com código e "Pago com"; GET pagamento **cartão** com aviso do Mercado Pago (sem QR). Todos passaram.
  `manage.py check` OK. **Visual (Chrome headless ~490px)**: loja (WhatsApp*/forma), pagamento Pix
  (QR + copia e cola), pagamento cartão (mock + aviso) e sucesso (lista + total) — sem overflow.

### Pendências / próximo passo
- **Pagamento real (gateway)**: Pix real (QR/BR Code) e **redirecionamento ao Mercado Pago** no cartão
  — a alinhar em conversa futura. Depois, avaliar aplicar o mesmo passo de pagamento à **inscrição** online.
- **Fase 5 — Financeiro/gráficos** segue como o próximo grande passo do evento complexo.

---

## 2026-07-04 - Toasts melhorados (canto da tela + visual) — padrão único do sistema

### Resumo
Refinamento das notificações (pedido do usuário):
- **Posição**: o balão agora aparece **sempre no canto superior direito da TELA** (topo no celular),
  não mais "grudado" na região do conteúdo. **Causa do bug**: `.conteudo-interno` tem
  `animation: entrar` (com `transform`), e um ancestral com `transform` quebra o `position: fixed`
  (vira o bloco de contenção). **Correção**: o `inicio.js` move o contêiner `.mensagens` para o
  `<body>`, fora de qualquer ancestral transformado.
- **Visual**: toast **maior**, com **ícone por tipo** (✅ sucesso, ⛔ erro, ℹ️ info, ⚠️ aviso),
  sombra mais forte, entrada com leve escala e uma **barra de progresso** (mostra o tempo até fechar).
- **Padrão único**: documentado que **todo o sistema** (inscrições, cadastros, e o que vier) deve usar
  esse mesmo tipo de notificação, só nos pontos que realmente exigem aviso (sem poluir a tela).
- A venda/inscrição **cancelada** continua exibida (mais apagada + selo "Cancelado") de propósito,
  para **auditoria** — confirmado com o usuário.

### Arquivos alterados
- `static/js/inicio.js`: move `.mensagens` para o `<body>` antes de exibir/auto-fechar os toasts.
- `static/css/inicio.css`: toast maior, ícone (`::before`), barra de progresso (`::after`), sombra e
  animações de entrada/saída aprimoradas.
- `docs/REGRAS_CODEX.md`: reforça que os toasts são o padrão único de notificação do sistema.

### Validação
- Toast conferido no desktop: aparece no **canto superior direito da tela**, maior, com ícone ✅,
  sombra e barra de progresso. `manage.py check` OK.

---

## 2026-07-04 - Página do evento (botões claros) + notificações (toasts) no módulo de eventos

### Resumo
1. **Página do evento** (`evento_pagina.html`): removida a seção "O formulário de inscrição pedirá…"
   (preview dos campos) — a pessoa vê os campos ao clicar em inscrever. Os dois botões ficaram
   **claros**: **"🎟️ Inscrever-se no evento"** (com dica "Para fazer a inscrição dos participantes.")
   e **"🛒 Comprar na loja"** (com dica "Só para comprar produtos/itens — não faz inscrição."), para
   o visitante não confundir inscrição com compra.
2. **Notificações (toasts)**: as mensagens de feedback viraram **toasts flutuantes** (canto superior
   direito no desktop, topo no celular), com cor por tipo (sucesso/erro/info/aviso), animação de
   entrada e **auto-fecham** em alguns segundos (ou ao clicar). Assim toda ação no módulo de eventos
   (criar/editar/remover produto, evento, faixa, campo, custo; registrar venda/inscrição no PDV;
   operadores; etc.) mostra visualmente que **deu certo** (ou o erro). Faltava aviso ao **reordenar
   campo** — adicionado ("Ordem dos campos atualizada.").

### Arquivos alterados
- `templates/core/evento_pagina.html`: sem preview de campos; botões com rótulo + dica claros.
- `static/css/eventos.css`: `.evento-acoes`/`.evento-acao-item`/`.evento-acao-dica`.
- `static/css/inicio.css`: `.mensagens` viram **toasts fixos** + `.mensagem`/variantes (success/error/
  info/warning) + animações `toast-entra`/`toast-sai`.
- `static/js/inicio.js`: toasts fecham ao clicar e somem sozinhos (auto-dismiss escalonado).
- `core/views.py`: `evento_campo_mover_view` passou a notificar.

### Decisões tomadas
- Toasts são as **mensagens do Django** (`messages`) estilizadas — mantém 1 só mecanismo. Auto-dismiss
  no `inicio.js` (carregado nas telas internas/PDV, onde estão as ações). Em páginas públicas de
  compra os erros continuam visíveis (não somem sozinhos), o que é desejável.
- **Regra**: toda ação relevante do usuário deve gerar uma notificação (sucesso/erro) — ver REGRAS.

### Validação
- Teste ponta a ponta: página do evento sem o preview e com os dois botões claros (incl. a dica "não
  faz inscrição"); CSS/JS de toast presentes; reordenar campo notifica; ação (salvar config) mostra o
  toast de sucesso. Todos passaram. `manage.py check` OK. Toast e página conferidos visualmente.

---

## 2026-07-04 - Ajustes da lojinha/PDV (feedback da validação)

### Resumo
Ajustes pedidos após validar a Lojinha:
1. **Botões +/- de quantidade**: nas telas de compra (loja, inscrição, PDV de venda e de inscrição),
   cada variação agora tem um **stepper** `[− n +]` (arredondado, com hover/efeito) em vez de digitar
   a quantidade — mais rápido no balcão. O total ao vivo recalcula ao clicar.
2. **"Nome do cliente" (PDV venda)**: texto de ajuda explicado — se preencher, é esse nome que fica no
   pedido; se vazio, usa o nome da inscrição vinculada (se houver) ou "Cliente (balcão)".
3. **WhatsApp, e-mail e CPF do responsável** viraram **obrigatórios** no formulário de inscrição
   (com o asterisco), junto do nome.
4. **Ajudante externo — navegação corrigida**: o botão "Voltar" das telas de PDV agora leva à landing
   **"Operar"** (não ao painel do Diretor, que dava "acesso restrito"); a landing "Operar" só mostra
   "Voltar para o painel" para o Diretor; e o ajudante externo, ao cair em "/inicio/", é **redirecionado
   para o evento dele** (não vê mais "Meus Dados"/"cadastrar aventureiro").

### Arquivos alterados
- `templates/core/_loja_itens.html`: variação com stepper `.qtd-stepper` (botões `.qtd-btn`).
- `static/js/qtd_stepper.js` (novo): +/- ajusta o input e dispara `input` (recalcula o total).
  Incluído em `evento_loja.html`, `evento_inscrever.html`, `evento_pdv.html`, `evento_pdv_inscricao.html`.
- `static/css/eventos.css`: estilo do stepper.
- `core/forms.py`: `InscricaoForm` — `responsavel_whatsapp/email/cpf` obrigatórios.
- `templates/core/evento_pdv.html`: ajuda do "Nome do cliente"; "Voltar" condicional (diretor→painel /
  operador→operar). `evento_pdv_inscricao.html`: "Voltar" condicional. `evento_operar.html`: "Voltar
  para o painel" só para diretor.
- `core/views.py`: `inicio_view` redireciona ajudante externo para o "Operar" do evento dele.

### Validação
- Teste ponta a ponta: stepper presente; whatsapp/email/cpf obrigatórios (bloqueia sem eles, cria com
  todos); ajudante externo (inicio→operar, PDV "Voltar"→operar, sem link para o painel); diretor
  "Voltar"→painel. Todos passaram. `manage.py check` OK. Stepper conferido visualmente (~490px).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.4c: operadores do evento (conclui a Lojinha)

### Resumo
**Parte 4.4c** (última do PDV/Lojinha): o **Diretor** define, por evento, **quem pode operar o PDV**:
- **Diretoria selecionada**: habilita membros da diretoria (Diretor/Tesoureiro/Secretário/Professor).
- **Ajudantes externos**: cria uma **conta temporária** (usuário + senha inicial **`1234`**) só para o
  evento; no 1º acesso a pessoa é **obrigada a trocar a senha** (2×); o Diretor pode **resetar** para
  `1234`; ao logar, o ajudante vê **só o(s) evento(s) dele** no menu e cai direto na tela **"Operar"**.
Operadores acessam o **PDV** (venda + inscrição) via a landing **"Operar"** (`/eventos/<id>/operar/`).
Gerência em **"Operadores"** na aba Lojinha do painel (habilitar/criar/resetar/remover). O menu lateral
foi **centralizado** num único parcial (`_menu.html`) para tratar os três casos (diretor/membro,
operador, ajudante externo) de forma consistente.

### Arquivos criados/alterados
- `core/models.py`: `PerfilUsuario` (OneToOne User, `precisa_trocar_senha`) e `OperadorEvento`
  (evento, usuario, `externo`). Migration `0013`.
- `core/permissoes.py`: `pode_operar_evento` + decorator `operador_required` (Diretor ou operador).
- `core/middleware.py` (novo) + `config/settings.py`: `TrocaSenhaObrigatoriaMiddleware` (enquanto
  `precisa_trocar_senha`, redireciona tudo para a troca de senha).
- `core/context_processors.py`: expõe `operador_eventos` e `eh_operador_externo`.
- `core/views.py`: `evento_operar_view` (landing), `evento_operadores_view` + add diretoria/externo,
  reset e remover; `trocar_senha_view`; PDV agora com `@operador_required`; login redireciona o
  ajudante externo para o evento dele.
- `core/urls.py`: rotas de operador + `trocar-senha/`. `core/admin.py`: `OperadorEvento`, `PerfilUsuario`.
- `templates/core/_menu.html` (novo, menu central) — substituiu o `<nav class="menu">` inline em **todos**
  os 9 templates internos. `evento_operar.html`, `evento_operadores.html`, `trocar_senha.html` (novos);
  `evento_painel.html` (botão "Operadores").
- `static/css/eventos.css`: cards de "Operar" e lista de operadores.

### Decisões tomadas
- Operadores por evento (`OperadorEvento`); `externo=True` = conta temporária de ajudante.
- Troca de senha obrigatória via **middleware** (cobre qualquer rota). Reset volta para `1234`.
- Menu do ajudante externo restrito a seus eventos (via `_menu.html` + `eh_operador_externo`); login
  o leva direto ao "Operar". Remover um ajudante externo sem outros eventos **apaga a conta**.
- Menu lateral **centralizado** em `_menu.html` (fim da duplicação; editar o menu num lugar só).

### Validação
- Teste ponta a ponta: gerência (habilitar diretoria; criar ajudante com senha 1234 + troca
  obrigatória); operador da diretoria acessa PDV/operar e **estranho é bloqueado**; login do ajudante
  externo → **troca de senha obrigatória** → "Operar" com **menu restrito** (só o evento; sem "Meus
  Dados"); ajudante vende no PDV; **reset** de senha; **remover** apaga a conta externa; menu do
  diretor intacto. Todos passaram. `manage.py check` OK. **Responsividade** (~490px) das telas novas +
  menu no desktop conferidos.

### Pendências / próximo passo
- **🎉 Lojinha (Fase 4) concluída.** Próximo: **Fase 5 — Financeiro/gráficos** (resultado detalhado,
  cupons de desconto, presença/check-in). Depois: pagamentos reais (gateway); loja oficial do clube.

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.4b: PDV inscrição + relatório de vendas por produto

### Resumo
Dois ajustes/entregas a partir da validação:
1. **Relatório "Vendidos por produto"** no **Resumo** (dashboard): tabela Produto | **Qtd** | **Arrecadado**.
   A **quantidade conta tudo, inclusive cortesia** (controle de quantos saíram); o **arrecadado é só o
   dinheiro** (cortesia entra com 0). Decisão: cortesia continua com **valor zerado** no financeiro.
2. **PDV — Nova inscrição (4.4b)**: o atendente faz uma **inscrição presencial** e, no mesmo balcão,
   pode **adicionar itens da lojinha**; tudo num **pagamento só** (forma de pagamento; **troco** no
   dinheiro sobre o **total combinado** = inscrição + itens; **total ao vivo**). Cria a inscrição +
   um **pedido de lojinha vinculado**; **cortesia** deixa o conjunto grátis (baixa estoque). Botão
   **"Nova inscrição (balcão)"** na aba Inscrições. A venda **só lojinha** continua na 4.4a. Restrito
   ao Diretor por ora (operadores → 4.4c).

### Arquivos criados/alterados
- `core/models.py`: `Inscricao` ganhou `origem`, `forma_pagamento`, `valor_recebido`, `registrado_por`
  + props `total_com_loja` e `troco`. Choices de pagamento movidas para antes de `Inscricao`.
  Migration `0012`.
- `core/views.py`: `evento_painel_view` calcula `vendas_por_produto`; nova `evento_pdv_inscricao_view`
  (inscrição + lojinha + pagamento combinado; cortesia zera; troco).
- `core/urls.py`: rota `evento_pdv_inscricao`. `core/admin.py`: inscrição mostra origem/forma.
- `templates/core/evento_pdv_inscricao.html` (novo). `evento_painel.html`: tabela "Vendidos por
  produto" no Resumo + botão "Nova inscrição (balcão)" + selo origem/forma nas inscrições.
- `static/js/evento_pdv_inscricao.js` (total combinado ao vivo por faixa/diretoria + lojinha + troco).
- `static/css/eventos.css`: tabela do relatório.

### Decisões (validadas com o usuário)
- **Cortesia**: valor 0 no financeiro; controle de quantidade fica no **relatório** (dashboard).
- **PDV inscrição + lojinha = um pagamento só** (uma transação, um troco); gera inscrição + pedido
  vinculado por baixo. Mantida a venda **só lojinha** (4.4a) para quem não vai se inscrever.

### Validação
- Teste ponta a ponta: PDV inscrição + lojinha com pagamento combinado (troco 6 sobre 54); inscrição
  sem lojinha (cartão); **cortesia** (inscrição+item grátis, baixa estoque); dinheiro insuficiente
  sobre o combinado rejeitado; relatório "Vendidos por produto" (qtd inclui cortesia); arrecadação (60)
  × vendas (24) separadas. Todos passaram. `manage.py check` OK. **Responsividade** (~490px) conferida.

### Pendências / próximo passo
- **Lojinha 4.4c** — **operadores do evento**: diretoria selecionada + contas temporárias de ajudantes
  externos (senha `1234`, troca obrigatória no 1º login, reset pelo Diretor; ajudante vê só o evento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.4a: PDV / balcão de vendas

### Resumo
**Parte 4.4a** (primeira do PDV): tela de **balcão** (`/eventos/<id>/pdv/`) para registrar vendas da
lojinha no dia do evento. O operador monta o pedido (quantidade por variação, **total ao vivo**),
escolhe a **forma de pagamento** (**Dinheiro** com **campo de valor recebido → troco automático**,
Pix, Cartão, **Cortesia**) e registra; pode **vincular a venda a uma inscrição** (opcional — para
rastrear o que foi comprado por pessoa) ou deixar **avulsa**. Baixa estoque e entra em "Vendas
(lojinha)" (cortesia não soma). Por ora **restrito ao Diretor**; os **operadores** (diretoria
selecionada + ajudantes externos) virão na 4.4c; a inscrição pelo PDV vem na 4.4b. Acesso pela aba
"Lojinha" do painel (botão **"PDV / Balcão"**).

### Arquivos criados/alterados
- `core/models.py`: `PedidoLoja` ganhou `origem` (online/pdv), `forma_pagamento`
  (online/dinheiro/pix/cartão/cortesia), `valor_recebido`, `registrado_por` + property `troco`.
  Choices `FORMA_PAGAMENTO_CHOICES`/`ORIGEM_PEDIDO_CHOICES`. Migration `0011`.
- `core/views.py`: `evento_pdv_view` (Diretor); `_criar_pedido` passou a aceitar
  forma/valor_recebido/origem/registrado_por e trata **cortesia** (itens grátis, estoque baixa).
- `core/urls.py`: rota `evento_pdv`. `core/admin.py`: pedido mostra origem/forma.
- `templates/core/evento_pdv.html` (novo, layout interno). `evento_painel.html`: botão "PDV / Balcão"
  na aba Lojinha + badges de origem/forma nos pedidos.
- `static/js/evento_pdv.js`: total ao vivo + alternância da forma + troco (e cortesia = total 0).
- `static/css/eventos.css`: formas de pagamento, troco, `.secao-acoes`.

### Decisões tomadas
- Vínculo venda×inscrição **opcional** (rastreia quando quiser; permite venda a passante). Reaproveita
  `PedidoLoja.inscricao`.
- **Cortesia** registra o item (baixa estoque) com valor 0 (não entra em vendas).
- PDV volta pra si mesmo após registrar (com mensagem de código + troco) para vendas rápidas em série.

### Validação
- Teste ponta a ponta (Diretor): GET; venda em dinheiro avulsa (troco 18, baixa estoque); venda
  vinculada a inscrição (herda o nome do responsável); cortesia (total 0, baixa estoque); dinheiro
  insuficiente e sem itens rejeitados; Resumo com vendas do PDV (cortesia não soma); **não-diretor
  bloqueado**. Todos passaram. `python manage.py check` OK. **Responsividade** (~490px) do PDV conferida.

### Pendências / próximo passo
- **Lojinha 4.4b** — fazer **inscrição** pelo PDV (presencial, com pagamento).
- **Lojinha 4.4c** — **operadores do evento**: diretoria selecionada + contas temporárias de ajudantes
  externos (senha `1234`, troca obrigatória no 1º login, reset pelo Diretor; ajudante vê só o evento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.3: comprar junto da inscrição + pedir mais

### Resumo
**Parte 4.3**: no fim do **formulário de inscrição** aparece uma seção **opcional** "Quer levar algo da
lojinha?" com os produtos (quantidade por variação + **subtotal ao vivo**). Ao confirmar, num envio
só, cria-se a **inscrição** e — se houver itens — um **pedido da lojinha vinculado** a ela (pagamento
simulado, baixa de estoque). Se qualquer item exceder o estoque, **nada** é criado (nem a inscrição).
Para **pedir mais**, as telas de sucesso (inscrição e pedido) trazem botão **"Comprar (mais) na
lojinha"**, e o evento continua no menu (logado) para voltar quando quiser. O pedido vinculado aparece
na lista de pedidos do painel e conta em "Vendas (lojinha)".

### Arquivos criados/alterados
- `core/models.py`: `PedidoLoja.inscricao` (FK opcional → `Inscricao`). Migration `0010`.
- `core/views.py`: helpers `_coletar_itens_loja`, `_marcar_quantidades`, `_criar_pedido` (extraídos e
  reaproveitados); `evento_loja_view` refatorada; `evento_inscrever_view` passou a ler os itens da
  lojinha e criar o pedido vinculado (comprador = responsável) na mesma transação;
  `evento_inscricao_sucesso_view` mostra o pedido vinculado + oferece a lojinha.
- `templates/core/_loja_itens.html` (novo parcial, usado na loja e na inscrição);
  `evento_loja.html` e `evento_inscrever.html` usam o parcial; `evento_inscrever.html` ganhou a seção
  opcional + subtotal ao vivo; `evento_inscricao_sucesso.html` mostra o pedido + botão "Comprar mais".
- `static/js/evento_loja.js`: agora funciona por documento (loja e inscrição), atualizando `#lojaTotal`.
- `static/css/eventos.css`: `.loja-total-inline`, `.sucesso-pedido`.

### Decisões tomadas
- Um envio → **duas entidades** (Inscricao + PedidoLoja vinculado); financeiro separado (arrecadação de
  inscrições × vendas da lojinha), mas ambos no evento. Validação **tudo-ou-nada** (estoque).
- Reaproveitamento por helpers/parcial para loja e inscrição ficarem consistentes.

### Validação
- Teste ponta a ponta: seção da lojinha no form; inscrição + pedido vinculado (herda comprador, baixa
  estoque, sucesso mostra os dois + "Comprar mais"); inscrição sem itens não cria pedido (mas oferece a
  lojinha); estoque insuficiente bloqueia inscrição+pedido; dashboard com ambos. Todos passaram.
  `python manage.py check` OK. **Responsividade** (Chrome headless ~490px) do form com lojinha conferida.

### Pendências / próximo passo
- **Lojinha 4.4** — PDV dos atendentes autorizados (vendem/inscrevem no dia, marcam pago/forma de
  pagamento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.2: comprar na página do evento

### Resumo
**Parte 4.2**: a lojinha passou a **vender**. Na página do evento há o botão **"Comprar na lojinha"**
(quando há produtos ativos e o evento não terminou), que abre a **loja** (`/eventos/<id>/loja/`):
lista os produtos ativos com suas variações (preço, estoque quando controlado), um campo de
**quantidade** por variação e o **total ao vivo** (JS). No fim, dados do comprador e **Finalizar
pedido** → **pagamento simulado**, gera **código**, **baixa o estoque** (dos produtos que controlam) e
mostra a tela de sucesso. Acesso igual ao evento (público sem login; só-membros com login); a loja
fica aberta **enquanto o evento não terminou** (independe do prazo de inscrição — dá para comprar no
dia). No **painel**, a aba "Lojinha" ganhou a **lista de pedidos** (com itens e **cancelar**, que
devolve ao estoque) e o **Resumo** passou a contar **"Vendas (lojinha)"** de verdade (entra nas
receitas/resultado).

### Arquivos criados/alterados
- `core/models.py`: `PedidoLoja` (evento, comprador, código, status, valor_total) e `ItemPedidoLoja`
  (variação + snapshots + quantidade + valores); `Evento.ja_terminou()`/`loja_aberta()`; props
  `VariacaoProduto.rotulo`/`esgotado`. Migration `0009`.
- `core/views.py`: `evento_loja_view` (monta o pedido, valida estoque, baixa com `F()`),
  `evento_pedido_sucesso_view`, `evento_pedido_cancelar_view` (Diretor; devolve estoque). Painel
  calcula `vendas_loja` e passa `pedidos`; `evento_pagina_view` passa `tem_loja`.
- `core/urls.py`: rotas `evento_loja`, `evento_pedido_sucesso`, `evento_pedido_cancelar`.
  `core/admin.py`: `PedidoLoja` (inline de itens).
- `templates/core/evento_loja.html` (novo, loja + carrinho) e `evento_pedido_sucesso.html`;
  `evento_pagina.html` (botão "Comprar na lojinha"); `evento_painel.html` (lista de pedidos + cancelar).
- `static/js/evento_loja.js` (total ao vivo). `static/css/eventos.css` (loja mobile-first).

### Decisões tomadas
- **Pedido numa página só** (quantidade por variação), sem carrinho persistente — simples e rápido no
  celular; total ao vivo no cliente, mas o valor é **recomputado no servidor** (Decimal).
- **Baixa/devolução de estoque** com `F()` (atômico); só afeta produtos que controlam estoque.
- Loja independente do prazo de inscrição; fecha quando o evento termina (`fim_datetime`).

### Validação
- Teste ponta a ponta: GET público (esconde inativos); botão na página; pedido válido (2 produtos,
  total e itens corretos, baixa de estoque); estoque insuficiente e pedido sem itens/sem nome
  rejeitados; dashboard com "Vendas (lojinha)"; cancelar devolve estoque e zera vendas; loja fechada
  após o evento terminar. Todos passaram. `python manage.py check` OK.
- **Responsividade (Chrome headless ~490px)**: loja com quantidades, "esgotado" sem campo, total e
  botão — sem overflow.

### Pendências / próximo passo
- **Lojinha 4.3** — comprar **junto da inscrição** (opcional) + **voltar e pedir mais** fácil.
- Depois: 4.4 (PDV dos atendentes: pago/forma de pagamento).

---

## 2026-07-04 - Evento complexo — Lojinha Fase 4.1: cadastro de produtos

### Resumo
Início da **Lojinha** (mini-sistema de vendas por evento). **Parte 4.1**: a aba "Lojinha" do painel
deixou de ser "em breve" e agora permite **cadastrar produtos** com **variações** (cada uma com seu
**preço**) e **controle de estoque opcional por produto** (alguns vendem à vontade; outros têm
quantidade por variação). Produto tem nome, descrição, **foto** opcional e liga/desliga ("à venda").
Cadastro em página dedicada, com **linhas de variação** repetíveis (adicionar/remover) e a coluna
"Estoque" aparecendo só quando "Controlar estoque" está marcado. A **venda** (carrinho/pedidos) vem
nas próximas partes.

### Contexto (alinhado com o usuário)
A lojinha do evento será usada de vários jeitos, em fases: comprar **junto da inscrição** (opcional),
**voltar e pedir mais** depois (ex.: mais lanche no dia do evento) e, no futuro, um **PDV para
atendentes** autorizados (caixa/cantina) que vendem/inscrevem no dia e marcam pago/forma de pagamento.
Tudo dentro da página do evento (para o financeiro do evento fechar). A loja **oficial do clube**
(uniformes etc.) é outra coisa, separada, para bem depois.

### Arquivos criados/alterados
- `core/models.py`: `ProdutoEvento` (evento, nome, descrição, foto, controla_estoque, ativo, ordem) e
  `VariacaoProduto` (produto, nome, valor, estoque, ordem). Migration `0008`.
- `core/forms.py`: `ProdutoEventoForm` (dados do produto; variações tratadas na view).
- `core/views.py`: `evento_produto_novo_view`, `evento_produto_editar_view`,
  `evento_produto_excluir_view` + helpers `_parse_variacoes`/`_salvar_variacoes` (linhas indexadas,
  sincroniza criar/editar/remover). Painel carrega `produtos`.
- `core/urls.py`: rotas `evento_produto_novo`/`_editar`/`_excluir`. `core/admin.py`: `ProdutoEvento`
  (inline de variações) e `VariacaoProduto`.
- `templates/core/evento_produto_form.html` (novo, com layout interno + variações) e
  `_variacao_linha.html` (linha repetível). `evento_painel.html`: aba "Lojinha" lista os produtos.
- `static/js/evento_produto.js`: adicionar/remover variação + mostrar/ocultar estoque.
- `static/css/eventos.css`: lista de produtos e linhas de variação (mobile-first).

### Validação
- Teste ponta a ponta: cadastro com estoque + 3 variações; produto sem estoque (estoque zerado);
  edição (mudar preço, remover e adicionar variação — sincroniza); preço inválido e produto sem
  variação rejeitados; painel lista os produtos; excluir; **responsável (não-diretor) bloqueado**.
  `python manage.py check` sem problemas.
- **Responsividade (Chrome headless ~484px)**: página de cadastro de produto, aba "Lojinha" do painel
  e formulário de inscrição conferidos — sem overflow horizontal; variações e cartões quebram bem.

### Pendências / próximo passo
- **Lojinha 4.2** — comprar na página do evento (carrinho + finalizar, pagamento simulado, baixa de
  estoque, entra em "Vendas (lojinha)" no Resumo).
- Depois: 4.3 (comprar junto da inscrição + voltar e pedir mais) e 4.4 (PDV dos atendentes).

---

## 2026-07-04 - Ajustes de validação das inscrições (feedback do usuário)

### Resumo
Após validar a Fase 2 na tela, o usuário apontou ajustes; feitos todos:
1. **Bug — comentário vazando na tela**: `_menu_eventos.html` e `_participante_linha.html` usavam
   comentário `{# … #}` de **duas linhas** (que no Django só vale numa linha), então o texto do
   comentário aparecia no menu e na página de inscrição. Trocado por `{% comment %}…{% endcomment %}`.
2. **Botão "Ver no mapa"** na página do evento: link que abre o **Google Maps** no endereço do evento
   (sem API/biblioteca externa — respeita a regra do projeto). Aparece abaixo do local.
3. **Campos do formulário — por participante ou uma vez**: ao cadastrar um campo, o Diretor agora
   escolhe **"Perguntar para cada participante"**. Se marcado, o campo aparece **dentro de cada
   participante** (além de nome/idade); senão, é preenchido **uma vez**, junto dos dados do
   responsável. A seção genérica "Informações do evento" saiu.
4. **Textos**: "Perguntas extras" → "Campos do formulário de inscrição"; "Seus dados/Seu nome" →
   "Dados do responsável/Nome do responsável".

### Arquivos alterados
- `core/models.py`: `CampoInscricao.por_participante` (bool) e `RespostaInscricao.participante` (FK
  opcional). Migration `0007`.
- `core/forms.py`: `CampoInscricaoForm` inclui `por_participante`; `InscricaoForm` monta como campos
  do form **só** os de inscrição única (`por_participante=False`).
- `core/views.py`: `evento_inscrever_view` reescrita — participantes com **índice por linha**
  (`part_*_<idx>`), leitura/validação dos campos por participante (`_ler_resposta_participante`,
  `_linha_participante`, `_linha_vazia`); grava `RespostaInscricao` ligada ao participante. Painel
  separa respostas gerais (`respostas_gerais`) das por participante.
- `templates/core/_menu_eventos.html`, `_participante_linha.html`: comentário corrigido; a linha de
  participante agora renderiza os campos "por participante" (com nomes indexados e repopulação).
- `templates/core/evento_inscrever.html`: campos únicos sob "Dados do responsável"; sem "Informações
  do evento". `evento_pagina.html`: botão "Ver no mapa". `evento_painel.html`: etiqueta de escopo
  ("por participante"/"uma vez") e respostas por participante na lista de inscritos; textos revistos.
- `static/js/evento_inscrever.js`: clonagem de linha por **índice** (substitui `__IDX__`), sem o
  antigo hidden de diretoria. `static/css/eventos.css`: linha vira cartão com campos, grupos de
  checkbox, etiqueta de escopo e botão do mapa.

### Validação
- Teste ponta a ponta: comentários não vazam mais (menu e inscrição); botão "Ver no mapa" com link do
  Google Maps; form com rótulos certos e sem "Informações do evento"; POST com **2 participantes com
  tamanhos diferentes** grava a resposta certa por participante e a resposta geral separada; campo
  obrigatório por participante faltando é rejeitado; painel mostra as respostas e as etiquetas de
  escopo. Todos passaram. `python manage.py check` sem problemas.

---

## 2026-07-04 - Evento complexo — Fase 2.4: inscrição de fato (conclui a Fase 2)

### Resumo
**Parte 2.4** (última da Fase 2): a inscrição passa a **funcionar de verdade** (pagamento **simulado**).
Na página do evento, "Inscrever-se" abre o **formulário de inscrição** (`/eventos/<id>/inscrever/`):
dados do responsável + **participantes** (linhas repetíveis: nome + idade + opção "diretoria") + os
**campos personalizados** do evento (renderizados conforme o tipo). O **preço** de cada participante é
calculado no servidor (faixa etária pela idade, ou valor da diretoria se marcado); soma no **valor
total**. A inscrição nasce **confirmada**, com **código único**, e leva a uma **tela de sucesso**
(código + total). No **painel**, a aba "Inscrições" ganhou a **lista de inscritos** (código, responsável,
contato, participantes/valores, respostas, situação) com ação **Cancelar**; o **Resumo** passou a
contar **inscritos** (participantes confirmados) e **arrecadação** de verdade. Acesso: público sem
login se o evento é aberto ao público, senão exige login; após o prazo, o formulário trava.

### Arquivos criados/alterados
- `core/models.py`: modelos `Inscricao` (código único, status, valor_total), `ParticipanteInscricao`
  (nome/idade/diretoria/faixa/valor) e `RespostaInscricao` (campo + rótulo snapshot + valor); método
  `Evento.preco_participante(idade, eh_diretoria)`. Migration `0006`.
- `core/forms.py`: `InscricaoForm` (responsável + campos personalizados dinâmicos por tipo;
  `campos_personalizados` e `resposta_texto`).
- `core/views.py`: `evento_inscrever_view`, `evento_inscricao_sucesso_view`,
  `evento_inscricao_cancelar_view` (Diretor) + helper `_parse_participantes`; painel agora carrega
  inscrições e calcula inscritos/arrecadação no Resumo.
- `core/urls.py`: rotas `evento_inscrever`, `evento_inscricao_sucesso`, `evento_inscricao_cancelar`.
- `core/admin.py`: `Inscricao` (inlines de participantes e respostas).
- `templates/core/`: `evento_inscrever.html` (form), `evento_inscricao_sucesso.html`,
  `_participante_linha.html` (linha repetível); `evento_pagina.html` (botão → formulário);
  `evento_painel.html` (lista de inscritos + Cancelar na aba "Inscrições").
- `static/js/evento_inscrever.js`: adicionar/remover participante + checkbox "diretoria" → hidden.
- `static/css/eventos.css`: linhas de participante, resumo de valores, lista de inscritos, sucesso.

### Decisões tomadas
- **Diretoria** por participante (checkbox, só aparece se o evento tem valor de diretoria) → aplica o
  valor da diretoria no lugar da faixa. Alinhamento por índice via input hidden (checkbox desmarcado
  não some da lista). Autodeclarado nesta etapa; o Diretor confere na lista.
- Preço **calculado e gravado no servidor** (snapshot em cada participante); dashboard soma o
  `valor_total` das inscrições **confirmadas**. Cancelar muda o status (sai da contagem).
- Campos personalizados viram campos de formulário Django conforme o tipo (validação de obrigatório e
  de opções “de graça”); respostas gravadas como texto legível, com rótulo em snapshot.
- Pagamento **simulado**: inscrição já confirmada; sem gateway (fica para “depois”, como no plano).

### Validação
- Teste ponta a ponta (test client): precificação (faixa/diretoria/sem-faixa); GET público do form;
  POST válido (2 participantes incl. diretoria + respostas, total e faixas corretos, sim/não = "Não",
  código de 6 chars, tela de sucesso); POST inválido (obrigatório vazio + idade faltando) rejeitado;
  escolha fora das opções rejeitada; painel com lista + Resumo (inscritos=2, arrecadação); cancelar
  remove da contagem; inscrição após o prazo bloqueada; evento só-membros exige login. Todos passaram.
  `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Fase 2 concluída.** A "página pública com pagamento simulado" (antiga Fase 3) ficou coberta por
  2.3 + 2.4. Próximos: **Lojinha** (produtos/variações/estoque + pedidos), **Financeiro/gráficos** e,
  depois, pagamentos reais (gateway) + mapa. Possíveis refinos: gating de “diretoria” por perfil real,
  editar inscrição, exportar lista, e-mail de confirmação.

---

## 2026-07-04 - Evento complexo — Fase 2.3: evento no menu de todos os perfis + página do evento

### Resumo
**Parte 2.3** da Fase 2: todo evento com inscrição **ainda não encerrado** (data futura/em andamento)
aparece numa seção **"Eventos ativos"** no menu lateral de **todos os perfis logados** (responsável,
diretor, tesoureiro, secretário, professor), com o **nome do evento** levando à **página do evento**.
Eventos passados somem do menu sozinhos. Criada a **página do evento** (`/eventos/<id>/pagina/`) —
página própria (sem a barra lateral interna) com nome, descrição, local, datas/horários, **status**
das inscrições (aberto/encerrado + prazo), **valores** (faixas etárias + diretoria) e um **preview
dos campos** do formulário. **Acesso**: evento **aberto ao público** → qualquer pessoa vê (sem login);
evento **só para membros** → exige login. O **botão "Inscrever-se"** aparece desabilitado com aviso de
que o envio virá na Fase 2.4.

### Arquivos criados/alterados
- `core/context_processors.py`: `perfis` passou a expor também `eventos_menu` (eventos com inscrição
  não encerrados) a todos os templates; helper `_eventos_menu` (filtra por data, só autenticados).
- `templates/core/_menu_eventos.html`: **novo** parcial com a seção "Eventos ativos" do menu.
- `templates/core/{inicio,usuarios,eventos,evento_form,evento_complexo_form,evento_painel}.html`:
  incluem o parcial no `<nav class="menu">` (fora do `is_diretor`, visível a todos).
- `templates/core/evento_pagina.html`: **nova** página do evento (pública/interna).
- `core/views.py`: nova `evento_pagina_view` (pública se `inscricao_aberta_publico`, senão login).
- `core/urls.py`: rota `evento_pagina` (`/eventos/<id>/pagina/`).
- `static/css/inicio.css`: estilos da seção "Eventos ativos" no menu (com truncagem do nome).
- `static/css/eventos.css`: estilos da página do evento + `.btn-acao:disabled`.

### Decisões tomadas
- Menu de eventos via **context processor** (aparece em todas as telas sem repetir lógica); inserido
  por **parcial** (`_menu_eventos.html`) para não reescrever a barra inteira em cada template.
- "Eventos ativos" = complexos com `data_fim` (ou `data`) **>= hoje** — filtro no nível de data
  (simples e suficiente); some sozinho quando o evento passa.
- **Página própria** (sem sidebar) para o evento, funcionando logada ou anônima; acesso público só
  quando `inscricao_aberta_publico=True` (senão, redireciona ao login com `?next=`).
- Botão "Inscrever-se" **desabilitado** nesta fase — o envio real (respostas + participantes) é a 2.4.

### Validação
- Teste ponta a ponta (test client): menu do **responsável** (não-diretor) mostra os eventos ativos e
  **oculta** o passado e os itens de diretor; página pública abre **sem login** (com dados, valores,
  campos e botão); evento só-membros **sem login redireciona** e **com login abre**; evento **simples**
  não tem página (404); **todas** as telas internas seguem renderizando com o menu. Todos passaram.
  `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Parte 2.4** — inscrição de fato: participantes por faixa/diretoria (cálculo do valor), respostas
  do formulário personalizado, pagamento **simulado**, código, **lista de inscritos** no painel e
  **contagem/arrecadação no dashboard**. Aí o botão "Inscrever-se" passa a funcionar.

---

## 2026-07-04 - Evento complexo — Fase 2.2: formulário de inscrição personalizável

### Resumo
**Parte 2.2** da Fase 2: o Diretor monta, por evento, os **campos personalizados** do formulário de
inscrição, na aba "Inscrições" do painel (subseção "Formulário de inscrição"). Cada campo tem
**pergunta/rótulo**, **tipo** (conjunto completo: texto curto, texto longo, número, escolha única,
escolha múltipla, sim/não, data), **opções** (só para escolha única/múltipla) e **obrigatório?**.
Os campos são adicionados por **modal**, podem ser **reordenados** (▲▼) e **removidos**. O
preenchimento/envio desse formulário (respostas) virá na Fase 2.4.

### Arquivos criados/alterados
- `core/models.py`: modelo `CampoInscricao` (evento, rótulo, tipo, opções, obrigatório, ordem) +
  `TIPO_CAMPO_INSCRICAO_CHOICES`; props `usa_opcoes` e `opcoes_lista`. Migration `0005_campoinscricao`.
- `core/forms.py`: `CampoInscricaoForm` (valida ≥2 opções para escolha; limpa `opcoes` nos demais tipos).
- `core/views.py`: painel passa `campos_inscricao` e `campo_form`; novas views `evento_campo_novo_view`,
  `evento_campo_excluir_view`, `evento_campo_mover_view` (reordenação robusta por renumeração).
  **Prefixos de formulário** (`faixa` e `campo`) para evitar colisão de IDs entre os modais.
- `core/urls.py`: rotas `evento_campo_novo`, `evento_campo_excluir`, `evento_campo_mover`.
- `core/admin.py`: registra `CampoInscricao`.
- `templates/core/evento_painel.html`: subseção "Formulário de inscrição" (lista com ▲▼ e remover) +
  modal "Adicionar campo".
- `static/js/evento_painel.js`: modal do campo + mostrar/ocultar "Opções" conforme o tipo escolhido.
- `static/css/eventos.css`: estilos da lista de campos, botões de ordenar e `.obrigatorio`.

### Decisões tomadas
- Um modelo por campo (`CampoInscricao`), opções como texto (uma por linha) → `opcoes_lista`.
- Formulários dos modais agora usam **prefixo** (`faixa-…`, `campo-…`) porque `faixa` e `campo`
  compartilham o nome de campo `rotulo` (evita `id` duplicado na mesma página).
- Reordenar por renumeração sequencial da `ordem` (robusto a valores repetidos).
- Erros do form voltam com mensagem (padrão dos demais modais do painel).

### Validação
- Teste ponta a ponta (test client, Diretor): painel renderiza a subseção e **não há colisão de IDs**
  (`id_faixa-rotulo` e `id_campo-rotulo` presentes, `id_rotulo` ausente); regressão da faixa com o novo
  prefixo; campo de texto; escolha única com 1 opção é rejeitada; escolha única válida normaliza as
  opções (`["P","M","G"]`); reordenar; excluir. Todos passaram. `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Parte 2.3** — evento no menu de todos os perfis + página do evento (descrição/local/prazo).
- Depois: 2.4 (inscrição de fato: participantes por faixa/diretoria, pagamento simulado, respostas
  do formulário, lista de inscritos + contagem/arrecadação no dashboard).

---

## 2026-07-04 - Evento complexo — Fase 2.1: fundação das inscrições (config + faixas)

### Resumo
Início da **Fase 2 (Inscrições)**, dividida em 4 partes (2.1 a 2.4). Esta é a **Parte 2.1 —
Fundação**: cada evento com inscrição passa a ter **configuração de inscrição** no painel (aba
"Inscrições"), com:
1. **Local** (obrigatório no evento com inscrição), **aberto ao público geral?** (sim = qualquer
   pessoa; não = só membros do clube) e **prazo limite de inscrição** (data/hora).
2. **Trava automática**: passado o prazo (ou, se vazio, o fim do evento), as inscrições ficam
   "encerradas" (badge verde "Abertas" / cinza "Encerradas" + data-limite exibida).
3. **Faixas etárias com valores** por evento (rótulo opcional + idade mín/máx + valor), adicionadas
   por modal e removíveis. Cada evento define as suas (variam de evento para evento).
4. **Valor da diretoria** (valor fixo que a diretoria paga, independe da idade; vazio = sem valor
   especial, 0 = grátis).
O formulário de inscrição personalizável (2.2), o evento no menu de todos os perfis + página do
evento (2.3) e a inscrição de fato com pagamento simulado + lista de inscritos (2.4) vêm nas
próximas partes.

### Arquivos criados/alterados
- `core/models.py`: `Evento` ganhou `inscricao_aberta_publico`, `inscricao_limite`,
  `valor_diretoria` + métodos `fim_datetime()`, `prazo_inscricao()`, `inscricoes_abertas()`.
  Novo modelo `FaixaEtariaPreco` (evento, rótulo, idade_min, idade_max, valor, ordem).
  Migration `0004_evento_inscricao_aberta_publico_and_more`.
- `core/forms.py`: `EventoInscricaoConfigForm` e `FaixaEtariaPrecoForm` (com validação idade_máx ≥
  idade_mín); `EventoComplexoForm` passou a exigir `local`.
- `core/views.py`: `evento_painel_view` monta config/faixas/status; novas views
  `evento_inscricao_config_view`, `evento_faixa_nova_view`, `evento_faixa_excluir_view` (POST).
- `core/urls.py`: rotas `evento_inscricao_config`, `evento_faixa_nova`, `evento_faixa_excluir`.
- `core/admin.py`: registra `FaixaEtariaPreco`.
- `templates/core/evento_painel.html`: aba "Inscrições" com status, form de configuração, lista de
  faixas e modal "Adicionar faixa".
- `static/js/evento_painel.js`: modais generalizados (helper `configurarModal`) para custo e faixa.
- `static/css/eventos.css`: estilos da config, faixas e `pill-cinza`.

### Decisões tomadas
- Faixas etárias como modelo próprio por evento (`FaixaEtariaPreco`); valor da diretoria no próprio
  `Evento` (independe da idade). Nada de faixas/valores fixos no sistema — cada evento define.
- Trava por comparação com `timezone.now()` (USE_TZ=True); prazo efetivo = `inscricao_limite` ou o
  fim do evento (`data_fim`/`data` + `horario_fim`/23:59), sempre aware.
- Erros dos forms de config/faixa voltam com mensagem (framework de messages), como já era nos custos.

### Validação
- Teste ponta a ponta (test client, logado como Diretor): GET do painel (200) com a config; salvar
  config (local/público/prazo/valor diretoria, com fuso correto SP→UTC); adicionar faixa válida;
  rejeitar faixa inválida (idade máx < mín); trava (evento passado = encerrado, futuro = aberto);
  excluir faixa. Todos passaram. `python manage.py check` sem problemas.

### Pendências / próximo passo
- **Parte 2.2** — formulário de inscrição personalizável por evento.
- Depois: 2.3 (evento no menu de todos os perfis + página do evento) e 2.4 (inscrição + pagamento
  simulado + lista de inscritos + contagem no dashboard).

---

## 2026-07-04 - Atualização geral da documentação (continuidade)

### Resumo
Revisão dos documentos para garantir continuidade em uma nova sessão. `README_PROJETO.md` atualizado
(perfis/permissões, Usuários restrita, módulo Eventos simples + complexo Fase 1, comandos
`configurar_perfis` e `importar_migracao`, novas rotas e models). `PLANEJAMENTO_EVENTO_COMPLEXO.md`
marca a **Fase 1 como concluída** e a **Fase 2 (Inscrições) como próximo passo** (seção "ONDE CONTINUAR").
`REGRAS_CODEX.md` passa a ter, na lista de regras obrigatórias, a **verificação obrigatória dos modais**
(só fechar no fundo se o mousedown E o click ocorreram no fundo — não fechar ao arrastar seleção).

### Arquivos alterados
- `docs/README_PROJETO.md`, `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`, `docs/REGRAS_CODEX.md`,
  `docs/HISTORICO_ALTERACOES.md`.

---

## 2026-07-04 - Ajustes na tela de Eventos (cards, moeda e modais)

### Resumo
Ajustes pedidos antes de seguir com o evento complexo:
1. **Card de evento com altura limitada**: título e descrição com no máximo 2 linhas (line-clamp) e
   cards da mesma linha com altura uniforme — não crescem mais com textos longos.
2. **Clicar no card** (fora dos botões) abre um **modal de visualização** com todos os dados do evento
   (só leitura). Os botões "Abrir painel"/"Duplicar" seguem seu comportamento normal.
3. **Moeda no padrão brasileiro** (`R$ 1.500,00`): novo filtro `moeda` usado no painel do evento.
4. **Modais não fecham ao arrastar seleção de texto** de dentro para fora (fecha só quando o mousedown
   e o clique ocorreram no fundo). Corrigido em todos os modais (Usuários, Eventos e Custos).

### Arquivos criados/alterados
- `core/templatetags/formato.py` (novo) + `__init__.py`: filtro `moeda`.
- `templates/core/evento_painel.html`: usa `{{ ...|moeda }}`.
- `templates/core/eventos.html`: card clicável, fonte oculta dos detalhes e modal de visualização.
- `static/css/eventos.css`: line-clamp do título/descrição, altura uniforme, card clicável, modal-desc.
- `static/js/eventos.js`: modal de visualização do evento (clona detalhe; ignora cliques em links/botões).
- `static/js/usuarios.js`, `static/js/eventos.js`, `static/js/evento_painel.js`: fechar modal só quando
  o mousedown começou no fundo (corrige o fechamento ao selecionar texto).
- `docs/REGRAS_CODEX.md`: nota do comportamento do modal + seção de formatação de moeda.

---

## 2026-07-04 - Evento complexo (com inscrição) — Fase 1: painel + custos

### Resumo
Início do "evento complexo" (mini-sistema por evento). **Fase 1**: criar o evento complexo
(`tipo=inscricao`, com data/hora de início e término) e seu **painel/dashboard** (`/eventos/<id>/`)
com abas (Resumo, Inscrições, Lojinha, Custos, Financeiro). Nesta fase funcionam **Resumo**
(indicadores: inscritos, arrecadação, vendas, receitas, custos e **resultado**) e **Custos**
(adicionar/remover custo com comprovante anexo; total reflete no resultado). Inscrições/Lojinha/
Financeiro ficam como "em breve". Pagamentos serão simulados nas próximas fases. Plano completo em
`docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`.

### Arquivos criados/alterados
- `core/models.py`: campo `Evento.data_fim` + modelo `CustoEvento` (migration `0003`).
- `core/forms.py`: `EventoComplexoForm` e `CustoEventoForm`.
- `core/views.py`: `evento_complexo_novo_view`, `evento_painel_view`, `evento_custo_novo_view`,
  `evento_custo_excluir_view`. `core/urls.py`: rotas correspondentes. `core/admin.py`: `CustoEvento`.
- `templates/core/evento_complexo_form.html` e `evento_painel.html`; `eventos.html` (habilita o card
  "Evento com inscrição" e mostra "Abrir painel" nos eventos complexos).
- `static/css/eventos.css` (painel: abas, KPIs, custos) e `static/js/evento_painel.js` (abas + modal).
- `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md` (novo) e demais docs atualizados.

### Decisões tomadas
- Reaproveita o modelo `Evento` (tipo `inscricao`) como base; `CustoEvento` relacionado por FK.
- Painel em página dedicada com abas (JS); demais módulos entram nas próximas fases.
- Resumo com indicadores (números); gráficos entram quando houver dados.

---

## 2026-07-03 - Corrige estilo do botão secundário nas telas internas

### Resumo
O botão "Cancelar" (e o "Duplicar") aparecia sem estilo porque `.btn-secundario` só existia em
`cadastro.css`, que não é carregado nas telas internas. Movido/adicionado o `.btn-secundario` para
`inicio.css` (carregado por todas as telas internas) e alinhados os botões do formulário de evento.

### Arquivos alterados
- `static/css/inicio.css`: adiciona o estilo do `.btn-secundario` (botão secundário das telas internas).
- `static/css/eventos.css`: alinha os botões do `.form-acoes` (zera o `margin-top` do `.btn-acao`).
- `docs/HISTORICO_ALTERACOES.md`: atualizado.

### Observação
- Isso também corrige o botão "Editar dados do aventureiro" em "Meus Dados", que usava a mesma classe.

---

## 2026-07-03 - Novo módulo "Eventos" (cadastro de evento simples)

### Resumo
Criado o módulo **Eventos** (restrito ao Diretor): tela `/eventos/` que lista os eventos do clube e
permite **criar evento**. O botão "Criar evento" abre um **modal** com a escolha do tipo — **Evento
simples** (implementado) e **Evento com inscrição** ("Em breve"). O cadastro simples (`/eventos/novo/`)
tem nome, local, descrição, data, horário de início e término. Cada evento tem **Duplicar**
(`?duplicar=<id>`), que abre o formulário pré-preenchido para recadastrar algo recorrente mudando só a
data. O componente de modal foi movido para `base.css` (reutilizável por Usuários e Eventos).

### Arquivos criados/alterados
- `core/models.py`: modelo `Evento` (+ migration `0002_evento`).
- `core/forms.py`: `EventoForm`. `core/views.py`: `eventos_view` e `evento_novo_view` (`@diretor_required`).
- `core/urls.py`: rotas `core:eventos` e `core:evento_novo`. `core/admin.py`: registra `Evento`.
- `templates/core/eventos.html` e `evento_form.html`: novas telas; item de menu "Eventos" (só diretor)
  adicionado também em `inicio.html` e `usuarios.html`.
- `static/css/eventos.css` e `static/js/eventos.js`: novos.
- `static/css/base.css`: passa a hospedar o **componente de modal** reutilizável.
- `static/css/usuarios.css`: removidos os estilos genéricos de modal (agora em `base.css`); mantidos os
  específicos (`.modal-pessoa*`, `.clicavel`).
- Documentação atualizada (`ESTADO_ATUAL`, `HISTORICO`, `REGRAS_CODEX`).

### Decisões tomadas
- Escolha do tipo via **um botão → modal com 2 cards** (a pedido do usuário). Pré-preenchimento apenas
  via **Duplicar** (sem auto-preencher do último). Evento "com inscrição" fica para depois.
- Modal como componente compartilhado em `base.css` (evita duplicação entre telas).

---

## 2026-07-03 - Tela "Usuários" restrita ao Diretor + modal com todos os dados

### Resumo
A tela "Usuários" passou a ser **restrita ao perfil Diretor** e, ao **clicar em qualquer card**
(responsável ou aventureiro), abre um **modal responsivo** (tela cheia no celular) com **todos os
dados** daquela pessoa. Isso inverte a regra anterior (que proibia dados sensíveis nessa tela): como
agora é restrita ao Diretor, exibir dados completos é permitido.

### Arquivos criados/alterados
- `core/permissoes.py`: novo (`eh_diretor` + decorator `diretor_required`).
- `core/context_processors.py`: novo (`is_diretor` em todos os templates).
- `config/settings.py`: registra o context processor `core.context_processors.perfis`.
- `core/views.py`: `usuarios_view` agora usa `@diretor_required`, guarda o contato dos responsáveis
  e passa os aventureiros completos (com idade/classes/foto/ficha preparadas).
- `templates/core/_aventureiro_detalhe.html`: novo parcial com o detalhe do aventureiro, reaproveitado
  em "Meus Dados" e no modal.
- `templates/core/inicio.html`: usa o parcial; item de menu "Usuários" só para o diretor (`is_diretor`).
- `templates/core/usuarios.html`: cards clicáveis, `#detalhesFonte` (fonte do modal) e o modal.
- `static/css/usuarios.css`: estilos do modal e dos cards clicáveis (responsivo, tela cheia no celular).
- `static/js/usuarios.js`: abre/fecha o modal (clona o detalhe, expande seções; fecha no X/fora/Esc).
- `docs/REGRAS_CODEX.md`: nova seção "Padrão de perfis e permissões" e atualização do "Padrão da tela
  Usuários"; `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md` atualizados.

### Decisões tomadas
- Perfis como grupos nativos do Django; gating por `@diretor_required` + `is_diretor` nos templates.
- Detalhes do modal renderizados no servidor (sem AJAX) num container fora de `.conteudo-interno`,
  para não afetar a pesquisa nem o accordion de `inicio.js`; o JS clona para o modal e expande as seções.

### Lições/armadilhas (documentadas em REGRAS_CODEX)
- `{# ... #}` é comentário de **uma linha**; para várias, usar `{% comment %}...{% endcomment %}`
  (um `{# #}` multi-linha fez o `{% include %}` de exemplo virar include real → recursão).
- Não escrever tags `{% ... %}` dentro de comentários HTML `<!-- -->` (o Django processa mesmo assim).

---

## 2026-07-03 - CSS global: interface sem cursor de texto fora de campos

### Resumo
Corrigido o "cursor de texto piscando" (caret) que aparecia ao clicar em textos que não são campos
digitáveis (títulos, rótulos, ícones, estado vazio, etc.). Criado `static/css/base.css` com
`user-select: none` no corpo e reativação da seleção apenas em campos de formulário e valores de
dados (`.dado-valor` / `.selecionavel`), para ainda permitir copiar CPF/telefone/e-mail. O `base.css`
passa a ser linkado em todas as telas, antes do CSS específico de cada página.

### Arquivos criados/alterados
- `static/css/base.css`: novo (regras globais de interface).
- `templates/core/{login,inicio,cadastro,cadastro_sucesso,editar_responsavel,usuarios}.html`:
  passam a linkar o `base.css` antes do CSS da página.
- `docs/REGRAS_CODEX.md`: nova seção "Padrão global de interface (base.css)".
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Comportamento de app: texto de interface não é selecionável (some o caret e o cursor I-beam);
  apenas campos e valores de dados permanecem selecionáveis/copiáveis.
- Regra documentada para valer em telas futuras (sempre linkar `base.css`; nunca usar
  `contenteditable`/`tabindex` em elementos que não são campos).

### Observação
- Se o caret ainda aparecer em qualquer texto mesmo com isso, pode ser o modo "navegação por cursor"
  (caret browsing) do navegador — geralmente ligado/desligado com a tecla F7.

---

## 2026-07-03 - Login sem diferenciar maiúsculas/minúsculas no usuário

### Resumo
Corrigido o login: o usuário agora é resolvido de forma case-insensitive (ex.: `fabiano`, `Fabiano`
e `FABIANO` autenticam o mesmo usuário). Antes, o Django exigia o username exato (`Fabiano`), o que
impedia o login de quem digitava em minúsculas. A senha continua sendo validada normalmente.

### Arquivos criados/alterados
- `core/views.py` (`login_view`): resolve o username real por `iexact` antes de `authenticate`.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Consistente com o cadastro (`ContaForm.clean_username`), que já impede usernames duplicados por
  `iexact`. Verificado que não há usernames que colidam só por caixa (seguro).

---

## 2026-07-03 - Planejamento do cadastro de diretoria (documentado, não implementado)

### Resumo
Gravado o planejamento do **cadastro de diretoria**, do **cadastro de diretoria + aventureiro**
(mesclagem) e da tela "Cadastre-se" com 3 tipos, em `docs/PLANEJAMENTO_CADASTRO_DIRETORIA.md`, para
não perder o que foi alinhado. **Nada implementado ainda** — aguarda a documentação oficial dos campos
e os textos dos termos (compromisso de voluntariado e autorização de imagem).

### Arquivos criados/alterados
- `docs/PLANEJAMENTO_CADASTRO_DIRETORIA.md`: novo (especificação/planejamento).
- `docs/HISTORICO_ALTERACOES.md`: atualizado.

### Pendências
- Ver a lista "Pontos em aberto" dentro do próprio arquivo de planejamento.

---

## 2026-07-03 - Perfis de acesso + usuário diretor inicial

### Resumo
Criado o comando `configurar_perfis`, que cria os 5 perfis de acesso (grupos nativos do Django) e o
usuário diretor inicial. Primeira execução: 5 grupos criados e usuário `Fabiano` (diretor) vinculado
ao perfil Diretor; login `Fabiano`/`1234` autentica.

### Perfis de acesso
- **Diretor, Responsável, Professor, Tesoureiro, Secretário.**
- Conceito: "Diretoria" é o grupo de integrantes do clube (diretor, secretário, tesoureiro, professor);
  "Responsável" é o lado dos pais. Uma pessoa pode ser das duas partes e alternar o perfil ao logar
  (lógica de alternância ainda a implementar). Por ora, só o Diretor receberá permissões nas telas.

### Arquivos criados/alterados
- `core/management/commands/configurar_perfis.py`: novo comando (idempotente).
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Usar **grupos nativos do Django** para os perfis (integram com o sistema de permissões; sem
  migration). Um modelo próprio de perfil/alternância poderá ser criado depois, se necessário.
- Usuário diretor inicial `Fabiano` com senha de desenvolvimento `1234` (trocar em produção),
  seguindo o mesmo padrão do `criar_dados_teste`. `is_staff`/`is_superuser` = False (é diretor no
  app, não admin do Django).

### Pendências / próximos passos (a validar antes de implementar)
- Cadastro de diretoria (inscrição) e a "mesclagem" diretoria + aventureiro.
- Tela "Cadastre-se" com escolha entre 3 tipos (aventureiro / diretoria / diretoria + aventureiro).
- Alternância de perfil (responsável ↔ diretoria) ao logar.
- Restringir o menu/tela "Usuários" ao perfil Diretor.
- Excluir a conta de teste `teste_responsavel` (2 aventureiros de teste).

---

## 2026-07-03 - Importação/migração dos cadastros do sistema antigo

### Resumo
Criado o comando de gerenciamento `importar_migracao`, que migra para o sistema novo **apenas os dados
de cadastro** ("cadastre-se") do sistema antigo, a partir do pacote exportado (pasta com `dados_json/`
e `arquivos/`). Importa: a conta de acesso (login com **hash de senha preservado**, então o responsável
continua logando com a mesma senha), dados de **pai, mãe e responsável legal**, **endereço**, dados de
cada **aventureiro**, **ficha médica**, **termo de autorização de imagem** e a **foto** de cada
aventureiro. Primeira execução real: **35 logins + 37 aventureiros** (todos com ficha médica, termo e
foto), com as telas "Meus Dados" e "Usuários" renderizando os dados corretamente.

### Arquivos criados/alterados
- `core/management/commands/importar_migracao.py`: novo comando (leitura dos JSON, mapeamento
  campo a campo, cópia de fotos para `media/`, idempotente, com `--dry-run`).
- `.gitignore`: passa a ignorar o pacote de exportação (`exportacao_migracao_*.zip`) e a pasta
  `migracao/` (dados de migração), para não versionar dados pessoais de menores.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- **Escopo**: só os cadastros com aventureiro. Dos 106 registros de responsável do sistema antigo, 71
  não tinham nenhum aventureiro e ficaram de fora; entram apenas os 35 com aventureiro. Um registro-lixo
  de teste (nome "teste", CPF inválido) foi pulado.
- **Diretoria não é importada.** A única pessoa que era diretoria e também responsável de aventureiro
  entra apenas como mãe/responsável do aventureiro; nenhum dado de diretoria é trazido.
- **Responsáveis no plural**: pai, mãe e responsável legal de cada aventureiro são preservados; a tela
  "Usuários" agrupa por CPF e junta os papéis (ex.: quem é pai e também responsável legal aparece uma
  vez com os dois papéis).
- **Modelo novo**: não existe model `Responsavel` separado — os dados de pai/mãe/responsável ficam em
  cada `Aventureiro`, e o "responsável" do sistema é o usuário Django (login).
- **Datas originais** de criação/inscrição preservadas (contornando `auto_now_add`).
- **Campos inexistentes no export** (ex.: nacionalidade/estado civil/RG do responsável no termo) ficam
  em branco; `tamanho_camiseta` (texto livre no sistema antigo) é gravado como está.

### Segurança de menores
- As **fotos** importadas são dados **reais** dos membros do clube (com termo de imagem) e ficam
  **apenas** em `media/` (git-ignored) — **nunca** versionadas.
- O pacote de exportação e os JSON/CSV com CPFs/nomes/dados de saúde de menores **não** vão ao Git.

### Pendências
- (Opcional) Importar também os logins de responsáveis sem aventureiro, caso desejado no futuro.
- Fotos e assinaturas em imagem além da foto 3x4 (ex.: assinaturas do termo) não foram importadas.

---

## 2026-07-02 - Arquivo de contexto CLAUDE.md

### Resumo
Criado `CLAUDE.md` na raiz: um guia rápido de contexto (o que é o projeto, stack, como rodar/testar,
estrutura, rotas, models, regras inegociáveis e convenções) que aponta para os docs oficiais como
fonte da verdade. Não altera código nem comportamento — só documentação. Sem migrations.

### Arquivos criados/alterados
- `CLAUDE.md`: novo (arquivo de contexto).
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Observação
As imagens soltas na raiz (foto de crianças e outra) continuam **fora do versionamento**
propositalmente (não versionar fotos reais de crianças).

---

## 2026-07-02 - Tela "Usuários" com vínculos familiares e pesquisa

### Resumo
Novo item de menu **Usuários** e nova tela `/usuarios/` (protegida por login) que mostra, de forma
resumida e visual, os responsáveis (pai, mãe e responsável legal de todos os aventureiros), os
aventureiros e o vínculo entre eles, com pesquisa inteligente em tempo real. Só dados resumidos —
nenhum dado sensível. Nenhum model foi alterado — sem migrations.

### Menu e rota
- Item **Usuários** adicionado abaixo de **Meus Dados** no menu lateral (mesmo visual; ativo em
  `/usuarios/`; funciona no desktop e no mobile). Adicionado nas duas telas (`inicio.html` e
  `usuarios.html`).
- Rota criada: `/usuarios/` (`core:usuarios`), com `@login_required`.

### Como os responsáveis são agrupados
- Para cada aventureiro consideram-se pai, mãe e responsável legal.
- Deduplicação por chave: **CPF**; se não houver, **nome + WhatsApp**; se não houver, **nome
  normalizado** (sem acentos/caixa). Responsáveis sem nome são ignorados.
- A mesma pessoa que aparece em mais de um papel (ex.: mãe e responsável legal) é mostrada **uma
  única vez**, com os papéis juntos; e lista todos os aventureiros a que está vinculada.

### Vínculos e resumo
- Card por responsável: nome, pílulas de papéis e "Aventureiros vinculados" (nome, idade e papel do
  vínculo, ex.: "Mãe / Responsável legal").
- Seção "Resumo por aventureiro": nome, idade e pai/mãe/responsável legal.
- Contadores no topo: Responsáveis (pessoas únicas), Aventureiros (total) e Vínculos (relações
  papel×aventureiro).

### Pesquisa inteligente
- `static/js/usuarios.js`: filtra os cards ao digitar (nome do responsável, papel, nome/idade do
  aventureiro e vínculos), ignorando maiúsculas/minúsculas e acentos; exibe "Nenhum vínculo
  encontrado para essa pesquisa." por seção quando não há resultado. Sem AJAX/bibliotecas.

### Dados sensíveis ocultos
- Não exibe CPF, RG, certidão, endereço, e-mail, telefone/WhatsApp, ficha médica, autorização de
  imagem nem foto (validado por teste automatizado).

### Arquivos criados/alterados
- `core/views.py`: helpers `_normaliza`, `_ordena_papeis`, `_chave_responsavel` e nova
  `usuarios_view`; import de `Aventureiro` e `unicodedata`.
- `core/urls.py`: rota `/usuarios/`.
- `templates/core/usuarios.html`: novo template.
- `templates/core/inicio.html`: item "Usuários" no menu.
- `static/css/usuarios.css`: novo (pesquisa, contadores, cards de responsável/aventureiro, vínculos).
- `static/js/usuarios.js`: novo (pesquisa em tempo real).
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- Visão geral do sistema (todos os aventureiros), pois é uma consulta de vínculos; acesso liberado
  a qualquer autenticado por ora (restrição por perfil fica para o futuro, documentado).
- Reuso do layout/menu de `inicio.css`; estilos próprios em `usuarios.css`. Pesquisa 100% no
  front-end (sem AJAX), conforme pedido.
- Sem alterar models nem `Meus Dados`; sem migrations.

### Validação
- Test client: proteção de login; menu "Usuários" ativo; agrupamento (Mariana aparece 1× como
  Mãe + Responsável legal, vinculada a Ana e Lucas; Roberto como Pai); contadores 2/2/6; resumo por
  aventureiro; e **nenhum dado sensível** vazado (CPF, e-mail, WhatsApp, endereço, RG, plano, foto).
- Visual (Chrome headless): desktop e mobile — layout bonito, responsivo e sem overflow.

### Pendências
- Restrição de acesso por perfil à tela "Usuários"; edição completa do aventureiro; "Esqueci minha
  senha"; validação avançada de CPF; envio de e-mail.

---

## 2026-07-02 - Avatar fictício nas fotos de teste e moldura redonda em "Meus Dados"

### Resumo
Ajustes visuais nas fotos: o comando de teste passou a gerar um **avatar de desenho fictício**
(silhueta com rosto sorridente + "Foto teste"), no lugar do quadrado com iniciais, e a moldura
da foto em "Meus Dados" ficou **redonda** (foto de perfil). Nenhuma foto real de pessoa/criança
é usada — apenas formas desenhadas com Pillow. Nenhum model alterado — sem migrations.

### Contexto
Foi solicitado usar fotos reais de crianças; isso foi **recusado** por segurança/privacidade de
menores e pela regra do projeto (não usar fotos reais de crianças). A alternativa segura adotada
foi desenhar um avatar fictício.

### Arquivos alterados
- `core/management/commands/criar_dados_teste.py`: `_gerar_foto_ficticia` agora desenha um avatar
  (cabeça, ombros, olhos e sorriso) sobre fundo colorido, com "Foto teste".
- `static/css/inicio.css`: moldura da foto do aventureiro agora circular (`border-radius: 50%`,
  100x100, `object-position: center 28%` para enquadrar o rosto).
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Como regenerar
```
python manage.py criar_dados_teste
```
(As fotos são regeradas quando ausentes; para forçar o novo avatar em fotos antigas, apague os
arquivos em `media/aventureiros/fotos_teste/` antes de rodar.)

### Validação
- Fotos regeradas e exibidas em cards com moldura redonda (validado por captura em Chrome headless).

---

## 2026-07-02 - Correção de fotos, dados completos e fechar painéis ao clicar fora em "Meus Dados"

### Resumo
Revisão da tela `/inicio/` ("Meus Dados") para: (1) exibir a foto do aventureiro de forma robusta,
com placeholder quando o arquivo não existe; (2) mostrar TODOS os dados do cadastro, organizados
por seção; e (3) fechar os painéis expansíveis ao clicar fora, abrir um recolhendo os outros, com
`Esc`. Nenhum model foi alterado — sem migrations.

### Fotos
- Investigação: o serving de mídia em DEBUG e a URL estão corretos (verificado: `GET /media/...`
  responde HTTP 200 e o `<img>` renderiza `src="/media/aventureiros/fotos_teste/..."`). A falha
  real acontecia quando o banco referenciava uma foto cujo **arquivo não existe fisicamente**
  (situação comum, pois `media/` é gitignored): `{% if av.foto %}` era verdadeiro e gerava um
  `<img>` quebrado.
- Correção: a view marca `av.foto_ok` usando `foto.storage.exists(...)`; o template só mostra a
  imagem quando o arquivo existe. Caso contrário (ou se a imagem falhar ao carregar, via `onerror`),
  exibe um **placeholder com as iniciais** do nome (`av.iniciais`). A página nunca quebra.
- As fotos dos aventureiros de teste continuam em `media/aventureiros/fotos_teste/`
  (`lucas_teste.png` / `ana_teste.png`), geradas/mantidas pelo comando `criar_dados_teste`.

### Dados completos (auditoria cadastro × Meus Dados)
- Seções reorganizadas: **Dados pessoais**, **Documentos e informações pessoais** (nova, separada),
  **Endereço**, **Pai**, **Mãe**, **Responsável legal**, **Ficha médica**, **Declaração médica**
  (nova, separada) e **Autorização de imagem**.
- Campos adicionados que faltavam:
  - Ficha médica: medicamentos por condição (cardíaco/diabetes/renais/psicológicos), exibidos como
    "Sim (medicamentos: …)"/"Não"; listas de doenças, alergias (com "qual") e histórico recente.
  - Declaração médica: status do aceite + resumo do termo + data.
  - Autorização de imagem: nacionalidade do menor, nacionalidade do responsável, estado civil,
    endereço, número e bairro (além dos que já apareciam).

### Fechar ao clicar fora
- `static/js/inicio.js`: um listener de clique fecha todo `<details>` aberto que não contém o
  elemento clicado (fecha ao clicar fora e recolhe os demais ao abrir um — accordion); `Esc` fecha
  tudo; clique dentro não fecha. Funciona no celular. As seções continuam sendo `<details>` nativos.

### Arquivos criados/alterados
- `core/views.py`: helpers `_iniciais` e `_foto_valida`; `inicio_view` marca `foto_ok`/`iniciais`;
  `_preparar_ficha` passou a montar os textos das condições com medicamentos.
- `templates/core/inicio.html`: foto com `foto_ok` + placeholder de iniciais + `onerror`; seções
  Documentos e Declaração médica separadas; Ficha médica com medicamentos; Autorização de imagem
  completa.
- `static/js/inicio.js`: fechamento dos painéis ao clicar fora / `Esc` / accordion.
- `static/css/inicio.css`: placeholder de foto (iniciais) mais bonito.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Validação
- Servidor real: `GET /media/aventureiros/fotos_teste/ana_teste.png` → HTTP 200 (image/png);
  `/inicio/` (logado) renderiza `<img src="/media/...">` para os dois aventureiros.
- Test client: auditoria confirma todas as seções/campos (Documentos, Declaração médica,
  medicamentos por condição, nacionalidades, estado civil, endereço/número/bairro, etc.);
  placeholder de iniciais quando o arquivo não existe ("FQ") e quando não há foto ("SS"), sem
  quebrar a página (200).
- Visual (Chrome headless): card totalmente expandido com todas as seções, responsivo e sem
  overflow horizontal.

### Pendências
- Edição completa dos dados do aventureiro; "Esqueci minha senha"; permissões/perfis; validação
  avançada de CPF; envio de e-mail.

---

## 2026-07-02 - "Meus Dados" reorganizado: responsável (com edição) + aventureiros clicáveis

### Resumo
Reorganização da tela `/inicio/` ("Meus Dados") para um fluxo mais claro: um card do
**Responsável** no topo (expansível, com edição) e a seção **Aventureiros cadastrados**
com cards clicáveis que abrem todos os dados do aventureiro em seções recolhíveis. Criada
a edição dos dados do responsável, que propaga a alteração aos aventureiros do usuário que
compartilham o mesmo responsável. Nenhum model foi alterado — sem migrations.

### Como ficou a tela
- **Card Responsável**: dados do responsável legal do aventureiro mais recente (nome, parentesco,
  e-mail, WhatsApp, total de aventureiros). Expande mostrando também CPF e cidade/estado (do termo
  de imagem), a meta da conta e o botão **Editar**. Sem aventureiros, mostra os dados da conta.
- **Aventureiros cadastrados**: card por aventureiro com foto 3x4 destacada, nome, pílulas
  (idade, camiseta, classes) e status (✓ ficha médica / ✓ autorização). Ao clicar, abre as seções:
  Dados pessoais, Endereço, Pai, Mãe, Responsável legal, Ficha médica e Autorização de imagem.
  Botão "Editar dados do aventureiro" desabilitado (com aviso de que a edição virá depois).
- Botão "Cadastrar outro aventureiro" (→ `/cadastro/novo-aventureiro/`) e estado vazio amigável.
- Mensagens de sucesso/erro via framework de `messages`.

### Edição do responsável
- Rota `/meus-dados/responsavel/editar/` (`core:editar_responsavel`), protegida por login.
- Form `ResponsavelLegalForm` (nome, parentesco, CPF, e-mail, WhatsApp), pré-preenchido com o
  responsável do aventureiro mais recente.
- Ao salvar, aplica os dados a todos os aventureiros do usuário logado com o **mesmo CPF de
  responsável** (base: o mais recente); se nenhum coincidir, altera só o mais recente. Nunca
  altera dados de outro usuário. Redireciona a `/inicio/` com mensagem de sucesso.

### Rotas criadas/alteradas
- Criada: `/meus-dados/responsavel/editar/` (`core:editar_responsavel`).
- `inicio_view`: passou a montar o contexto do responsável (além dos aventureiros).

### Arquivos criados/alterados
- `core/forms.py`: novo `ResponsavelLegalForm`.
- `core/views.py`: contexto do responsável em `inicio_view`; nova `editar_responsavel_view`;
  import de `messages`.
- `core/urls.py`: rota de edição do responsável.
- `templates/core/inicio.html`: reescrita (card do responsável + cards clicáveis + mensagens).
- `templates/core/editar_responsavel.html`: novo (form de edição, reutiliza `cadastro.css` e `_campo.html`).
- `static/css/inicio.css`: estilos de mensagens, painel do responsável, cards de aventureiro
  (foto destacada, status, accordion), botões e responsividade; `overflow-x: hidden` de guarda.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- Reaproveitar `<details>/<summary>` nativos (sem JS) para painel do responsável e cards dos
  aventureiros; reutilizar a parcial `_dado.html` e cálculos na view (idade, listas).
- Edição do responsável de forma segura: propaga por CPF do responsável, materializando os alvos
  antes de alterar o CPF; sempre restrita a `request.user`.
- Não alterar models (os dados do responsável já vivem em `Aventureiro`); sem migrations.
- Edição completa do aventureiro deixada para depois (botão apenas visual/desabilitado), para não
  introduzir edição incompleta que pudesse quebrar o cadastro.

### Validação
- Test client: `/inicio/` mostra card do responsável (Mariana), os 2 aventureiros com foto,
  status e seções (Pai/Mãe separados); edição do responsável atualiza os **dois** aventureiros
  (mesmo CPF), com mensagem de sucesso; segurança (outro usuário não vê nem edita dados alheios);
  proteção de login na rota de edição.
- Visual (Chrome headless): desktop colapsado e expandido e mobile — layout bonito, responsivo e
  **sem overflow horizontal** (confirmado por diagnóstico de largura).

### Pendências
- Edição completa dos dados do aventureiro; "Esqueci minha senha"; permissões/perfis; validação
  avançada de CPF; envio de e-mail.

---

## 2026-07-02 - Fotos fictícias dos aventureiros de teste (com verificação de existência)

### Resumo
Ajuste no comando `criar_dados_teste` para garantir que cada aventureiro de teste tenha
uma foto 3x4 fictícia associada e válida. Antes, a foto era regerada a cada execução;
agora o comando **verifica se a foto está correta** (campo preenchido, apontando para o
caminho esperado e com o arquivo existindo em `media/`) e só (re)gera quando está faltando
ou quebrada — caso contrário, mantém. Nenhum model foi alterado — sem migrations.

### O que muda
- `Lucas Henrique Oliveira Santos` → `media/aventureiros/fotos_teste/lucas_teste.png` (iniciais "LH").
- `Ana Clara Oliveira Santos` → `media/aventureiros/fotos_teste/ana_teste.png` (iniciais "AC").
- O comando informa, por aventureiro, "foto mantida" ou "foto gerada".

### Arquivos criados/alterados
- `core/management/commands/criar_dados_teste.py`: bloco da foto agora verifica a existência
  física do arquivo e a correspondência do caminho antes de decidir manter ou regerar; a
  saída passou a informar o status da foto de cada aventureiro.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Como recriar os dados de teste
```
python manage.py criar_dados_teste
```

### Validação
- Rodado com as fotos já corretas → "foto mantida" para os dois.
- Apagado o arquivo do Lucas e rodado de novo → "foto gerada" só para o Lucas, "foto mantida"
  para a Ana; ambos os arquivos existem no disco e os campos `foto` apontam para eles.
- A tela "Meus Dados" exibe as fotos dos dois aventureiros (validado no passo anterior).

### Pendências
- Sem novas pendências (mantêm-se as anteriores: "Esqueci minha senha", edição pela área logada,
  permissões/perfis, validação avançada de CPF, envio de e-mail).

---

## 2026-07-02 - Autenticação real e tela "Meus Dados" funcional

### Resumo
Implementação da autenticação real do Django (login, logout e proteção de rota) e
transformação da tela `/inicio/` em uma área funcional "Meus Dados", que exibe os dados
da conta e os aventureiros do usuário logado (com foto, ficha médica e autorização de
imagem em seções recolhíveis). O cadastro inicial passou a autenticar o usuário
automaticamente. Nenhum model foi alterado — sem migrations.

### Login real
- `login_view` autentica com `authenticate` + `login` (campos `usuario`/`senha`). Em erro,
  exibe "Usuário ou senha inválidos.". Sucesso vai para `/inicio/` (ou `next`, se seguro).
  Removido o script inline que apenas navegava. Mantidos os links "Cadastre-se" e "Esqueci
  minha senha" (este último ainda sem função).

### Rotas protegidas / criadas
- `/inicio/` agora usa `@login_required` (sem login, redireciona para `/?next=/inicio/`).
- Criada `/sair/` (`core:sair`), logout via POST (`@require_POST`), redireciona para o login.

### Área "Meus Dados"
- Card "Dados da Conta": usuário, e-mail, data de criação e total de aventureiros.
- Um card por aventureiro: foto 3x4, pílulas de resumo (sexo, idade, cidade/UF, camiseta) e
  seções recolhíveis (`<details>`): Dados pessoais, Endereço, Responsáveis, Ficha médica e
  Autorização de imagem. Idade e listas (classes, doenças, alergias, condições, histórico)
  são calculadas na view. Estado vazio amigável quando não há aventureiros.
- Menu lateral com nome do usuário e botão "Sair" (acessível também no mobile).
- Botão "Cadastrar outro aventureiro" leva a `/cadastro/novo-aventureiro/`.

### Cadastro ajustado para autenticação real
- Após criar o `User`, o cadastro faz `login(...)` automático (backend `ModelBackend`) e mantém
  a sessão como retaguarda. A tela de sucesso e o botão "Ir para a tela inicial" abrem `/inicio/`
  já logado.
- `cadastro_novo_aventureiro_view` prioriza `request.user`; sem usuário (nem sessão), vai ao login.

### Arquivos criados/alterados
- `config/settings.py`: `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`.
- `core/views.py`: login/logout reais, `@login_required` em `inicio_view`, contexto de "Meus Dados"
  (helpers `_idade`, `_classes_investidas`, `_preparar_ficha`), login automático no cadastro e uso
  de `request.user` no fluxo de novo aventureiro.
- `core/urls.py`: rota `/sair/`.
- `templates/core/login.html`: formulário de login real + aviso de erro; sem JS de navegação falsa.
- `templates/core/inicio.html`: reescrita como "Meus Dados" (conta + cards dos aventureiros + Sair);
  usa `static/js/inicio.js`.
- `templates/core/_dado.html`: nova parcial rótulo+valor.
- `static/js/inicio.js`: novo (menu recolhível do mobile; detalhes via `<details>` nativo).
- `static/css/login.css`: estilo `.aviso-login`.
- `static/css/inicio.css`: estilos de "Meus Dados" (conta, cards de aventureiro, pílulas, accordion,
  botões de ação e Sair, estado vazio) e responsividade.
- `core/admin.py`: `list_display`/`search_fields` de Aventureiro com responsável legal e `criado_em`.
- `docs/README_PROJETO.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`,
  `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- Reaproveitar a autenticação padrão do Django (sem libs). Login/logout com as rotas e settings
  padrão; logout via POST + CSRF (não link GET), por segurança.
- Seções recolhíveis com `<details>/<summary>` nativos (acessível e sem JS extra).
- Cálculos de exibição na view (idade, listas) e parcial `_dado.html` para reduzir repetição.
- Sem alterar models: a relação existente já bastava; sem migrations.
- `.gitignore` inalterado: `media/` e `db.sqlite3` seguem fora do Git.

### Validação (test client, ponta a ponta)
- `/inicio/` sem login → redireciona para `/?next=/inicio/`.
- Login errado → mensagem de erro; login `teste_responsavel`/`123456` → `/inicio/`.
- "Meus Dados" mostra conta, os 2 aventureiros de teste, fotos, ficha médica (doenças/alergias),
  autorização de imagem e os aceites.
- Logout → volta ao login; depois `/inicio/` volta a exigir login.
- Cadastro inicial autentica automaticamente (sessão com `_auth_user_id`); novo aventureiro na
  conta logada aparece em "Meus Dados".

### Pendências
- "Esqueci minha senha", edição dos dados pela área logada, permissões/perfis, validação avançada
  de CPF e envio de e-mail: futuros.

---

## 2026-07-02 - Comando de gerenciamento para gerar dados de teste

### Resumo
Criação do management command `criar_dados_teste`, que popula o banco local com uma
conta de teste (`teste_responsavel`, senha `123456`) e 2 aventureiros fictícios completos
(ficha de inscrição, ficha médica, autorização de imagem e fotos fictícias geradas com
Pillow). O comando é idempotente: pode ser rodado várias vezes sem duplicar dados e sem
tocar em dados de outros usuários. Nenhum model foi alterado — sem migrations.

### Como rodar
```
python manage.py criar_dados_teste
```
- Conta: usuário `teste_responsavel`, senha `123456`, e-mail `teste.responsavel@example.com`.
- Aventureiros: "Lucas Henrique Oliveira Santos" e "Ana Clara Oliveira Santos" (mesma família,
  mesmos responsáveis; a mãe é a responsável legal).
- Fotos fictícias salvas em `media/aventureiros/fotos_teste/lucas_teste.png` e `ana_teste.png`.

### Arquivos criados/alterados
- `core/management/__init__.py`: novo (pacote de comandos).
- `core/management/commands/__init__.py`: novo.
- `core/management/commands/criar_dados_teste.py`: novo — o comando em si (dados fictícios,
  geração das fotos com Pillow e mensagens de saída).
- `docs/README_PROJETO.md`: seção "Popular o banco com dados de teste".
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Idempotência: `get_or_create` no `User` (reutiliza se existir) e `update_or_create` para
  Aventureiro (chaveado por `usuario` + `cpf`), FichaMedica e AutorizacaoImagem (por aventureiro).
  A senha é sempre redefinida para `123456` para garantir o acesso de teste.
- Fotos geradas localmente com Pillow (fundo colorido + iniciais + "Foto teste", proporção 3x4),
  sem imagens externas nem fotos reais. O campo `foto` aponta para o arquivo em
  `media/aventureiros/fotos_teste/` (caminho de teste solicitado, distinto do `upload_to` padrão).
- Carregamento de fonte robusto (tenta Arial/DejaVu e a fonte que acompanha o Pillow; cai na
  fonte padrão se nenhuma existir), para as iniciais aparecerem grandes.
- Não foram alterados models, admin nem o fluxo de cadastro do usuário final.
- `media/` e `db.sqlite3` continuam fora do Git (`.gitignore`); os dados/fotos de teste são
  recriados pelo comando quando necessário.

### Validação
- Comando executado duas vezes: 1ª "criados com sucesso", 2ª "já existiam e foram atualizados",
  sem duplicar (segue 1 usuário, 2 aventureiros, 2 fichas médicas, 2 autorizações).
- Conferido: `check_password("123456")` verdadeiro, fotos existentes em disco, aceites (declaração
  médica e imagem) verdadeiros, e os três models visíveis no admin (já registrados).

### Pendências
- Sem novas pendências específicas. Mantêm-se as anteriores (autenticação real, "Meus Dados",
  permissões, validação avançada de CPF, "Esqueci minha senha", envio de e-mail).

---

## 2026-07-02 - Fluxo para cadastrar múltiplos aventureiros na mesma conta

### Resumo
Implementação do fluxo que permite ao mesmo usuário/responsável cadastrar mais de um
aventureiro sem criar uma nova conta. A tela de sucesso passou a oferecer "Cadastrar
outro aventureiro" e "Ir para a tela inicial". Foi criada a rota
`/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso"), que vincula
o novo aventureiro ao mesmo usuário e permite reaproveitar os dados dos responsáveis do
último cadastro. NÃO foi implementado login real nem permissões: o usuário atual é
mantido temporariamente na sessão.

### Problema encontrado
Apesar de o model já permitir `um usuário → vários aventureiros`, não havia caminho de
UI para isso: `/cadastro/` sempre exigia criar uma conta nova; após o cadastro o usuário
não era identificado (sem sessão/login); e a tela de sucesso só oferecia "Ir para a tela
inicial". Na prática, cada aventureiro exigiria um novo usuário.

### Solução implementada
- Após o cadastro inicial, o id do usuário é guardado na sessão (`cadastro_usuario_id`)
  junto com o nome do último aventureiro (`cadastro_ultimo_nome`) — solução **temporária**
  até a autenticação real (basta trocar por `request.user` no futuro).
- Nova rota `/cadastro/novo-aventureiro/` (nome `core:cadastro_novo_aventureiro`) que exige
  esse usuário na sessão, não cria novo `User` e salva o aventureiro na mesma conta.
- O mesmo template `cadastro.html` serve os dois fluxos (parametrizado por `modo_novo` e
  `conta_form`), evitando duplicar o wizard. A numeração das etapas e os índices usados pelo
  JS são calculados dinamicamente.
- Reaproveitamento dos dados de pai/mãe/responsável legal do último aventureiro, enviados
  pelo backend via `json_script` e preenchidos pelo JS quando o usuário marca a opção
  (ainda editáveis).

### Rotas criadas/alteradas
- Criada: `/cadastro/novo-aventureiro/` (`core:cadastro_novo_aventureiro`).
- Alteradas (comportamento): `/cadastro/` (grava usuário na sessão) e `/cadastro/sucesso/`
  (mostra nome e as duas opções).

### Arquivos criados/alterados
- `core/urls.py`: nova rota `cadastro/novo-aventureiro/`.
- `core/views.py`: refatorado — helpers `_instanciar_forms_aventureiro`, `_validar_aceites`,
  `_salvar_aventureiro` e `_dados_responsaveis_anteriores`; `cadastro_view` grava usuário na
  sessão; nova `cadastro_novo_aventureiro_view`; `cadastro_sucesso_view` passa nome e opções.
  Constantes `SESSAO_USUARIO_ID` / `SESSAO_ULTIMO_NOME`.
- `templates/core/cadastro.html`: cabeçalho/banner condicional (`modo_novo`), etapa "Conta"
  condicional (`conta_form`), bloco de reuso dos responsáveis + `json_script`, link de rodapé
  condicional.
- `templates/core/cadastro_sucesso.html`: nome do aventureiro e botões "Cadastrar outro
  aventureiro" / "Ir para a tela inicial".
- `static/js/cadastro.js`: numeração das etapas e índices de validação dinâmicos; usuário
  condicional na revisão; reaproveitamento dos dados dos responsáveis.
- `static/css/cadastro.css`: estilos `.aviso-info`, `.reuso-responsaveis`, `.sucesso-acoes`,
  `.sucesso-pergunta`.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`, `docs/REGRAS_CODEX.md`,
  `docs/README_PROJETO.md`: documentação atualizada.

### Decisões tomadas
- Reaproveitar um único template/JS/CSS em vez de duplicar o wizard, controlando as diferenças
  por contexto (`modo_novo`, `conta_form`) e cálculo dinâmico das etapas no JS.
- Manter a identificação do usuário por sessão como solução simples e segura enquanto não há
  login real, documentando claramente que é temporária.
- Não alterar models — a relação `ForeignKey` (um-para-muitos) já suportava o cenário; sem
  migrations nesta tarefa.
- Validação autoritativa no servidor (aceites, forms) preservada nos dois fluxos.
- Fluxo testado ponta a ponta (cadastro inicial + segundo aventureiro na mesma conta, sem novo
  usuário, com ficha médica/autorização/aceites; redirecionamento sem sessão; bloqueio sem aceites).

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada — substituir a sessão temporária por `request.user`.
- Página real de "Meus Dados" e listagem de aventureiros ainda NÃO criadas.
- Permissões / perfis, validação avançada de CPF, "Esqueci minha senha" e envio de e-mail: futuros.

---

## 2026-07-01 - Ajuste visual do link "Cadastre-se" no login

### Resumo
O link "Cadastre-se" da tela de login deixou de ser um botão em destaque e passou a
ser um link de texto discreto, porém não menor que "Esqueci minha senha" (0.95rem,
peso 600, contra 0.92rem do "Esqueci minha senha").

### Arquivos criados/alterados
- `static/css/login.css`: `.link-cadastro` reescrito como link de texto discreto (sem
  caixa/borda/fundo), com hover de sublinhado.
- `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`: atualizados.

### Decisões tomadas
- Manter o "Cadastre-se" visível e um pouco maior que o "Esqueci minha senha", conforme pedido.
- Apenas CSS alterado; HTML e demais telas preservados.

### Pendências
- Sem novas pendências (mantêm-se as anteriores: autenticação, "Meus Dados", permissões, etc.).

---

## 2026-07-01 - Fluxo de cadastro de aventureiro

### Resumo
Implementação da estrutura inicial de criação de conta e cadastro completo de
aventureiro: link "Cadastre-se" no login, tela de cadastro em formato wizard de
7 etapas (`/cadastro/`), models para salvar os dados, upload de foto, aceites
obrigatórios e tela de confirmação (`/cadastro/sucesso/`). Ao finalizar, é criado
o `User` do Django e salvos os dados do aventureiro. NÃO há login automático,
permissões, recuperação de senha nem envio de e-mail.

### Models criados
- `Aventureiro`: FK `usuario` (um usuário pode ter vários aventureiros); dados principais,
  classes investidas (4 BooleanFields), endereço, documentos, dados de pai/mãe/responsável legal,
  cidade e data da inscrição (`data_inscricao` automática), aceites e `criado_em`.
- `FichaMedica`: OneToOne com `Aventureiro` (plano de saúde, doenças, alergias, condições de saúde,
  outras informações e tipo sanguíneo). Campos "qual/motivo" condicionais.
- `AutorizacaoImagem`: OneToOne com `Aventureiro` (dados do menor e do responsável legal para o termo).

### Rotas criadas
- `/cadastro/` (`core:cadastro`) e `/cadastro/sucesso/` (`core:cadastro_sucesso`).
- Em DEBUG, o Django passa a servir `/media/` (uploads).

### Arquivos criados/alterados
- `core/models.py`: novos models Aventureiro, FichaMedica, AutorizacaoImagem (com `choices`, `verbose_name`, BooleanFields, TextField, DateField/DateTimeField).
- `core/forms.py`: novo — ContaForm, AventureiroForm, FichaMedicaForm, AutorizacaoImagemForm (com mixin de estilo e validações de senha/username).
- `core/views.py`: novas views `cadastro_view` e `cadastro_sucesso_view` (validação conjunta + criação transacional).
- `core/urls.py`: novas rotas de cadastro e sucesso.
- `core/admin.py`: registro dos três models no admin.
- `core/migrations/0001_initial.py`: migration inicial dos models (criada e aplicada).
- `templates/core/cadastro.html`, `templates/core/cadastro_sucesso.html`, `templates/core/_campo.html`, `templates/core/_campo_check.html`: novos templates.
- `static/css/cadastro.css` e `static/js/cadastro.js`: novos (wizard, progresso, condicionais, preview de foto, atalhos, revisão).
- `templates/core/login.html`: link "Cadastre-se" entre "Entrar" e "Esqueci minha senha".
- `static/css/login.css`: estilo do link "Cadastre-se".
- `config/settings.py`: `MEDIA_URL` e `MEDIA_ROOT`.
- `config/urls.py`: serve mídia em DEBUG.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`, `docs/REGRAS_CODEX.md`, `docs/README_PROJETO.md`: documentação atualizada.

### Decisões tomadas
- Wizard de 7 etapas em uma única página/`<form>` (etapas mostradas/ocultadas via JS); validação
  autoritativa no servidor. Solução simples, bonita e segura, sem bibliotecas externas.
- Quatro formulários combinados com `prefix` (conta/av/med/img) para evitar colisão de nomes.
- Uso do `User` padrão do Django para a conta; aventureiros ligados por FK (um-para-muitos),
  preparando o reaproveitamento de responsáveis no futuro.
- Aceites obrigatórios (declaração médica e autorização de imagem) validados no servidor e no JS.
- Foto via `ImageField` (requer Pillow, já instalado); preview no navegador antes do envio.
- Validação básica: senha obrigatória e confirmada, username único. CPF sem validação avançada (futuro).
- Fluxo testado ponta a ponta (criação de User + models, casos negativos) e visual validado em mobile/desktop.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Página real de "Meus Dados" e listagem de aventureiros ainda NÃO criadas.
- Reaproveitamento de responsáveis em novos cadastros ainda NÃO implementado (depende de login).
- Validação avançada de CPF, permissões, recuperação de senha e envio de e-mail: futuros.

---

## 2026-07-01 - Configuração do versionamento Git e regras de commit/push

### Resumo
Configuração do versionamento do projeto no Git e no GitHub, e registro das regras
obrigatórias de commit e push para toda alteração futura. Não houve alteração de
funcionalidades, layout ou telas.

### Git
- Git já estava inicializado (criado na tarefa anterior); branch principal: `main`.
- Remoto `origin` configurado para: https://github.com/fabianopolone123/PINHALJUNIOR2.0.git
- `.gitignore` revisado (Python/Django): passou a ignorar também `.env`, `*.sqlite3`,
  `staticfiles/` e `media/`, mantendo as entradas anteriores.
- `README.md` criado na raiz (não existia) com descrição básica e links para a pasta `docs/`.
- Commit criado com o estado atual e push enviado para o GitHub.

### Arquivos criados/alterados
- `.gitignore`: revisado com as entradas exigidas para Python/Django.
- `README.md`: criado na raiz do projeto.
- `CODEX.md`: adicionadas as seções "Fluxo obrigatório de Git" e "Padrão de mensagens de commit".
- `docs/REGRAS_CODEX.md`: adicionadas as seções "Fluxo obrigatório para toda alteração"
  (antes/durante/depois + segurança no Git) e "Padrão obrigatório para mensagens de commit".
- `docs/ESTADO_ATUAL.md`: adicionada a seção "Versionamento (Git)".
- `docs/HISTORICO_ALTERACOES.md`: esta entrada.

### Decisões tomadas
- Branch principal padronizada como `main`.
- Não versionar arquivos sensíveis/locais (`.env`, banco SQLite, ambientes virtuais, cache).
- Não sobrescrever conteúdo existente do `README.md` (foi criado por não existir).
- Regra: nunca usar `force push` nem apagar histórico; em caso de conflito, analisar com segurança.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Página real de "Meus Dados", permissões/perfis, models e migrations ainda NÃO existem.

---

## 2026-07-01 - Tela inicial interna com menu lateral

### Resumo
Criação da tela inicial interna (área logada) na rota `/inicio/`, com menu lateral
fixo no desktop e menu recolhível (gaveta) no celular. O primeiro e único item de
menu é "Meus Dados" (em destaque como ativo). A área principal traz um cabeçalho de
boas-vindas, um card em destaque de "Meus Dados" e cards ilustrativos. NÃO há
autenticação, permissões, sessão, models ou migrations — apenas estrutura visual.

### Arquivos criados/alterados
- `core/views.py`: adicionada a view `inicio_view` (renderiza `core/inicio.html`).
- `core/urls.py`: adicionada a rota `inicio/` (nome `core:inicio`).
- `templates/core/inicio.html`: novo template da tela interna (menu lateral, área principal,
  cards, script inline do menu recolhível e comentários indicando onde adicionar futuros
  itens de menu / permissões).
- `static/css/inicio.css`: novo CSS próprio da tela interna (mobile first, menu lateral,
  cards, hover, animação de entrada, `prefers-reduced-motion`).
- `templates/core/login.html`: botão "Entrar" agora redireciona (apenas visualmente) para
  `/inicio/`; continua sem validar usuário/senha.
- `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`, `docs/REGRAS_CODEX.md`: documentação atualizada.

### Decisões tomadas
- No celular, o menu lateral vira gaveta recolhível (botão hambúrguer + overlay) — solução
  simples e segura, sem cortar a tela.
- CSS da tela interna em arquivo próprio (`inicio.css`), sem misturar com `login.css`.
- Menu estruturado para permissões futuras: item ativo via classe `ativo` e comentários
  no template indicando onde novos itens (condicionais por perfil) serão inseridos.
- Ícones do menu/cards com emoji (sem biblioteca externa).
- Botão "Entrar" reaproveita o script inline existente, apenas redirecionando para `/inicio/`.
- Validação visual com Chrome headless (CDP): mobile 390px (sem overflow, menu fechado e aberto)
  e desktop 1280px.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Página real de "Meus Dados" (visualizar/editar) ainda NÃO criada.
- Permissões / perfis de usuário ainda NÃO implementados.
- Cadastro / banco de usuários e models/migrations ainda NÃO existem.

---

## 2026-07-01 - Melhoria visual da tela de login

### Resumo
Melhoria visual da tela de login (rota `/`), deixando-a mais moderna, com efeitos
suaves e mantendo total responsividade mobile first. Alteração apenas de CSS — o
HTML e a estrutura do projeto foram preservados. Nenhuma autenticação foi
implementada e nenhuma dependência foi instalada.

### Arquivos criados/alterados
- `static/css/login.css`: reescrito de forma organizada (sem duplicação), adicionando:
  fundo com gradiente animado e formas circulares desfocadas flutuando; card com
  glassmorphism suave, sombra mais elegante e animação de entrada; brilho atrás do
  logo com `drop-shadow`; título com linha decorativa; foco realçado nos campos;
  botão "Entrar" com gradiente, brilho deslizante no hover e efeito de clique;
  link "Esqueci minha senha" com sublinhado animado; suporte a `prefers-reduced-motion`.
- `docs/ESTADO_ATUAL.md`: atualizado com o novo padrão visual da tela de login.
- `docs/HISTORICO_ALTERACOES.md`: esta entrada.
- `docs/REGRAS_CODEX.md`: adicionada seção com o padrão visual a ser preservado.

### Decisões tomadas
- Manter o HTML da tela de login intacto (todas as classes, campos, botão e link preservados);
  concentrar as melhorias apenas no CSS.
- Usar glassmorphism suave (card translúcido com `backdrop-filter`) mantendo bom contraste
  do texto escuro.
- Incluir `@media (prefers-reduced-motion: reduce)` para acessibilidade.
- Validação visual feita com Chrome headless (CDP) em 390px (mobile, sem overflow horizontal:
  scrollWidth = innerWidth = 390) e 1280px (desktop).

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Cadastro / banco de usuários do sistema ainda NÃO implementado.
- Funcionalidade do link "Esqueci minha senha" ainda NÃO implementada.
- Dashboard / área interna ainda NÃO criada.

---

## 2026-07-01 - Estrutura inicial, tela de login e documentação interna

### Resumo
Criação da estrutura inicial do projeto Django, da tela de login visual
(responsiva, mobile first) acessível na rota principal `/`, e do sistema de
documentação interna do projeto. A autenticação ainda NÃO foi implementada.

### Estado atual do projeto (resumo do que já existe)
- Projeto Django configurado (`config/`) com `templates/` e `static/`.
- App principal `core` com a view da tela de login.
- Tela de login visual na rota `/` com logo, título, campos de usuário e senha,
  botão "Entrar" e link "Esqueci minha senha".
- Logo do clube exibido no topo (`static/img/logo.png`, com fundo transparente).
- CSS próprio da tela de login (`static/css/login.css`), sem frameworks externos.

### Arquivos criados/alterados
- `manage.py`: utilitário de linha de comando do Django.
- `config/settings.py`: configurações do projeto (apps, templates, static, idioma pt-br, fuso America/Sao_Paulo).
- `config/urls.py`: rotas raiz do projeto (inclui as rotas do app `core` e o admin).
- `config/wsgi.py` e `config/asgi.py`: pontos de entrada WSGI/ASGI.
- `config/__init__.py`: pacote do projeto.
- `core/views.py`: view `login_view` que renderiza a tela de login.
- `core/urls.py`: rota `/` nomeada `core:login`.
- `core/apps.py`, `core/admin.py`, `core/models.py`, `core/__init__.py`, `core/migrations/__init__.py`: estrutura do app `core` (sem models por enquanto).
- `templates/core/login.html`: template da tela de login (logo, título, formulário e script inline que impede o envio real).
- `static/css/login.css`: estilos da tela de login (mobile first, gradiente azul/verde, card arredondado, foco nos campos, hover no botão).
- `static/img/logo.png`: logo do clube (fundo tornado transparente).
- `static/img/logo_original_backup.png`: backup do logo original recebido.
- `static/img/LEIA-ME.txt`: instruções sobre o logo.
- `requirements.txt`: dependência do Django.
- `.gitignore`: arquivos ignorados pelo Git.
- `CODEX.md`: guia rápido para o Codex.
- `docs/README_PROJETO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`, `docs/HISTORICO_ALTERACOES.md`: documentação interna do projeto.

### Decisões tomadas
- Usar CSS próprio, sem Bootstrap ou Tailwind.
- Layout mobile first, com card de login centralizado.
- Paleta de cores azul/verde inspirada no logo do clube.
- O botão "Entrar" não autentica; o envio do formulário é bloqueado via script inline.
- O link "Esqueci minha senha" aponta para `#` (sem funcionalidade ainda).
- O logo original vinha com fundo cinza sólido (RGB, sem transparência); o fundo foi
  recortado para transparente e o arquivo original foi mantido como backup.

### Pendências
- Autenticação real (login/logout) ainda NÃO implementada.
- Cadastro / banco de usuários do sistema ainda NÃO implementado.
- Funcionalidade do link "Esqueci minha senha" ainda NÃO implementada.
- Dashboard / área interna ainda NÃO criada.
- App `core` ainda não possui models nem migrations de negócio.
