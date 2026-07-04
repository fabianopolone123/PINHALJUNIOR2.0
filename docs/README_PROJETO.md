# Clube de Aventureiros Pinhal Júnior

## Nome do projeto

Clube de Aventureiros Pinhal Júnior

## Objetivo geral do sistema

Sistema web para o Clube de Aventureiros Pinhal Júnior. O projeto já possui
autenticação real (login/logout), cadastro de conta e de aventureiros (com ficha
médica e autorização de imagem) e uma área interna "Meus Dados" que exibe os dados
da conta e dos aventureiros do usuário logado.

Além do cadastro, o sistema tem um **módulo de Eventos** completo (evento simples e evento
complexo com inscrições, lojinha e PDV/balcão) — ver a seção "Estado atual" e
`docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`.

O foco continua sendo uma interface bonita, moderna e **responsiva (mobile first)**,
com CSS próprio (sem frameworks externos).

## Stack usada

- **Django** (5.2.x) — framework web principal
- **Python** (3.10+)
- **HTML** — templates
- **CSS** — estilos próprios, sem frameworks externos
- **JavaScript** — puro, sem frameworks (wizard do cadastro em `static/js/cadastro.js` + scripts inline)
- **Pillow** — necessário para o `ImageField` (upload da foto 3x4)
- **Banco de dados**: SQLite (padrão do Django), com os models de cadastro migrados

## Estado atual do sistema

- Estrutura inicial do Django criada e funcionando.
- Tela de login visual acessível na rota principal `/` (com link "Cadastre-se").
- Tela inicial interna (área logada) acessível em `/inicio/`, com menu lateral e o item "Meus Dados".
- Fluxo de cadastro de aventureiro em `/cadastro/` (wizard de 7 etapas) que cria o `User` e salva
  a ficha de inscrição, a ficha médica e a autorização de imagem; confirmação em `/cadastro/sucesso/`.
- Cadastro de outro aventureiro na mesma conta em `/cadastro/novo-aventureiro/` (wizard de 6 etapas,
  sem "Conta de acesso"), com opção de reaproveitar os dados dos responsáveis do último cadastro.
- Models de cadastro criados e migrados (`Aventureiro`, `FichaMedica`, `AutorizacaoImagem`).
- Logo do clube exibido no login, no menu lateral e no cadastro.
- **Autenticação real implementada** (login por username/senha, logout e `@login_required` na área interna).
- Tela "Meus Dados" funcional: card do **Responsável** no topo (com edição) e os aventureiros
  do usuário logado em cards clicáveis com detalhes por seção.
- **Perfis de acesso** (grupos do Django): Diretor, Responsável, Professor, Tesoureiro, Secretário.
  Por enquanto **só o Diretor** recebe permissões nas telas (ex.: "Usuários" e "Eventos" só aparecem/
  funcionam para o Diretor). Comando `configurar_perfis` cria os perfis + o usuário diretor `Fabiano`.
- Tela **"Usuários"** (restrita ao Diretor): responsáveis, aventureiros e vínculos; clicar num card abre
  um modal com **todos os dados** da pessoa.
