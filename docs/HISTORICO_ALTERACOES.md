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
