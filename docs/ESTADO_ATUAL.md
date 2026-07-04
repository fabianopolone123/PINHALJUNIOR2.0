# Estado Atual do Sistema

> Resumo rápido do estado atual. Atualize este arquivo após qualquer alteração.

**Última atualização:** 2026-07-04 (Evento complexo — Fase 2.1: fundação das inscrições — configuração, faixas etárias, valor da diretoria e trava por prazo)

## Nome do sistema
Clube de Aventureiros Pinhal Júnior

## Objetivo do sistema
Sistema web do clube com autenticação real, cadastro de conta e de aventureiros e
área interna "Meus Dados" que exibe os dados do usuário logado e de seus aventureiros.

## Funcionalidades prontas
- Estrutura inicial do Django funcionando.
- Tela de login responsiva (mobile first) na rota `/`, com visual moderno.
- **Autenticação real**: login por username/senha (`authenticate` + `login`), com mensagem
  "Usuário ou senha inválidos." em caso de erro; após logar, vai para `/inicio/`. O usuário é
  resolvido **sem diferenciar maiúsculas/minúsculas** (ex.: `fabiano` = `Fabiano`), consistente
  com o cadastro (que impede usernames duplicados por `iexact`).
- **Logout** em `/sair/` (POST, botão "Sair" no menu lateral); volta para o login.
- **Proteção de rota**: `/inicio/` usa `@login_required`; sem login, redireciona para `/`
  (com `?next=`). Configurados `LOGIN_URL`, `LOGIN_REDIRECT_URL` e `LOGOUT_REDIRECT_URL`.
- Tela interna "Meus Dados" (`/inicio/`) **funcional e reorganizada**:
  - Card do **Responsável** no topo (dados do responsável legal do aventureiro mais recente):
    nome, parentesco, e-mail, WhatsApp e total de aventureiros; expande (`<details>`) mostrando
    nome, parentesco, CPF, e-mail, WhatsApp, cidade/estado (do termo de imagem) e um botão **Editar**.
    Sem aventureiros, exibe os dados básicos da conta.
  - Seção **Aventureiros cadastrados**: um card clicável por aventureiro com foto 3x4 destacada,
    nome, pílulas (idade, camiseta, classes) e status de ficha médica/autorização; ao abrir, mostra
    **todos** os dados em seções recolhíveis: Dados pessoais, Documentos, Endereço, Pai, Mãe,
    Responsável legal, Ficha médica (com medicamentos por condição), Declaração médica e
    Autorização de imagem (completa). Botão "Editar dados do aventureiro" ainda desabilitado.
  - **Foto**: exibida em **moldura redonda** (foto de perfil). Só aparece se o arquivo existir
    fisicamente (a view checa `storage.exists`); caso contrário, mostra um placeholder com as
    **iniciais** do nome. O `<img>` tem `onerror` que troca para o placeholder se a imagem falhar
    (nunca quebra a página). As fotos de teste são **avatares fictícios** desenhados com Pillow
    (silhueta com rosto sorridente) — nunca fotos reais de crianças.
  - **Fechar ao clicar fora**: painéis `<details>` abertos (responsável, aventureiro e seções
    internas) recolhem ao clicar fora deles; abrir um recolhe os outros (accordion); `Esc` fecha
    tudo. Implementado em `static/js/inicio.js` (clique dentro não fecha).
  - Botão "Cadastrar outro aventureiro" e estado vazio amigável quando não há aventureiros.
- Edição do responsável em `/meus-dados/responsavel/editar/` (form `ResponsavelLegalForm`): altera
  nome, parentesco, CPF, e-mail e WhatsApp de todos os aventureiros do usuário com o mesmo CPF de
  responsável (ou apenas o mais recente, se nenhum coincidir); volta a `/inicio/` com mensagem de sucesso.