- Módulo **"Eventos"** (restrito ao Diretor): **evento simples** (nome, local, descrição, data, horário)
  com "Duplicar", e **evento complexo (com inscrição)** com painel/dashboard (`/eventos/<id>/`) em abas
  (Resumo, Inscrições, Lojinha, Custos, Financeiro). Já concluídos:
  - **Fase 1**: base do evento complexo + painel (Resumo + Custos).
  - **Fase 2 (Inscrições)**: configuração (local, aberto ao público?, prazo/trava, faixas etárias de
    preço, valor da diretoria), **formulário personalizável** por evento (campos "uma vez" ou "por
    participante"), **página do evento** (pública/só-membros) que aparece no **menu de todos os
    perfis**, e a **inscrição de fato** (participantes por faixa/diretoria, código, pagamento
    **simulado**, lista de inscritos + arrecadação no dashboard).
  - **Fase 4 (Lojinha)**: produtos com variações/estoque; **comprar** na página do evento (com
    **passo de pagamento simulado**: WhatsApp obrigatório, autopreenchimento do comprador, escolha
    Pix/Cartão, tela de pagamento com QR Pix simulado/copia e cola ou aviso de redirecionamento ao
    Mercado Pago, aprovação simulada), junto da inscrição, e no **PDV/balcão** (venda + inscrição
    presencial, formas de pagamento com troco, cortesia, vínculo opcional a inscrição); **operadores**
    por evento (diretoria selecionada + ajudantes externos com conta temporária/senha `1234`/troca
    obrigatória).
  - **Notificações**: toasts flutuantes no canto da tela (padrão único do sistema).
  - **Próximo**: **Fase 5 (Financeiro/gráficos)**. Plano completo em `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`.
- **Migração** dos cadastros do sistema antigo via comando `importar_migracao` (dados reais ficam só
  local; nada de dados de menores no Git).

> **Fonte da verdade detalhada:** `docs/ESTADO_ATUAL.md` (mais completo e atualizado a cada mudança).

## Como rodar o projeto localmente

Pré-requisitos: Python 3.10+ e Django instalado (ver `requirements.txt`).

```bash
# (opcional) criar e ativar ambiente virtual
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# instalar dependências
pip install -r requirements.txt

# rodar o servidor de desenvolvimento
python manage.py runserver
```

Depois, acesse no navegador: http://127.0.0.1:8000/

Observação: ao rodar, o Django pode exibir um aviso sobre migrações pendentes
das apps internas (admin, auth, sessions). Isso é normal e não afeta a tela de
login. Se quiser remover o aviso, rode `python manage.py migrate`.

### Popular o banco com dados de teste

Para validar rapidamente uma conta com 2 aventureiros já cadastrados, use o
comando de gerenciamento que gera dados fictícios (sem pessoas nem imagens reais):

```bash
python manage.py criar_dados_teste
```

Ele cria (ou atualiza, se já existirem) o usuário `teste_responsavel` (senha `123456`)
com 2 aventureiros completos — ficha de inscrição, ficha médica, autorização de imagem
e fotos 3x4 fictícias (avatar de desenho, sem pessoas reais) geradas com Pillow em
`media/aventureiros/fotos_teste/` (`lucas_teste.png` e `ana_teste.png`). O comando é seguro para rodar mais de uma vez
(usa `get_or_create`/`update_or_create` e não apaga dados de outros usuários). As fotos só
são regeradas quando estão faltando ou apontando para um arquivo inexistente; se já
estiverem corretas, são mantidas (o comando informa "foto mantida" ou "foto gerada").

### Perfis de acesso e usuário diretor

Para criar os perfis de acesso e o usuário diretor inicial (necessário para ver "Usuários" e "Eventos"):

```bash
python manage.py configurar_perfis
```

Cria os grupos **Diretor, Responsável, Professor, Tesoureiro, Secretário** e o usuário
**`Fabiano`** (senha `1234`, perfil Diretor — senha de desenvolvimento, trocar em produção). Idempotente.

### Migração dos cadastros do sistema antigo (opcional)

Para importar os cadastros (login, pai/mãe/responsável, aventureiros, ficha médica, termo e foto) a
partir do pacote exportado do sistema antigo:

```bash
python manage.py importar_migracao --origem "<pasta descompactada>" --dry-run   # simula
python manage.py importar_migracao --origem "<pasta descompactada>"             # executa
```

As fotos reais e os dados pessoais de menores ficam **apenas** em `media/` (git-ignored) — nunca no Git.

### Como testar o login e a tela "Meus Dados"

1. Rode `python manage.py criar_dados_teste` (se ainda não rodou).
2. Acesse `http://127.0.0.1:8000/` e faça login com **usuário `teste_responsavel`** e
   **senha `123456`** — você será levado a `/inicio/`.
3. Em "Meus Dados" aparecem os dados da conta e os 2 aventureiros de teste (com foto,
   ficha médica e autorização de imagem em seções recolhíveis).
4. Para sair, use o botão **Sair** no menu lateral (volta ao login). Depois disso,
   acessar `/inicio/` diretamente redireciona para a tela de login.

## Estrutura geral de pastas

> A árvore abaixo é **ilustrativa** (do início do projeto). O app cresceu bastante (vários models,
> views, templates e estáticos do módulo de Eventos/Lojinha). A relação **completa e atualizada** de
> rotas, models, templates e estáticos está em `docs/ESTADO_ATUAL.md`.

```
PINHALJUNIOR2.0/
├── CODEX.md                  # Guia rápido para o Codex
├── manage.py                 # Utilitário de linha de comando do Django
├── requirements.txt          # Dependências do projeto
├── .gitignore
├── db.sqlite3                # Banco SQLite (vazio / padrão)
├── config/                   # Configuração do projeto Django
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                     # App principal
│   ├── __init__.py
│   ├── admin.py              # Models registrados no admin
│   ├── apps.py
│   ├── models.py             # Aventureiro, FichaMedica, AutorizacaoImagem
│   ├── forms.py              # Formulários do cadastro
│   ├── urls.py
│   ├── views.py
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py
├── templates/
│   └── core/
│       ├── login.html            # Tela de login
│       ├── inicio.html           # Tela inicial interna
│       ├── cadastro.html         # Wizard de cadastro (7 etapas)
│       ├── cadastro_sucesso.html # Confirmação do cadastro
│       ├── _campo.html           # Parcial de campo (label + widget)
│       └── _campo_check.html     # Parcial de campo checkbox
├── static/
│   ├── css/
│   │   ├── login.css
│   │   ├── inicio.css
│   │   └── cadastro.css
│   ├── js/
│   │   └── cadastro.js       # Wizard, condicionais, preview de foto
│   └── img/
│       ├── logo.png
│       ├── logo_original_backup.png
│       └── LEIA-ME.txt
├── media/                    # Uploads dos usuários (ex.: fotos) — não versionado
└── docs/                     # Documentação interna (este diretório)
    ├── README_PROJETO.md
    ├── REGRAS_CODEX.md
    ├── ESTADO_ATUAL.md
    └── HISTORICO_ALTERACOES.md
```

## Apps existentes

- **config**: projeto Django (settings, urls, wsgi, asgi). Não é um app de negócio.
- **core**: app principal. Views de login, tela inicial e cadastro; models de aventureiro.

## Rotas existentes

> Lista **parcial** (principais). O módulo de Eventos/Lojinha tem muitas outras rotas
> (`/eventos/<id>/...`, `/pdv/`, `/operadores/`, `/loja/`, etc.) — ver `docs/ESTADO_ATUAL.md`.

- `/` — tela de login com autenticação real (view `core.views.login_view`, nome `core:login`).
- `/sair/` — logout (POST); encerra a sessão e volta ao login (view `core.views.sair_view`, nome `core:sair`).
- `/inicio/` — área logada "Meus Dados", protegida por `@login_required` (view `core.views.inicio_view`, nome `core:inicio`).
- `/meus-dados/responsavel/editar/` — edição dos dados do responsável legal, protegida por login (view `core.views.editar_responsavel_view`, nome `core:editar_responsavel`).
- `/usuarios/` — responsáveis, aventureiros e vínculos, **restrita ao Diretor** (`@diretor_required`); clicar num card abre modal com todos os dados (view `core.views.usuarios_view`, nome `core:usuarios`).
- `/eventos/` — lista de eventos, **restrita ao Diretor** (view `core.views.eventos_view`, nome `core:eventos`).
- `/eventos/novo/` — cadastro de evento simples (nome `core:evento_novo`; aceita `?duplicar=<id>`).
- `/eventos/complexo/novo/` — cria evento complexo (nome `core:evento_complexo_novo`).
- `/eventos/<id>/` — painel do evento complexo (nome `core:evento_painel`); `/eventos/<id>/custos/...` adiciona/remove custos.
- `/cadastro/` — cadastro inicial: cria a conta + o primeiro aventureiro (view `core.views.cadastro_view`, nome `core:cadastro`).
- `/cadastro/novo-aventureiro/` — cadastra outro aventureiro na mesma conta, sem etapa de conta (view `core.views.cadastro_novo_aventureiro_view`, nome `core:cadastro_novo_aventureiro`).
- `/cadastro/sucesso/` — confirmação, com opções "Cadastrar outro aventureiro" e "Ir para a tela inicial" (view `core.views.cadastro_sucesso_view`, nome `core:cadastro_sucesso`).
- `/admin/` — Django admin (models de cadastro registrados).
- `/media/...` — arquivos de mídia (uploads), servidos pelo Django em DEBUG.

## Models existentes

- **Aventureiro** — ficha de inscrição + dados dos responsáveis; FK `usuario` (um usuário pode ter vários).
- **FichaMedica** — OneToOne com Aventureiro (dados médicos).
- **AutorizacaoImagem** — OneToOne com Aventureiro (dados do termo de imagem).
- **Evento** — evento do clube (`tipo` simples/inscrição; datas/horários; config de inscrição:
  aberto ao público, prazo, valor da diretoria).
- **CustoEvento** — custo/despesa de um evento.
- **FaixaEtariaPreco** e **CampoInscricao** — faixas de preço e campos do formulário, por evento.
- **Inscricao**, **ParticipanteInscricao**, **RespostaInscricao** — inscrições (com pagamento/origem).
- **ProdutoEvento**, **VariacaoProduto**, **PedidoLoja**, **ItemPedidoLoja** — lojinha e pedidos.
- **OperadorEvento** e **PerfilUsuario** — operadores do PDV e a flag de troca de senha.

> A lista **completa e atualizada** de models, rotas, templates e estáticos está em `docs/ESTADO_ATUAL.md`.

## Templates existentes

> Lista **parcial** (base do projeto). Há muitos templates do módulo de Eventos/Lojinha
> (painel, página do evento, inscrição, loja, PDV, operadores, parciais `_menu.html`,
> `_loja_itens.html`, etc.) — a relação completa está em `docs/ESTADO_ATUAL.md`.

- `templates/core/login.html` — tela de login (com link "Cadastre-se").
- `templates/core/inicio.html` — tela inicial interna.
- `templates/core/cadastro.html` — wizard de cadastro (7 etapas).
- `templates/core/cadastro_sucesso.html` — confirmação do cadastro.
- `templates/core/_campo.html` e `_campo_check.html` — parciais reutilizáveis de campo.

## Arquivos estáticos existentes

- `static/css/login.css`, `static/css/inicio.css`, `static/css/cadastro.css` — estilos por tela.
- `static/js/cadastro.js` — wizard do cadastro (etapas, progresso, condicionais, preview de foto, atalhos, revisão).
- `static/img/logo.png` — logo do clube (usado no login, no menu lateral e no cadastro).
- `static/img/logo_original_backup.png` — backup do logo original recebido.
- `static/img/LEIA-ME.txt` — instruções sobre o logo.

Outros scripts inline: em `login.html` (redireciona para `/inicio/`) e em `inicio.html`
(abre/fecha o menu recolhível no celular).

## Funcionalidades existentes

- Tela de login visual e responsiva na rota `/`, com **autenticação real** (login/logout) e link "Cadastre-se".
- Tela inicial interna em `/inicio/` com menu lateral (desktop) / gaveta (mobile) e cards.
- Cadastro de aventureiro em `/cadastro/` (wizard de 7 etapas): conta de acesso, ficha de inscrição,
  responsáveis, ficha médica, declaração médica, autorização de imagem e revisão. Ao finalizar, cria
  o `User` e salva Aventureiro + FichaMedica + AutorizacaoImagem; confirma em `/cadastro/sucesso/`.
- Cadastro de **múltiplos aventureiros na mesma conta**: a tela de sucesso oferece "Cadastrar outro
  aventureiro", que leva a `/cadastro/novo-aventureiro/` (wizard de 6 etapas, sem "Conta de acesso").
  Esse fluxo reaproveita o mesmo usuário (identificado por sessão, temporariamente) e permite preencher
  automaticamente os dados de pai/mãe/responsável legal com base no último cadastro.

## Funcionalidades ainda NÃO implementadas

- Funcionalidade do link "Esqueci minha senha" (hoje aponta para `#`).
- Edição dos dados do aventureiro pela área logada (hoje é somente visualização).
- Permissões dos **demais perfis** (por enquanto só o Diretor tem acesso; Responsável/Professor/
  Tesoureiro/Secretário existem sem permissões) e a **alternância de perfil** (diretoria ↔ responsável).
- **Cadastro de diretoria** e o cadastro "diretoria + aventureiro" (planejado em
  `docs/PLANEJAMENTO_CADASTRO_DIRETORIA.md`).
- **Evento complexo — Fase 5** (em andamento): a parte do **Financeiro** (aba com o **extrato completo**
  do evento — resultado, resumos e lançamentos) já está **concluída**; faltam **dashboard/gráficos** no
  Resumo, **cupons de desconto** e **presença/check-in**. Depois, **pagamentos reais** (gateway) e **loja
  oficial do clube** (uniformes, separada da lojinha de evento) — ver `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`.
  (Fases 1, 2/Inscrições, "3"/página pública e 4/Lojinha já estão **concluídas**.)
- Validação avançada de CPF e envio de e-mail.

## Observações importantes para futuros desenvolvimentos

- **Não usar** Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter o foco em **responsividade mobile first**.
- Preservar o padrão visual já criado (paleta azul/verde inspirada no logo).
- A `SECRET_KEY` em `config/settings.py` é de desenvolvimento; trocar em produção.
- `DEBUG = True` e `ALLOWED_HOSTS = []` são configurações de desenvolvimento.
- Ao criar models, lembrar de gerar as migrations correspondentes.
- Sempre atualizar a documentação em `docs/` após qualquer alteração
  (ver `CODEX.md` e `docs/REGRAS_CODEX.md`).
