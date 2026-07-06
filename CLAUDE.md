# CLAUDE.md — Contexto do projeto

Guia rápido para o assistente (e para devs). Leia também, obrigatoriamente, antes de alterar:
`CODEX.md`, `docs/README_PROJETO.md`, `docs/REGRAS_CODEX.md`, `docs/ESTADO_ATUAL.md`,
`docs/HISTORICO_ALTERACOES.md`. **Estes docs são a fonte da verdade e devem ser atualizados a cada mudança.**

## O que é
Sistema web do **Clube de Aventureiros Pinhal Júnior** (Django). Já possui autenticação real,
cadastro de conta e de aventureiros (com ficha médica e autorização de imagem), área interna
"Meus Dados", a tela "Usuários" (vínculos familiares) e um **módulo de Eventos** completo: evento
simples e **evento complexo** com inscrições (Fase 2), lojinha e **PDV/balcão** com operadores
(Fase 4). Também há o módulo **Presença**, o módulo **WhatsApp** (integração com a API da W-API —
configurar a instância e enviar mensagens; só Diretor) e a **Loja do Clube** (loja oficial de uniformes/
lenços, independente da lojinha de evento; cadastro de produtos com **grupos/variações** + vitrine com
**carrinho** e pagamento simulado; só Diretor por ora). O clube tem **3 áreas financeiras**: eventos (feito),
**mensalidades** (a fazer) e **loja** (base feita). **Próximos:** mensalidades e um Financeiro geral
consolidando as três — ver `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md` e `docs/ESTADO_ATUAL.md`.

## Stack
- Django 5.2 / Python 3.10+ · SQLite · Pillow (foto 3x4)
- HTML + **CSS próprio** (sem Bootstrap/Tailwind/libs) + JS puro
- Idioma pt-br, fuso America/Sao_Paulo

## Como rodar / testar
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver          # http://127.0.0.1:8000/
python manage.py criar_dados_teste  # popula dados de teste (idempotente)
```
Usuário de teste: **`teste_responsavel`** / senha **`123456`** (2 aventureiros com foto/ficha/autorização).

## Estrutura
- `config/` — projeto Django (settings, urls). `core/` — app único (views, models, forms, urls, admin,
  management command `criar_dados_teste`).
- Templates em `templates/core/`, estáticos em `static/{css,js,img}`, uploads em `media/` (git-ignored).

## Rotas (todas as internas exigem `@login_required`)
- `/` login (auth real) · `/sair/` logout (POST) · `/inicio/` "Meus Dados" · `/trocar-senha/`
- `/meus-dados/responsavel/editar/` editar responsável · `/usuarios/` responsáveis+aventureiros+vínculos
- `/cadastro/` conta+1º aventureiro · `/cadastro/novo-aventureiro/` outro na mesma conta · `/cadastro/sucesso/`
- **Recuperação de senha** (pública, via WhatsApp): `/recuperar-senha/` (CPF do resp. legal → código de 4 dígitos → nova senha), `.../codigo/`, `.../reenviar/`, `.../nova-senha/`
- **Eventos** (Diretor; PDV/operar também por operadores): `/eventos/`, `/eventos/<id>/` (painel),
  `/eventos/<id>/pagina|inscrever|loja|pdv|pdv/inscricao|operar|operadores/` etc. — lista completa em `docs/ESTADO_ATUAL.md`.
- **Presença** (Diretor): `/presenca/`, `/presenca/<id>/`, `/presenca/<id>/marcar/`
- **WhatsApp** (Diretor): `/whatsapp/` (config W-API + envio), `/whatsapp/config/`, `/whatsapp/enviar/`
- **Loja do Clube** (Diretor no menu; vitrine/carrinho `@login_required`): `/loja/` (abas Gerenciar/Loja),
  `/loja/produto/novo|<id>/editar|<id>/excluir/`, `/loja/produto/<id>/` (vitrine), `/loja/carrinho/…`,
  `/loja/finalizar|pagamento|sucesso/`, `/loja/compra/<id>/cancelar/`
- `/admin/`

## Models (`core/models.py`)
- `Aventureiro` (FK `usuario`; ficha de inscrição + pai/mãe/responsável legal; campo `ativo`). Um usuário → vários.
- `FichaMedica` (OneToOne) · `AutorizacaoImagem` (OneToOne).
- **Eventos/Lojinha/Presença**: `Evento`, `CustoEvento`, `FaixaEtariaPreco`, `CampoInscricao`, `Inscricao`,
  `ParticipanteInscricao`, `RespostaInscricao`, `ProdutoEvento`, `VariacaoProduto`, `PedidoLoja`,
  `ItemPedidoLoja`, `OperadorEvento`, `PerfilUsuario`, `CupomDesconto`, `PresencaEvento`.
- **WhatsApp**: `WhatsappConfig` (singleton; ID/token/URL base da W-API) — módulo WhatsApp (só Diretor).
- **Loja do Clube**: `ProdutoLoja` → `GrupoLoja` → `VariacaoLoja` (produto composto: grupos "escolha única"/
  "itens", com obrigatório + orientação), `FotoProdutoLoja` (galeria + lightbox; capa = 1ª foto) e
  `CompraLoja`/`ItemCompraLoja` (compra vinculada ao login e, opc., a um aventureiro; `kit` agrupa itens de
  um mesmo uniforme). Pagamento simulado.
- **Recuperação de senha**: `PerfilUsuario.whatsapp_principal_origem` (pai/mãe/resp legal) — para onde vai
  o código; código de recuperação fica na **sessão** (não há model novo pra ele).
  (migrations até `0022`). Detalhes em ESTADO_ATUAL.

## Regras inegociáveis
- **Após CADA alteração**: atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`
  (e `REGRAS_CODEX.md`/`README_PROJETO.md` quando aplicável) e **versionar no Git**:
  `git status` → `git add` → `commit` (mensagem em pt-BR, verbo no presente) → `git push origin main`.
  **Nunca** `force push` nem reescrever histórico.
- CSS próprio, mobile-first; preservar a paleta azul/verde e o padrão visual existente.
- Não instalar dependências novas sem autorização. Não alterar models sem necessidade; se alterar, criar migrations.
- **Segurança de menores: NUNCA usar fotos reais de crianças** nem baixar imagens da internet.
  Imagens de teste são avatares fictícios desenhados com Pillow. (Há imagens soltas na raiz que
  NÃO devem ser versionadas.)
- Fazer só o que foi pedido; não quebrar login, cadastro nem o cadastro de múltiplos aventureiros.

## Convenções úteis
- Parciais de template reutilizáveis: `_campo.html`, `_campo_check.html` (formulários) e `_dado.html`
  (rótulo+valor em "Meus Dados").
- Painéis expansíveis usam `<details>/<summary>` nativos; fechar-ao-clicar-fora em `static/js/inicio.js`.
- "Meus Dados": foto só aparece se o arquivo existir (`foto.storage.exists`), senão placeholder com iniciais.
- Verificação visual sem navegador dedicado: renderizar via test client + Chrome headless
  (`--force-device-scale-factor=1`; o viewport mínimo do headless é ~484px).