- Menu lateral fixo (desktop) e recolhível/gaveta (mobile), com nome do usuário e botão "Sair".
- Menu com dois itens: **Meus Dados** e **Usuários** (item ativo destacado conforme a tela).
- Tela **Usuários** (`/usuarios/`, **restrita ao perfil Diretor** via `@diretor_required`): visão
  geral de responsáveis e aventureiros com o vínculo familiar. Agrupa responsáveis únicos (pai, mãe e
  responsável legal de todos os aventureiros) por CPF (ou nome+WhatsApp, ou nome), juntando papéis
  quando é a mesma pessoa; mostra os aventureiros vinculados a cada responsável (com idade e papel do
  vínculo) e um resumo por aventureiro. Tem contadores (Responsáveis/Aventureiros/Vínculos) e
  **pesquisa inteligente** em tempo real (ignora maiúsculas/acentos). **Ao clicar em qualquer card**
  (responsável ou aventureiro), abre um **modal responsivo** (tela cheia no celular) com **todos os
  dados** daquela pessoa — no responsável: CPF, e-mail, celular/WhatsApp, papéis e aventureiros
  vinculados; no aventureiro: dados pessoais, documentos, endereço, pai/mãe/responsável, ficha médica,
  termo de imagem e foto (reaproveita o parcial `_aventureiro_detalhe.html` de "Meus Dados"). Como é
  restrita ao Diretor, aqui é permitido exibir dados sensíveis. O item de menu "Usuários" aparece só
  para o diretor.
- **Perfis/permissões**: `core/permissoes.py` (`eh_diretor` + decorator `diretor_required`) e o context
  processor `core/context_processors.py` (`is_diretor` em todos os templates, para `{% if is_diretor %}`).
- Módulo **Eventos** (`/eventos/`, **restrito ao Diretor**): lista os eventos do clube em cards
  (nome, tipo, data, horário, local, descrição) e permite **criar evento**. O botão "Criar evento"
  abre um **modal** para escolher o tipo: **Evento simples** (implementado) ou **Evento com inscrição**
  (marcado como "Em breve"). O cadastro de evento simples (`/eventos/novo/`) tem nome, local, descrição,
  data, horário de início e término. Cada evento na lista tem um botão **Duplicar** que abre o
  formulário já preenchido com aquele evento (`?duplicar=<id>`), para recadastrar algo recorrente
  mudando só a data/horário. Menu "Eventos" aparece só para o diretor.
- **Evento complexo (com inscrição) — Fase 1**: no modal de "Criar evento", a opção **"Evento com
  inscrição"** cria um evento `tipo=inscricao` (com data/hora de início **e término**, para eventos de
  vários dias) e leva ao **painel do evento** (`/eventos/<id>/`). O painel tem **abas** (Resumo,
  Inscrições, Lojinha, Custos, Financeiro): **Resumo** mostra indicadores (inscritos, arrecadação,
  vendas, receitas, custos e **resultado** — verde/vermelho); **Custos** permite adicionar custos
  (título, descrição, valor e **comprovante** anexo) e removê-los, com o total refletindo no resultado.
  As abas Lojinha/Financeiro estão como "em breve" (próximas fases). O plano completo (todas
  as fases) está em `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`. Pagamentos ficam simulados por ora.
- **Evento complexo — Fase 2.1 (fundação das inscrições)**: a aba **Inscrições** do painel deixou de
  ser "em breve" e agora tem a **configuração da inscrição** do evento: **local** (obrigatório no
  evento com inscrição), **aberto ao público geral?** (sim = qualquer pessoa; não = só membros do
  clube), **prazo limite de inscrição** (data/hora) e **valor da diretoria** (valor fixo que a
  diretoria paga, independe da idade; vazio = sem valor especial, 0 = grátis). Mostra um **status**
  ("✅ Abertas" / "⛔ Encerradas") com a data-limite: passado o prazo (ou, se vazio, o fim do evento),
  trava automaticamente. Também gerencia **faixas etárias com valores** por evento (rótulo opcional +
  idade mín/máx + valor), adicionadas por modal e removíveis — cada evento define as suas. Ainda
  faltam (próximas partes da Fase 2): 2.2 formulário de inscrição personalizável; 2.3 evento no menu
  de todos os perfis + página do evento; 2.4 inscrição de fato (pagamento simulado) + lista de
  inscritos + contagem no dashboard.
