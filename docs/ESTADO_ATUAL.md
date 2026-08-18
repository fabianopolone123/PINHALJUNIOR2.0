# Estado Atual do Sistema

> Resumo rápido do estado atual. Atualize este arquivo após qualquer alteração.

**Última atualização:** 2026-08-18 (**Eventos: copiar a lista de inscritos**): a aba **Inscrições** do painel
ganhou dois botões de cópia — **📋 Copiar lista** e **📋 Copiar por inscrição** —, que era o que faltava para
levar a lista de inscritos **para fora do sistema** com **telefone** e **número (código) da inscrição**. São
dois formatos porque são dois usos: a versão em **colunas separadas por TAB** (cabeçalho + uma linha por
**pessoa**: nº, participante, idade, WhatsApp, inscrição, responsável) cola direto em **planilha** — Excel e
Google Sheets quebram em colunas ao colar texto tabulado, sem passar por importação de CSV —, e a versão
**agrupada por inscrição** (responsável + WhatsApp + código numa linha, participantes com idade abaixo) é a que
se lê no **WhatsApp**, um contato por família. Decisões que importam: **copiar em vez de baixar arquivo** (foi o
pedido, e evita rota nova e o "onde foi salvo?" no celular); o **texto é montado no servidor**
(`_export_inscritos_evento`, que reaproveita o `_participantes_txt` do aviso interno) e não raspado do DOM — a
lista da tela tem pills, selos e `<details>`, e um texto tirado do HTML quebraria no próximo ajuste visual, então
**o JS só copia**; na versão em colunas o **WhatsApp repete em cada participante** da mesma inscrição, porque na
planilha cada linha tem de se sustentar sozinha (célula vazia estragaria filtro e ordenação); a **numeração é a
do aviso interno** (ordem de `criado_em`), então o "nº 3" da planilha e o "3)" do texto agrupado falam da mesma
gente. **Só inscrição confirmada** entra — cancelada não é inscrito —, inclusive quem vai **pagar por fora**:
para contato o que importa é estar inscrito (a lista de pendência de pagamento continua sendo o aviso interno). O
texto pronto vai no HTML em duas `<textarea>` **fora da tela** (não `hidden`: a cópia de reserva precisa de
`select()` num campo que exista de fato) e os botões só aparecem quando há alguém confirmado. Nada de model,
migration ou rota nova. Suíte: **306 testes OK** (295 + 11). Antes: prazo de inscrição próprio da diretoria.

