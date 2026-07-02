# Estado Atual do Sistema

> Resumo rápido do estado atual. Atualize este arquivo após qualquer alteração.

**Última atualização:** 2026-07-01 (tela inicial interna com menu lateral)

## Nome do sistema
Clube de Aventureiros Pinhal Júnior

## Objetivo do sistema
Sistema web do clube. No momento possui apenas a tela inicial de login (visual),
servindo de base para o desenvolvimento futuro.

## Funcionalidades prontas
- Estrutura inicial do Django funcionando.
- Tela de login visual e responsiva (mobile first) na rota `/`, com visual moderno.
- Logo do clube exibido no topo da tela de login (com fallback "CA" caso não carregue).
- Formulário visual: campos "Usuário" e "Senha", botão "Entrar", link "Esqueci minha senha".
- Tela inicial interna (área logada) na rota `/inicio/`, com menu lateral fixo (desktop)
  e menu recolhível/gaveta (mobile), item "Meus Dados" ativo e cards visuais.
- Botão "Entrar" da tela de login navega (apenas visualmente) para `/inicio/`, sem autenticação.

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
- Área principal com cabeçalho de boas-vindas, card em destaque "Meus Dados" e cards
  ilustrativos (Cadastro, Atividades, Conquistas), com sombras suaves e hover.
- Fundo claro com detalhes decorativos radiais suaves; animação de entrada do conteúdo.
- Suporte a `prefers-reduced-motion`. Testado em mobile (390px, sem overflow) e desktop (1280px).

## Funcionalidades incompletas / não implementadas
- Autenticação real (login/logout) — NÃO implementada.
- Cadastro / banco de usuários do sistema — NÃO implementado.
- Link "Esqueci minha senha" — sem funcionalidade (aponta para `#`).
- Menu com um único item ("Meus Dados"); o item ainda não abre página própria (aponta para `/inicio/`).
- Permissões / perfis de usuário — NÃO implementados (menu preparado para isso via comentários).
- Models e migrations de negócio — não existem.

## Próximas etapas previstas
- (A definir) Implementar autenticação de usuários.
- (A definir) Criar a página real de "Meus Dados" (visualizar/editar dados).
- (A definir) Adicionar novos itens de menu conforme perfil/permissão do usuário.
- (A definir) Implementar o fluxo de "Esqueci minha senha".

> Observação: nenhuma dessas etapas foi iniciada.

## Apps existentes
- `config` — projeto Django (settings, urls, wsgi, asgi).
- `core` — app principal (views da tela de login e da tela inicial interna; sem models).

## Templates existentes
- `templates/core/login.html`
- `templates/core/inicio.html`

## Arquivos CSS existentes
- `static/css/login.css`
- `static/css/inicio.css`

## Arquivos JavaScript existentes
- Nenhum arquivo `.js` separado.
- Script inline em `templates/core/login.html`: impede o envio real e redireciona para `/inicio/` (navegação de teste).
- Script inline em `templates/core/inicio.html`: abre/fecha o menu recolhível no celular.

## Rotas existentes
- `/` — tela de login (`core.views.login_view`, nome `core:login`).
- `/inicio/` — tela inicial interna (`core.views.inicio_view`, nome `core:inicio`).
- `/admin/` — Django admin padrão (sem uso específico do projeto).

## Configurações importantes
- `DEBUG = True` (desenvolvimento).
- `ALLOWED_HOSTS = []` (desenvolvimento).
- Idioma: `pt-br`. Fuso horário: `America/Sao_Paulo`.
- Banco: SQLite (`db.sqlite3`), ainda sem dados do sistema.
- `STATICFILES_DIRS` aponta para a pasta `static/`.
- `TEMPLATES DIRS` aponta para a pasta `templates/`.
- `SECRET_KEY` é de desenvolvimento (trocar em produção).

## Observações importantes para continuação
- Não usar Bootstrap, Tailwind ou frameworks visuais externos (CSS é próprio).
- Manter responsividade mobile first e o padrão visual azul/verde já criado.
- Ao criar models, gerar as migrations correspondentes.
- Sempre atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md` após qualquer alteração.