- Na lista de Eventos, os cards têm **altura limitada** (título/descrição em até 2 linhas) e **clicar no
  card** (fora dos botões) abre um **modal de visualização** com todos os dados do evento (só leitura).
  Valores monetários usam o filtro `moeda` (`core/templatetags/formato.py`) → `R$ 1.500,00`.
- Logo do clube exibido no topo da tela de login (com fallback "CA" caso não carregue).
- Ao finalizar o cadastro inicial, o usuário é **autenticado automaticamente** (login real) e
  levado à tela de sucesso; "Ir para a tela inicial" abre `/inicio/` já logado.
- Fluxo de cadastro de aventureiro em `/cadastro/`: wizard de 7 etapas (conta, ficha de inscrição,
  responsáveis, ficha médica, declaração médica, autorização de imagem, revisão), com barra de
  progresso, campos condicionais, upload/preview de foto e tela de sucesso em `/cadastro/sucesso/`.
- Link "Cadastre-se" na tela de login (entre "Entrar" e "Esqueci minha senha"), em estilo
  discreto de link de texto (levemente maior que "Esqueci minha senha").
- Ao finalizar o cadastro, cria o `User` do Django e salva Aventureiro + FichaMedica + AutorizacaoImagem.
- Cadastro de **múltiplos aventureiros na mesma conta**: a tela de sucesso mostra o nome cadastrado e
  oferece "Cadastrar outro aventureiro" e "Ir para a tela inicial". A opção leva a
  `/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso"), que vincula o novo
  aventureiro ao usuário logado (`request.user`); como retaguarda, ainda aceita o usuário guardado
  na sessão (`cadastro_usuario_id`). Sem nenhum dos dois, redireciona para o login.
- Nesse fluxo, é possível reaproveitar os dados de pai, mãe e responsável legal do último cadastro
  marcando uma opção; os campos são preenchidos automaticamente e podem ser editados antes de finalizar.
- Comando de gerenciamento `criar_dados_teste` para popular o banco local com uma conta de teste
  (`teste_responsavel` / `123456`) e 2 aventureiros completos (ficha de inscrição, ficha médica,
  autorização de imagem e fotos 3x4 fictícias geradas com Pillow: `lucas_teste.png`/`ana_teste.png`).
  Idempotente (pode rodar várias vezes); as fotos só são regeradas quando estão faltando ou apontam
  para arquivo inexistente — se já estiverem corretas, são mantidas.
- Comando de gerenciamento `importar_migracao` para **migrar os cadastros do sistema antigo** a partir
  do pacote exportado (pasta com `dados_json/` e `arquivos/`). Traz **apenas** os dados de cadastro
  ("cadastre-se"): a conta de acesso (login com **hash de senha preservado** → o responsável continua
  logando com a mesma senha), os dados de **pai, mãe e responsável legal**, o **endereço**, os dados de
  cada **aventureiro**, a **ficha médica**, o **termo de autorização de imagem** e a **foto** de cada
  aventureiro. **Não** importa: diretoria, financeiro, eventos, loja, whatsapp, assinaturas, nem
  responsáveis sem nenhum aventureiro vinculado; pula um registro-lixo de teste do sistema antigo.
  Uso: `python manage.py importar_migracao --origem "<pasta>"` (com `--dry-run` para simular).
  Idempotente (reaproveita o login pelo username; pula aventureiro já existente por usuário+nome).
  Primeira execução (2026-07-03): **35 logins + 37 aventureiros** (com ficha médica, termo e foto).
  As fotos importadas são dados **reais** dos membros e ficam **apenas** em `media/` (git-ignored) —
  **nunca** versionadas. Os dados pessoais de menores (JSON/CSV/zip da exportação) **não** vão ao Git.
- **Perfis de acesso** (grupos nativos do Django): **Diretor, Responsável, Professor, Tesoureiro,
  Secretário**. Conceito: "Diretoria" é o grupo de integrantes do clube (diretor, secretário,
  tesoureiro, professor); "Responsável" é o lado dos pais. Uma pessoa pode ter os dois lados e
  alternar o perfil ao logar (lógica de alternância a implementar). Por enquanto, só o **Diretor**
  receberá permissões nas telas; os demais perfis existem sem permissões (definir depois).
- Comando de gerenciamento `configurar_perfis`: cria os 5 perfis e o **usuário diretor inicial**
  (`Fabiano` / senha `1234` — senha de desenvolvimento, trocar em produção), vinculado ao perfil
  Diretor. Idempotente. Uso: `python manage.py configurar_perfis`.

## Padrão visual da tela de login (atual)
- Fundo com gradiente azul→verde animado (movimento lento) e formas circulares desfocadas flutuando.
- Card com glassmorphism suave (fundo translúcido + `backdrop-filter`), sombra elegante e animação de entrada.
- Brilho radial suave atrás do logo, dando profundidade; logo com leve `drop-shadow`.
- Título em destaque com linha decorativa (gradiente azul→verde) abaixo do subtítulo.
- Campos com foco realçado (borda azul + halo) e leve elevação.
- Botão "Entrar" com gradiente, efeito de brilho deslizante no hover, elevação e clique.
- Link "Esqueci minha senha" discreto, com sublinhado animado no hover.
- Animações desativadas automaticamente quando o usuário prefere menos movimento (`prefers-reduced-motion`).
- Testado visualmente em mobile (390px, sem overflow) e desktop (1280px).

## Padrão visual da tela interna (atual)
- Menu lateral fixo à esquerda no desktop (gradiente azul), com logo, nome do sistema
  e itens de menu; item ativo destacado em verde.
- No celular, o menu vira gaveta recolhível: barra superior com botão hambúrguer,
  gaveta deslizante e overlay que fecha ao tocar fora.
- Rodapé da barra com o nome do usuário logado e o botão "Sair".
- Área principal "Meus Dados": card do **Responsável** no topo (expansível, com botão Editar) e
  a seção **Aventureiros cadastrados** com cards clicáveis (foto 3x4 destacada, pílulas de resumo,
  status de ficha/autorização e seções recolhíveis com todos os detalhes).
- Pílulas/etiquetas para informações rápidas; cards com sombras suaves, bordas arredondadas
  e hover leve; painéis e seções recolhíveis via `<details>/<summary>` nativos (sem JS).
- Mensagens de feedback (sucesso/erro) via framework de messages do Django.
- Fundo claro com detalhes decorativos radiais suaves; animação de entrada dos cards.
- Suporte a `prefers-reduced-motion`. Layout responsivo (mobile first): cards empilhados no
  celular e em grade de 2 colunas em telas largas; sem overflow horizontal (validado).

## Models existentes
- `Aventureiro` — ficha de inscrição + dados dos responsáveis (pai, mãe, responsável legal);
  FK `usuario` (um usuário pode ter vários aventureiros); `data_inscricao` e `criado_em` automáticos.
- `FichaMedica` — OneToOne com `Aventureiro` (plano de saúde, doenças, alergias, condições, tipo sanguíneo).
- `AutorizacaoImagem` — OneToOne com `Aventureiro` (dados do menor e do responsável para o termo).
- `Evento` — evento do clube (`tipo` simples/inscrição, nome, local, descrição, data, **data_fim**,
  horário de início/término, `criado_por` FK User, `criado_em`). Campos de inscrição (evento complexo):
  **`inscricao_aberta_publico`**, **`inscricao_limite`** (prazo) e **`valor_diretoria`**. Métodos
  `fim_datetime()`, `prazo_inscricao()` e `inscricoes_abertas()`. Migrations `0002`, `0003`, `0004`.
- `CustoEvento` — custo/despesa de um evento (FK `evento`, nome, descrição, valor, comprovante,
  `criado_por`). Migration `0003_evento_data_fim_custoevento`.
- `FaixaEtariaPreco` — faixa etária com valor de inscrição, por evento (FK `evento`, rótulo,
  idade_min, idade_max, valor, ordem). Migration `0004`.

## Funcionalidades incompletas / não implementadas
- Link "Esqueci minha senha" — sem funcionalidade (aponta para `#`).
- Edição dos dados do aventureiro pela área logada — hoje "Meus Dados" é somente visualização.
- Permissões / perfis de usuário — NÃO implementados.
- Validação avançada de CPF — NÃO implementada (deixada para o futuro).
- Envio de e-mail — NÃO implementado.

