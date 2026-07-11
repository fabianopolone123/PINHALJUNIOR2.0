# Planejamento — Cadastro de Diretoria e tipos de cadastro

> **Status:** IMPLEMENTADO em 2026-07-11 (base). Ver `docs/ESTADO_ATUAL.md`.
> Feito: modelos `MembroDiretoria`/`FichaMedicaDiretoria`, perfil "Diretoria",
> tela "Cadastre-se" com 3 opções, cadastro só-diretoria e o fluxo mesclado
> (Diretoria + Aventureiro → 2 perfis com alternância).
>
> **Ainda pendente (próximo passo):** exibir o membro da diretoria em "Meus Dados"/
> "Usuários"; UI do Diretor para **atribuir o papel específico** (Diretor/Secretário/
> Tesoureiro/Professor); **assinatura desenhada** dos termos da diretoria; substituir o
> texto do compromisso pelo oficial, se o clube fornecer um juramento formal.
>
> Campos e decisões abaixo (registrado em 2026-07-03) permanecem como referência.

---

## Contexto (o que já foi feito antes deste planejamento)
- Importação dos cadastros do sistema antigo (comando `importar_migracao`): 35 logins + 37 aventureiros.
- Perfis de acesso criados (grupos do Django) + usuário diretor inicial (comando `configurar_perfis`):
  **Diretor, Responsável, Professor, Tesoureiro, Secretário**; usuário `Fabiano` (senha dev `1234`) no perfil Diretor.

## Conceito de perfis
- **Diretoria** = grupo de integrantes do clube: **Diretor, Secretário, Tesoureiro, Professor**.
- **Responsável** = lado dos pais (separado da diretoria).
- Uma pessoa pode ser **das duas partes** (integrante da diretoria **e** responsável por aventureiro).
  Nesse caso, ao logar, **alterna entre o perfil Responsável e o perfil Diretoria**.
- Por enquanto, só o **Diretor** recebe permissões nas telas; os demais perfis existem sem permissões.

---

## 1) CADASTRO DE DIRETORIA — campos

### Conta de acesso
- Usuário (username) · Senha · Confirmar senha

### Identificação
- Nome completo
- Igreja · Distrito
- CPF · RG
- Data de nascimento
- Estado civil → **se "Casado(a)"**: campo condicional **Nome do cônjuge**
- **Tem filhos?** (sim/não) → **se sim**: **Quantidade de filhos** (apenas o número; não cadastra cada filho aqui)

### Contato
- E-mail · WhatsApp
- Telefone residencial (se tiver) · Telefone comercial (se tiver)

### Endereço
- Endereço · Número · Bairro · Cidade · CEP · Estado

### Foto
- Anexar foto *(assinatura digital fica para depois)*

### Informações de saúde
- "Possui alguma dificuldade de saúde que limite a participação nas atividades do clube?" (sim/não)
- **Se sim**: descrição do que é

### Informações educacionais
- Escolaridade: **Ensino Fundamental** · **Ensino Médio** · **Ensino Superior**

### Aceites (checkbox no cadastro — textos/assinatura completos depois)
1. **Termo de compromisso de voluntariado** — aceite. *(texto oficial pendente)*
2. **Declaração médica (atestado)** — "Atesto serem verdadeiras as informações médicas preenchidas e
   isento o clube por quaisquer acidentes decorrentes da omissão de problemas médicos."
3. **Termo de autorização de imagem** — o **mesmo do aventureiro, adaptado para maior de idade**
   (o próprio adulto autoriza; sem a parte de "menor/responsável legal"). Autoriza o uso de qualquer
   material (fotos, documentos) em campanhas profissionais e institucionais do clube, para evitar
   questões futuras de direito de imagem. Campos reaproveitam os dados da identificação. *(texto oficial pendente)*

---

## 2) CADASTRO DE DIRETORIA + AVENTUREIRO (mesclagem)
Na ordem:
1. Passa por **todo o cadastro de diretoria** (seção 1).
2. Segue para o **cadastro de responsável** — com opção de **reaproveitar** os dados já digitados na
   diretoria (nome, CPF, contato, endereço), para não redigitar. *(a confirmar)*
3. Entra no **fluxo de cadastro de aventureiro**, podendo cadastrar **mais de um aventureiro**.
4. Resultado: **1 login com 2 perfis (Diretoria + Responsável)**, com **alternância** ao logar.

---

## 3) Tela "Cadastre-se" — 3 opções
Ao clicar em "Cadastre-se", a pessoa escolhe o tipo:
1. **Aventureiro** (fluxo atual: responsável + aventureiro)
2. **Diretoria**
3. **Diretoria + Aventureiro**

---

## Como pretendo implementar (rascunho técnico)
- Novo modelo `MembroDiretoria` (ligado ao usuário) com: identificação + cônjuge/quantidade de filhos
  + contato + endereço + foto + saúde (limitação + descrição) + escolaridade + os 3 aceites (booleanos).
  Requer migration.
- Versão do termo de autorização de imagem adaptada para adulto (reaproveitando a lógica do aventureiro).
- Escolha dos 3 tipos na tela "Cadastre-se" + alternância de perfil (Diretoria ↔ Responsável).
- Wizard no mesmo padrão visual do cadastro de aventureiro.
- Ordem sugerida: **1º** modelo + cadastro de diretoria puro → **2º** mesclagem + tela de escolha + alternância.

---

## Pontos em aberto (confirmar antes/durante a implementação)
- [ ] **Textos oficiais** do termo de compromisso de voluntariado e do termo de autorização de imagem
      (usar provisório até chegarem?).
- [ ] **Reaproveitar** os dados da diretoria como responsável no fluxo mesclado (recomendado: sim).
- [ ] Como o **papel específico** (diretor/secretário/tesoureiro/professor) é atribuído a quem faz o
      cadastro de diretoria (ex.: entra "pendente" e o diretor define depois).
- [ ] Restringir o menu/tela **"Usuários"** ao perfil Diretor (não remover o código).
- [ ] Excluir a conta de teste `teste_responsavel` (2 aventureiros de teste) — quando for oportuno.
- [ ] Assinatura digital dos termos (etapa futura).

---

## Referência — campos do sistema ANTIGO (para consulta)
> Só referência; **não** vamos importar esses dados de diretoria.

**Tabela `diretoria`:** nome, igreja, distrito, endereco, numero, bairro, cep, cidade, estado, email,
whatsapp, telefone_residencial, telefone_comercial, nascimento, estado_civil, cpf, rg, conjuge,
filho_1, filho_2, filho_3, possui_limitacao_saude, limitacao_saude_descricao, escolaridade,
autorizacao_imagem (aceite), declaracao_medica (aceite), foto, assinatura.

**Tabela `diretoriaficha`:** termo de compromisso (`compromisso_data` + assinatura) e termo de
autorização de imagem (`termo_imagem_data` + assinatura), com campos de nacionalidade, dados do
responsável/pessoa, e-mail/telefone de contato e data (dia/mês/ano/cidade).
