# Regras do Codex

Estas são as regras obrigatórias para toda nova alteração feita neste projeto.

## Regras obrigatórias

- Antes de fazer qualquer alteração, ler os arquivos dentro da pasta `docs/`.
- Ler também o arquivo `CODEX.md` da raiz do projeto.
- Antes de alterar qualquer arquivo, entender o padrão já existente.
- Não apagar código existente sem necessidade.
- Não alterar nomes de rotas, templates, apps, arquivos ou classes sem motivo.
- Não implementar funcionalidades além do que foi pedido.
- Não instalar bibliotecas externas sem autorização.
- Não usar Bootstrap, Tailwind ou frameworks visuais externos, a menos que seja solicitado.
- Manter o projeto simples, organizado e fácil de continuar.
- Criar migrations quando alterar models.
- Atualizar a documentação sempre que fizer qualquer alteração no projeto.
- Registrar no histórico o que foi feito, quais arquivos foram alterados e o motivo da alteração.
- Manter foco em responsividade mobile first.
- Preservar o padrão visual já criado.
- Evitar duplicação de CSS, HTML e lógica Python.
- Usar nomes claros para funções, views, templates, classes CSS e arquivos.
- Quando houver dúvida, fazer a solução mais simples e segura.
- No final de cada tarefa, informar quais arquivos foram criados ou alterados.
- Nenhuma tarefa deve ser considerada concluída sem atualizar `docs/ESTADO_ATUAL.md` e `docs/HISTORICO_ALTERACOES.md`.

## Regra obrigatória de manutenção da documentação

Toda vez que o Codex fizer qualquer alteração no sistema, deve atualizar obrigatoriamente:

- docs/ESTADO_ATUAL.md
- docs/HISTORICO_ALTERACOES.md

Se criar nova regra ou padrão técnico, deve atualizar:

- docs/REGRAS_CODEX.md

Se mudar estrutura geral, rota, app, configuração ou modo de rodar o projeto, deve atualizar:

- docs/README_PROJETO.md

## Padrão visual a preservar (tela de login)

Ao mexer na tela de login ou em novas telas, preservar o padrão visual já criado:

- Paleta azul/verde inspirada no logo (ver variáveis CSS em `static/css/login.css`).
- Fundo com gradiente azul→verde e formas decorativas suaves.
- Cards com bordas arredondadas, glassmorphism suave e sombra elegante.
- Campos com foco realçado (borda azul + halo) e boa altura para toque (mobile first).
- Botão principal com gradiente e transições suaves (hover/clique).
- Reaproveitar as variáveis CSS (`:root`) em vez de repetir cores/valores.
- Sempre manter `@media (prefers-reduced-motion: reduce)` para acessibilidade.
- CSS puro, sem Bootstrap/Tailwind ou frameworks externos.

## Padrão de layout interno (área logada)

Para as telas internas (após o login), preservar o padrão criado em
`templates/core/inicio.html` e `static/css/inicio.css`:

- Menu lateral fixo à esquerda no desktop (gradiente azul) com logo, nome do sistema e itens.
- No celular, o menu vira gaveta recolhível (botão hambúrguer + overlay). Nada pode ficar cortado.
- Item de menu ativo recebe a classe `ativo` (destaque em verde).
- Cada tela interna deve ter seu próprio CSS (não misturar com `login.css`), reaproveitando a paleta.
- Novos itens de menu devem ser adicionados no `<nav class="menu">`, no ponto marcado por comentário.
- O menu foi preparado para permissões futuras: exibir/ocultar itens conforme o perfil do usuário
  (ex.: envolver o item em `{% if ... %}`), quando a autenticação for implementada.
- Ícones podem ser emoji, caractere ou SVG inline — nunca biblioteca externa.