## Próximas etapas previstas
- **Evento complexo — Fase 2.2**: formulário de inscrição personalizável por evento (próximo passo).
- **Evento complexo — Fase 2.3**: evento visível no menu de todos os perfis + página do evento.
- **Evento complexo — Fase 2.4**: inscrição de fato (participantes por faixa/diretoria, pagamento
  simulado, código), lista de inscritos no painel e contagem/arrecadação no dashboard.
- (A definir) Permitir editar os dados do aventureiro pela área logada.
- (A definir) Implementar o fluxo de "Esqueci minha senha".

## Apps existentes
- `config` — projeto Django (settings, urls, wsgi, asgi).
- `core` — app principal (views de login, tela inicial e cadastro; models de aventureiro).

## Templates existentes
- `templates/core/login.html` (login real, com mensagem de erro)
- `templates/core/inicio.html` (área "Meus Dados": card do responsável + cards clicáveis dos aventureiros)
- `templates/core/editar_responsavel.html` (edição do responsável legal)
- `templates/core/usuarios.html` (responsáveis, aventureiros e vínculos, com pesquisa e modal de detalhes)
- `templates/core/eventos.html` (lista de eventos + modal de escolha de tipo)
- `templates/core/evento_form.html` (formulário do evento simples)
- `templates/core/evento_complexo_form.html` (criação do evento complexo)
- `templates/core/evento_painel.html` (painel/dashboard do evento complexo)
- `templates/core/_aventureiro_detalhe.html` (parcial com o detalhe completo do aventureiro)
- `templates/core/cadastro.html` (wizard de cadastro)
- `templates/core/cadastro_sucesso.html`
- `templates/core/_campo.html` e `templates/core/_campo_check.html` (parciais de campo reutilizáveis)
- `templates/core/_dado.html` (parcial rótulo+valor usada em "Meus Dados")

