# Instruções para o Codex

Antes de qualquer alteração neste projeto, leia obrigatoriamente:

1. docs/README_PROJETO.md
2. docs/REGRAS_CODEX.md
3. docs/ESTADO_ATUAL.md
4. docs/HISTORICO_ALTERACOES.md

Após qualquer alteração, atualize obrigatoriamente:

- docs/ESTADO_ATUAL.md
- docs/HISTORICO_ALTERACOES.md

E, ao final, versione no Git (ver seção "Fluxo obrigatório de Git" abaixo).

## Regras principais

- Não finalize nenhuma tarefa sem registrar o que foi alterado.
- Não implemente funcionalidades além do que foi pedido.
- Não apague código existente sem necessidade.
- Preserve o padrão visual e estrutural já criado.
- Quando houver dúvida, siga a solução mais simples e segura.

## Fluxo obrigatório de Git (commit e push após cada alteração)

Toda alteração feita no projeto deve terminar versionada no Git e enviada ao GitHub:

1. `git status`
2. `git add .`
3. `git commit -m "<mensagem descritiva em português do Brasil>"`
4. `git push` (remoto `origin`, branch `main`)

Regras de segurança:
- Nunca fazer `force push`.
- Nunca apagar histórico do Git.
- Nunca sobrescrever arquivos remotos sem autorização.
- Se o push falhar, informar o erro e analisar com segurança antes de qualquer pull/merge.

## Padrão de mensagens de commit

- Sempre em português do Brasil.
- Curtas, claras e descritivas; explicar objetivamente o que mudou.
- Usar verbo no presente quando possível (ex.: `cria`, `melhora`, `ajusta`, `corrige`).