**Anterior (Eventos: prazo de inscrição próprio da diretoria):** o evento ganhou um
**segundo prazo de inscrição, só para quem inclui alguém da diretoria**
(`Evento.inscricao_limite_diretoria`, migration **0069**), na mesma "Configuração da inscrição". Serve ao caso
real: a diretoria fecha a lista **depois** das famílias. A regra combinada é o ponto central — **uma inscrição
que inclua alguém da diretoria vale por esse prazo INTEIRA**, então o aventureiro que entra na mesma inscrição
aproveita a janela extra mesmo com o prazo comum já vencido (foi exatamente o pedido: "se inscrever uma
diretoria e na hora adicionar um aventureiro, o que vale é o prazo da diretoria"). E o prazo da diretoria **só
estende, nunca restringe**: o prazo de uma inscrição com diretoria é sempre o **mais generoso** dos dois, então
ninguém perde uma janela que já tinha — vencendo o prazo da diretoria antes do comum, ela continua se
inscrevendo no prazo comum (`prazo_inscricao_diretoria()` devolve o `max` dos dois; `tem_prazo_diretoria` só é
True quando de fato estende, para uma data inútil não virar informação na tela). Desenho que importa: **a tela
abre pelo prazo mais generoso** (`inscricoes_abertas(tem_diretoria=True)`) — fechá-la pelo prazo comum
impediria a diretoria de chegar ao formulário —, e **quem decide é a validação do POST**, pela composição real
da inscrição; a trava final está no model, então POST forjado depois dos **dois** prazos não cria nada (há
teste). Quem é "diretoria" continua sendo **quem marca a caixinha** (decisão do usuário), igual ao que já vale
para o **valor** da diretoria: o sistema não confere o cadastro — a brecha conhecida (marcar para furar prazo)
é a mesma que já existe para pagar menos, e fechá-la depende do vínculo exato participante × aventureiro, que é
dívida antiga. Nas telas: a página do evento ganhou um **terceiro estado** (faixa **âmbar** "Inscrições
encerradas — só diretoria"; verde diria "aberto" e vermelho "encerrado", e as duas enganam metade de quem lê),
a tela de inscrição abre com um aviso explicando a regra, e o painel mostra o selo **⛺ Só diretoria** com a
data da janela. O **PDV/balcão segue sem checar prazo** (inscrição presencial feita pela própria diretoria).
Suíte: **295 testes OK** (280 + 15). Conferido em 520/800/1400px com sonda: zero overflow. Antes: valor da
diretoria parcelado.

**Anterior (Eventos: valor da diretoria parcelado):** em evento caro (caso do
**Aventuri**) o valor que **a diretoria** paga pesa de uma vez só. Agora ele pode ser **dividido em parcelas
cobradas pelo clube** — no estilo das mensalidades, **não** é parcelamento de cartão: o clube **recebe em N
vezes**. Quantas parcelas é **por evento** (`Evento.parcelas_diretoria`, migration **0068**; `1` = à vista, que
é o padrão e o comportamento de todos os eventos existentes), no mesmo formulário "Configuração da inscrição".
Na tela de inscrição, a opção **"Dividir o valor da diretoria em Nx"** só aparece quando há participante
marcado como **diretoria**; marcando, o total passa a mostrar **"a pagar agora"**. **Só a parte da diretoria é
parcelada** — e é aqui que está o desenho principal: numa **inscrição mista** (o pai que é da diretoria
inscrevendo os filhos), no ato sai **uma única cobrança** com a **1ª parcela da diretoria + o valor integral dos
outros participantes + a lojinha**, e as parcelas restantes cobrem **apenas** o valor da diretoria. Uma cobrança
só, não duas: com dois pagamentos, um falhar deixaria a inscrição confirmada pela metade. A **1ª parcela nasce
paga** (é o pagamento dela que confirma a inscrição, como em todo o resto do sistema) e as seguintes **vencem
mês a mês**, em `ParcelaInscricao`. A família volta a pagar por uma **página pública com token**
(`/inscricao/<token>/parcelas/`, mesmo mecanismo do acerto de mensalidades — quem se inscreve pode não ter
conta), **uma parcela por cobrança**, para a baixa e a taxa do gateway ficarem individuais; o link aparece na
tela de sucesso e no painel do Diretor, que também tem **baixa manual** por parcela (parcela acertada em
dinheiro — e aqui o valor **entra** no caixa, ao contrário do "pago direto ao evento"). **A parte financeira é o
ponto delicado**: `Inscricao.valor_total` continua sendo o valor da inscrição, mas **toda soma de caixa passou a
usar `valor_no_caixa`** (total − parcelas em aberto), senão a arrecadação do evento e o Financeiro do clube
mostrariam dinheiro que não chegou; no **extrato**, a linha da inscrição vale o **`valor_no_ato`** e cada parcela
paga depois é um **lançamento próprio na data em que caiu**, então o extrato soma exatamente a arrecadação sem
contar a mesma parcela duas vezes (há teste comparando os dois). No painel, um card **"Parcelas da diretoria"**
(recebido × a receber × vencido) deixa claro que é dinheiro **do** clube que ainda não chegou — diferente do
card "Fora do caixa", que é dinheiro que nunca passa por aqui. Outros pontos: (1) a trava é no **servidor**
(`permite_parcelar_diretoria()` reavaliado no POST: forjar `parcelar_diretoria=1` num evento à vista não
parcela nada); (2) parcelar **não se combina** com "pago direto ao evento" nem existe sem Mercado Pago
configurado — nos dois casos não há cobrança para dividir; (3) a sobra dos centavos vai na **1ª** parcela, então
as seguintes ficam iguais e redondas; (4) **não há cobrança automática** das parcelas seguintes ainda (o Diretor
manda o link) — pendência registrada. Suíte na época: **280 testes OK** (253 + 27). Conferido em
520/800/1400px com sonda: zero overflow. Antes: Eventos — aviso interno de inscrição para a diretoria.

**Anterior (Eventos: aviso interno de inscrição para a diretoria):** quem organiza um
evento precisava abrir o painel para saber quem se inscreveu. Agora, **por evento**, dá para ligar
**"Avisar a diretoria a cada inscrição"** e escolher **um integrante** que recebe, a cada nova inscrição, a
**lista de inscritos** pelo WhatsApp (campos `Evento.notificar_inscricoes` e `notificar_inscricoes_para`,
migration **0067**, na aba Inscrições → Configuração). A lista é **agrupada por inscrição** — responsável +
WhatsApp numa linha, e abaixo cada participante com **nome e idade** —, que é como a diretoria fala com a
família: um contato por inscrição, não um por criança. Ela **cresce** a cada inscrição, sempre com o total.
**A separação por pagamento é a parte acionável**: quem escolheu uma forma marcada como **paga direto ao
evento** (`Inscricao.pagamento_externo`) fechou a inscrição **sem pagar**, então a mensagem marca a linha com
**⚠️ pagar por fora** e traz, no fim, o bloco **"Pagamento por fora — falta acertar (N)"** com nome, telefone
e forma de cada um, explicando que é preciso entrar em contato e depois **marcar como pago no painel**; quem
já foi baixado (`pago_externo_em`) sai do bloco. Novo template **`inscricao_evento_interno`** ("Nova inscrição
em evento") na aba 🧩 **Templates**, com os marcadores `{evento} {novo} {total_inscritos} {lista} {por_fora}`;
é o único aviso interno cujo **destinatário não é o checklist** de lá — vem do evento —, então a tela explica
isso e o POST **não zera** a M2M. **Envio manual** nos dois lugares: botão "📤 Enviar a lista agora" no painel
do evento e, na aba Templates, um seletor dos eventos com destinatário + "Enviar lista agora" (rota única
`/eventos/avisar-inscritos/`, que recebe o evento no POST). Pontos de desenho: (1) o gancho está nos **dois**
caminhos de inscrição — site (`_criar_inscricao_de_payload`) e **balcão/PDV**, que cria a inscrição por fora
do payload; sem isso a lista do WhatsApp divergiria da do painel (há teste); (2) sai em `on_commit` + thread,
como as demais notificações, para a chamada da W-API não segurar o request nem o webhook do Mercado Pago;
(3) é aviso interno → `forcar=True` (não passa pelo gate anti-bloqueio), como o "Novo pedido da loja";
(4) **inscrito nunca sai da lista** — nem quem pagou na hora, nem quem vai pagar por fora (a primeira versão
aparava as inscrições mais antigas para caber na mensagem, e isso foi **abandonado**: o que sumia era gente).
Quando o texto não cabe numa mensagem do WhatsApp, quem resolve é o **`_partir_texto_whatsapp`**, que divide
em **partes numeradas** ("(1 de 3)") cortando **só em quebra de linha** — vale para **todas** as notificações,
já que vive no `_notificar_whatsapp`; falha numa parte volta com a posição dela e o extrato 📨 Envios grava uma
linha por parte; (5) o botão manual funciona **mesmo com o automático desligado**. Suíte: **253 testes OK**
(237 + 16). Conferido em 520/1400px com sonda: zero overflow. Antes: recuperação de senha mostra o usuário.

**Anterior (Recuperação de senha mostra o usuário de acesso):** quem procura o
"Esqueci minha senha" muitas vezes não esqueceu a senha — esqueceu **o login**, e o fluxo antigo não dizia
qual era em lugar nenhum: a pessoa redefinia a senha e continuava sem conseguir entrar. Agora, depois de
digitar o CPF do responsável legal, a **tela do código** mostra o **usuário de acesso** da conta encontrada,
em destaque (card `.recup-usuario`, com `.selecionavel` para dar copiar), e a **mensagem do WhatsApp** leva o
usuário junto do código ("Seu usuário de acesso é: …"). O login vai na sessão do fluxo (`recup["usuario"]`),
gravado pelo `_recup_gerar_e_enviar` — então o **reenvio** também repete o usuário, sem consulta extra. Ponto
de desenho (decisão do usuário, com o custo explicado): mostrar **na tela**, e não só no WhatsApp, significa
que **quem souber o CPF de um responsável descobre o login** sem ter o celular da família; escolhido assim
porque o caso real é a mãe que não lembra o próprio usuário e precisa da resposta na hora. Como o CPF
continua sendo a chave de entrada, **CPF desconhecido não abre a etapa do código nem vazia nada** (há teste).
Isso **aumenta** o peso da dívida técnica já registrada de **falta de throttle** nesta tela (cada POST
válido dispara um WhatsApp real) — vale ligar um limite por IP/CPF antes de divulgar o recurso. Sem
migration. Suíte: **237 testes OK** (233 + 4; o fluxo de recuperação não tinha nenhum teste até hoje).
Conferido em 485/800/1400px com sonda, inclusive com login comprido: `scrollWidth == clientWidth` em todas.
Antes: Eventos — inscrição paga direto ao evento.

**Anterior (Eventos: inscrição paga direto ao evento):** alguns eventos (caso do
**Aventuri**) são pagos **direto para a organização**, não para o clube — mas a inscrição precisa ser feita e
controlada aqui. Em cima do seletor de formas já existente (`formas_pagamento_online`, de 12/08), o evento
ganhou **`formas_pagamento_fora`** + **`instrucoes_pagamento_fora`** (migrations **0065** e **0066**), no mesmo
formulário "Configuração da inscrição". É **por forma de pagamento** (nenhuma / Pix / cartão / ambas), então dá
para **cobrar o cartão pelo site e deixar só o Pix por fora** no mesmo evento. Escolhendo uma forma marcada,
quem se inscreve **não passa pela tela de fatura**: a
inscrição é criada na hora como **confirmada**, com `Inscricao.pagamento_externo=True` e **pagamento pendente**,
a notificação de inscrição sai igual e a **orientação cadastrada aparece** na página de inscrição e na de
sucesso. Na lista do painel a linha ganha o selo **⏳ Pagamento pendente / ✅ Pago por fora** e o botão **"Marcar
como pago"** (reversível, só Diretor). **O dinheiro fica fora dos dois financeiros** — nem no resultado do
evento nem no Financeiro do clube; a baixa manual **não** joga valor no caixa, só registra que a pessoa acertou
com o evento. No painel isso vira um card à parte (**"Fora do caixa"**: já acertado × a acertar) e no extrato do
evento o lançamento aparece marcado **"fora do caixa"** (como os cancelados: visível para auditoria, fora dos
totais). Pontos de desenho: (1) **evento que não marcar forma nenhuma continua idêntico** (cobra pelo Mercado
Pago) — o padrão é `nenhuma`; (2) `formas_fora()` é sempre a **interseção com `formas_online()`**: marcar como
"por fora" uma forma que o evento nem oferece não faz nada; (3) POST forjado cai na forma liberada, como no
fluxo cobrado; (4) inscrição **grátis não vira pendente** (não há o que pagar); (5) item de lojinha levado junto
herda o `pagamento_externo` (campo novo em `PedidoLoja`) — sem isso, uma camiseta comprada numa inscrição por
fora entraria no caixa sem nunca ter sido cobrada; (6) a **compra avulsa na lojinha** do evento **não** é
afetada (lá não há o que acertar depois). As classes `.insc-forma-*` (usadas desde a criação da tela)
**não tinham CSS nenhum** e ganharam estilo agora. Suíte: **233 testes OK** (218 + 15). Conferido em
1400/900/520/380px, zero overflow de página. Antes: WhatsApp — extrato de envios + webhook de entrega.

**Anterior (WhatsApp: quem recebeu e quem não — extrato de envios + webhook de
entrega):** até aqui o sistema só sabia que a **W-API aceitou** a mensagem; número sem WhatsApp, número errado
ou pessoa que bloqueou o clube devolvem sucesso e a mensagem morre no caminho — e nas **notificações
automáticas** (que rodam em thread) a falha sumia em silêncio, porque ninguém lia o retorno. Agora: (1) novo
model **`MensagemWhatsapp`** (migration **0064**) — o par do `LogEmail`, uma linha por mensagem que o sistema
tentou mandar, com destino, nome, origem, `message_id`, situação e motivo da falha; **o texto NÃO é gravado**
(mesma regra do e-mail) e guarda as últimas **300**. (2) O registro fica **dentro do `_enviar_whatsapp`**, que
virou casca de `_wapi_post_texto` — assim **nenhum** dos 7 pontos de envio escapa do extrato; cada um passa a
sua `origem` (cobrança, notificação, aniversário, reengajamento, autorização, avulsa, recuperação).
(3) **Webhook de entrega**: `wapi_parser.extrair_status` reconhece o aviso de status (SENT/RECEIVED/READ/FAILED,
incluindo os sinônimos `SERVER_ACK`/`DELIVERY_ACK`/`PLAYED` e os **ACKs numéricos 1..5**) e o webhook público
aplica em `MensagemWhatsapp.atualizar_status`, casando pelo `message_id`. (4) Nova aba **📨 Envios** na tela
`/whatsapp/`: KPIs (enviadas / chegaram / lidas / não chegaram), filtro **"só as que não chegaram"**, tabela com
selo por situação e o motivo da falha, e badge de problemas na própria aba. (5) Botão **"Ligar webhook de
entrega"** na aba 🔔 Webhook. Pontos de desenho: **o status é tratado ANTES de tudo no webhook** — se um payload
de entrega entrasse como "mensagem recebida", marcaria contato e até **autorização** de quem não escreveu nada
(termômetro verde falso); há teste de regressão disso. O status **não retrocede** (o WhatsApp manda os avisos
fora de ordem e o `READ` chega antes do `RECEIVED` com frequência), mas o **FAILED sempre vale**. Um aviso pode
trazer **lista de ids** (o `READ` costuma vir em lote). **Formato real, medido na instância do clube** (a doc
pública não abre nada disso): são **dois** endpoints de configuração e ambos existem —
`/webhook/update-webhook-delivery` ("Webhook de envio") e `/webhook/update-webhook-message-status` ("Webhook de
status") —, e chegam **dois eventos**: `webhookDelivery`, que vem **sem campo de status** (é o eco da saída, e
por isso vale como *enviada*, nunca como *entregue*), e `webhookStatus`, cujo vocabulário é
**`SERVER`/`DELIVERY`/`READ`** — não `SENT`/`RECEIVED`, que era o que a doc sugeria. O evento sem status só é
aceito com **`fromMe=true`**: sem essa trava, um evento de conversa de nome parecido seria engolido como status
e o clube **perderia a mensagem recebida** (e a autorização que ela pode carregar). Nota de método: **sondar
por GET não descobre rota na W-API** — ela responde `Cannot GET /v1/webhook/<qualquer coisa>` mesmo para as
rotas que funcionam com PUT. Suíte: **217 testes OK** (196 + 21). Antes: Top 10 de quem deve mais.

**Anterior (Mensalidades: Top 10 de quem deve mais):** a aba **Resumo** ganhou o
bloco **"Top 10 — quem está devendo mais"**, entre o gráfico mês a mês e o detalhe por mês: ranking com
posição (os 3 primeiros em vermelho), nome do aventureiro, responsável, quantos meses em aberto, barra
proporcional a quem deve mais e o valor. Helper `_top_devedores(ano)` — **uma** consulta agregada
(`Sum`/`Count` com `filter=Q(ano=ano)`). Decisão principal: o ranking soma **toda** a dívida em aberto, de
**qualquer ano**, porque "quem deve mais" ignorando o ano anterior daria ordem errada; para o número conversar
com os KPIs (que são do ano selecionado), cada linha mostra **quanto vem de outros anos**. Respeita as regras
do clube: **aventureiro inativo não entra** (inativo não é cobrado) e `demo` nunca entra; isento e pago não
contam. Sem devedor, o card diz "🎉 Ninguém com mensalidade em aberto". **Bug pré-existente corrigido de
passagem:** a tela de Mensalidades tinha **rolagem horizontal na página** em telas estreitas — o
`.mens-resumo-topo` usava `1fr` (que tem `min-width: auto` e não encolhe abaixo do conteúdo), então o gráfico
de 12 meses esticava a grade e o `.mens-grafico-scroll` **não conseguia rolar por dentro**; virou
`minmax(0, 1fr)` nas duas media queries. Conferido em 380/520/800/1400px: `scrollWidth == clientWidth` em
todas. Suíte: **196 testes OK** (188 + 8). Antes: inativar um evento.

**Anterior (Inativar um evento):** o Diretor agora **liga e desliga** um evento.
Novo campo `Evento.ativo` (migration **0063**, padrão `True` — nenhum evento existente muda) com botão
**⏸️ Inativar / ▶️ Reativar** na lista de eventos e no cabeçalho do painel (POST `/eventos/<id>/ativar/`).
Inativo, o evento **sai do menu** de todos os perfis (o rótulo do menu já dizia "Eventos ativos") e as telas
públicas **param de abrir** — página, inscrição, lojinha e a tela de pagamento —, **mesmo dentro da data**;
serve para suspender ou adiar sem excluir (excluir só funciona em evento vazio, e por regra não apaga evento
com inscrição/pedido/presença). Três camadas, de propósito: (1) o **menu** filtra `ativo=True`; (2)
`_evento_inativo_bloqueio` fecha as views públicas — **404** para visitante anônimo (o evento simplesmente
não existe para quem tem o link) e volta ao `/inicio/` com aviso para quem está logado; (3) a trava real fica
no **model** — `inscricoes_abertas()` e `loja_aberta()` devolvem `False`, então **POST forjado também é
recusado** (a lição das formas de pagamento: esconder o botão no HTML não é validação). **Para o Diretor nada
fecha**: painel, balcão/PDV, presença, operadores e financeiro seguem iguais, com selo "⏸️ Inativo" e faixa de
aviso no painel — inativar **não apaga nem esconde** inscrição, pedido, presença nem dinheiro que já entrou.
Foi escolhido **não** mexer no PDV: o balcão é ferramenta do Diretor/operador, não a porta pública que se quer
fechar. Não confundir com `demo` (dado fictício, que sai de tudo). **O botão não aparece em evento que já
terminou** — ele já saiu do menu e não aceita inscrição, então inativar não faria nada; se o evento passado
estiver inativo, o **"Reativar" continua** (senão o selo "Inativo" ficaria preso para sempre). O card do
inativo é **cinza de verdade** (fundo/borda cinza, sem sombra, `grayscale` nos emojis) com selo **"INATIVO"** em
pílula cinza-escura de texto branco; o `opacity` no card inteiro foi abandonado porque apagava também os
**botões**, que precisam continuar legíveis. Suíte: **188 testes OK** (173 + 15).
Conferido em 380/520/1400px com sonda: **zero overflow**; a captura pegou um defeito já corrigido — o selo
"Inativo" no `.evento-topo` (flex de 3 itens) **espremia o nome do evento**, e foi para o `.evento-meta`, que
quebra linha. Antes: cookies de sessão/CSRF só por HTTPS.

**Anterior (Cookies de sessão/CSRF só por HTTPS):** `SESSION_COOKIE_SECURE` e
`CSRF_COOKIE_SECURE` não estavam definidos e o cookie saía **sem a flag `Secure`** — confirmado em produção
com `curl`. O 301 do Nginx **não protege**: quando ele chega, o cookie já foi enviado em texto puro na
requisição `http://`. Ambos agora são `not DEBUG` (em `http://127.0.0.1` o navegador não guarda cookie
`Secure` e o login local quebraria). **`SECURE_SSL_REDIRECT` fica desligado de propósito** — quem redireciona
é o Nginx, antes do Django; ligar duplicaria e arriscaria laço, e o aviso `security.W008` do `check --deploy`
é **esperado**. Novo `SegurancaCookiesTests` (4 testes) trava os dois lados (produção exige, desenvolvimento
não), mais o `SECURE_PROXY_SSL_HEADER` — sem ele o Django não reconhece HTTPS e nem mandaria o cookie.
**Pendente:** `SECURE_HSTS_SECONDS` (HSTS mal configurado é irreversível por meses; começar baixo e sem
`includeSubDomains`) e a **divergência de ambiente** — produção roda **Django 5.2.15 / Python 3.12.3** e a
máquina de desenvolvimento **6.0.5 / 3.14.3**; no VPS **cada app tem venv própria** (de 5.2.11 a 6.1 lado a
lado, sem Django no Python do sistema), então o certo é **igualar o local**, não mexer no servidor.
Antes: formas de pagamento por evento.

**Anterior (Formas de pagamento online por evento):** o Diretor escolhe, **por
evento**, o que o site aceita — **só Pix**, **só cartão** ou **os dois** (padrão). Novo campo
`Evento.formas_pagamento_online` (migration **0062**) na aba de configuração da inscrição do painel do evento.
Vale para a **inscrição** e para a **lojinha** daquele evento; o **PDV/balcão não muda** (lá o operador segue
com dinheiro, cortesia etc., variável `formas`). Os rádios do `evento_inscrever.html` eram **chumbados** e
agora iteram `formas_pagamento`; a lojinha já iterava. A validação é **no servidor**
(`Evento.aceita_forma_online`) — esconder o rádio não impede POST forjado, e há teste de regressão disso. Na
inscrição, forma não permitida **cai na 1ª liberada** em vez de usar o antigo `or "pix"` fixo, que num evento
só-cartão cobraria pelo caminho desligado. A lista canônica `FORMAS_PAGAMENTO_ONLINE` **saiu da `views.py`
para a `models.py`** (o model precisa dela para filtrar; duas cópias divergiriam). Como o padrão é `ambos`,
**nenhum evento existente muda de comportamento**. Suíte: **169 testes OK** (161 + 8). Antes: abas de
Aniversários.

**Anterior (Aniversários: abas com o padrão visual do projeto):** as abas eram
**links sublinhados soltos** — nasceram com as classes `abas`/`aba`/`aba-ativa`, que **não existiam em CSS
nenhum** (inventadas na criação da tela). Refeitas no mesmo padrão de `loja.css`/`mensalidades.css`: trilho com
fundo suave, pílula de **44px** (alvo de toque), **ativa em gradiente azul** com sombra e **badge** verde de
contagem — total de aniversariantes, mensagens ligadas (`n/3`) e envios do ano (`ativos_qtd`/`envios_qtd` no
contexto). A aba ativa leva `aria-current="page"` e o link da lista **preserva o mês selecionado**. No celular
(≤480px) o **rótulo some** e fica ícone + badge — três abas com texto não cabem lado a lado —, mas a **ativa
mantém o nome** para não virar adivinhação de ícone. Novo teste confere que **toda classe usada no HTML existe
no CSS** (é o defeito que passou: classe sem estilo e sem ninguém reclamando) + teste do `aria-current`.
Suíte: **161 testes OK**. Conferido em 1400px e 520px. Antes: cards desalinhados no desktop.

**Anterior (Aniversários: cards desalinhados no desktop):** no desktop os cards
tinham **larguras diferentes** — "É hoje!" ia até a borda e "Agosto"/"Faltando data" paravam em 640px. Causa:
**`.wa-card { max-width: 640px }`**, herdado da tela do WhatsApp (onde os cards são formulários e a largura
menor é proposital); o card "É hoje!" usa `card aniv-hoje`, **sem** `wa-card`, e por isso era o único sem o
limite. Corrigido com a classe **`.aniv-largo { max-width: none }`** nos três cards de lista/tabela; os
**formulários da aba ✏️ continuam em 640px** (texto longo é mais legível em coluna estreita), por isso um
modificador explícito em vez de zerar o `max-width` da tela toda. Medido com sonda: os dois cards agora em
**980px**. Suíte: **159 testes OK**. *Nota de método:* o defeito estava na captura revisada na véspera e passou
batido a olho — comparar **números** (largura de cada card) é o que pega. Antes: responsividade + 3 correções.

**Anterior (Aniversários: responsividade + 3 correções achadas na verificação
visual):** revisão de tela em 8 larguras (485→1920) com Chrome headless e uma **sonda de overflow** (compara
`scrollWidth` com `clientWidth` e lista quem estoura). Resultado final: **zero overflow em todas**, botão com
**40px** de altura (alvo de toque). CSS reescrito em **3 faixas**: ≥760px tudo numa linha; 560–760 nome/idade/
detalhe empilham com o botão à direita; <560px empilha tudo, com pílulas de mês ocupando a largura e botão de
largura mínima; extra ≤380px reduzindo paddings. `minmax(0, 1fr)` + `overflow-wrap:anywhere` no nome e no
detalhe — sem isso um nome comprido empurra a grade e cria rolagem horizontal na página inteira. **Três bugs
que só apareceram na captura:** (1) **comentário de template vazando como texto** — `{# ... #}` do Django é de
**UMA linha**; escrito em várias, virava conteúdo visível em cada linha da lista. O mesmo erro estava no
seletor de canal da cobrança (de 31/07), também corrigido; ambos agora usam `{% comment %}` e há **teste de
regressão** varrendo `{#`/`#}` no HTML de 3 telas. (2) **A lista do mês não tinha botão de envio** — o include
só havia entrado na lista "É hoje". (3) A nota de perfil duplicado mostrava a **chave técnica**
("responsavel") em vez do rótulo ("Responsável"). Suíte: **159 testes OK**. Antes: Aniversários — disparo
automático + envio manual.

**Anterior (Aniversários: disparo automático + envio manual):** fecha o módulo.
Cada perfil ganhou **canais** (`enviar_whatsapp`/`enviar_email` no `TemplateAniversario`) e o envio saiu do
papel. (1) Novo model **`EnvioAniversario`** (migration **0061**) — é a **trava**: `UniqueConstraint(chave, ano,
canal)` **condicionada a `ok=True`**, então a pessoa recebe **no máximo uma vez por ano em cada canal**, não
importa se o cron rodou duas vezes ou se alguém clicou no manual depois do automático. **Falha não ocupa a
trava** (senão um erro de rede queimaria o aniversário até o ano seguinte) e pode ser retentada. Reenvio
forçado usa `update_or_create` — atualiza a linha existente em vez de estourar a constraint. (2) Motor
**`_enviar_aniversario`**: aniversário **não é transacional** (o clube é quem inicia), então passa pelos
**dois gates** — WhatsApp por `_pode_notificar` (anti-bloqueio da W-API) e e-mail por
`_enviar_email(transacional=False)`, que respeita descadastro/bounce e leva o `List-Unsubscribe`. Um canal
barrado **não impede o outro**. `forcar=True` refaz o envio mas **não fura os gates**. (3) **Botão "📤 Enviar"
por pessoa** (AJAX) na lista, com selos `💬 ✓`/`✉️ ✓` de quem já recebeu e confirmação no reenvio.
(4) Comando **`enviar_aniversarios`** para cron diário, com `--dry-run`, `--pausa` e **10s entre cada pessoa**.
(5) Nova aba **📬 Envios** com o histórico (sucesso e falha, manual × automático). Suíte: **158 testes OK**
(138 + 20). **Operacional:** agendar o cron (ver `DEPLOY_VPS.md`) e ligar as mensagens na aba ✏️ — todas
nascem desligadas. Antes: Novo módulo Aniversariantes.

**Anterior (Novo módulo: 🎂 Aniversariantes):** item de menu novo (só Diretor) com
duas abas. **🎈 Aniversariantes** — lista única dos **três perfis** (aventureiro, responsável e diretoria) com
dia/mês, idade que completa e de onde a pessoa vem; seletor de mês com contagem por mês + "Ano todo", destaque
**"É hoje!"** e ordenação por dia. **✏️ Mensagens** — um texto por perfil (`TemplateAniversario`, migration
**0060**), com assunto, alavanca de ativo e os marcadores `{nome}`/`{nome_completo}`/`{idade}`; nasce com texto
padrão e **desligado**. **O disparo automático ainda NÃO existe** — esta etapa é a consulta + os textos.
Pontos de desenho: (1) **deduplicação por pessoa** — o mesmo adulto costuma ser diretoria **e** responsável, e
receberia duas mensagens; a chave é CPF → WhatsApp → nome normalizado, e a prioridade é **diretoria >
responsável** (a tela mostra "também é responsável"); mãe de dois filhos também aparece **uma vez**. (2) O
**aventureiro tem chave própria (`av:<id>`)**, nunca a de pessoa: a criança usa o telefone/e-mail do
responsável e seria engolida por ele na deduplicação — bug pego na verificação visual, com teste de regressão.
(3) **29/02 cai em 28/02** para não sumir do calendário em ano comum. (4) Só entra gente **ativa e não-demo**.
**Dado que faltava:** o cadastro nunca pediu data de nascimento de pai/mãe/responsável — foram criados
`pai_data_nascimento`/`mae_data_nascimento`/`resp_data_nascimento` (opcionais) e o campo do responsável entrou
em **Meus Dados → Editar responsável**; a tela mostra um card **"⚠️ Faltando data de nascimento"** contando
quem fica de fora. Cobertura hoje em produção: aventureiros **35/35** e diretoria **10/10** já têm data;
**responsáveis começam em zero**. Suíte: **138 testes OK** (118 + 20). Antes: Acerto público deixa de cobrar
inativo.

**Anterior (Acerto público deixa de cobrar inativo):** a regra do clube é
**aventureiro inativo não é cobrado**, mesmo com mês em aberto. A cobrança (`_cobrancas_familias`), o painel do
Diretor (total `aberto`), a área do responsável e o Financeiro já filtravam `aventureiro__ativo=True` — mas a
**página pública de acerto** (o link do WhatsApp de cobrança, token permanente) **não**: ela listava e pedia
pagamento da dívida de quem já saiu. Corrigido em `_mensalidades_abertas_familia` + 2 testes (inativo não
aparece / família só com inativo vê "Tudo em dia"). A regra virou convenção explícita no `CLAUDE.md`, com a
lista dos pontos onde o filtro precisa existir — **pagas contam sempre**, só o "em aberto" de inativo é
ignorado. Produção: 4 inativos, 1 deles com **R$ 240,00** em 8 mensalidades abertas (já invisível na cobrança e
nos totais; agora também no acerto). Optou-se por **filtrar** em vez de marcar isento: aplica a regra sozinho,
sem ação manual a cada desligamento e sem reescrever histórico. Sem migration. Suíte: **118 testes OK**.
Antes: WhatsApp — resposta da autorização com log e retry.

**Anterior (WhatsApp: resposta da autorização com log e retry):** fecha a pendência
aberta em 14/07. A confirmação automática da autorização era **disparo único dentro de `try/except: pass`**,
ignorando o retorno de `_enviar_whatsapp` — bastava uma instabilidade da W-API para a pessoa autorizar e
**nunca** receber resposta, sem log e sem nova tentativa (foi o que aconteceu num caso real, descoberto só na
investigação). Agora: novo campo **`PerfilUsuario.confirmacao_autorizacao_em`** (migration **0059**) marca
quando a confirmação **saiu com sucesso**; autorizado com o campo vazio = **pendente**, e a **próxima mensagem
da pessoa tenta de novo**. O envio saiu do fluxo principal para o helper **`_confirmar_autorizacao`**, que
confere o retorno, **loga** a falha (`logger.warning`, em vez de engolir), só marca quando a W-API confirma e
nunca levanta exceção (roda dentro do webhook). Dois cuidados de compatibilidade: (1) a migration tem
**backfill** — quem já estava autorizado é marcado como já confirmado, senão a próxima mensagem de **todos**
dispararia uma segunda resposta; (2) a **marcação manual** ("✓ Marcar autorizado") passa a fechar a pendência
junto, porque quem autorizou por fora não deve receber a confirmação do nada depois. Suíte: **116 testes OK**
(107 + 9). Antes: DEPLOY_VPS — conhecimento operacional.

**Anterior (DEPLOY_VPS: conhecimento operacional do servidor):** só documentação,
sem código. Registrado no `docs/DEPLOY_VPS.md` o que custou tempo descobrir nesta sessão: (1) **os dois atalhos
de deploy parecidos** — `pinhaljunior2-deploy` (este sistema, `/var/www/pinhaljunior2`, porta 8010) × 
`pinhaljunior-deploy` **sem o "2"** (sistema antigo, `/srv/sitepinhal`, porta 8000), cujo uso por engano
**reativa o `sitepinhal.service`** que deve ficar parado; (2) o VPS **é compartilhado por 11 aplicações
Django** (lista + domínios) com **1 vCPU, 3,8 GB e sem swap** — não mexer em serviço de outro projeto, e
`reboot` derruba os 11; (3) **dependências que expiram sem alerta** (assinatura da W-API → 403; sessão do
WhatsApp → 401 pede QR de novo; senha de app do Gmail), com o comando de diagnóstico da W-API que envia para o
próprio número do clube; (4) **bloqueio em rede corporativa (FortiGate)** — domínio novo tende a cair como não
classificado; conserto é a reclassificação no FortiGuard, e o paliativo que cobre todos os perfis é
*Web Rating Overrides*, não a lista de URLs; (5) aviso de que o deploy só traz o que já está no GitHub (se
`Commit anterior == Commit atual`, faltou o push). Antes: Cobrança — opção "Ambos".

**Anterior (Cobrança: opção "Ambos" (WhatsApp + e-mail)):** o seletor de canal da
aba Cobranças ganhou **💬+✉️ Ambos** — um clique manda pelos dois canais, cada um com as suas regras. `CANAL_AMBOS`
é opção de **envio**, não valor gravável: cada mensagem que sai vira um `CobrancaEnviada` do canal real, então a
contagem por canal continua exata. Pontos do desenho: (1) a mensagem é montada **uma vez por família** e reusada
nos dois canais — com o modo IA ligado, gerar por canal dobraria o custo e mandaria textos diferentes para a
mesma pessoa (há teste); (2) com o filtro **"só quem não recebeu este mês"**, em "ambos" a família recebe **só
pelo canal que falta** — quem já foi cobrada por WhatsApp leva só o e-mail, sem duplicar; (3) cada canal mantém
o seu gate — o e-mail respeita descadastro/bounce e, se barrar, o WhatsApp **ainda sai** (a falha entra na lista
com o motivo); (4) se **um** dos canais não estiver configurado o lote **não aborta** — segue pelo outro; só
recusa se nenhum estiver. O filtro "só quem já me mandou mensagem" continua exclusivo do WhatsApp e, em "ambos",
não exclui a família (senão barraria também o e-mail). A resposta agora traz `por_canal`, e o badge da linha
mostra `💬 n · ✉️ n`. Sem migration. Suíte: **107 testes OK** (99 + 8). Antes: correção do seletor de canal.

**Anterior (Correção: seletor de canal disparava a troca de telefone):** o
`<select>` "Enviar por" da aba Cobranças nasceu com a classe **`mens-cob-tel-sel`**, que é o gancho do handler
que troca o **telefone de cobrança da família** — então só de mudar o canal o front disparava um POST indevido
(com `usuario_id=undefined`) e mostrava erro na tela, sem o Diretor ter clicado em enviar nada. Corrigido nos
dois lados: classe própria **`mens-cob-canal-sel`** no template (a causa) e o handler passou a exigir
`data-usuario` no elemento (proteção contra outro `<select>` herdar a classe). CSS do seletor herdado + destaque.
Teste de regressão conferindo a classe da tag. Suíte: **99 testes OK**. *Diagnóstico do mesmo período (não é
código):* a instância da W-API estava com **assinatura vencida** (403) e depois **desconectada** (401), o que
derrubava toda cobrança por WhatsApp; após renovar e parear, envio real validado (218 grupos). Antes: E-mail —
extrato dos últimos envios.

**Anterior (E-mail: extrato dos últimos envios):** a tela `/email/` ganhou o card
**📬 Últimos envios** — antes só havia contador agregado, e ao ligar as notificações não dava para saber **o
que** saiu, para quem e por que falhou. Novo model **`LogEmail`** (migration **0058**): destinatário, assunto,
`origem` (tipo da notificação / `cobranca` / `teste`), `ok`, `detalhe` e data; mantém as últimas **200** linhas
(apara em lote, não a cada envio) e o **corpo NÃO é gravado** (evita acumular dado pessoal — há teste
garantindo). `LogEmail.registrar` nunca levanta exceção. Grava tanto o **sucesso** quanto a **falha**, e também
o que foi **barrado pelo gate** (descadastro/bounce) — com o motivo em português, para o descadastro não sumir
em silêncio. A propriedade `rotulo_origem` traduz a origem usando o rótulo do próprio `TEMPLATES_NOTIFICACAO`.
`email_envio.enviar` e `_enviar_email` ganharam `origem=`. Suíte: **98 testes OK** (90 + 8). Nota de operação:
o campo **`Reply-To` deve ficar vazio** para as respostas caírem na própria conta de envio (sem ele, a resposta
vai para o `From`); e a cobrança já envia **1 por requisição com 10s entre cada** nos **dois** canais (o pacing
está no JS, não no canal). Antes: Notificações por e-mail — Etapas 3 e 4.

**Anterior (Notificações por e-mail — Etapas 3 e 4: fan-out + cobrança):**
o e-mail passou a **sair de verdade**. (1) **`_notificar` virou fan-out**: renderiza o texto **uma vez** (a IA,
quando ligada, é chamada 1× por notificação) e despacha para os canais marcados no template — cada um com o seu
gate (WhatsApp = `_pode_notificar`, e-mail = `_pode_enviar_email`). Assinatura ganhou `email=`; retorna o
resultado por canal (`"whatsapp:enviado email:descadastrado"`). Sem número **e** sem e-mail nem chega a
renderizar (`sem_canal`), o que evita chamada de IA à toa. (2) **`texto_para_email`** tira o `*negrito*` do
WhatsApp (só `*...*`; `_` e `~` aparecem em endereços e dariam falso positivo) — o mesmo texto serve aos dois
canais sem manter duas versões. (3) **Os 5 gatilhos passam o e-mail**: cadastro (aventureiro e diretoria),
mensalidade paga, inscrição em evento, compra na loja e o aviso interno da diretoria. Helper **`_email_familia`**
(par do `_whatsapp_familia`). (4) **Cobrança por e-mail** com **seletor de canal** na aba Cobranças. O
bloqueante era o `CobrancaEnviada` não distinguir canal — ganhou o campo **`canal`** (default `whatsapp`, então
o histórico antigo continua correto) e a contagem/filtro "só quem não recebeu este mês" passou a ser **por
canal** (`cobrado_mes_whatsapp`/`cobrado_mes_email`). Cobrança **não é transacional**: vai com
`transacional=False`, ou seja, respeita descadastro, leva `List-Unsubscribe` e é barrada por bounce; o motivo
volta legível na tela (`_MOTIVO_EMAIL`). Novo `ConfigMensalidade.assunto_cobranca_email` (padrão
**`ASSUNTO_COBRANCA_PADRAO`**, deliberadamente sem caixa alta/"!"/"URGENTE" — gatilho de spam). O pacing de
**10s entre cada** e o 1-por-request já existiam no JS e valem para os dois canais; o filtro "só quem já me
mandou mensagem" só se aplica ao WhatsApp (no e-mail o gate é outro). Migration **0057**. Suíte: **90 testes
OK** (72 + 18). Também corrigido em produção o único e-mail inválido da base (um `pai_email` com o domínio
digitado pela metade): **0 e-mails inválidos** agora. **Feature completa** — falta só
ligar cada notificação na tela. Antes: Notificações por e-mail — Etapa 2.

**Anterior (Notificações por e-mail — Etapa 2: canal por notificação +
camada anti-spam):** o canal de e-mail ganhou **consentimento** e cada notificação passou a escolher por onde
sai. **Ainda não dispara nada** — a Etapa 3 liga os gatilhos. (1) `TemplateNotificacao` += **`enviar_whatsapp`**
(nasce `True`, é como sempre funcionou), **`enviar_email`** (nasce `False`) e **`assunto`**; a aba 🧩 Templates
ganhou o bloco "Por onde enviar" (2 checkboxes) + campo de assunto por notificação. Os 5 tipos ganharam
**assunto padrão** (6º item da tupla de `TEMPLATES_NOTIFICACAO`); `get_tipo` preenche o assunto também em
templates **já existentes** que estejam sem. (2) Novo model **`ContatoEmail`** — o análogo do `ContatoWhatsapp`,
mas para o risco de **spam**, não de bloqueio da API: `descadastrado_em`, `bounce_em`/`bounce_motivo`,
contador e `token` de descadastro. Método `pode_receber(transacional)` com a regra: **bounce bloqueia tudo;
descadastro bloqueia só o que não é comprovante**. (3) Gate **`_pode_enviar_email`** + ponto único
**`_enviar_email`** (espelham `_pode_notificar`/`_notificar`; `forcar=True` fura o descadastro mas **nunca** o
bounce). (4) **Descadastro público** `/descadastrar/<token>/` (`@csrf_exempt` por causa do POST One-Click do
Gmail, RFC 8058) — página com confirmação e **reversível**. (5) `email_envio.enviar` ganhou `contato=` e
`transacional=`: monta o cabeçalho **`List-Unsubscribe` + `List-Unsubscribe-Post`** (o que faz Gmail/Outlook
mostrarem "Cancelar inscrição"), **`Reply-To`**, **rodapé de identificação** em todo e-mail e a linha de saída
só nos não-transacionais; e **marca bounce** automaticamente em recusa 5xx — falha 4xx/conexão **não** suprime
(problema nosso, não do endereço). (6) `EmailConfig` += `reply_to`, `site_url` (base do link de descadastro; as
notificações saem em thread, sem `request`) e `rodape`; card "🛡️ Proteção contra spam" na tela com o painel de
descadastrados/recusados. Migration **0056**. **Autenticação já resolvida** de graça: como o remetente é
`@gmail.com`, SPF/DKIM/DMARC passam pelo Google (só precisaria de DNS se trocar para o alias
`@pinhaljunior.com.br`). **Validação da base** (só DNS, nada enviado): 62 endereços distintos, **59 em domínios
saudáveis**; problemas = 1 digitação (um `pai_email` com o domínio pela metade) e 2× um endereço
`@example.com` (null MX, registros de teste). Suíte: **72 testes OK** (45 + 11 + 16). Próximo:
Etapa 3 (ligar os 5 transacionais); depois Etapa 4 (cobrança/lembrete, com canal no `CobrancaEnviada` e
pacing). Antes: Notificações por e-mail — Etapa 1.

**Anterior (Notificações por e-mail — Etapa 1: base + tela):** começou o
**segundo canal de notificação**, ao lado do WhatsApp. Esta etapa é só a **infraestrutura — nada dispara por
e-mail ainda**. (1) Novo model **`EmailConfig`** (singleton `get_solo`, migration **0055**): servidor SMTP,
porta, segurança (STARTTLS/SSL/nenhuma), conta, **senha de app** (mascarada, só troca quando uma nova é
digitada — mesmo padrão do token da W-API e da chave da IA), nome do remetente e contador
`enviados`/`falhas`/`ultimo_envio_em`/`ultimo_erro`. (2) **`core/email_envio.py`** — cliente de envio com
`django.core.mail` (**nativo, sem dependência nova**, diferente das outras integrações que usam `urllib`); monta
a conexão SMTP a partir do `EmailConfig`, **não** do settings; `enviar(config, destino, assunto, corpo)` devolve
`(ok, detalhe)` no mesmo contrato do `_enviar_whatsapp`, nunca levanta exceção e traduz as falhas comuns de SMTP
para mensagens acionáveis. Remove os espaços da senha de app (o Gmail a exibe em grupos de 4). (3) Novo módulo
**✉️ E-mail** (`/email/`, só Diretor, em `ITENS_MENU`): configuração + **envio de teste** (AJAX) + card de envios
com zerar contador. Rotas `/email/config|testar|zerar/`; template `core/email.html` e `static/js/email.js`
espelhando o módulo de IA; reusa `whatsapp.css` (sem CSS novo). (4) Helper **`_email_do_usuario`** — resolve o
melhor e-mail conhecido na ordem conta de login → ficha da diretoria → **`resp_email`** do aventureiro (a conta
de login quase nunca tem e-mail: **1 de 43**; já o `resp_email` está preenchido em **100%** das famílias).
**Validado em produção**: SMTP do Gmail autentica, o VPS alcança `smtp.gmail.com` nas portas 587/465/25 e o envio
real pelo código novo chegou à caixa. Suíte: **56 testes OK** (45 + 11 novos). Próximo: canal por notificação no
`TemplateNotificacao` (Etapa 2). Antes: WhatsApp/Liberação — marcar autorizado manualmente.

**Anterior (WhatsApp/Liberação: marcar autorizado manualmente):** cada linha
não-autorizada (com conta) da aba **🚦 Liberação** ganhou o botão **"✓ Marcar autorizado"** — para quem
autorizou por fora (ligação/presencial) ou cuja mensagem não chegou ao webhook (o "caso 2" do diagnóstico
anterior). Ao clicar,
marca a conta como **autorizada** e grava a **data da última mensagem** (como se tivesse escrito) tanto no
`PerfilUsuario` (termômetro fica verde) quanto no **`ContatoWhatsapp`** — que é a fonte do gate
`_pode_notificar`, então a pessoa passa a **receber as notificações automáticas** de verdade. Só preenche o que
está vazio (não sobrescreve contato real mais recente). AJAX, atualiza a linha na hora (pill verde + "há
instantes"), só Diretor. Peças: view `whatsapp_liberar_view` + rota `whatsapp/liberar/`; botão `.wa-lib-liberar`
em `whatsapp.html`; handler em `whatsapp.js` (delegação); CSS em `whatsapp.css`. Reusa `_numero_do_contato`.
Sem migration. Suíte: 45 testes OK. Antes: WhatsApp/Liberação — busca inteligente.

**Anterior (WhatsApp/Liberação: busca inteligente):** a aba **🚦 Liberação** ganhou
um **campo de busca ao vivo** — começa a digitar e a lista de responsáveis/diretoria filtra na hora, por **nome**
(ignora acento/caixa) ou por **número** (dígitos). Mostra contador "N de M", "nenhum contato encontrado" quando não
há match e **Esc** limpa. Filtro 100% no front (JS puro, sem request), sobre a lista já renderizada. Arquivos:
`templates/core/whatsapp.html` (input `#waLibBusca` + `#waLibSemResultado`), `static/js/whatsapp.js` (índice
pré-computado nome+dígitos por linha e `input`/`keydown` handlers) e `static/css/whatsapp.css` (`.wa-lib-busca*`).
Sem migration. Suíte: 45 testes OK. Contexto: veio de diagnóstico da resposta automática de autorização —
**caso 1**: mensagem chegou/autorizou mas a resposta de confirmação **falhou em silêncio** (envio transitório
engolido por `except: pass`, sem retry) — reenviada manualmente; **pendência de robustez** (logar falha + retry
idempotente) **ainda não implementada** *(feita depois, em 01/08, com a migration `0059`)*. **Caso 2**: **nenhum**
rastro de entrada no webhook (nem `ContatoWhatsapp`) — a mensagem nunca chegou ao clube; não é bug de código.
*(Identificação das pessoas removida: o repositório é público.)* Antes: Revisão geral — parte 4.

**Anterior (Revisão geral — parte 4: responsividade mobile):** fecha a revisão.
(1) **Alvos de toque** aumentados para ~40px: `.ordem-btn` (reordenar campos), `.entrega-btn` (baixa de
entrega no evento) e `.loja-kit-remover` (remover item do carrinho). (2) As **3 tabelas da aba Vendas** da
Loja (`loja.html`) ganharam wrapper `.tabela-scroll` (rolagem horizontal em telas estreitas, como já fazia o
painel do evento). (3) **Salvaguarda global `img { max-width: 100% }`** em `base.css` (nenhuma imagem estoura
a largura no mobile). (4) No mobile, os campos **valor/estoque** da linha de variação da Loja deixam de ter
largura fixa (110px) e fluem (media ≤560px, espelha o `eventos.css`). Só CSS/HTML. Suíte: 45 testes OK.
**Revisão geral concluída** (partes 1-4: gate + críticos, robustez WhatsApp, performance, mobile). Antes:
Revisão parte 3.

**Anterior (Revisão geral — parte 3: performance):** (1) **`_foto_valida`** não
faz mais `storage.exists()` (stat de disco) por aventureiro — confia no campo e o template trata arquivo
ausente com `onerror` (grande ganho em Usuários/Presença; adicionado `onerror` na foto da diretoria em
inicio.html). (2) **`presenca_view`**: um `annotate(Count("presencas"))` em vez de um `COUNT` por evento.
(3) **`whatsapp_view`**: `_liberacao_lista()` computada **uma vez** e passada a `_inativos_para_reengajar`
(antes rodava 2× por request). (4) **`mensalidades_view`**: `ConfigMensalidade.get_solo()` chamada 1× (antes
5×). (5) **`_loja_relatorio`**: itens materializados uma vez (dois loops reusam a lista). (6) **Índices** novos
(migration **0054**): `Aventureiro.ativo/demo`, `Pagamento.status/tipo`, `Mensalidade.ano/status`. Suíte: 45
testes OK. **Pendente (recomendação, não feito):** `static/img/logo.png` tem 448 KB (servido em toda página)
e `logo_original_backup.png` (1,7 MB) é backup morto dentro de `static/` — otimizar/mover exige sua
confirmação (binários). Próximo: mobile. Antes: Revisão parte 2.

**Anterior (Revisão geral — parte 2: robustez das notificações):** (1) as
notificações automáticas passam a ser enviadas em **thread daemon** (`_em_thread`, fire-and-forget) dentro
do `on_commit` — a chamada HTTP do WhatsApp/OpenAI (até ~20s cada; o aviso interno percorre vários
diretores) **não bloqueia** mais o request nem o webhook do Mercado Pago (evita timeout → reenvio). O
thread fecha a própria conexão de banco e loga erros. (2) O **reconhecimento da autorização** passou a ser
**match exato** (normalizado) em vez de substring — evita que uma "mensagem de autorização" curta (ex.:
"autorizo") seja disparada por qualquer texto que a contenha. Nota: a cobrança/reengajamento em lote já são
**1-por-request** com pausa de 10s no front (não bloqueiam). Suíte: 45 testes OK. Próximo: performance e
mobile. Antes: Revisão parte 1.

**Anterior (Revisão geral — parte 1: gate transacional + críticos de produção):** a partir de uma auditoria geral. (1) **Gate das notificações**: as notificações
**transacionais** (compra na loja, mensalidade paga, boas-vindas, inscrição) agora **enviam sempre** —
são resposta direta a uma ação da própria pessoa, com o número que ela forneceu (baixo risco de bloqueio);
o filtro anti-bloqueio (`_pode_notificar`) fica reservado a avisos não solicitados/futuros. Conjunto
`NOTIF_TRANSACIONAIS`; o bloco pré-checkout do evento aberto foi reescrito para convidar a "avisos futuros"
(a confirmação já vem sempre). (2) **Webhook do Mercado Pago** agora tem `try/except` de topo (loga e
responde 500 sem traceback; nunca vaza erro). (3) **Idempotência do pagamento**: `_aprovar_pagamento` faz um
**claim atômico** (`UPDATE ... WHERE finalizado=False`) — webhooks duplicados/concorrentes do MP não criam
mais compra/inscrição em dobro nem baixam estoque duas vezes (validado: 3 aprovações → 1 finalização).
(4) **`cadastro_aventureiro_view` atômica** (não deixa User órfão se salvar o aventureiro falhar). (5)
**`DEBUG` seguro**: sem a env `DJANGO_DEBUG`, liga só quando não há `ALLOWED_HOSTS` (dev local); produção
fica `DEBUG=False` mesmo se esquecerem a variável. Suíte: 45 testes OK. **Operacional:** confirmar
`DJANGO_SECRET_KEY` setada no `/etc/pinhaljunior2.env` do VPS. Próximo: robustez WhatsApp (envio em lote em
background, match de autorização estrito), performance e mobile. Antes: Notificações — Etapa 5.

**Anterior (Notificações automáticas por WhatsApp — Etapa 5: inscrição + autorização pré-checkout):** fecha a feature. (A) Toda **inscrição em evento** (ponto único
`_criar_inscricao_de_payload`, grátis/imediata e paga via MP) manda uma **confirmação** ao responsável
(`inscricao_evento`, `{nome}/{evento}/{total}/{codigo}`, via `on_commit`, respeita o gate). (B) Na página de
inscrição de **evento aberto ao público**, quando o WhatsApp está configurado e a notificação de inscrição
está ativa, aparece um **bloco "Autorizar no WhatsApp"** (contexto `mostrar_autorizar`/`link_autorizar`,
usa o link curto `/autorizar/`) — assim o inscrito desconhecido **se libera antes do checkout** e o gate
deixa a confirmação passar. CSS `.notif-autorizar` em eventos.css. Sem migration. **Feature completa**: as
5 notificações (loja compra/pedido, mensalidade paga, cadastro, inscrição) configuráveis na aba 🧩
Templates, com gate anti-bloqueio via `ContatoWhatsapp` e alavanca IA×texto por notificação. Suíte: 45
testes OK. Antes: Etapa 4 (novo cadastro).

**Anterior (Notificações automáticas por WhatsApp — Etapa 4: novo cadastro):**
todo cadastro que **cria uma conta nova** — de **aventureiro** (`cadastro_aventureiro_view`) e de
**diretoria** (`cadastro_diretoria_view`, exceto quando emenda no aventureiro, que envia a de aventureiro) —
dispara uma **boas-vindas** (`cadastro_novo`) com o **usuário de acesso** (`{usuario}`), ao WhatsApp do
responsável/integrante, via `on_commit`. Respeita o gate anti-bloqueio (chega a quem já escreveu ao clube;
o cadastro de novo aventureiro em conta já existente **não** notifica). Helper `_notificar_cadastro`. Sem
migration. Próximo: inscrição em evento + autorização pré-checkout no evento aberto (Etapa 5). Antes: Etapa
3 (Mensalidade paga).

**Anterior (Notificações automáticas por WhatsApp — Etapa 3: Mensalidade
paga):** todo **pagamento de mensalidade** dispara um **agradecimento** ao responsável (`mensalidade_paga`,
respeita o gate anti-bloqueio) — tanto o online (baixa múltipla em `_finalizar_mensalidade`, via
`on_commit`) quanto a **baixa manual** do Diretor (`mensalidade_pagar_view`). O número é o do **responsável
financeiro** (reusa `_resolver_origem_numero` + `cobranca_whatsapp_origem`), o nome é o do responsável e os
`{itens}` listam as competências pagas (ex.: "Mensalidade Jul/2026"). Helpers `_whatsapp_familia`,
`_rotulo_mensalidade`, `_notificar_mensalidade_paga`. Sem migration. Próximo: novo cadastro (Etapa 4).
Antes: Etapa 2 (Loja).

**Anterior (Notificações automáticas por WhatsApp — Etapa 2: Loja):** ligado o
1º gatilho. Toda **compra da Loja do Clube** (ponto único `_criar_compra_loja`, tanto o fluxo pago via
Mercado Pago quanto o simulado) agora dispara, **após o commit** (`transaction.on_commit`, não trava/derruba
a transação do webhook): (1) **confirmação ao comprador** (`loja_compra`, respeita o gate anti-bloqueio) e
(2) **aviso interno** (`loja_pedido`, `forcar=True`) aos integrantes da diretoria marcados na aba Templates,
para providenciar os materiais. Helpers `_notificar_compra_loja` e `_whatsapp_membro_diretoria`. Sem
migration. Próximo: Mensalidade paga (Etapa 3). Antes: Etapa 1 (base + aba Templates).

**Anterior (Notificações automáticas por WhatsApp — Etapa 1: base + aba
Templates):** começou o sistema de **notificações automáticas por WhatsApp**. Esta etapa é só a
**infraestrutura** (nada dispara ainda): (1) o webhook passa a gravar **TODO número** que escreve ao clube
(cadastrado ou não) em **`ContatoWhatsapp`** (nome, 1ª/última msg, contagem, `autorizou_em`) — é a lista
consultada antes de cada envio; (2) helpers reutilizáveis **`_pode_notificar`** (gate anti-bloqueio: só
envia a quem **autorizou** OU mandou msg dentro de `WhatsappConfig.notificar_janela_dias`, padrão 60),
**`_render_notificacao`** (texto do sistema **ou** IA com prompt, reusa `openai_ia`+`registrar_uso`) e
**`_notificar`** (ponto único de envio, com o gate; `forcar=True` só p/ avisos internos); (3) nova aba
**🧩 Templates** na tela WhatsApp que configura as **5 notificações** (`loja_compra`, `loja_pedido` [aviso
interno], `mensalidade_paga`, `cadastro_novo`, `inscricao_evento`) — por notificação: liga/desliga,
alavanca **IA×texto do sistema** (com prompt), marcadores próprios e, no aviso interno, **checklist da
diretoria** que recebe. Model `TemplateNotificacao` + `TEMPLATES_NOTIFICACAO` (textos/prompts padrão);
view `whatsapp_templates_view`; rota `whatsapp/templates/salvar/`; migration **0053**. Filtro
anti-bloqueio **sempre aplicado**. Próximo: ligar os gatilhos (Loja/Mensalidade/Cadastro/Inscrição +
autorização pré-checkout no evento aberto). Antes: Virada do VPS para o domínio raiz.

**Anterior (Virada do VPS para o domínio raiz):** o **sistema novo** agora atende em
**`https://pinhaljunior.com.br/`** no VPS. A instalação em `/var/www/pinhaljunior2` continua a mesma
(`pinhaljunior2.service`, Gunicorn em `127.0.0.1:8010`), mas o Nginx passou a apontar a **raiz `/`**,
`/static/` e `/media/` para ela; o `DJANGO_FORCE_SCRIPT_NAME=/sistema-novo` foi removido do env de produção e
as URLs públicas viraram **`/static/`** e **`/media/`**. A rota antiga **`/sistema-novo/`** foi mantida
temporariamente por compatibilidade, com rewrite para a raiz antes do proxy. O sistema antigo
**`sitepinhal.service`** foi **parado e desabilitado**, e ficou arquivado em
`/srv/sitepinhal-archive/sitepinhal_20260711_221836.tar.gz`. Validação no VPS: `manage.py check`,
`collectstatic`, `nginx -t` e HTTP 200 em `/`, `/cadastro/`, `/recuperar-senha/`, `/static/css/login.css` e
`/sistema-novo/`. **Atenção operacional:** o Mercado Pago no VPS segue em **modo teste**.

**Última atualização:** 2026-07-12 (**Doc: consolidação das fontes da verdade**): `CLAUDE.md` e
`docs/README_PROJETO.md` atualizados com o módulo **Configurações IA**, a **cobrança por IA/telefone** e toda a
evolução do **WhatsApp** (grupos, webhook, autorização, liberação, reengajamento, `/autorizar`) — rotas, models
(migrations até **0052**) e a convenção de integrações externas. Sem mudança de código. Antes: Autorização — resposta automática.

**Anterior (Autorização: resposta automática):** quando alguém manda a mensagem de
autorização, o sistema responde automaticamente com uma confirmação curta (**1x só**, texto configurável na aba
Autorização, vazio = não responde). É resposta a quem escreveu (seguro). `WhatsappConfig.resposta_autorizacao`;
`_registrar_contato_whatsapp` envia na 1ª autorização; migration **0052**. Antes: reengajamento — uma vez por silêncio.

**Anterior (Reengajamento: uma vez por silêncio):** o reengajamento agora manda **uma
vez só** por período de silêncio e **não insiste** — critério por mensagem (`reengajado_em < ultima_msg_em`), não
por janela de tempo. Só volta a ser elegível se a pessoa **responder** e depois ficar calada `reengajar_dias` de
novo. Cold nunca entra. `_inativos_para_reengajar` ajustado; sem migration. Antes: reengajamento com pausa (10s).

**Anterior (WhatsApp: reengajamento com pausa (10s)):** o "Reengajar inativos agora"
passou a enviar **um a um com 10s entre cada** (barra de progresso + cancelar), igual ao "Enviar a todos" da
cobrança — antes mandava tudo de uma vez. `whatsapp_reengajar_view` envia 1 por request (`usuario_id`); JS faz o
pacing (alvos via `json_script`); comando `reengajar_inativos` pausa com `time.sleep`. Helpers `_reengajar_um`/
`_numero_do_contato`; sem migration. Antes: WhatsApp — responsividade das abas.

**Anterior (WhatsApp: responsividade das abas (mobile)):** com 5 abas a barra cortava no
celular; agora `.wa-abas` usa `flex-wrap` (+ media ≤520px) e todas as abas ficam visíveis sem overflow. Revisão
mobile das últimas telas confirmada por screenshot a 484px (abas, Grupos, Webhook, Autorização, Liberação,
Reengajamento e Cobranças com termômetro/seletor/alavanca). Só CSS. Antes: WhatsApp — reengajamento de inativos.

**Anterior (WhatsApp: reengajamento de inativos):** na aba **🚦 Liberação**, config de
**reengajamento** — se um contato que já interagiu fica `reengajar_dias` (padrão 30) sem responder, o clube manda
uma **mensagem curta** ("ainda quer receber?") pra reativar. Só para quem já mandou msg (nunca cold); não reenvia
na janela. Botão "Reengajar inativos agora" + comando `reengajar_inativos` (cron). Campos
`WhatsappConfig.reengajar_dias`/`mensagem_reengajamento`, `PerfilUsuario.reengajado_em`; helpers
`_inativos_para_reengajar`/`_reengajar_inativos`; migration **0051**. Antes: rastreio inclui diretoria + painel Liberação.

**Anterior (WhatsApp: rastreio inclui diretoria + painel Liberação):** o casamento do
número recebido agora acha **responsáveis E diretoria** (`_perfil_por_whatsapp`, inclui `MembroDiretoria.whatsapp`).
Nova aba **🚦 Liberação** na tela WhatsApp: painel único listando responsáveis + diretoria com termômetro
(🟢/🟡/🔴 + "há X") e resumo "N de M já mandaram msg" (`_liberacao_lista`). Sem migration (rastreio fica em
`PerfilUsuario`). Termômetro das Cobranças segue só responsáveis. Antes: Cobranças — enviar em lote só p/ liberados.

**Anterior (Cobranças: enviar em lote só para liberados):** no "Enviar a todos" (aba
Cobranças) há um checkbox **"Só quem já me mandou mensagem (evita bloqueio)"** (padrão marcado) — o lote mira só
famílias que autorizaram OU já mandaram mensagem (rastreio via webhook). `data-liberado` por família +
`alvosLote()` no JS; sem migration. Antes: WhatsApp — link curto de autorização.

**Anterior (WhatsApp: link curto de autorização):** rota pública **`/autorizar/`**
(`pinhaljunior.com.br/autorizar`) que **redireciona** pro wa.me da autorização — link **curto e branded** que se
compartilha (o wa.me fica atrás). A aba Autorização mostra o curto (Copiar) + o wa.me em `<details>`. Helper
`_wa_link_autorizacao`; `autorizar_view` (503 se não configurado); sem migration. Antes: link wa.me avulso.

**Anterior (WhatsApp: link wa.me de autorização):** a aba **✍️ Autorização** gera um
**link wa.me avulso** (`https://wa.me/<numero_clube>?text=<msg de autorização>`) com botão **Copiar** e **Abrir**.
O responsável clica → manda a mensagem pronta pro clube → webhook casa o número → família **autorizada** (termômetro
verde), sem o clube iniciar conversa. Campo novo `WhatsappConfig.numero_clube` (aba Configurações); handler de
copiar genérico; migration **0050**. **Disparo no grupo: CANCELADO** (decisão do usuário). QR: não feito (dep nova).
Antes: WhatsApp — rastreio de contato + autorização (termômetro).

**Anterior (WhatsApp: rastreio de contato + autorização (termômetro nas Cobranças)):**
toda mensagem recebida pelo webhook (direta) é casada com o telefone de um responsável; grava a **data da última
mensagem** da família e, se o texto bate com a **mensagem de autorização** (nova aba **✍️ Autorização**, texto
configurável; compara sem acento/caixa), marca **autorização recebida**. Em **Mensalidades → Cobranças** cada
família tem um **termômetro** (verde=autorizado / amarelo=mandou msg sem autorizar / vermelho=nunca) + "última msg
há X". Campos `PerfilUsuario.ultima_msg_whatsapp_em`/`autorizacao_recebida_em`, `WhatsappConfig.mensagem_autorizacao`;
helpers `_familia_por_whatsapp`/`_registrar_contato_whatsapp`; migration **0049**. NÃO troca o número
automaticamente (só rastreia). Futuro: link wa.me pronto p/ o responsável; disparo no grupo despriorizado.
Antes: WhatsApp — webhook de recebidas + últimas 5 (Fase 2).

**Anterior (WhatsApp: webhook de recebidas + últimas 5 — Fase 2):** nova aba **🔔
Webhook** na tela WhatsApp com a **URL do webhook** (+ botão "Configurar webhook na W-API", `PUT
/webhook/update-webhook-received`) e o painel **"Últimas 5 mensagens recebidas"** (poll de 5s), para testar o
recebimento. Endpoint público `webhooks/whatsapp/` recebe, faz parsing robusto (`core/wapi_parser.py`, portado do
BEEZAP: remetente de `sender.id`, texto de `message.conversation`, detecta grupo e ignora status) e guarda em
`WhatsappWebhookEvent` (payload cru, 100 últimos). Rotas `whatsapp/webhook/configurar|eventos/`; migration **0048**.
Próximo (Fase 3): marcar o responsável como "liberado" (whitelist) pelo telefone recebido + campanha no grupo.
Antes: WhatsApp — abas + Grupos (Fase 1).

**Anterior (WhatsApp: abas + Grupos — Fase 1 do módulo de liberação):** a tela WhatsApp
agora tem **duas abas** — **Configurações** (instância + teste) e **Grupos**. A aba Grupos busca os grupos da
conta na W-API (`GET /v1/group/get-all-groups`, botão "Atualizar lista") e mostra **nome + ID**, persistindo em
`GrupoWhatsapp` (vínculo ID↔nome). Cliente novo `core/wapi.py` (`listar_grupos`/`dados_grupo`/
`configurar_webhook_recebido`/`enviar_texto`, via urllib). Rota `whatsapp/grupos/sincronizar/`; migration **0047**.
É a base do **módulo de liberação de números** (Fase 2 = webhook de recebidas + whitelist; Fase 3 = campanha
"quem falta" no grupo dos pais, postagem manual). Antes: Cobranças — telefone do responsável financeiro.

**Anterior (Cobranças: telefone do responsável financeiro por família):** na aba
**Cobranças**, cada família com **2+ telefones** (pai/mãe/resp. legal) tem um **seletor** de para qual WhatsApp a
cobrança vai — o do **responsável financeiro**. A escolha **persiste** (toast "alterado" ao trocar) e habilita o
envio se antes não havia número. Campo **próprio e independente** (`PerfilUsuario.cobranca_whatsapp_origem`),
separado do WhatsApp principal/recuperação (o login pode não ser quem paga). Endpoint
`mensalidades/cobrancas/telefone/`; helper `_resolver_origem_numero`; migration **0046**. Antes: cobrança pela IA
(prompt com quebras de linha).

**Anterior (Cobrança de mensalidades pela IA — 1º uso do GPT):** na aba **Cobranças**
de Mensalidades, uma **alavanca** (switch, persiste na hora via `mensalidades/cobrancas/modo/`) escolhe se a
cobrança por WhatsApp usa a **mensagem padrão** ou é redigida **pela IA** (GPT). Prompt editável no form de
mensagens (`ConfigMensalidade.prompt_cobranca_ia`, flag `cobranca_via_ia`; constante `PROMPT_COBRANCA_IA_PADRAO`);
usa os mesmos marcadores `{nome}/{itens}/{total}/{link}` (reaproveita `_montar_mensagem_cobranca`). No envio
(individual/lote) com modo IA, `_gerar_cobranca_ia` monta o prompt, chama o GPT e envia o texto (tokens vão pro
contador de Configurações IA). Guard: modo IA sem IA configurada → barra com aviso. Migration **0045**.
Antes: Configurações IA — modelo fixo + contador de tokens.

**Anterior (Configurações IA: modelo fixo + contador de tokens):** a tela `/ia/`
(🤖, só Diretor) guarda **só a chave da API**; o **modelo é fixo** `gpt-4.1-nano` (o mais barato, constante
`MODELO` em `core/openai_ia.py`) e a **URL base não é mais configurável**. Novo card **"Consumo de tokens"**
acumulando chamadas + tokens de entrada (total/em cache/fora do cache) + saída + total, com **"Zerar contador"**
(atualiza ao vivo após cada teste). `OpenAIConfig` ganhou os contadores `chamadas`/`tokens_prompt`/`tokens_cache`/
`tokens_completion` (métodos `registrar_uso`/`zerar_uso`); `conversar`/`enviar_prompt` devolvem `(ok, texto, uso)`.
Migration **0044**. Antes: módulo Configurações IA (criação).

**Anterior (Módulo Configurações IA — criação):** novo módulo **Configurações IA**
(🤖, só Diretor) no padrão WhatsApp/Mercado Pago — singleton `OpenAIConfig` e tela `/ia/` com **salvar config** e
**enviar um teste** (resposta da IA na própria tela). Cliente `core/openai_ia.py` via `urllib` (sem dependência
nova). Rotas `ia/`, `ia/config/`, `ia/testar/`; item de menu `ia`; template `core/ia.html` + `static/js/ia.js`.
É só a **configuração base** — onde a IA será aplicada no sistema vem depois.

**Anterior (Mercado Pago: sinal de credenciais salvas):** na tela `/mercadopago/`,
cada par (Teste/Produção) ganhou um **badge "✓ Configurado / Não configurado"** no cabeçalho e os campos de
segredo passam a mostrar os **últimos 4 dígitos** do que está salvo (`••••••1234`) — dá pra confirmar que as
credenciais estão gravadas sem colar de novo. Propriedades novas em `MercadoPagoConfig`
(`teste_configurado`/`prod_configurado` + mascaradas por par); sem migration. Antes: Revisão dos pagamentos + fix do recusado.

**Anterior (Revisão dos pagamentos + fix do recusado):** revisão geral de Pix e
**cartão (Checkout Pro)** nas 3 áreas (loja, mensalidades, eventos) — engine consistente (cartão disponível nos
6 pontos; gross-up da taxa ok; webhook valida assinatura e consulta o MP como fonte da verdade; página genérica
trata cartão com "confirmando + polling"). **Corrigido:** pagamento **recusado/cancelado** ficava girando para
sempre; agora mostra aviso de recusa + "Voltar e tentar de novo" (`pagamento_mp.js` trata `rejeitado`/`cancelado`;
bloco `#pixRejeitado`; `voltar_url` por tipo em `pagamento_view`; teste em `PagamentoLojinhaTests`). Pendências
**operacionais** (não código): cadastrar webhook URL + secret no painel do MP e confirmar a taxa real do cartão
em produção. Antes: Cadastros (obrigatoriedade + Sim/Não + validação com aviso).

**Anterior (Cadastros: obrigatoriedade + Sim/Não + validação com aviso**): revisão da
obrigatoriedade dos campos nos cadastros de **aventureiro** e **diretoria**. Asterisco automático (via
`_campo.html`); perguntas **Sim/Não obrigatórias** (novo parcial `_campo_simnao.html`); ao avançar/finalizar,
um **aviso lista os campos obrigatórios que faltam** (`static/js/wizard_validacao.js`, caixa `#avisoValidacao`).
A **ficha médica** virou Sim/Não obrigatório por pergunta (detalhe só se "Sim"; gates `teve_doencas`/
`tem_deficiencia`; tipo sanguíneo obrigatório) num corpo **compartilhado** `_ficha_medica_campos.html`
(mixin `FichaMedicaCamposMixin` em forms.py). Diretoria exige foto/nacionalidade/nascimento/igreja/distrito/RG/
estado civil/e-mail/endereço completo/escolaridade + "Tem filhos?" e cônjuge condicionais. Aventureiro exige
foto/sexo/nascimento/colégio/série/ano/camiseta/endereço completo/grau+e-mail do responsável, **Bolsa Família**
Sim/Não, **classes** com opção "Nenhuma", **pai/mãe** com "Tem os dados? Sim/Não" (se Sim, todos obrigatórios),
e no termo de imagem nacionalidade do menor + nacionalidade/estado civil/RG do responsável; o termo de imagem é
**pré-preenchido** com os dados já digitados. Sem migration (obrigatoriedade no form). Condicionais por grupo de
radios (`data-depende-nome`) no `cadastro.js`/`cadastro_diretoria.js`. Antes: Comandos de migração (diretoria + assinaturas).

**Anterior (Comandos de migração: diretoria + assinaturas antigas**): dois comandos
(`importar_diretoria` e `importar_assinaturas`), idempotentes, com `--dry-run`, que rodam **localmente** lendo o
ZIP de exportação (git-ignored) — depois db/media vão para o VPS. `importar_diretoria` cria `MembroDiretoria`
(+ficha+foto), vincula ao perfil Diretoria, trata **mesclagens** (diretoria+responsável em logins diferentes →
anexa ao login com o aventureiro; 1 login/2 perfis) e cria o User dos só-diretoria (preservando senha). A config
de skip/mesclagem fica em `migracao_mesclagem.json` **local** (git-ignored; contém logins reais). `importar_assinaturas`
casa **por CPF** e importa as assinaturas antigas (`aventureiroficha`→`AssinaturaDocumento`;
`diretoriaficha`→`AssinaturaDocumentoDiretoria`, com a **declaração médica = cópia do compromisso**). Resultado
local: 10 membros de diretoria, 96 assinaturas de aventureiro, 21 de diretoria. Antes: Diretor atribui o papel da diretoria.

**Anterior (Diretor atribui o papel da diretoria**): nova tela do Diretor
(`/usuarios/diretoria/`, botão "Gerenciar diretoria (papéis)" em Usuários) que lista os integrantes da
diretoria e permite **atribuir o papel** (Diretor/Secretário/Tesoureiro/Professor ou "Diretoria sem papel").
A atribuição ajusta os **grupos** do usuário (remove os demais papéis e aplica o escolhido) → o perfil/menu
reflete o papel. Views `diretoria_equipe_view`/`diretoria_papel_view`. Antes: "Meus Dados" mostra os dados da
diretoria.

**Anterior ("Meus Dados" mostra os dados da diretoria**): quando um integrante da
diretoria acessa "Meus Dados", aparece um **card "Diretoria"** (painel expansível) com identificação, contato,
endereço, escolaridade e resumo da ficha médica, além do **papel** (Diretor/Secretário/Tesoureiro/Professor ou
"papel a definir"). `inicio_view` carrega o `MembroDiretoria` (`_papel_diretoria`); card em `inicio.html`;
estilos `.resp-avatar-img`/`.painel-corpo .bloco-rotulo` em `inicio.css`. Antes: assinatura desenhada dos 3
documentos da diretoria.

**Anterior (Diretoria: assinatura desenhada dos 3 documentos**): no cadastro de
diretoria, os aceites por checkbox viraram **assinatura desenhada** (dedo/mouse) — cada documento (compromisso
de voluntário, declaração médica e autorização de imagem do adulto) tem a sua, gravada como PNG + snapshot do
texto do termo, no mesmo padrão do aventureiro (reusa `_assinatura_doc.html`, o modal e `assinatura.js`). Model
`AssinaturaDocumentoDiretoria` (via molde abstrato `AssinaturaDocumentoBase`, migration **0042**); textos em
`termos.py` (`montar_texto_diretoria`). Responsividade mobile verificada (490px). Corrigido bug do preview
(imagem quebrada no estado vazio) que afetava também o aventureiro. Antes: Cadastro de Diretoria (base).

**Anterior (Cadastro de Diretoria + tela de escolha + 2 perfis**): o "Cadastre-se"
(`/cadastro/`) virou uma **tela de escolha** com 3 opções — **Aventureiro**, **Diretoria** e **Diretoria +
Aventureiro**. Novo **cadastro de diretoria** (`/cadastro/diretoria/`, ficha "Compromisso para Voluntários"):
wizard com Conta, Identificação (cônjuge condicional ao estado civil; qtd. de filhos), Contato/Endereço,
**ficha médica completa** (mesma do aventureiro, via molde abstrato `FichaMedicaBase`), Escolaridade e **3 aceites**
(compromisso de voluntário, declaração médica e **autorização de imagem do adulto** — adaptada da versão do
menor). Cria conta + `MembroDiretoria` + `FichaMedicaDiretoria`, entra no perfil **Diretoria** e loga. A opção
**Diretoria + Aventureiro** (`?com_aventureiro=1`) emenda no cadastro de aventureiro (pré-preenchendo o
responsável com os dados da diretoria) → **1 login com 2 perfis** (Diretoria + Responsável), com a **alternância**
"Ver como" já existente. No `core/menus.py`, "Responsável" passou a ser **implícito** (quem tem aventureiro
não-demo) e convive com o novo perfil "Diretoria". Migration **0041**; `configurar_perfis` cria o grupo
"Diretoria". Papel específico (Diretor/Secretário/Tesoureiro/Professor) e a exibição do membro em "Meus Dados"/
"Usuários" ficam para o **próximo passo**. Antes: Ficha médica alinhada ao formulário oficial DSA.

**Anterior (Ficha médica alinhada ao formulário oficial DSA**): a **Ficha Médica**
passou a bater com o formulário oficial da DSA (PDF `Fichas-Secretaria-Padrão`). Foram adicionadas as **6
doenças** que faltavam na lista "Já teve ou tem" — **Varíola, Coqueluche, Difteria, Caxumba, Rinite e
Bronquite** — e um **bloco novo "Deficiência física"** (Cadeirante / Visual / Auditiva / Fala-mudez). 10
BooleanField novos em `FichaMedica` (migration **0040**, todos `default=False`); refletidos no cadastro
(etapa ficha médica), na exibição de "Meus Dados"/Usuários (`_preparar_ficha` alimenta `doencas_lista` e a
nova `deficiencias_lista`) e, por tabela, no form (`exclude=aventureiro`) e no admin. O **telefone fixo** de
pai/mãe do formulário oficial ficou deliberadamente de fora. Próximo passo combinado: **cadastro de diretoria**
(ficha "Compromisso para Voluntários"). Antes: Perfil Responsável (Loja/Mensalidades/Presença próprias).

**Anterior (Perfil Responsável: Loja, Mensalidades e Presença próprias + registro
central de menu**): início do trabalho nos **perfis**. Criado **`core/menus.py`** — o **registro central** de
itens de menu + acesso por perfil (`ITENS_MENU`, `ACESSO_PADRAO`, `perfil_do_usuario`, `itens_menu_para`,
`pode_acessar`): **fonte única da verdade** de "quem vê/acessa o quê", desenhada para o **futuro módulo de
permissões** encaixar (em `_ids_liberados`) **sem reescrever** menu nem views. O `_menu.html` deixou de ser
chumbado (`{% if is_diretor %}`) e **itera `menu_itens`** (do context processor `perfis`). O **perfil
Responsável** ganhou **telas próprias** (mesma URL do Diretor; a view **ramifica por perfil**): **Loja** = só a
**vitrine** + aba **"Meus pedidos"** (sem Gerenciar/Vendas; vitrine no parcial `_loja_vitrine.html`);
**Mensalidades** = **resumo** (pago no ano × em aberto) + lista das **vencidas em aberto** (mês atual +
atrasados) para **selecionar e pagar** (Pix/cartão, `minhas_mensalidades_pagar`, escopo família) + botão
**"adiantar meses"** (`?frente=1`) + **texto de apelo**; **Presença** = **relatório só-leitura** dos próprios
filhos (esteve/faltou por evento; não marca). O Diretor ganhou na aba **Cobranças** a **mensagem de apelo**
(`ConfigMensalidade.mensagem_apelo`, migration **0038**). Templates novos: `_loja_vitrine.html`,
`loja_responsavel.html`, `mensalidades_responsavel.html`, `presenca_responsavel.html`. **Seletor de perfil:**
no **topo** do menu (logo abaixo do título) há o **cartão do usuário** — nome + **perfil selecionado** (chip); com
2+ perfis vira um **dropdown** (`<details>`) que lista os perfis que o usuário **possui** (grupos) e troca a
visão ao clicar (rota `trocar_perfil`, chave `PERFIL_ATIVO_KEY`; `perfil_efetivo`/`perfis_do_usuario`/
`pode_trocar_perfil` em `core/menus.py`). O nome do usuário saiu do rodapé (só sobrou Sair + copyright). **Dados fictícios (demo):** flag
**`Aventureiro.demo`/`Evento.demo`** (migration **0039**) marca dados de teste que **NUNCA** entram nas
contagens do clube (Usuários, Mensalidades/Presença do Diretor, Financeiro, menu de eventos) — a presença do
responsável casa a "demo-ness" (família demo só vê eventos demo). Comando **`dados_demo_fabiano`** dá **todos
os 5 perfis** ao Fabiano + cria **2 aventureiros fictícios** (com mensalidades pagas/em aberto e presença) para
ele testar o perfil Responsável. Testes em `core.tests` (`PerfilResponsavelTests`, `DemoIsolamentoTests`).
Antes: Cobrança de mensalidades por WhatsApp + página pública de acerto.

**Anterior (Cobrança de mensalidades por WhatsApp + página pública de acerto):** novo
sistema de cobrança das mensalidades. **(1) Página pública de acerto** (`/acerto/<token>/`, sem login): um
**token fixo por família** (`PerfilUsuario.token_acerto`) abre uma página que mostra as mensalidades em aberto de
todos os aventureiros da família e permite **pagar na hora** (Pix/cartão) — o Pix é gerado só no clique, nada
"vence" se demorar. **(2) Aba "Cobranças"** no Mensalidades: **mensagem configurável**
(`ConfigMensalidade.mensagem_cobranca`, marcadores `{nome}/{itens}/{total}/{link}`), **envio por WhatsApp**
(W-API) **a um ou a todos**, **filtro "só quem não recebeu este mês"** e **histórico** (`CobrancaEnviada`,
mês/ano). Agrupada por família; usa o WhatsApp principal e o link de acerto. Migrations **0036** (token) e
**0037** (mensagem + CobrancaEnviada). Testes em `core.tests` (`AcertoPublicoTests`, `CobrancaWhatsappTests`).
Antes: Pagamentos Mercado Pago — Etapa 6 (cartão).

**Anterior (Pagamentos Mercado Pago — Etapa 6: cartão de crédito, Checkout Pro):**
os **4 pontos** (lojinha de evento, Loja do Clube, inscrição e mensalidades) aceitam **Pix e cartão**. O
cartão usa **Checkout Pro** (redireciona ao MP; sem SDK, sem dado de cartão no servidor, sem dependência nova).
**Todas as taxas vão pro cliente**: o **juro do parcelamento** é do comprador (config **"Parcelado comprador"**
na conta MP, até 12x) e a **taxa de intermediação** (fixa) é **embutida no preço** via *gross-up*
(`cobrado = venda ÷ (1 − taxa%)`), com a taxa em `MercadoPagoConfig.taxa_cartao_pct` (padrão **4,98%** = crédito
na hora) — a tela de config tem um **termômetro** (taxa residual média que o clube arcou; ideal ≈ 0). A taxa do
clube passou a ser **`valor_bruto − líquido`** (uniforme): no Pix o clube absorve (~1%); no cartão o repasse
cobre → **líquido bate com a venda → taxa ≈ 0**. `mercadopago.criar_preferencia` (via `urllib`); Pagamento
`forma="cartao"`; página genérica trata cartão ("confirmando pagamento" + polling); webhook e finalizações
reusados (a forma do objeto vem de `pagamento.forma`). Migration **0035** (`taxa_cartao_pct`). Testes em
`core.tests` (preferência + webhook com taxa repassada ≈ 0; gross-up; cartão em mensalidade e inscrição). **Setup
do lado do usuário:** deixar o parcelamento como **"Parcelado comprador"** no painel do MP. Antes: Financeiro
remove "Onde está o dinheiro".

**Anterior (Financeiro: remove "Onde está o dinheiro" e ajusta caixa):** a aba
Financeiro não exibe mais o card/modal **"Onde está o dinheiro"** (banco/espécie/caixa físico). Para o resultado
do caixa bater com o valor informado da conta do clube (**R$ 3.353,00**), o banco local foi ajustado nas
mensalidades: 5 cobranças de R$ 30,00 e 1 cobrança de R$ 27,00 foram reabertas, e 1 mensalidade paga teve
`valor_pago` ajustado para R$ 28,00. Validação local e no VPS: resultado financeiro R$ 3.353,00, `check` OK,
`migrate` sem pendências e `/sistema-novo/` 200. Backup do banco online anterior:
`/var/www/pinhaljunior2/backup/db_before_caixa_mensalidades_20260707_003251.sqlite3`. Antes: Pagamentos
Mercado Pago — Etapa 5.

**Última atualização:** 2026-07-06 (**Pagamentos Mercado Pago — Etapa 5: taxa/líquido nos relatórios**): os
relatórios financeiros agora mostram o **líquido que caiu no banco** (bruto − custos − **taxa do Mercado Pago**).
O clube absorve a taxa (não repassa), mas ela aparece descontada no **Financeiro geral** (taxa por fonte +
`saidas`/`resultado` líquidos + linhas "Taxa Mercado Pago" no extrato), no **painel financeiro do evento**
(`saidas_total` = custos + taxa), nas **Mensalidades** (KPI Recebido mostra o líquido) e na **Loja (Vendas)**
(linha de taxa). A taxa vem do campo `Pagamento.taxa` (real do MP, fallback 1%): no geral soma por **tipo**; no
evento soma os **Pagamentos distintos** das inscrições/pedidos (evita duplicar quando inscrição+lojinha
compartilham a cobrança). Pagamentos manuais/dinheiro/importados têm taxa zero → líquido = bruto. Testes em
`core.tests` (geral e painel do evento). **Pendência:** cartão de crédito (Etapa 6). Antes: Etapa 4 (Inscrição).

**Anterior (Pagamentos Mercado Pago — Etapa 4: Inscrição de evento via Pix):** a
**inscrição online** passou a cobrar **Pix real** quando há valor a pagar (antes nascia confirmada sem pagar).
Com MP configurado e total &gt; 0, `evento_inscrever_view` valida e **serializa** os dados (responsável;
participantes com `valor`/`faixa_id`/respostas/cupom; campos extra; itens da lojinha) num `Pagamento`
(`tipo="inscricao"`) e vai à página de pagamento genérica; a inscrição só é criada **na aprovação** por
`_finalizar_inscricao` → `_criar_inscricao_de_payload` (helper compartilhado com a criação imediata). Inscrição
**gratuita** (total 0) ou **sem MP** cria na hora; **balcão/PDV** inalterado. Preço fixado na cobrança e cupom
marcado só no pagamento (uso único; se o cupom for usado por outro no meio, a pessoa mantém o preço pago). FK
`Inscricao.pagamento`, `forma_pagamento="pix"` (migration **0034**). Testes em `core.tests.InscricaoPixTests`.
**Pendências:** taxa/líquido nos relatórios (Etapa 5), cartão (Etapa 6). Antes: Etapa 3 (Loja do Clube).

**Anterior (Pagamentos Mercado Pago — Etapa 3: Loja do Clube via Pix):** a **Loja do
Clube** passou a cobrar **Pix real** (MP), reaproveitando a engine e a **página de pagamento genérica**.
`loja_pagamento_view`, com MP configurado + Pix, cria um `Pagamento` (`tipo="loja_clube"`, `payload` com o
carrinho serializado + comprador) e redireciona para `/pagamento/<ref>/`; na aprovação, `_finalizar_loja_clube`
reconstrói os itens (`_loja_resolver_kits`, extraído de `_loja_cart_detalhado`) e cria a `CompraLoja` (Pix, FK
`pagamento`, baixa estoque) → volta a `loja_sucesso`. Sem MP configurado, mantém o simulado. **A compra só nasce
na aprovação.** Também: toast de sucesso no "Marcar pago/Desfazer" das mensalidades. FK `CompraLoja.pagamento`
(migration **0033**). Testes em `core.tests.LojaClubePixTests`. **Pendências:** Inscrição (Etapa 4), taxa/líquido
nos relatórios (Etapa 5), cartão (Etapa 6). Também nesta leva (correções do deploy no VPS): cookies próprios
(`pinhaljunior2_sessionid`/`_csrftoken`) para não deslogar por colisão com o sistema antigo; **cache-busting** dos
estáticos (`ManifestStaticFilesStorage`) para o navegador sempre pegar o JS/CSS novo; e fix de `fetch` com
caminho absoluto que quebrava sob o prefixo `/sistema-novo/`. Antes: Etapa 2.

**Anterior (Pagamentos Mercado Pago — Etapa 2: Mensalidades online + admin do
Pagamento):** (1) o model `Pagamento` entrou no **/admin/** (lista só-leitura, para auditoria: bruto, taxa,
líquido, status, forma, modo, mp_id). (2) **Mensalidades online via Pix**: na aba Aventureiros, cada aventureiro
com valor em aberto tem o botão **"💳 Cobrar em aberto via Pix"** → modal seleciona os meses (checkbox + total ao
vivo) → gera **uma cobrança Pix só** (`mensalidade_cobrar_view`, `Pagamento tipo="mensalidade"` com os ids no
`payload`); na aprovação (webhook ou "Simular" no teste), `_finalizar_mensalidade` **quita todos os meses
escolhidos** automaticamente (forma Pix, `valor_pago`, `pago_em`, FK `Mensalidade.pagamento`; idempotente).
Reaproveita a engine da Etapa 1 e já serve a futura tela do responsável. Criadas ainda uma **página de pagamento
genérica** (`pagamento.html`) e uma **tela de sucesso genérica** (`pagamento_sucesso.html`), por `referencia` do
pagamento, reaproveitáveis nas Etapas 3/4. Rotas novas: `mensalidades/cobrar/`, `pagamento/<ref>/`,
`pagamento/<ref>/sucesso/`. Migration **0032** (`Mensalidade.pagamento`). Testes em
`core.tests.MensalidadePixTests`. **Pendências:** Loja do Clube (Etapa 3), Inscrição (Etapa 4), taxa/líquido nos
relatórios (Etapa 5), cartão (Etapa 6); tela do responsável pagar as próprias mensalidades (futura). Antes:
Pagamentos Mercado Pago — Etapa 1.

**Anterior (Pagamentos Mercado Pago — Etapa 1: engine Pix + webhook + lojinha de
evento):** início da integração real de pagamentos (**só Pix** nesta parte; cartão fica com o caminho preparado).
Criada uma **engine única reaproveitável** para os 4 pontos (lojinha de evento, Loja do Clube, mensalidades,
inscrição) e **ligada primeiro na lojinha de evento**. Peças: **`MercadoPagoConfig`** (singleton, só Diretor,
tela `/mercadopago/`; **dois pares** de credenciais — teste/produção — + `modo` ativo; segredos mascarados,
trocam só se digitar novo; mostra a **URL do webhook**); **`core/mercadopago.py`** (cliente via `urllib`, sem
dependência nova: `criar_pix`, `consultar_pagamento` que extrai a **taxa real** de `fee_details` + o **líquido**
de `net_received_amount`, `validar_assinatura` HMAC-SHA256); model genérico **`Pagamento`** (tipo, forma,
`referencia`, `mp_payment_id`, status, `valor_bruto`/`taxa`/`valor_liquido`, `payload` JSON = o que está sendo
pago, `finalizado` p/ idempotência) + FK `PedidoLoja.pagamento`; **webhook** `/webhooks/mercadopago/` (público,
`csrf_exempt`, idempotente — valida assinatura, consulta o pagamento no MP como fonte da verdade, grava taxa/
líquido e **finaliza** criando o objeto pago). Na lojinha, `evento_pagamento_view` usa Pix real quando o MP está
configurado (QR do MP + **polling** + botão **"Simular aprovação" só no modo teste**); sem config, mantém o
simulado antigo. O **pedido só nasce na aprovação**. O clube **absorve a taxa** mas o sistema grava o **líquido
real** (a exibição nos relatórios vem na Etapa 5). Migration **0031**. Testes em
`core.tests.PagamentoLojinhaTests`/`MercadoPagoClienteTests`. **Pendências:** cadastrar a URL do webhook + a
secret no painel do MP; confirmar a **taxa real** com um Pix de produção (o sandbox não paga Pix de teste — o
botão "Simular" usa 1%); próximas etapas: mensalidades online, Loja do Clube, inscrição e taxa nos relatórios.
Antes: Preparação para deploy no VPS.

**Anterior (Preparação para deploy no VPS):** o projeto agora aceita configuração
de produção por variáveis de ambiente sem quebrar o uso local: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SQLITE_PATH`, `DJANGO_FORCE_SCRIPT_NAME`,
`DJANGO_STATIC_URL`, `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_URL` e `DJANGO_MEDIA_ROOT`. Também foi adicionado
`gunicorn` ao `requirements.txt` para o serviço systemd do VPS. Localmente, sem variáveis, continua usando
`DEBUG=True`, banco `db.sqlite3`, `static/` e `media/`. Antes: Cadastro: assinatura desenhada dos 3 documentos.

**Deploy VPS:** em 2026-07-06, a nova versão ficou publicada em
`https://pinhaljunior.com.br/sistema-novo/`, isolada do sistema antigo (`sitepinhal`, porta 8000). A nova
instalação usa `/var/www/pinhaljunior2/current`, venv em `/var/www/pinhaljunior2/.venv`, SQLite persistente em
`/var/www/pinhaljunior2/data/db.sqlite3`, media em `/var/www/pinhaljunior2/media`, staticfiles em
`/var/www/pinhaljunior2/staticfiles`, env file `/etc/pinhaljunior2.env`, serviço `pinhaljunior2.service`
(Gunicorn em `127.0.0.1:8010`) e atalho global `pinhaljunior2-deploy`. Detalhes em `docs/DEPLOY_VPS.md`.

**Dados no VPS:** em 2026-07-06, o banco `db.sqlite3` e a pasta `media/` locais foram enviados uma vez para o
VPS novo. O serviço `pinhaljunior2` foi parado durante a troca, o banco/media anteriores do VPS foram salvos em
backup com timestamp, permissões foram ajustadas e a aplicação voltou ativa. Validação: 37 usuários, 39
aventureiros, 36 ativos e mídia servindo via `/sistema-novo/media/`.

**Restauração do banco no VPS:** em 2026-07-07, após testes manuais no ambiente online, o banco do VPS foi
substituído novamente pelo `db.sqlite3` local. Backup do banco online anterior:
`/var/www/pinhaljunior2/backup/db_before_local_restore_20260707_002006.sqlite3`. Validação: `check` OK,
`migrate` sem pendências, 37 usuários, 39 aventureiros, 36 ativos, 0 pagamentos, 87 arquivos de mídia e
`/sistema-novo/` respondendo 200.

**WhatsApp:** a configuração da W-API (`WhatsappConfig`) é persistida no banco, não na sessão/navegador. Em
2026-07-06 foi reforçada a proteção contra apagamento acidental: ID da instância e token só são substituídos
quando um novo valor é digitado; envio com campos vazios preserva os valores salvos. Há teste automatizado para
essa persistência (`core.tests.WhatsappConfigTests`).

**Última atualização:** 2026-07-06 (**Cadastro: assinatura desenhada dos 3 documentos**): o responsável **assina
com o dedo/mouse** (canvas, sem lib) os **3 documentos** da inscrição — ficha de inscrição, declaração médica e
termo de imagem — e a **assinatura substitui o checkbox** (assinar = aceitar). Cada assinatura vira um
`AssinaturaDocumento` (imagem PNG em `media/assinaturas/` + **snapshot do texto do termo preenchido**). O
responsável **não** vê a própria assinatura depois (só "assinado em ..."); **só o Diretor** acessa o **termo
assinado** numa página pronta pra imprimir/salvar PDF (`aventureiro_termos_view`, rota
`usuarios/aventureiro/<pk>/termos/`, link "Ver termos assinados" na tela Usuários). Modal reutilizável
(`static/js/assinatura.js`, `templates/core/_assinatura_doc.html`), termo de imagem interpolado com os dados no
cadastro. Migration **0030**. De quebra, `mensalidade_isento/_desconto_pct` deixaram de ser obrigatórios no
cadastro público (corrige travamento pré-existente). Antes: Loja/Vendas "Pedido para o fornecedor".

**Anterior:** (**Loja/Vendas: "Pedido para o fornecedor"**): nova seção na aba Vendas da
Loja com o relatório **por produto → variação** mostrando **só o que falta entregar** (= o que pedir ao
fornecedor); itens já entregues não aparecem e, sem pendências, mostra "Tudo entregue". Em `_loja_relatorio`
(chave `fornecedor`, só `falta_entregar > 0`). Antes: Financeiro contas Disponível × Reservado.

**Anterior:** (**Financeiro: contas Disponível × Reservado (loja); fim do rateio**): os **4
cards** do topo do Resumo mostram o **líquido de cada fonte** (Mensalidades/Loja/Eventos/Custos gerais) — pra ver
quem gera mais lucro/prejuízo. **Removido o "rateio"** (confuso). Novo bloco de **duas contas**: **💚 Disponível
pra gastar** (Mensalidades + lucro de eventos − custos gerais) e **🔒 Reservado da loja** (vendas − fornecedores,
travado); as duas somam o resultado. Mantidos os quadros "Como o resultado se forma" e **"Onde está o dinheiro"**
(**na conta/banco** + **em espécie**; espécie = resultado − banco; Diretor edita só o saldo do banco; `CaixaClube`
singleton, mig. **0028/0029**; rota `financeiro/caixa/`). Antes: cards por contribuição.

**Anterior:** (**Financeiro: quanto cada fonte contribui no resultado**): novo quadro na
aba **Resumo** que **rateia os custos gerais do clube** (que ficam à parte e por isso os cards de líquido por
fonte não somavam o resultado) entre as fontes, proporcional ao líquido de cada uma, mostrando por fonte o
valor e a **% do resultado** (com barra) — Mensalidades/Loja/Eventos agora **somam exatamente** o resultado
líquido. Contexto `contribuicao`/`custos_gerais_total` em `financeiro_view`; card `.fin-contrib`. Antes:
Máscara de moeda pt-BR em todos os valores R$.

**Anterior:** (**Máscara de moeda pt-BR em todos os valores R$**): fecha a pendência —
os **preços de produto** (Loja do Clube e lojinha de evento), os **valores de evento** (custo, faixa etária e
valor da diretoria) e o **"valor recebido" (dinheiro) do PDV** deixaram de ser `type=number` e passaram ao
padrão `moeda_br.js` (mostra `1.234,56`, envia `1234.56`). No PDV, o **cálculo de troco ao vivo** foi ajustado
para ler os **dígitos como centavos** (não `parseFloat`, que quebraria com o separador de milhar) — validado
com POST de venda em dinheiro (troco correto). Para isso o `moeda_br.js` ganhou um **modo inline** (um único `input[type=text] data-moeda` sem
campo oculto, normalizado no `submit` por listener em captura) — usado pelos campos de formulário Django
(`CustoEventoForm.valor`, `FaixaEtariaPrecoForm.valor`, `EventoInscricaoConfigForm.valor_diretoria`) e pelas
linhas de variação clonadas por JS (`_loja_var_linha.html`, `_variacao_linha.html`). Back-end inalterado. Agora
**todo** campo de valor R$ usa a máscara. Também registrado (retroativo) o quadro **"Como o resultado líquido
se forma"** do Financeiro (commit `d0fc5d8`: mensalidades + loja + eventos − custos gerais = resultado líquido;
cards de fonte passam a rotular "líquido da fonte"). Antes: Módulo Financeiro geral.

**Anterior:** (**Módulo Financeiro geral**): novo item **"Financeiro"** (📈, só Diretor)
que **consolida mensalidades + loja + eventos** num só lugar. KPIs (Entradas/Saídas/Resultado) e 3 abas:
**Resumo** (resumo por fonte, **donut** de entradas por fonte, **fluxo mensal** entradas × saídas), **Extrato**
(extrato consolidado único, cronológico, com **filtro por fonte** + busca, +verde/−vermelho e comprovantes) e
**Custos do clube** (lançar gastos gerais com valor/data/**comprovante**, listar/remover). Modelo `CustoClube`
(mig. **0025**); rotas `/financeiro/…`. Entradas = mensalidades pagas + loja + (inscrições + lojinha de
eventos); Saídas = custos de evento + custos do clube. **Ajustes (2026-07-06):** KPI "Resultado líquido";
**custos do clube importados** do antigo (14, R$ 5.066,60, com comprovantes); custo agora é lançado por
**modal** (sem data, vários **comprovantes** — `ComprovanteCustoClube`, mig. **0026**); donut centralizado +
cards de mesma altura + botões no rodapé; **máscara de moeda pt-BR** (`moeda_br.js`) nos valores; extrato com
filtros/busca corrigidos. **Líquido por fonte (2026-07-06):** os cards mostram o **líquido** de cada fonte
(mensalidades; loja = vendas − custos da loja; eventos = entradas − custos; custos gerais) e **somam o
resultado**. Custo do clube tem **destino** (Geral/Loja, mig. **0027**); a **loja** (aba Vendas) tem seção de
**custos/pagamentos da loja** + resultado. Antes: Mensalidades (dashboard mês a mês).

**Anterior:** (**Mensalidades: dashboard mês a mês**): a tela de Mensalidades ganhou
**abas** — **Resumo** (dashboard: **donut de taxa de pagamento**, **gráfico de barras mês a mês** recebido ×
em aberto em CSS puro, e **cards "Detalhe por mês"** — % paga com barra colorida, pagas/em aberto/isentos e
recebido/a receber por mês) e **Aventureiros** (a lista operacional). O resumo conta inscrições + mensalidades.
Tudo por **ano**. Antes: módulo Mensalidades (base).

**Anterior:** (**Módulo Mensalidades**): novo item **"Mensalidades"** (💰, só Diretor),
separado do financeiro. Cada aventureiro tem, por mês do ano, uma cobrança — o mês de inscrição nasce como
**"inscrição"** e os seguintes como **"mensalidade"** (gerado **automaticamente** no cadastro). **Valores
configuráveis** (padrão R$ 30, `ConfigMensalidade`); aventureiros podem ser **isentos** ou ter **desconto %**.
Tela com KPIs (previsto/recebido/em aberto/isentos), seletor de ano, **"Gerar cobranças <ano>"** e, por
aventureiro, os 12 meses com **marcar pago/desfazer** (forma, sem recarregar), **isenção/desconto do
aventureiro** e **edição por mês** (botão ✏️: **% de desconto** com o valor calculado ao vivo, ou isentar só
aquele mês, rota `mensalidades/editar/`); busca e filtro **"Só quem deve"**. Novos aventureiros geram as
cobranças automaticamente no cadastro (não há botão de gerar em massa). A barra tem **2 botões** que abrem
modais: **"Valores da mensalidade"** (config, rota `mensalidades/config/`) e **"Reajustar mensalidades"**
(aplica os valores atuais às cobranças em aberto a partir de um mês, rota `mensalidades/reajustar/`). No
dashboard, os cards mês a mês mostram só os meses **com** cobrança. **Aventureiro inativo não interfere** nos
totais: **Recebido** conta todos os pagos (histórico), mas **Em aberto/Previsto** contam só de **ativos** (e o
reajuste pula inativos) — mantém só os dados de antes de ficar inativo. Modelos `ConfigMensalidade`/`Mensalidade` +
campos no Aventureiro (mig. **0024**); rotas `/mensalidades/…`. O **histórico de 2026** do sistema antigo foi
**importado** (352 cobranças, 104 pagas; dados locais). Antes: Loja (aba Vendas + import de pedidos).

**Anterior:** (**Loja: aba "Vendas" (relatório + entrega) + import de pedidos**): a tela
da Loja ganhou a aba **"Vendas"** (📊, Diretor): **KPIs** (arrecadado, nº de compras, ticket médio, itens a
entregar), **Mais vendidos** (produto **composto** conta **por pedido**; simples por **unidade**) e **Por
forma de pagamento**, e **Todas as compras** — lista detalhada, **buscável** (busca + filtro **"Só a
entregar"**), com **marcar entrega por item** e **"Entregar tudo"** por pedido (rota `loja/entrega/compra/`).
O KPI de média é "Média por compra" (arrecadado ÷ nº de compras). O `ItemCompraLoja` ganhou controle de **entrega** (`quantidade_entregue`/`entregue_em`/
`entregue_por`; mig. **0023**). Foram **importados os pedidos pagos** da loja antiga (21 compras, R$ 3.083,50,
Pix) com comprador/forma/data/entrega preservados (dados locais, não versionados). Rota `loja/entrega/`.
Antes: galeria de fotos + fix de estilo.

**Anterior:** (**Loja: galeria de fotos + fix de estilo**): produto agora tem
**galeria de fotos** (várias por produto — como fica o uniforme, tabela de tamanhos) com **miniaturas** e
**ampliação em tela cheia (lightbox)** no celular e no PC; no cadastro há **upload múltiplo** e remoção; a 1ª
foto é a **capa** (`ProdutoLoja.capa`, modelo `FotoProdutoLoja`, mig. **0022**). Corrigido o **estilo dos
campos do comprador** no carrinho (faltava a classe `evento-form`). Importado o **"Uniforme de Gala -
Aventureiro (Completo)"** do sistema antigo: **61 variações** (Camiseta / Calça-Saia em escolha única +
Acessórios obrigatórios) + **5 fotos** (as fotos ficam só em `media/`, git-ignored). Antes: criação do módulo Loja.

**Anterior:** (**Loja do Clube (loja oficial)**): novo módulo **"Loja"** (🛍️) no menu
(**só Diretor** por ora), **independente** da lojinha de evento — é a 1ª das 3 áreas financeiras do clube
(eventos ✅, mensalidades ⏳, loja ▶). Tela com **2 abas**: **Gerenciar** (cadastrar produtos + compras
recentes) e **Loja** (vitrine com **carrinho na sessão**). Produto em 3 níveis **Produto → Grupos →
Variações**: **simples** (lista direta) ou **composto** (ex.: **Uniforme de Gala** = Camiseta/Calça/Saia em
"escolha única" + Acessórios em "itens"). Grupo tem modo (escolha única/itens), **obrigatório** e
**orientação**; itens podem ser obrigatórios com **aviso soft** (avisa o que falta e pergunta se já tem — não
bloqueia). Compra **vinculada ao login** e opcionalmente a um **aventureiro** (1 = automático; 2+ = escolher,
útil pro bordado do Kit Nome). **Pagamento simulado** (Pix QR/copia-e-cola + cartão via Mercado Pago no
futuro), reaproveitando os helpers do evento; `CompraLoja` só nasce após a aprovação; Diretor pode
**cancelar** (devolve estoque). Modelos `ProdutoLoja`/`GrupoLoja`/`VariacaoLoja`/`CompraLoja`/`ItemCompraLoja`
(mig. **0021**). Rotas `/loja/…`. Antes: Recuperação de senha pelo WhatsApp + notificações/AJAX.

**Anterior:** (**Recuperação de senha pelo WhatsApp** + notificações/AJAX): o link
**"Esqueci minha senha"** funciona. Fluxo público em 3 etapas (sessão): **CPF** do responsável legal →
envia **código de 4 dígitos** para o **WhatsApp principal** da conta → digita o código (5 tentativas,
expira em 10 min, reenvio com espera de 60 s) → **nova senha** (2×). Código guardado **com hash** na
sessão; destino sempre **mascarado**. Em **Usuários** (Diretor) há o controle **"WhatsApp principal"**
(pai/mãe/resp legal; padrão = responsável legal) por conta — campo `PerfilUsuario.whatsapp_principal_origem`
(mig. **0020**). Rotas `/recuperar-senha/…` e `/usuarios/conta/<id>/principal/`.
**Refinamentos (mesmo dia):** todas as notificações usam o **toast padrão** (o CSS do toast foi para o
`base.css`; o **login** também virou toast); os formulários de **login e recuperação** enviam por **AJAX**
(`static/js/ajax_form.js` + `form[data-ajax-toast]`), então **erro repete o toast sem recarregar** a
página (contrato JSON `{"redirect":url}` ou `{"msg","tipo"}`; helpers `_eh_ajax`/`_ajax_redirect`/
`_ajax_toast`); corrigido um **vazamento de `messages`** (login passou a renderizar `messages`). Antes:
Módulo WhatsApp (W-API))

**Anterior:** (**Módulo WhatsApp (W-API)**: novo item **"WhatsApp"** (💬) no menu
(**só Diretor**). Tela `/whatsapp/` com duas seções: **Configuração da instância** (ID da instância,
**token** exibido só com os **últimos 4 dígitos** e só substituído se digitar um novo, e **URL base**
opcional com padrão `https://api.w-api.app/v1`) e **Enviar mensagem** (número + texto). O número é
**normalizado** (aceita espaços/traços/parênteses/`+55`) para o formato da API (DDI 55 + dígitos), com
**prévia ao vivo**; envio **AJAX** com **toast padrão**. POST na W-API via **urllib** (sem novas
dependências): `POST {base_url}/message/send-text?instanceId=<id>`, `Authorization: Bearer <token>`,
body `{"phone","message"}`. Model **`WhatsappConfig`** (singleton, mig. **0019**). Antes: Aventureiro
inativo/desligado + cascata na conta)

**Anterior:** (**Aventureiro inativo/desligado + cascata na conta**: em **Usuários**
(Diretor), ao abrir um aventureiro (modal), há o botão **"Marcar como inativo"** (⛔) / **"Reativar"** (✅).
Campo `Aventureiro.ativo` (mig. **0018**). **Cascata**: ao inativar, se o responsável (conta `usuario`) não
tiver mais **nenhum** aventureiro ativo, a **conta é desativada** (`is_active=False`); se tiver outro ativo
(irmão), a conta continua ativa; reativar volta a conta. **Contas de Diretor/staff são protegidas** (nunca
desativadas). Cards de aventureiro inativo ficam com selo **"Inativo"** e riscados; o **responsável** (pai/
mãe/resp) também aparece **Inativo** quando **todos os aventureiros dele** estão inativos; a **Presença** e
a **cobertura do Resumo** contam só **ativos**. Antes: Módulo Presença do clube)

**Anterior:** (**Módulo Presença do clube**: novo item **"Presença"** no menu
(Diretor) → escolhe o **evento** → **lista de todos os aventureiros** do clube com **foto grande** e botão
**Marcar** (toggle presente/ausente, sem recarregar); **clicar na foto** abre a foto ampliada num **modal**.
Busca em tempo real e contador "presentes X de Y". É **independente** do check-in de inscrição do evento
complexo. Model `PresencaEvento` (existência = presente; mig. **0017**). Também **ativada a guarda de
exclusão**: evento com **presença marcada** não pode ser excluído (fecha o item pendente da Fase 5.4).
Antes: Refinos de UX dos eventos)

**Anterior:** (**Refinos de UX dos eventos**: (1) a **barra de abas do painel** virou
um **card/toolbar** (fundo, borda, cantos arredondados), com a aba de seção ativa **preenchida** em azul e
um **divisor** antes das abas de ação (Dia do evento / Vender no balcão / Operadores) — fica claro que são
os botões do painel; (2) o console **"Dia do evento"** ganhou **atalhos de balcão** no topo (**Nova
inscrição (balcão)** e **Vender na lojinha**), para o atendente vender/inscrever sem sair da tela. Também
**confirmado** que a lojinha (botão "Comprar na loja" e seção "Quer levar algo da lojinha?") **já** só
aparece quando há produtos ativos. Antes: Fase 5.4d (contadores do dia no painel; Fase 5.4 concluída))

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
  vínculo) e um resumo por aventureiro. Tem contadores (Responsáveis/Aventureiros/**Ativos**) e
  **pesquisa inteligente** em tempo real (ignora maiúsculas/acentos). **Ao clicar em qualquer card**
  (responsável ou aventureiro), abre um **modal responsivo** (tela cheia no celular) com **todos os
  dados** daquela pessoa — no responsável: CPF, e-mail, celular/WhatsApp, papéis e aventureiros
  vinculados; no aventureiro: dados pessoais, documentos, endereço, pai/mãe/responsável, ficha médica,
  termo de imagem e foto (reaproveita o parcial `_aventureiro_detalhe.html` de "Meus Dados"). Como é
  restrita ao Diretor, aqui é permitido exibir dados sensíveis. O item de menu "Usuários" aparece só
  para o diretor.
- **Perfis/permissões**: `core/permissoes.py` (`eh_diretor` + decorator `diretor_required`) e o context
  processor `core/context_processors.py` (`is_diretor` e `eventos_menu` em todos os templates — o
  primeiro para `{% if is_diretor %}`, o segundo para a seção "Eventos ativos" do menu).
- Módulo **Eventos** (`/eventos/`, **restrito ao Diretor**): lista os eventos do clube em cards
  (nome, tipo, data, horário, local, descrição) e permite **criar evento**. O botão "Criar evento"
  abre um **modal** para escolher o tipo: **Evento simples** (implementado) ou **Evento com inscrição**
  (marcado como "Em breve"). O cadastro de evento simples (`/eventos/novo/`) tem nome, local, descrição,
  data, horário de início e término. Cada evento na lista tem um botão **Duplicar** que abre o
  formulário já preenchido com aquele evento (`?duplicar=<id>`), para recadastrar algo recorrente
  mudando só a data/horário. Menu "Eventos" aparece só para o diretor. Cada evento tem também um botão
  **Excluir** (🗑️) que aparece **apenas quando o evento está "vazio"** (sem nenhuma inscrição, sem
  nenhum pedido **e sem presença marcada**); a exclusão pede **confirmação** e mostra **toast**. Eventos
  com inscrições/pedidos/presença **não** têm o botão (são preservados). A view (`evento_excluir_view`, POST) revalida a regra no
  servidor e a exclusão remove em cascata a configuração do evento (custos, produtos, faixas, campos,
  operadores).
- **Evento complexo (com inscrição) — Fase 1**: no modal de "Criar evento", a opção **"Evento com
  inscrição"** cria um evento `tipo=inscricao` (com data/hora de início **e término**, para eventos de
  vários dias) e leva ao **painel do evento** (`/eventos/<id>/`). O painel tem **abas** (Resumo,
  Inscrições, Lojinha, Custos, Financeiro): **Resumo** mostra indicadores (inscritos, arrecadação,
  vendas, receitas, custos e **resultado** — verde/vermelho); **Custos** permite adicionar custos
  (título, descrição, valor e **comprovante** anexo) e removê-los, com o total refletindo no resultado.
  (Lojinha e Financeiro **já implementados** — ver adiante.) O plano completo (todas as fases) está em
  `docs/PLANEJAMENTO_EVENTO_COMPLEXO.md`. Pagamentos ficam simulados por ora.
- **Evento complexo — Fase 2.1 (fundação das inscrições)**: a aba **Inscrições** do painel deixou de
  ser "em breve" e agora tem a **configuração da inscrição** do evento: **local** (obrigatório no
  evento com inscrição), **aberto ao público geral?** (sim = qualquer pessoa; não = só membros do
  clube), **prazo limite de inscrição** (data/hora) e **valor da diretoria** (valor fixo que a
  diretoria paga, independe da idade; vazio = sem valor especial, 0 = grátis). Mostra um **status**
  ("✅ Abertas" / "⛔ Encerradas") com a data-limite: passado o prazo (ou, se vazio, o fim do evento),
  trava automaticamente. Também gerencia **faixas etárias com valores** por evento (rótulo opcional +
  idade mín/máx + valor), adicionadas por modal e removíveis — cada evento define as suas.
- **Evento complexo — Fase 2.2 (formulário de inscrição personalizável)**: na mesma aba "Inscrições",
  subseção **"Formulário de inscrição"**, o Diretor monta os **campos personalizados** do evento:
  pergunta/rótulo, **tipo** (texto curto, texto longo, número, escolha única, escolha múltipla,
  sim/não, data), **opções** (só para escolha única/múltipla), **obrigatório?** e **por participante?**
  (se marcado, o campo é perguntado em cada participante; senão, uma vez, junto do responsável). Os
  campos são adicionados por modal, **reordenáveis** (▲▼) e removíveis.
- **Evento complexo — Fase 2.3 (evento no menu de todos os perfis + página do evento)**: todo evento
  com inscrição **ainda não encerrado** aparece numa seção **"Eventos ativos"** no menu lateral de
  **todos os perfis logados** (responsável, diretor, tesoureiro, secretário, professor), com o nome do
  evento levando à **página do evento** (`/eventos/<id>/pagina/`). Eventos passados somem do menu
  sozinhos. A página do evento é uma **página própria** (sem a barra lateral) com nome, descrição,
  local (com botão **"Ver no mapa"** que abre o Google Maps no endereço), datas/horários, **status**
  das inscrições (aberto/encerrado + prazo), **valores** (faixas + diretoria) e **preview dos campos**
  do formulário. **Acesso**: evento **aberto ao público** → sem login; **só membros** → exige login.
- **Evento complexo — Fase 2.4 (inscrição de fato — Fase 2 CONCLUÍDA)**: na página do evento,
  "Inscrever-se" abre o **formulário de inscrição** (`/eventos/<id>/inscrever/`) com dados do
  responsável + **participantes** (linhas repetíveis: nome + idade + opção "diretoria") + os **campos
  personalizados** (os "uma vez" junto do responsável; os "por participante" dentro de cada
  participante). O **preço** de cada participante é calculado no servidor (faixa pela
  idade ou valor da diretoria) e somado no **valor total**. A inscrição nasce **confirmada**, com
  **código único**, e mostra uma **tela de sucesso** (pagamento **simulado**). No painel, a aba
  "Inscrições" tem a **lista de inscritos** (com participantes/valores, respostas e ação **Cancelar**)
  e o **Resumo** conta **inscritos** (participantes confirmados) e **arrecadação** de verdade. Acesso:
  público sem login se aberto ao público, senão exige login; após o prazo, o formulário trava.
- **Evento complexo — copiar a lista de inscritos**: no cabeçalho da sub-aba "Lista de inscrições", dois
  botões levam a lista para fora do sistema, sem gerar arquivo. **📋 Copiar lista** copia uma linha por
  **pessoa** inscrita, em **colunas separadas por TAB** (nº, participante, idade, WhatsApp, inscrição,
  responsável) — cola direto em planilha (Excel/Sheets quebram em colunas ao colar texto tabulado). **📋
  Copiar por inscrição** copia a lista **agrupada por família** (responsável + WhatsApp + código numa linha,
  participantes com idade abaixo), no mesmo desenho do aviso interno — é o formato de colar no WhatsApp. Só
  inscrição **confirmada** entra (cancelada fica fora; quem vai pagar por fora entra, porque está inscrito) e
  os botões só aparecem quando há alguém confirmado. O texto é montado no **servidor**
  (`_export_inscritos_evento`) e vai no HTML em `<textarea class="copiar-fonte">` fora da tela; o JS só copia,
  com toast padrão e "✅ Copiado!" no botão (fallback de `select()` + `execCommand` como no código Pix).
- **Evento complexo — Lojinha Fase 4.1 (cadastro de produtos)**: a aba **"Lojinha"** do painel permite
  cadastrar **produtos** com **variações** (cada uma com seu **preço**) e **controle de estoque
  opcional** por produto (quando ligado, cada variação tem quantidade). Produto tem nome, descrição,
  **foto** opcional e "à venda" (liga/desliga). Cadastro em página dedicada com linhas de variação
  repetíveis; a coluna "Estoque" aparece só se "Controlar estoque" estiver marcado.
- **Evento complexo — Lojinha Fase 4.2 (comprar na página do evento)**: botão **"Comprar na lojinha"**
  na página do evento abre a **loja** (`/eventos/<id>/loja/`) com os produtos ativos, **quantidade por
  variação** e **total ao vivo**; ao finalizar (dados do comprador), o **pagamento é simulado**, gera
  **código**, **baixa o estoque** dos produtos que controlam e mostra tela de sucesso. Acesso igual ao
  evento (público sem login; só-membros com login); a loja fica aberta **enquanto o evento não
  terminou**. No painel, a aba "Lojinha" lista os **pedidos** (com itens e **cancelar** — devolve ao
  estoque) e o **Resumo** conta **"Vendas (lojinha)"** (entra em receitas/resultado).
- **Evento complexo — Lojinha: fluxo de pagamento online (simulado)**: a compra pela **página pública**
  do evento (cliente final, para chegar já pago e **evitar fila** na retirada) ganhou um passo de
  pagamento. Na loja, o **WhatsApp é obrigatório** (e-mail opcional) e os **dados do comprador são
  lembrados** no próprio aparelho (localStorage — celular e PC) para não redigitar em pedidos
  seguintes; a pessoa escolhe a **forma de pagamento** (**Pix** ou **Cartão de crédito**). Ao
  "Ir para o pagamento", abre a **tela de pagamento** (`/eventos/<id>/loja/pagamento/`): no **Pix**,
  a tela clássica com **QR Code (simulado/decorativo)** e **código "copia e cola"** com botão
  **Copiar**; no **cartão**, um aviso de que **em produção** haverá **redirecionamento ao Mercado
  Pago** (integração futura). O botão **"Simular pagamento aprovado"** confirma o pedido. O
  **`PedidoLoja` só é criado no banco após a aprovação** (enquanto pendente fica na **sessão** —
  sem pedido "pendente" nem estoque reservado por carrinho abandonado); só então baixa o estoque
  (revalidado) e mostra a **tela de sucesso melhorada** (lista dos itens, total e "Pago com Pix/
  Cartão"). O QR e o "copia e cola" são **simulados** (sem biblioteca externa); o pagamento real
  virá com o gateway. Escopo: **só a loja pública** (o PDV/balcão e a inscrição seguem como estavam).
- **Evento complexo — Lojinha Fase 4.3 (comprar junto da inscrição + pedir mais)**: no fim do
  formulário de inscrição há uma seção **opcional** "Quer levar algo da lojinha?" (quantidade por
  variação + subtotal ao vivo); ao confirmar, cria a inscrição **e** um **pedido vinculado** (mesma
  transação, baixa de estoque; se faltar estoque, nada é criado). As telas de sucesso (inscrição e
  pedido) trazem botão **"Comprar (mais) na lojinha"** para pedir mais facilmente. O pedido vinculado
  (`PedidoLoja.inscricao`) aparece na lista de pedidos e conta em "Vendas (lojinha)".
- **Evento complexo — Lojinha Fase 4.4a (PDV / balcão)**: tela **"PDV / Balcão"** (`/eventos/<id>/pdv/`,
  botão na aba Lojinha) para registrar vendas no dia: monta o pedido, escolhe **forma de pagamento**
  (**Dinheiro** com **valor recebido → troco automático**, Pix, Cartão, **Cortesia**), **vínculo
  opcional** a uma inscrição (rastreabilidade) e registra (baixa estoque; cortesia não soma em vendas).
  **Restrito ao Diretor** por ora.
- **Evento complexo — Lojinha Fase 4.4b (PDV inscrição + relatório)**: botão **"Nova inscrição
  (balcão)"** na aba Inscrições → tela onde o atendente faz a **inscrição presencial** e, opcional,
  **adiciona itens da lojinha**, tudo num **pagamento só** (forma + **troco** sobre o total combinado;
  **total ao vivo**). Cria a inscrição + pedido de lojinha vinculado; cortesia deixa grátis (baixa
  estoque). No **Resumo**, tabela **"Vendidos por produto"** (Qtd conta tudo, inclusive cortesia;
  Arrecadado só o dinheiro). Restrito ao Diretor por ora.
- **Evento complexo — Lojinha Fase 4.4c (operadores do evento) — CONCLUI a Lojinha**: o Diretor define,
  por evento (botão **"Operadores"** na aba Lojinha), quem opera o PDV: **diretoria selecionada** e/ou
  **ajudantes externos** (conta temporária com senha inicial **`1234`**, **troca obrigatória no 1º
  acesso**, **reset** pelo Diretor). O operador acessa a landing **"Operar"** (`/eventos/<id>/operar/`)
  → PDV de venda e/ou inscrição. O **ajudante externo** vê **só o(s) evento(s) dele** no menu e cai
  direto no "Operar". Menu lateral **centralizado** em `_menu.html`; middleware força a troca de senha.
- **Evento complexo — Fase 5 (Financeiro) — parte 1: extrato completo**: a aba **"Financeiro"** do
  painel deixou de ser "em breve" e virou o **extrato/prestação de contas** do evento. Mostra: o
  **Resultado** em destaque (**Entradas − Saídas = Resultado**, verde/vermelho, com selo Lucro/Prejuízo/
  Zerado); **resumos** em cards (**por fonte** — inscrições × lojinha; **por forma de pagamento** —
  dinheiro/Pix/cartão/cortesia/online, com quantidade; **por canal** — online × balcão; **saídas** —
  total de custos + botão que leva à aba Custos); a tabela **"Vendidos por produto"** (movida do
  Resumo); e o **Extrato** — lista **cronológica** de **todos** os lançamentos (cada inscrição, pedido e
  custo), com data, tipo (badge), código, forma, canal e valor (**+ verde** para entradas, **− vermelho**
  para saídas). **Cancelados aparecem** no extrato (riscados, com selo "cancelado") para auditoria, mas
  **não entram nos totais** (só contam confirmados; cortesia soma R$ 0). Divisão de responsabilidades
  definida: **número/tabela mora no Financeiro; gráfico mora no Resumo/dashboard**. Custos continuam
  sendo **cadastrados** na aba Custos (o Financeiro só consolida).
- **Evento complexo — Fase 5 (Financeiro) — parte 2: Resumo/dashboard**: a aba **"Resumo"** virou um
  **dashboard** visual e didático. Tem: **KPIs repaginados** (ícones; Receitas em verde, Custos em
  vermelho, Resultado em destaque verde/vermelho); **gráficos em CSS/SVG puro, sem bibliotecas** —
  **Receitas × Custos** (barras verde/vermelho + resultado), **Entradas por forma de pagamento** e
  **Inscritos por faixa etária** (barras azul, com valor rotulado); e um painel **"Aventureiros do clube
  neste evento"** com um **donut** ("X de Y inscritos", %) e duas listas — **Inscritos** e **Ainda não
  inscritos** — dos aventureiros cadastrados no clube, com **busca em tempo real**. O casamento é por
  **conjunto de nomes** (tokens sem acento/caixa/conectores, helper `_nome_casa`): o participante casa com
  o aventureiro quando **todos os nomes digitados são cobertos** por tokens do nome cadastrado **e** isso
  aponta para **um único** aventureiro. O casamento é **ciente de iniciais** — um token de 1 letra casa
  com um token que começa por ela (ex.: "Alice **Z** Moreira" casa com "Alice **Zanatta** Moreira") — e,
  quando um nome curto serve para mais de um, **desambigua pelo sobrenome do responsável** (ex.: "Beatriz"
  + responsável "…Staine" → "Beatriz Gonçalves Staine"). Se ainda restar mais de um, vira **"a conferir"**
  — e agora a tela **lista** cada caso (participante + inscrição + os candidatos), em vez de só um contador.
  Ainda é **melhor esforço** (inscrição guarda nome livre) — o vínculo exato/manual pode vir depois. A
  cobertura conta **só aventureiros ativos** (os inativos/desligados saem do total do clube). A aba **Inscrições** ganhou uma **busca** sobre a lista (por responsável/participante) para
  responder "fulano se inscreveu?" (quando não acha, **a lista some** e aparece só "nenhuma inscrição
  encontrada"). Cor segue a regra: barras de magnitude em **um tom** (azul) e status (verde/vermelho)
  sempre com **rótulo** (cor nunca é a única pista).
- **Evento complexo — Fase 5.3 (Cupons de desconto)**: aba **"Desconto"** no painel (Diretor) para
  **gerar cupons** — informa a **% de desconto**, a **quantidade** (stepper − / +, **até 5 por vez**; ao
  passar de 5, toast "no máximo 5 cupons por vez") e a **faixa etária** a que o cupom se aplica (ou
  "qualquer faixa"). A **lista** mostra cada cupom com a **faixa**, o **percentual** e o **status**
  (Disponível / "Usado por FULANO · −R$ X") e permite remover os não usados. O cupom vale **só para
  inscrição** (não na lojinha) e é de **uso único**.
  - **Cupom por participante**: nos formulários de inscrição (**online** e **balcão/PDV**) cada
    participante tem seu **próprio campo de cupom** — o desconto vale **só para aquele participante** (o
    usuário escolhe em quem aplicar). Pode haver mais de um cupom por inscrição (um por participante).
  - **Validação ao vivo**: ao digitar/sair do campo, o sistema valida no servidor (endpoint JSON
    `evento_cupom_validar`, que **não grava nada**) e mostra o **toast padrão** — verde quando aplicado
    (com o **desconto em R$**) ou vermelho quando inválido. O **total** já **abate** o desconto na hora e
    um resumo mostra **"Cupons: −R$ X"** (vale para online **e** balcão).
  - **Faixa etária**: se o cupom é restrito a uma faixa e a idade do participante não casar, aparece o
    erro "**Cupom é só para <faixa>**" (no ao vivo e ao enviar). **Cortesia** (balcão) ignora o cupom.
  - **Uso único**: o cupom só é marcado como usado ao **confirmar** a inscrição (o servidor revalida —
    não há cupom "reservado" por formulário aberto). Guarda quem usou, **qual participante**, valor e
    vínculo à inscrição; aparece na inscrição (painel) e na tela de sucesso. Models `CupomDesconto.faixa`
    e `.participante` (migration `0015`; base era a `0014`).
- **Evento complexo — Fase 5.4 (Check-in + Retirada: console "Dia do evento")**: tela **"Dia do evento"**
  (`/eventos/<id>/dia/`, botão na barra de abas do painel e na landing "Operar"), aberta ao **Diretor e
  aos operadores** do evento. Serve para o dia do evento: por **família** (inscrição confirmada), lista os
  **participantes** com o **check-in** (Marcar chegada ↔ ✅ Chegou) e os **itens da lojinha comprados**
  com a **retirada** (Não entregue / Parcial (x/y) / ✅ Entregue). Os pedidos são casados à inscrição por
  **vínculo direto** (`PedidoLoja.inscricao`) ou **mesma conta única** (mesma regra do painel; helper
  `_casar_pedidos_inscricoes`); os **pedidos avulsos** (passantes, sem dono) aparecem numa **seção
  separada**. Tem **resumo do dia** (check-in X/Y + retiradas X/Y) e **busca** em tempo real
  (responsável/participante/código).
  - **5.4a** (só leitura): os campos de modelo e a tela de consulta. Novos campos:
    `ParticipanteInscricao.presente`/`presente_em`/`presente_por` e `ItemPedidoLoja.quantidade_entregue`/
    `entregue_em`/`entregue_por` (props `entregue`/`entrega_parcial`/`status_entrega`; migration **0016**).
  - **5.4b** (marcar): dá para **marcar check-in por participante** e **entrega por unidade** direto na
    tela, **sem recarregar** — o **selo é clicável** (entrega/desfaz tudo) e itens com mais de 1 têm
    **stepper − x/y +** (entrega parcial). Endpoints JSON `evento_checkin` e `evento_entrega` (POST,
    `@operador_required`, validam que o participante/item é do evento e de inscrição/pedido **confirmado**,
    limitam a entrega a 0..quantidade) atualizam a linha e o **resumo do dia** ao vivo; guardam **quem
    marcou e quando** (`presente_por`/`presente_em`, `entregue_por`/`entregue_em`). Parcial: `_dia_entrega.html`
    (parcial reutilizado nas duas seções) + `evento_dia.js` (fetch com `X-CSRFToken`).
  - **5.4c** ("vai levar agora?" no balcão): tanto o **PDV de vendas** (`evento_pdv`) quanto o **PDV de
    inscrição** (`evento_pdv_inscricao`) têm um checkbox **"Entregar os itens agora"** (marcado por
    padrão). Marcado → o pedido já nasce **entregue** (`quantidade_entregue = quantidade` + quem/quando);
    desmarcado → itens ficam **pendentes** para retirar depois no console. Implementado com o parâmetro
    `entregar_agora` no helper `_criar_pedido` (usado pelos dois PDVs).
  - **5.4d** (contadores no painel — encerra a Fase 5.4): a aba **Resumo** tem o painel **"📋 Dia do
    evento"** com **check-in** (presentes X/Y) e **retiradas** (itens entregues X/Y) + botão **"Abrir
    console"** (só quando há participantes/itens) — helper `_resumo_dia` reusado no contexto do painel
    (`dia`). **Guarda de exclusão**: o evento complexo já é protegido (não exclui com inscrições/pedidos —
    cobre presença/entrega); guarda por presença em **evento simples** fica como futuro (não há presença
    em evento simples ainda).
  - **Atalhos de balcão no console** (refino): o topo do "Dia do evento" tem os botões **"Nova inscrição
    (balcão)"** (`evento_pdv_inscricao`) e **"Vender na lojinha"** (`evento_pdv`) — para o atendente
    vender/inscrever sem sair da tela. Gates: inscrição enquanto o evento não terminou; venda quando a loja
    está aberta e há produtos ativos (contexto `pode_inscrever`/`pode_vender`). Os atalhos passam
    **`?de=dia`**; nas telas de PDV o botão **Voltar** então retorna ao **"Dia do evento"** (o `de` é
    preservado no redirect após registrar).
  - **Barra de abas em card** (refino): a `.painel-abas` virou um card/toolbar (fundo/borda/cantos), aba de
    seção ativa **preenchida** em azul e **divisor** antes das abas de ação — deixa claro que são os botões
    do painel.
- **Evento complexo — Compras da lojinha por inscrição**: na aba **Inscrições** do painel, cada inscrito
  mostra (ao expandir) um bloco **"Compras na lojinha"** com os pedidos daquela pessoa — casados por
  **vínculo direto** (`PedidoLoja.inscricao`) **ou pela mesma conta logada** (`pedido.usuario ==
  inscricao.usuario`, só quando o responsável tem **uma** inscrição no evento, para não atribuir errado).
  Cada pedido lista os itens e o valor; os da mesma conta ganham a etiqueta "· mesma conta". Mostra o
  **Total geral (inscrição + lojinha)** e uma **pílula 🛒** no topo com o gasto na lojinha. Pedidos
  **avulsos** (passante, sem conta/vínculo) não são atribuídos e continuam só na aba **Lojinha**.
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
- **Migração de eventos (por evento, com conciliação bancária)**: o **"ACAMPAMENTO 2026"** (evento 7 do
  sistema antigo) foi migrado para o **evento 60** — dados do evento + 5 faixas + **24 inscrições reais**
  com **valor recebido conciliado contra o extrato** (Mercado Pago): R$ 4.597,41 (14 Pix + 3 cartão + 7
  cortesia/diretoria), `forma_pagamento` e **data original** preservadas. Feito por scripts one-off
  (parser do extrato + matcher + Artifact de revisão), sem comando versionado (conciliação é manual). Os
  **extratos bancários** (`EXTRATOS/`) são dados financeiros e **não** vão ao Git (`.gitignore`). Também
  migrados os **9 custos** do evento (R$ 4.723,50) com nome/valor/data — **Resultado do acampamento =
  −R$ 126,09** — e os **9 comprovantes anexados** (contrato da chácara, invoices, fotos das compras),
  trazidos do export atualizado ("com_arquivos") e copiados para `media/eventos/custos/` (git-ignored).
  Também migrado o **"Passaporte da Diversão"** (evento 6 antigo → **evento 62**): faixas (1-4=R$20 /
  5-12=R$40), **51 inscrições / 69 crianças** (R$ 2.500), **4 produtos da lojinha com fotos** + 13
  variações, **vendas R$ 1.825,50** (229 itens; só pagas e não-teste) com **retirada por item** preservada,
  e custos R$ 607,12 (3 do antigo R$ 183,39 + **taxa de cartão/Pix do Mercado Pago R$ 423,73** lançada como
  custo). **Resultado = R$ 3.718,38**. Conferido contra o **relatório PDF do sistema antigo** (bruto/loja/
  inscrições/faixas/líquido idênticos). Valores corretos do antigo (sem conciliação bancária).
  **Cuidado aprendido**: no sistema antigo a **inscrição é um item do pedido da loja** ("Inscricao do
  evento") — não contar como venda; e a **idade** pode vir como texto ("6 anos") — parsear o número.
  Próximo: migrar os eventos restantes (ids 2/4/5 "Reunião do Clube"), um a um.
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
- Mensagens de feedback via framework de messages do Django, exibidas como **toasts flutuantes**
  (canto superior direito / topo no celular) que somem sozinhos ou ao clicar. Toda ação relevante do
  módulo de eventos gera uma notificação (sucesso/erro/info).
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
  **`inscricao_aberta_publico`**, **`inscricao_limite`** (prazo), **`valor_diretoria`** e
  **`formas_pagamento_online`** (`ambos`/`pix`/`cartao`, padrão `ambos` — o que o **site** aceita neste
  evento; migration **`0062`**). Métodos `fim_datetime()`, `prazo_inscricao()`, `inscricoes_abertas()`,
  **`formas_online()`** (lista `(valor, rótulo)` filtrada, para montar a tela) e
  **`aceita_forma_online(forma)`** (validação do POST — esconder o rádio no HTML não impede envio forjado).
  O **PDV/balcão não usa** essas duas últimas: lá o operador segue com dinheiro/cortesia (variável `formas`).
  Também: **`ativo`** (liga/desliga o evento para o público, mig. **0063**); **`formas_pagamento_fora`** +
  **`instrucoes_pagamento_fora`** (formas pagas direto ao evento, mig. **0065**/**0066**; métodos
  `formas_fora()`, `forma_paga_por_fora(forma)` e a property `tem_pagamento_por_fora`); e o aviso interno de
  inscrição **`notificar_inscricoes`** + **`notificar_inscricoes_para`** (FK User da diretoria que recebe a
  lista de inscritos a cada inscrição, mig. **0067**); e **`parcelas_diretoria`** (em quantas vezes a parte da
  diretoria pode ser paga, mig. **0068**; `1` = à vista, padrão) com os métodos
  **`permite_parcelar_diretoria()`** (exige `parcelas_diretoria > 1` **e** `valor_diretoria` definido) e
  **`dividir_parcelas(total)`** (divide somando exatamente o total, com a sobra dos centavos na 1ª parcela).
  E o prazo próprio da diretoria: **`inscricao_limite_diretoria`** (mig. **0069**) + os métodos
  **`prazo_inscricao_diretoria()`** (o `max` entre ele e o prazo comum — **só estende, nunca restringe**),
  **`prazo_inscricao_efetivo(tem_diretoria)`**, **`inscricoes_abertas(tem_diretoria=False)`** e as properties
  **`tem_prazo_diretoria`** (True só quando estende de fato) e **`so_diretoria_pode_inscrever`**. Uma inscrição
  com diretoria vale por esse prazo **inteira** (o aventureiro que entra junto aproveita a janela).
  Migrations `0002`, `0003`, `0004`, `0062`, `0063`, `0065`, `0066`, `0067`, `0068`, `0069`.
- `CustoEvento` — custo/despesa de um evento (FK `evento`, nome, descrição, valor, comprovante,
  `criado_por`). Migration `0003_evento_data_fim_custoevento`.
- `FaixaEtariaPreco` — faixa etária com valor de inscrição, por evento (FK `evento`, rótulo,
  idade_min, idade_max, valor, ordem). Migration `0004`.
- `CampoInscricao` — campo personalizado do formulário de inscrição, por evento (FK `evento`, rótulo,
  tipo, opções, obrigatório, **por_participante**, ordem). Migrations `0005`, `0007`.
- `PerfilUsuario` — OneToOne com User (`precisa_trocar_senha`, usado pelas contas temporárias;
  **`whatsapp_principal_origem`** = pai/mãe/resp legal, para onde vai o código de recuperação, mig.
  **0020**). E `OperadorEvento` — quem opera o PDV de um evento (FK `evento`, FK `usuario`, `externo`). Migration `0013`.
- `Inscricao` — inscrição num evento (FK `evento`, FK `usuario` opcional, dados do responsável, código
  único, status, **origem** online/pdv, **forma_pagamento**, **valor_recebido**, **registrado_por**,
  valor_total; props `total_com_loja`/`troco`). Migration `0012`. Também **`token_parcelas`** (token do link
  público das parcelas, mig. **0068**, criado por `get_token_parcelas()`) e as props do parcelamento:
  **`parcelado`**, **`parcelas_abertas`**, **`total_parcelas_aberto`**, **`valor_no_ato`** (o que entrou no dia
  da inscrição — total menos TODAS as parcelas 2..N) e **`valor_no_caixa`** (total menos as parcelas **em
  aberto**). **Toda soma de caixa de inscrição usa `valor_no_caixa`**; o extrato usa `valor_no_ato` mais um
  lançamento por parcela paga. `ParticipanteInscricao` (nome, idade, eh_diretoria,
  faixa, valor + **check-in**: `presente`/`presente_em`/`presente_por`, mig. `0016`) e `RespostaInscricao` (FK `inscricao`, FK `participante` opcional, campo + rótulo
  snapshot + valor). Migrations `0006`, `0007`. Respostas de campos "por participante" têm
  `participante` preenchido; as de campos "uma vez" ficam com `participante` nulo.
- `ParcelaInscricao` — uma parcela do valor da **diretoria** numa inscrição (FK `inscricao`, `numero`/`total`,
  valor, `vencimento`, status aberta/paga/cancelada, `forma_pagamento`, `valor_pago`, `pago_em`,
  `registrado_por`, FK `pagamento`; props `rotulo`, `em_aberto`, `vencida`; único por inscrição+número).
  Migration **0068**. Só existe em inscrição parcelada: a **1ª nasce paga** (cobrada no ato junto do resto) e as
  seguintes vencem mês a mês. Cada parcela paga online tem **o seu** `Pagamento` (tipo `parcela_inscricao`),
  então a baixa e a taxa do gateway ficam individuais.
- `ProdutoEvento` — produto da lojinha do evento (FK `evento`, nome, descrição, foto, controla_estoque,
  ativo, ordem) e `VariacaoProduto` (FK `produto`, nome, valor, estoque, ordem). Migration `0008`.
  O preço fica em cada variação; estoque só conta quando `controla_estoque` está ligado.
- `PedidoLoja` — pedido da lojinha (FK `evento`, FK `usuario` opcional, **FK `inscricao` opcional**,
  dados do comprador, código, status, **origem** online/pdv, **forma_pagamento**, **valor_recebido**,
  **registrado_por**, valor_total; property `troco`) e `ItemPedidoLoja` (FK `pedido`, FK `variacao`
  opcional + snapshots de nome, quantidade e valores + **retirada por unidade**:
  `quantidade_entregue`/`entregue_em`/`entregue_por`, props `entregue`/`entrega_parcial`/`status_entrega`,
  mig. `0016`). Migrations `0009`, `0010`, `0011`.
- `CupomDesconto` — cupom de desconto de **inscrição** (FK `evento`, `codigo` único, `percentual`,
  `ativo`, FK **`faixa`** opcional = faixa etária a que se aplica, FK `inscricao` opcional = onde foi
  usado, FK **`participante`** opcional = quem usou, `usado_por`, `valor_desconto`, `usado_em`,
  `criado_por`; property `usado`). Uso único; aplica em **1 participante** (o que o usuário escolher,
  digitando o código na linha dele). Migrations `0014` (base) e **`0015`** (`faixa` + `participante`).
- `Aventureiro.ativo` (BooleanField, default True; mig. **0018**) — aventureiro ativo/inativo (desligado).
  Ao desligar, a conta (`usuario`) é desativada se não sobrar nenhum aventureiro ativo. A Presença lista só
  aventureiros ativos.
- `PresencaEvento` — presença de um **aventureiro** do clube num **evento** (FK `evento` related_name
  `presencas`, FK `aventureiro`, `marcado_em`, `marcado_por`; `unique_together` evento+aventureiro). A
  **existência do registro = presente**. Independente do check-in de inscrição do evento complexo. Usado
  pelo módulo **Presença** e pela **guarda de exclusão** de eventos. Migration **0017**.
- `WhatsappConfig` — configuração do gateway **W-API** (**linha única/singleton** via `get_solo()`,
  `pk=1`). Campos: `instance_id`, `token`, `base_url` (default `https://api.w-api.app/v1`),
  `atualizado_por`/`atualizado_em`. Propriedades: `configurado` (tem ID + token) e `token_mascarado`
  (só os últimos 4 dígitos). Usado pelo módulo **WhatsApp**. Migration **0019**.
- **Loja do Clube** (loja oficial, independente da lojinha de evento; mig. **0021**):
  - `ProdutoLoja` — produto da loja (nome, descrição, foto, `composto`, `controla_estoque`, `ativo`, ordem).
    Props `variacoes_ativas`, `preco_minimo`, `preco_base` (estimativa "a partir de" somando obrigatórios).
  - `GrupoLoja` — grupo de variações de um produto (FK `produto`, nome, `modo` = `unica`/`itens`,
    `obrigatorio`, `orientacao`, ordem). Produto simples = 1 grupo padrão.
  - `VariacaoLoja` — opção de um grupo (FK `grupo`, nome, valor, estoque, `obrigatorio` [itens], `ativo`,
    ordem). Props `rotulo`, `esgotado`.
  - `CompraLoja` — compra (FK `usuario`, dados do comprador, código `LC…`, status, `forma_pagamento`,
    `valor_total`; props `status_entrega`/`falta_entregar_total`). `ItemCompraLoja` — item (FK `compra`/
    `produto`/`variacao`/`aventureiro` + snapshots + `quantidade`/valores + `kit` = agrupa itens de um kit +
    **entrega** `quantidade_entregue`/`entregue_em`/`entregue_por`, props `entregue`/`status_entrega`/
    `falta_entregar`, mig. **0023**). Pedidos migrados do sistema antigo usam código `LM<id>`.
  - `FotoProdutoLoja` — foto da **galeria** de um produto (FK `produto`, `imagem`, `ordem`; a 1ª é a capa,
    via property `ProdutoLoja.capa`). Mig. **0022**. Suporta várias fotos + lightbox na vitrine.

## Funcionalidades incompletas / não implementadas
- Recuperação de senha ("Esqueci minha senha") — **IMPLEMENTADA** pelo WhatsApp (código de 4 dígitos).
  Falta permitir que o **responsável logado** altere o próprio WhatsApp principal (hoje só o Diretor).
- Edição dos dados do aventureiro pela área logada — hoje "Meus Dados" é somente visualização.
- Validação avançada de CPF — NÃO implementada (deixada para o futuro).

> **Corrigido em 2026-08-12:** esta lista dizia que **perfis de usuário** e **envio de e-mail** não estavam
> implementados. Os dois estão prontos há tempo — perfis (5 grupos, `core/menus.py`, seletor "Ver como") e
> e-mail (`core/email_envio.py`, tela `/email/`, gate anti-spam, `LogEmail`). A seção tinha ficado para trás.

### Dívida técnica conhecida (levantada em 2026-08-12)
- **Sem proteção contra brute force**: o login não tem throttle; e a **etapa 1 da recuperação de senha**
  dispara **um WhatsApp real por POST**, sem limite — risco de a W-API bloquear o número do clube.
  **Ficou mais caro em 15/08**: como a etapa 2 passou a mostrar o **usuário de acesso**, quem tiver o CPF de
  um responsável também descobre o login. Um limite por IP/CPF nessa tela é a próxima coisa a fazer ali.
- **`SECURE_HSTS_SECONDS`** ainda sem valor (ver "Configurações importantes").
- **Ambiente local diferente do de produção** (Django 6.0.5/Python 3.14 aqui × 5.2.15/3.12 no VPS) — testar
  local não garante o comportamento em produção.
- `core/middleware.py`: `request.path.startswith("/static")` ignora o `FORCE_SCRIPT_NAME`. Hoje não morde
  porque o Nginx serve os estáticos, mas é latente.
- `core/views.py` com ~7.000 linhas; vale dividir por domínio quando houver folga.

## Próximas etapas previstas
- **🎉 Lojinha (Fase 4) concluída** (produtos, comprar na página, junto da inscrição, PDV de vendas,
  PDV de inscrição, operadores).
- **Fase 5 — Financeiro**: parte 1 (**extrato** na aba Financeiro), parte 2 (**Resumo/dashboard**:
  KPIs, gráficos CSS/SVG, cobertura do clube + buscas) e parte 3 (**cupons de desconto** — por
  participante, com faixa, geração em lote e validação ao vivo) **CONCLUÍDAS**. **Fase 5.4 (Check-in +
  Retirada) CONCLUÍDA** (5.4a console + campos; 5.4b marcar check-in/entrega; 5.4c "entregar agora" no
  balcão; 5.4d contadores do dia no painel). Guarda de exclusão por presença em **evento simples** fica
  como item futuro (depende de presença em evento simples, que não existe). **Próximos:** pagamentos reais
  (gateway) e loja oficial do clube (uniformes, separada).
- **Depois**: pagamentos reais (gateway); loja oficial do clube (uniformes) — separada da lojinha.
- **Depois**: pagamentos reais (gateway); loja oficial do clube (uniformes) — separada da lojinha de evento.
- Possíveis refinos das inscrições: gating de "diretoria" por perfil real, editar inscrição, exportar
  lista de inscritos, e-mail de confirmação.
- **Evento complexo — Fase 2.4**: inscrição de fato (participantes por faixa/diretoria, pagamento
  simulado, código), lista de inscritos no painel e contagem/arrecadação no dashboard.
- (A definir) Permitir editar os dados do aventureiro pela área logada.
- (A definir) Permitir ao responsável logado escolher o próprio WhatsApp principal (recuperação).

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
- `templates/core/evento_pagina.html` (página do evento — pública/interna, com botão de inscrever)
- `templates/core/evento_inscrever.html` (formulário de inscrição) e `evento_inscricao_sucesso.html`
- `templates/core/evento_produto_form.html` (cadastro/edição de produto da lojinha)
- `templates/core/evento_loja.html` (loja/carrinho do evento), `evento_pagamento.html` (tela de
  pagamento simulada: Pix com QR/copia-cola ou cartão) e `evento_pedido_sucesso.html`
- `templates/core/evento_pdv.html` (PDV / balcão de vendas) e `evento_pdv_inscricao.html` (PDV inscrição)
- `templates/core/_loja_itens.html` (parcial: itens da lojinha para escolher — loja, inscrição e PDV)
- `templates/core/_menu.html` (parcial: menu lateral central, usado por todas as telas internas)
- `templates/core/evento_operar.html` (landing do operador), `evento_operadores.html` (gerência) e `trocar_senha.html`
- `templates/core/evento_dia.html` (console "Dia do evento": check-in + retirada) e `_dia_entrega.html`
  (parcial: controle de retirada por unidade de um item — selo clicável + stepper)
- `templates/core/presenca_selecionar.html` (escolher evento) e `presenca_evento.html` (folha de presença:
  lista de aventureiros com foto + marcar + modal da foto ampliada)
- `templates/core/whatsapp.html` (módulo WhatsApp: configurar instância W-API + enviar mensagem de teste)
- `templates/core/recuperar_cpf.html`, `recuperar_codigo.html`, `recuperar_nova_senha.html` (recuperação
  de senha em 3 etapas; **envio por AJAX** via `ajax_form.js` — `form[data-ajax-toast]` —, com **toast
  padrão**; erro não recarrega a página)
- `templates/core/_menu_eventos.html` (parcial: seção "Eventos ativos" do menu, para todos os perfis)
- **Loja do Clube**: `loja.html` (abas Gerenciar + vitrine/carrinho), `loja_produto_form.html` (cadastro
  com grupos/variações), `loja_produto.html` (configurador + carrinho + aviso soft), `loja_pagamento.html`
  (pagamento simulado), `loja_sucesso.html`; parciais `_loja_grupo.html` e `_loja_var_linha.html`
- `templates/core/_participante_linha.html` e `_variacao_linha.html` (parciais de linha repetível)
- `templates/core/_aventureiro_detalhe.html` (parcial com o detalhe completo do aventureiro)
- `templates/core/cadastro.html` (wizard de cadastro)
- `templates/core/cadastro_sucesso.html`
- `templates/core/_campo.html` e `templates/core/_campo_check.html` (parciais de campo reutilizáveis)
- `templates/core/_dado.html` (parcial rótulo+valor usada em "Meus Dados")

## Arquivos CSS existentes
- `static/css/base.css` — regras globais de interface (linkado em todas as telas, **antes** do CSS
  da página). Torna o texto de interface **não selecionável** (sem cursor de texto/caret fora de
  campos digitáveis); mantém selecionáveis os campos de formulário e os valores de dados
  (`.dado-valor` / `.selecionavel`). Também hospeda os **componentes reutilizáveis** de **modal** (janela
  suspensa) e de **notificações/toasts** (`.mensagens`/`.mensagem`, com fallback de cores) — para o toast
  valer em qualquer página, inclusive as públicas do login/recuperação. (Antes o toast ficava no `inicio.css`.)
- `static/css/eventos.css` — tela de Eventos (lista, cards, formulário e cards de escolha de tipo).
- `static/css/login.css`
- `static/css/inicio.css`
- `static/css/cadastro.css`
- `static/css/usuarios.css` (complementa `inicio.css` na tela "Usuários")
- `static/css/presenca.css` — módulo Presença (seletor de evento, folha com foto grande + botão marcar,
  foto ampliada no modal)
- `static/css/whatsapp.css` — módulo WhatsApp (cards de configuração e de envio; inputs próprios;
  paleta azul/verde; mobile-first)
- `static/css/recuperar.css` — recuperação de senha (indicador de etapas, campo do código grande,
  link de reenvio); complementa `login.css`. As notificações usam o **toast padrão** (CSS em `base.css`).
- `static/css/loja.css` — **Loja do Clube** (abas, cards de gerenciamento, vitrine em grade, carrinho,
  cadastro de grupos/variações, configurador do produto e telas de pagamento); mobile-first; paleta azul/verde.

## Arquivos JavaScript existentes
- `static/js/cadastro.js` — wizard de etapas (numeração e índices calculados dinamicamente, servindo
  tanto ao cadastro de 7 etapas quanto ao de 6 etapas), barra de progresso, campos condicionais,
  preview da foto, atalhos (copiar pai/mãe para responsável legal), reaproveitamento dos dados dos
  responsáveis no cadastro de novo aventureiro, revisão e validação dos aceites.
- `static/js/inicio.js` — menu recolhível no celular; painéis `<details>` de "Meus Dados" (fechar ao
  clicar fora / abrir outro / `Esc`); e o **módulo único de toasts** do sistema: move `.mensagens` para
  o `<body>`, auto-fecha (~4,5s, igual à barra de progresso), fecha ao clicar e expõe
  **`window.mostrarToast(texto, tipo)`** para criar toast pelo JS (ex.: "copiado!"). É seguro em
  qualquer página (cada bloco tem guarda de elemento), por isso é carregado também nas páginas públicas
  do evento (loja, pagamento, sucesso, página do evento, inscrição) e nas telas de **recuperação de
  senha**. O CSS do toast vive no `base.css` (componente reutilizável).
- `static/js/usuarios.js` — pesquisa em tempo real na tela "Usuários" e o **modal** de dados
  completos (clona o detalhe do card, expande as seções e fecha no X/fora/Esc).
- `static/js/eventos.js` — abre/fecha o modal de escolha do tipo de evento (X/fora/Esc).
- `static/js/evento_painel.js` — abas do painel do evento complexo + modais (custo, faixa, campo);
  botões `[data-aba-ir]` (trocar de aba); e a **busca em tempo real** da cobertura do clube e da lista de
  inscrições (helper `ligarBusca`, padrão do `usuarios.js`); e a **cópia da lista de inscritos**
  (`.btn-copiar-lista` → `<textarea class="copiar-fonte">` indicada em `data-fonte`).
- `static/js/evento_inscrever.js` — linhas de participante (adicionar/remover) + campos por participante.
- `static/js/evento_produto.js` — linhas de variação (adicionar/remover) + mostrar/ocultar estoque.
- `static/js/qtd_stepper.js` — botões +/- de quantidade nas telas de compra (dispara o recálculo).
- `static/js/evento_loja.js` — total ao vivo da loja/inscrição conforme as quantidades.
- `static/js/loja_comprador.js` — lembra os dados do comprador (nome/WhatsApp/e-mail) no localStorage
  e autopreenche na loja pública (celular e PC).
- `static/js/evento_pagamento.js` — botão "Copiar" do código Pix na tela de pagamento (com fallback);
  o feedback usa o toast padrão via `window.mostrarToast`.
- `static/js/evento_pdv.js` — PDV vendas: total, forma de pagamento e troco.
- `static/js/evento_insc_cupom.js` — inscrição (online **e** balcão): total ao vivo (faixa/diretoria +
  lojinha), **cupom por participante** (validação ao vivo contra o servidor + toast + abate do total) e
  troco no balcão. Substituiu o antigo `evento_pdv_inscricao.js`.
- `static/js/evento_dia.js` — console "Dia do evento": busca em tempo real (responsável/participante/
  código) + **ações de marcar** (check-in por participante e entrega por unidade via fetch/JSON com
  `X-CSRFToken`, atualização inline dos selos/stepper e do resumo do dia).
- `static/js/presenca.js` — módulo Presença: marcar/desmarcar (fetch/JSON + `X-CSRFToken`, atualiza botão e
  contador), **modal da foto** ampliada e busca em tempo real. Ao marcar/desmarcar com sucesso, mostra o
  **toast** padrão ("<nome> — presente ✅" / "<nome> — ausente"); toast de erro em falha.
- `static/js/whatsapp.js` — módulo WhatsApp: **prévia ao vivo** do telefone normalizado, botão
  **mostrar/ocultar** token e **envio AJAX** (fetch/JSON + `X-CSRFToken`) com o **toast** padrão de
  sucesso/erro.
- `static/js/ajax_form.js` — **componente genérico**: envia qualquer `form[data-ajax-toast]` por
  **fetch**; a resposta é `{"redirect":url}` (navega) ou `{"msg","tipo"}` (só toast, sem recarregar).
  Assim o erro **repete a notificação** sem recarregar a página. Usado no **login** (senha errada) e nas
  telas de **recuperação de senha**. Fallback: sem JS, POST normal.
- `static/js/loja.js` — **Loja**: alternância das abas (Gerenciar/Loja), confirmação de ações destrutivas
  (`form[data-confirmar]`) e atalho para o carrinho.
- `static/js/loja_produto_form.js` — cadastro de produto: alternar simples/composto, adicionar/remover
  **grupos** e **opções** (índices únicos), mostrar/ocultar estoque e a coluna "obrig." por modo do grupo.
- `static/js/loja_produto.js` — configurador do produto na vitrine: **subtotal ao vivo**, **aviso soft** de
  itens obrigatórios (modal: continuar/voltar) e rascunho da seleção no localStorage (não perde ao recarregar).

## Rotas existentes
- `/` — tela de login com autenticação real (`core.views.login_view`, nome `core:login`).
- `/sair/` — logout (POST) (`core.views.sair_view`, nome `core:sair`).
- `/inicio/` — área "Meus Dados", protegida por `@login_required` (`core.views.inicio_view`, nome `core:inicio`).
- `/meus-dados/responsavel/editar/` — edição do responsável, protegida por login (`core.views.editar_responsavel_view`, nome `core:editar_responsavel`).
- `/usuarios/` — responsáveis, aventureiros e vínculos, **restrita ao Diretor** (`core.views.usuarios_view`, nome `core:usuarios`).
- `/usuarios/aventureiro/<id>/ativo/` — marca inativo/reativa um aventureiro (POST, Diretor; cascata na conta) (`core:aventureiro_toggle_ativo`).
- `/usuarios/aventureiro/<id>/termos/` — **termos assinados** do aventureiro (Diretor): monta cada termo com o texto do momento + a imagem da assinatura, página pronta pra imprimir/salvar PDF (`core.views.aventureiro_termos_view`, nome `core:aventureiro_termos`).
- `/usuarios/conta/<id>/principal/` — define o **WhatsApp principal** da conta (pai/mãe/resp legal) p/ recuperação (POST, Diretor) (`core:usuario_principal`).
- `/eventos/` — lista de eventos, **restrita ao Diretor** (`core.views.eventos_view`, nome `core:eventos`).
- `/eventos/novo/` — cadastro de evento simples, **restrita ao Diretor** (`core.views.evento_novo_view`, nome `core:evento_novo`; aceita `?duplicar=<id>`).
- `/eventos/complexo/novo/` — cria evento complexo (`core.views.evento_complexo_novo_view`, nome `core:evento_complexo_novo`).
- `/eventos/<id>/excluir/` — exclui um evento (POST, Diretor), **só se vazio** (sem inscrições/pedidos) (`core.views.evento_excluir_view`, nome `core:evento_excluir`).
- `/eventos/<id>/` — painel do evento complexo (`core.views.evento_painel_view`, nome `core:evento_painel`).
  Se o evento não existir (ex.: link antigo de um evento excluído), **redireciona** para `/eventos/` com
  um toast informativo (em vez de 404).
- `/eventos/<id>/pagina/` — página do evento (pública se aberto ao público, senão exige login) (`core.views.evento_pagina_view`, nome `core:evento_pagina`).
- `/eventos/<id>/inscrever/` — formulário de inscrição (`core.views.evento_inscrever_view`, nome `core:evento_inscrever`).
- `/eventos/<id>/inscrever/sucesso/` — confirmação da inscrição (`core:evento_inscricao_sucesso`).
- `/eventos/<id>/inscricoes/<id>/cancelar/` — cancela inscrição (POST, Diretor) (`core:evento_inscricao_cancelar`).
- `/eventos/<id>/produtos/novo/`, `.../produtos/<id>/editar/` e `.../produtos/<id>/excluir/` — lojinha: cadastro/edição/remoção de produto (Diretor).
- `/eventos/<id>/loja/` — loja do evento (comprar), `.../loja/pagamento/` (tela de pagamento simulada:
  GET mostra Pix/cartão; POST simula a aprovação e cria o pedido), `.../loja/sucesso/` (confirmação) e
  `.../pedidos/<id>/cancelar/` (POST, Diretor).
- `/eventos/<id>/pdv/` — PDV / balcão de vendas da lojinha (Diretor por ora) (`core:evento_pdv`).
- `/eventos/<id>/pdv/inscricao/` — PDV: inscrição presencial + lojinha, pagamento combinado (`core:evento_pdv_inscricao`).
- `/eventos/<id>/operar/` — landing do operador (vender/inscrever) (`core:evento_operar`, operador ou Diretor).
- `/eventos/<id>/dia/` — console "Dia do evento": check-in dos participantes + retirada dos itens (`core:evento_dia`, operador ou Diretor).
- `/eventos/<id>/dia/checkin/` — marca/desmarca check-in de um participante (POST JSON, operador/Diretor) (`core:evento_checkin`).
- `/eventos/<id>/dia/entrega/` — registra a entrega de um item por unidade (POST JSON, operador/Diretor) (`core:evento_entrega`).
- `/eventos/<id>/operadores/` — gerência de operadores (Diretor); rotas POST de add diretoria/externo, reset e remover.
- `/trocar-senha/` — troca de senha (obrigatória no 1º acesso das contas temporárias) (`core:trocar_senha`).
- `/eventos/<id>/custos/novo/` e `/eventos/<id>/custos/<id>/excluir/` — adicionar/remover custo (POST).
- `/eventos/<id>/inscricoes/config/` — salva a configuração da inscrição (POST, `core:evento_inscricao_config`).
- `/eventos/<id>/inscricoes/<id>/pago/` — baixa manual do pagamento por fora (POST, Diretor; reversível).
- `/eventos/<id>/parcelas/<id>/pago/` — baixa manual de uma **parcela da diretoria** (POST, Diretor;
  reversível). Diferente da baixa acima: aqui o valor **entra** no caixa do clube.
- `/inscricao/<token>/parcelas/` e `/inscricao/<token>/parcelas/pagar/` — **públicas** (sem login): a família
  vê as parcelas da inscrição e paga **uma por vez** (Pix/cartão). O token vem de
  `Inscricao.get_token_parcelas()`; quem se inscreve pode não ter conta no sistema.
- `/eventos/avisar-inscritos/` — envia AGORA a lista de inscritos ao integrante escolhido no evento
  (POST, Diretor; `core:evento_avisar_inscritos`). **Sem pk na URL de propósito**: o evento vem no POST,
  porque o mesmo botão é usado no painel do evento e na aba Templates do WhatsApp (com seletor de evento).
- `/eventos/<id>/inscricoes/faixa/novo/` e `/eventos/<id>/inscricoes/faixa/<id>/excluir/` — adicionar/remover faixa etária (POST).
- `/eventos/<id>/inscricoes/campo/novo/`, `.../campo/<id>/excluir/` e `.../campo/<id>/mover/` — adicionar/remover/reordenar campo do formulário (POST).
- `/eventos/<id>/descontos/novo/` e `/eventos/<id>/descontos/<id>/excluir/` — gerar (com quantidade/faixa) / remover cupom de desconto (POST, Diretor).
- `/eventos/<id>/cupom/validar/` — validação **ao vivo** de um cupom para um participante (GET, JSON; não grava) (`core:evento_cupom_validar`).
- `/presenca/` — módulo Presença: escolher o evento (Diretor) (`core.views.presenca_view`, nome `core:presenca`).
- `/presenca/<id>/` — folha de presença: lista de aventureiros com foto + marcar (`core:presenca_evento`).
- `/presenca/<id>/marcar/` — marca/desmarca presença de um aventureiro (POST JSON, Diretor) (`core:presenca_marcar`).
- `/whatsapp/` — módulo WhatsApp: configurar a instância W-API + enviar mensagem de teste (Diretor) (`core.views.whatsapp_view`, nome `core:whatsapp`).
- `/whatsapp/config/` — salva ID/token/URL base da instância (POST, Diretor; token vazio não sobrescreve) (`core:whatsapp_config`).
- `/whatsapp/enviar/` — envia uma mensagem pela W-API (POST JSON, Diretor; normaliza o telefone) (`core:whatsapp_enviar`).
- `/cadastro/` — cadastro inicial: conta + primeiro aventureiro (`core.views.cadastro_view`, nome `core:cadastro`).
- `/cadastro/novo-aventureiro/` — outro aventureiro na mesma conta (`core.views.cadastro_novo_aventureiro_view`, nome `core:cadastro_novo_aventureiro`).
- `/cadastro/sucesso/` — confirmação (`core.views.cadastro_sucesso_view`, nome `core:cadastro_sucesso`).
- `/recuperar-senha/` — recuperação de senha, etapa 1: CPF do responsável legal (`core:recuperar_senha`).
- `/recuperar-senha/codigo/` — etapa 2: digitar o código de 4 dígitos (`core:recuperar_senha_codigo`).
  Mostra também o **usuário de acesso** da conta achada pelo CPF (o mesmo vai na mensagem do WhatsApp) —
  quem esquece o login resolve aqui.
- `/recuperar-senha/reenviar/` — reenvia o código (POST, espera de 60 s) (`core:recuperar_senha_reenviar`).
- `/recuperar-senha/nova-senha/` — etapa 3: definir a nova senha 2× (`core:recuperar_senha_nova`).
- **Loja do Clube** (Diretor no menu; vitrine/carrinho `@login_required`):
  - `/loja/` — tela com abas Gerenciar/Loja (`core:loja`, Diretor).
  - `/loja/produto/novo/`, `/loja/produto/<id>/editar/`, `/loja/produto/<id>/excluir/` — CRUD de produto (Diretor).
  - `/loja/produto/<id>/` — página do produto na vitrine (configurar + adicionar ao carrinho) (`core:loja_produto`).
  - `/loja/carrinho/adicionar/`, `/loja/carrinho/remover/` — carrinho na sessão (POST).
  - `/loja/finalizar/` → `/loja/pagamento/` → `/loja/sucesso/` — checkout + pagamento simulado.
  - `/loja/compra/<id>/cancelar/` — cancela compra e devolve estoque (POST, Diretor).
  - `/loja/entrega/` — marca/desmarca entrega de um item (POST/JSON, Diretor). Aba "Vendas" = relatório.
- `/admin/` — Django admin (models de cadastro registrados).
- Em DEBUG, o Django serve os arquivos de mídia em `/media/`.

## Configurações importantes
- **`DEBUG` e `ALLOWED_HOSTS` vêm do ambiente**, não estão fixos no código. Se `DJANGO_DEBUG` não for
  definido, o padrão é seguro: liga o DEBUG só quando **não há** `DJANGO_ALLOWED_HOSTS` (= máquina local).
  Em produção (VPS) o `/etc/pinhaljunior2.env` define os dois — `DEBUG=0`.
- **Cookies só por HTTPS em produção**: `SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` = `not DEBUG`.
  Fixar em `True` quebraria o desenvolvimento local (`http://127.0.0.1` não guarda cookie `Secure`).
- **`SECURE_SSL_REDIRECT` fica desligado de propósito** — quem redireciona HTTP→HTTPS é o Nginx, antes do
  Django. O aviso `security.W008` do `check --deploy` é **esperado**; não "consertar".
  Já `SECURE_PROXY_SSL_HEADER` **precisa** existir: sem ele o Django não reconhece a requisição como HTTPS.
- **Pendente:** `SECURE_HSTS_SECONDS` sem valor (`security.W004`). HSTS mal configurado é irreversível por
  meses no navegador de quem já visitou — se ligar, começar baixo e **sem** `includeSubDomains`.
- **Ambiente divergente:** produção roda **Django 5.2.15 / Python 3.12.3**; a máquina de desenvolvimento
  está em **6.0.5 / 3.14.3**. O `requirements.txt` (`>=5.2,<6.0`) casa com produção. No VPS cada aplicação
  tem venv própria (rodam de 5.2.11 a 6.1 lado a lado), então o certo é **igualar o local**, não o servidor.
- Idioma: `pt-br`. Fuso horário: `America/Sao_Paulo`.
- Banco: SQLite (`db.sqlite3`), já com os models de cadastro migrados.
- `STATICFILES_DIRS` aponta para a pasta `static/`.
- `MEDIA_URL = "media/"` e `MEDIA_ROOT = BASE_DIR / "media"` (uploads, ex.: foto 3x4).
- `TEMPLATES DIRS` aponta para a pasta `templates/`.
- Autenticação: `LOGIN_URL = "core:login"`, `LOGIN_REDIRECT_URL = "core:inicio"`,
  `LOGOUT_REDIRECT_URL = "core:login"`.
- `SECRET_KEY` é de desenvolvimento (trocar em produção).
- Middleware próprio `core.middleware.TrocaSenhaObrigatoriaMiddleware` (após o de autenticação):
  força a troca de senha das contas temporárias de ajudantes.
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