## Arquivos CSS existentes
- `static/css/base.css` — regras globais de interface (linkado em todas as telas, **antes** do CSS
  da página). Torna o texto de interface **não selecionável** (sem cursor de texto/caret fora de
  campos digitáveis); mantém selecionáveis os campos de formulário e os valores de dados
  (`.dado-valor` / `.selecionavel`). Também hospeda o **componente reutilizável de modal** (janela
  suspensa) usado por várias telas.
- `static/css/eventos.css` — tela de Eventos (lista, cards, formulário e cards de escolha de tipo).
- `static/css/login.css`
- `static/css/inicio.css`
- `static/css/cadastro.css`
- `static/css/usuarios.css` (complementa `inicio.css` na tela "Usuários")

## Arquivos JavaScript existentes
- `static/js/cadastro.js` — wizard de etapas (numeração e índices calculados dinamicamente, servindo
  tanto ao cadastro de 7 etapas quanto ao de 6 etapas), barra de progresso, campos condicionais,
  preview da foto, atalhos (copiar pai/mãe para responsável legal), reaproveitamento dos dados dos
  responsáveis no cadastro de novo aventureiro, revisão e validação dos aceites.
- `static/js/inicio.js` — menu recolhível no celular e o fechamento dos painéis `<details>` de
  "Meus Dados" ao clicar fora / abrir outro / `Esc` (clique dentro não fecha).
- `static/js/usuarios.js` — pesquisa em tempo real na tela "Usuários" e o **modal** de dados
  completos (clona o detalhe do card, expande as seções e fecha no X/fora/Esc).
- `static/js/eventos.js` — abre/fecha o modal de escolha do tipo de evento (X/fora/Esc).
- `static/js/evento_painel.js` — abas do painel do evento complexo + modal de "Adicionar custo".

## Rotas existentes
- `/` — tela de login com autenticação real (`core.views.login_view`, nome `core:login`).
- `/sair/` — logout (POST) (`core.views.sair_view`, nome `core:sair`).
- `/inicio/` — área "Meus Dados", protegida por `@login_required` (`core.views.inicio_view`, nome `core:inicio`).
- `/meus-dados/responsavel/editar/` — edição do responsável, protegida por login (`core.views.editar_responsavel_view`, nome `core:editar_responsavel`).
- `/usuarios/` — responsáveis, aventureiros e vínculos, **restrita ao Diretor** (`core.views.usuarios_view`, nome `core:usuarios`).
- `/eventos/` — lista de eventos, **restrita ao Diretor** (`core.views.eventos_view`, nome `core:eventos`).
- `/eventos/novo/` — cadastro de evento simples, **restrita ao Diretor** (`core.views.evento_novo_view`, nome `core:evento_novo`; aceita `?duplicar=<id>`).
- `/eventos/complexo/novo/` — cria evento complexo (`core.views.evento_complexo_novo_view`, nome `core:evento_complexo_novo`).
- `/eventos/<id>/` — painel do evento complexo (`core.views.evento_painel_view`, nome `core:evento_painel`).
- `/eventos/<id>/custos/novo/` e `/eventos/<id>/custos/<id>/excluir/` — adicionar/remover custo (POST).
- `/eventos/<id>/inscricoes/config/` — salva a configuração da inscrição (POST, `core:evento_inscricao_config`).
- `/eventos/<id>/inscricoes/faixa/novo/` e `/eventos/<id>/inscricoes/faixa/<id>/excluir/` — adicionar/remover faixa etária (POST).
- `/cadastro/` — cadastro inicial: conta + primeiro aventureiro (`core.views.cadastro_view`, nome `core:cadastro`).
- `/cadastro/novo-aventureiro/` — outro aventureiro na mesma conta (`core.views.cadastro_novo_aventureiro_view`, nome `core:cadastro_novo_aventureiro`).
- `/cadastro/sucesso/` — confirmação (`core.views.cadastro_sucesso_view`, nome `core:cadastro_sucesso`).
- `/admin/` — Django admin (models de cadastro registrados).
- Em DEBUG, o Django serve os arquivos de mídia em `/media/`.

## Configurações importantes
- `DEBUG = True` (desenvolvimento).
- `ALLOWED_HOSTS = []` (desenvolvimento).
- Idioma: `pt-br`. Fuso horário: `America/Sao_Paulo`.
- Banco: SQLite (`db.sqlite3`), já com os models de cadastro migrados.
- `STATICFILES_DIRS` aponta para a pasta `static/`.
- `MEDIA_URL = "media/"` e `MEDIA_ROOT = BASE_DIR / "media"` (uploads, ex.: foto 3x4).
- `TEMPLATES DIRS` aponta para a pasta `templates/`.
- Autenticação: `LOGIN_URL = "core:login"`, `LOGIN_REDIRECT_URL = "core:inicio"`,
  `LOGOUT_REDIRECT_URL = "core:login"`.
- `SECRET_KEY` é de desenvolvimento (trocar em produção).
- Requer `Pillow` (já instalado) para o `ImageField` da foto.

## Versionamento (Git)
- Repositório Git inicializado; branch principal: `main`.
- Remoto `origin`: https://github.com/fabianopolone123/PINHALJUNIOR2.0.git
- `.gitignore` configurado para Python/Django (ignora `.env`, `*.sqlite3`, ambientes virtuais, cache, `staticfiles/`, `media/`, etc.).
- `README.md` na raiz com descrição básica e apontando para a pasta `docs/`.
- `CLAUDE.md` na raiz: arquivo de contexto (guia rápido) que aponta para os docs oficiais.
- Regra obrigatória: após qualquer alteração, rodar `git add .`, criar commit descritivo em
  português do Brasil e fazer `git push` (ver `CODEX.md` e `docs/REGRAS_CODEX.md`).

## Observações importantes para continuação
- Não usar Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter responsividade mobile first e o padrão visual azul/verde já criado.
- Ao criar models, gerar as migrations correspondentes.
- Sempre atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md` após qualquer alteração.
- Ao final de cada alteração, versionar no Git (commit + push) conforme o fluxo obrigatório.
