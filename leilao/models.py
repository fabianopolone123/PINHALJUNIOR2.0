"""Models do módulo de **Leilão online ao vivo**.

Banco **próprio** (`leilao.sqlite3`), separado do sistema do clube: 50 pessoas
martelando lance não podem encostar no banco que roda mensalidades/eventos/loja.
Ver `docs/PLANEJAMENTO_LEILAO.md`.

Duas regras atravessam o arquivo inteiro:

1. **O relógio é do servidor.** `Lote.fecha_em` é uma data/hora absoluta; o
   navegador só desenha a diferença. Ninguém ganha ou perde um lote por ter o
   relógio do celular adiantado.
2. **Valor é dinheiro, não contador.** Tudo em `Decimal` com 2 casas — nunca
   `float`, que arredonda errado em soma de centavos.
"""

import hashlib
import re
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone


# Quanto o botão de lance soma por toque. É **fixo** e vale para todo item de
# todo leilão: o clube pediu "R$ 5 e ponto". Configurar isso por leilão e por
# item existia e foi removido — no pregão ao vivo o locutor anuncia "de cinco
# em cinco" uma vez e ninguém confere tabela; incremento variável só criava a
# chance de um item sair com regra diferente da que foi falada em voz alta.
# As colunas `Leilao.incremento_padrao` e `Lote.incremento` ficaram DORMENTES.
INCREMENTO_PADRAO = Decimal("5.00")


def _novo_token():
    """Token opaco (URL-safe) para identificar participante/lote sem expor id."""
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
class ConfigLeilao(models.Model):
    """Configuração do módulo — **linha única** (singleton, `get_solo()`).

    Espelha o `MercadoPagoConfig` do clube de propósito: o leilão **não** importa
    model do `core`. O que ele reaproveita é `core/mercadopago.py`, que é
    **biblioteca pura** (só `urllib`) e recebe o objeto de config de quem chama —
    então basta esta classe expor `access_token` e `webhook_secret`.

    O preço desse isolamento é digitar as credenciais do Mercado Pago mais uma
    vez aqui. É o preço certo: o leilão pode até usar outra conta, e uma
    aplicação nunca escreve no banco da outra.
    """

    MODO_CHOICES = [
        ("teste", "Teste (sandbox)"),
        ("producao", "Produção"),
    ]

    modo = models.CharField("Modo", max_length=10, choices=MODO_CHOICES, default="teste")

    access_token_teste = models.CharField("Access Token de teste", max_length=255, blank=True)
    webhook_secret_teste = models.CharField(
        "Assinatura secreta do webhook (teste)", max_length=255, blank=True
    )
    access_token_prod = models.CharField("Access Token de produção", max_length=255, blank=True)
    webhook_secret_prod = models.CharField(
        "Assinatura secreta do webhook (produção)", max_length=255, blank=True
    )

    # Endereço público do leilão. Serve para montar o `notification_url` de cada
    # cobrança: é o que faz o Mercado Pago avisar ESTE serviço, e não o do clube.
    site_url = models.URLField(
        "Endereço público do leilão", blank=True,
        help_text="Ex.: https://pinhaljunior.com.br/leilao — usado no webhook do Mercado Pago.",
    )

    # --- Áudio ao vivo (MediaMTX / WebRTC) ---
    # A caixa de áudio da tela é PLUGÁVEL de propósito: se o teste de carga
    # reprovar o WebRTC no VPS compartilhado, basta apontar `audio_externo_url`
    # para uma live (YouTube/Meet) sem reescrever nada do leilão.
    audio_ativo = models.BooleanField("Transmitir a voz do locutor", default=False)
    audio_caminho = models.CharField(
        "Caminho no MediaMTX", max_length=60, default="leilao",
        help_text="Nome do 'path' configurado no MediaMTX (ex.: leilao).",
    )
    audio_publicar_usuario = models.CharField("Usuário de publicação", max_length=60, blank=True)
    audio_publicar_senha = models.CharField("Senha de publicação", max_length=120, blank=True)
    audio_externo_url = models.URLField(
        "Plano B: link de live externa", blank=True,
        help_text="Preenchido só se o áudio próprio for descartado. A tela passa a apontar para cá.",
    )

    # --- Música de fundo: DESLIGADA, o clube ouviu e não quis ---
    # A coluna fica; o campo saiu do formulário e nada mais o lê. Não religue
    # sem pedir: a decisão foi de ouvido, com a tela pronta, e é a mais difícil
    # de tomar por código.
    musica = models.FileField(
        "Música de fundo (opcional)", upload_to="musica/", blank=True,
        help_text=(
            "MP3/OGG que o clube tenha direito de usar. Sem arquivo, a tela toca "
            "uma base ambiente gerada no próprio navegador."
        ),
    )

    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="Atualizado por",
    )

    class Meta:
        verbose_name = "Configuração do leilão"
        verbose_name_plural = "Configuração do leilão"

    def __str__(self):
        return f"Configuração do leilão ({self.get_modo_display()})"

    @classmethod
    def get_solo(cls):
        """A configuração, **sem escrever no banco**.

        Não usa `get_or_create` de propósito: este método é chamado pelo context
        processor a **cada carregamento de página** e por uma thread de fundo a
        cada item vendido. Um `get_or_create` transforma toda leitura numa
        tentativa de escrita — que no SQLite disputa a trava com quem está
        registrando lance (já apareceu como `database is locked` nos testes).

        Sem linha salva, devolve uma instância **em memória** com os padrões. Ela
        só vai ao banco quando alguém salva a configuração de fato.
        """
        obj = cls.objects.filter(pk=1).first()
        return obj if obj is not None else cls(pk=1)

    # As três propriedades que o `core/mercadopago.py` consome.
    @property
    def access_token(self):
        return self.access_token_prod if self.modo == "producao" else self.access_token_teste

    @property
    def webhook_secret(self):
        return self.webhook_secret_prod if self.modo == "producao" else self.webhook_secret_teste

    @property
    def configurado(self):
        return bool(self.access_token)

    @property
    def token_mascarado(self):
        """Nunca exibir o token inteiro na tela (regra do módulo WhatsApp)."""
        tok = self.access_token
        return f"…{tok[-4:]}" if len(tok) > 4 else ("—" if not tok else "…")


# ---------------------------------------------------------------------------
# O leilão (uma sessão/noite de leilão)
# ---------------------------------------------------------------------------
class Leilao(models.Model):
    """Uma sessão de leilão: a noite inteira, com sua fila de lotes.

    Só **um** leilão fica `ao_vivo` por vez — é o que a tela pública abre. Os
    outros ficam em rascunho (montando a fila) ou encerrados (histórico).
    """

    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("ao_vivo", "Ao vivo"),
        ("encerrado", "Encerrado"),
    ]

    nome = models.CharField("Nome do leilão", max_length=120)
    descricao = models.TextField("Descrição", blank=True)
    status = models.CharField("Situação", max_length=12, choices=STATUS_CHOICES, default="rascunho")

    # --- Incremento: NÃO É MAIS CONFIGURÁVEL. Coluna dormente. ---
    # O lance soma `INCREMENTO_PADRAO` (R$ 5), sempre. Saiu do formulário e
    # nada mais lê este campo. Ver o comentário da constante.
    incremento_padrao = models.DecimalField(
        "Incremento do lance (R$)", max_digits=10, decimal_places=2, default=INCREMENTO_PADRAO,
        help_text="DORMENTE — o incremento é fixo em R$ 5,00.",
    )
    # --- Cronômetro: NÃO EXISTE MAIS. Colunas dormentes. ---
    # Quem bate o martelo é o locutor, e o pregão não tem contagem regressiva.
    # Estes campos saíram do formulário e nada mais os lê. Não religue sem
    # pedir: foi decisão de quem vai conduzir o evento.
    segundos_por_lote = models.PositiveIntegerField(
        "Cronômetro do lote (segundos)", default=60,
        help_text="Contagem regressiva de cada lote. Padrão: 60 s.",
    )
    reiniciar_cronometro = models.BooleanField(
        "Reiniciar o cronômetro a cada lance", default=True,
        help_text="Regra clássica anti-'lance no último segundo'.",
    )
    segundos_extra = models.PositiveIntegerField(
        "Botão de tempo extra (segundos)", default=30,
        help_text="Quanto o botão '+tempo' do locutor acrescenta.",
    )
    # --- Prazo para pagar: NÃO EXISTE MAIS. Coluna dormente. ---
    # Quem arremata não paga na hora: acumula os itens e paga TUDO de uma vez,
    # quando o locutor libera (ver `pagamentos_liberados`). O prazo de 15
    # minutos existia para a pessoa não sair do leilão para pagar — mas ele
    # fazia exatamente isso, tirava a pessoa do pregão no meio dos lances, e
    # ainda devolvia o item à fila de quem estava só sem o celular na mão.
    minutos_para_pagar = models.PositiveIntegerField(
        "Prazo para pagar (minutos)", default=15,
        help_text="DORMENTE — não há prazo; o pagamento é liberado no fim.",
    )

    # O locutor abre a bilheteria no fim do leilão: até aqui ninguém paga nada,
    # e é UM botão para todo mundo (não por pessoa). Enquanto for False, a tela
    # de arremates mostra a lista e o total, mas sem botão de pagar.
    pagamentos_liberados = models.BooleanField(
        "Pagamentos liberados", default=False,
        help_text="Ligado pelo locutor no fim do leilão, libera todo mundo a pagar.",
    )
    fechamento_automatico = models.BooleanField(
        "Fechar o lote sozinho quando o tempo acabar", default=False,
        help_text=(
            "Desligado (padrão): o cronômetro chega a zero e ESPERA — quem bate o "
            "martelo é o locutor, pelo botão VENDIDO. É assim que um leilão de "
            "verdade funciona: o 'dou-lhe uma, dou-lhe duas' é do leiloeiro."
        ),
    )

    # --- Música de fundo: DESLIGADA (ver ConfigLeilao.musica) ---
    # Colunas dormentes. Nada lê nem escreve nelas: não há botão, evento nem
    # estado de música. Se voltarem a valer, o caminho era locutor → ação
    # "musica" → `HUB.publicar` → `aplicarMusica()` no leilao.js.
    musica_ligada = models.BooleanField("Música de fundo tocando", default=False)
    musica_volume = models.PositiveSmallIntegerField(
        "Volume da música (%)", default=18,
        help_text="Baixinho de propósito: é fundo, não show. O locutor ajusta ao vivo.",
    )

    # Contador da numeração dos itens. Precisa existir separado do "maior
    # número em uso": contando pelo maior, apagar o último item faria o próximo
    # cadastro reaproveitar um número que talvez já esteja COLADO numa caixa.
    # Este só sobe.
    ultimo_numero_item = models.PositiveIntegerField("Último nº de item usado", default=0)

    # --- A tela de quem chega antes de o pregão começar ---
    # Antes isto dizia "Intervalo", que é mentira para quem acabou de entrar:
    # não há intervalo nenhum, o leilão ainda não começou. A espera é o primeiro
    # contato da pessoa com o clube — vale um "bem-vindo" e as informações que
    # ela precisa (como funciona o lance, a que horas começa, o Pix).
    boas_vindas_titulo = models.CharField(
        "Título da tela de espera", max_length=80, default="Seja bem-vindo!",
        help_text="Aparece grande para quem entra antes do primeiro item.",
    )
    boas_vindas_texto = models.TextField(
        "Informações úteis", blank=True,
        default=(
            "O leilão começa em instantes — pode deixar esta tela aberta.\n"
            "Cada toque no botão soma R$ 5 ao lance.\n"
            "Quem arremata paga por Pix na hora, sem sair da tela.\n"
            "Ligue o som para ouvir o locutor ao vivo."
        ),
        help_text="Uma informação por linha. Dá para editar com o leilão já no ar.",
    )

    # --- Chat: SEM CONTAGEM DE TEMPO. Colunas dormentes. ---
    # O chat fica aberto enquanto o leilão está no ar (ver `chat_aberto`).
    # Estes três campos — `chat_segundos`, `chat_aberto_em` e `chat_aberto_ate`
    # — são o que sobrou do chat "de intervalo", com prazo. Nada os lê.
    chat_segundos = models.PositiveIntegerField(
        "Duração do chat entre lotes (segundos)", default=120,
        help_text="DORMENTE — o chat fica aberto o leilão inteiro.",
    )
    chat_aberto_em = models.DateTimeField(
        "Chat aberto em", null=True, blank=True,
        help_text=(
            "Marco da rodada atual do chat. Cada intervalo é uma conversa NOVA "
            "para quem participa — abre limpa. O locutor continua vendo tudo."
        ),
    )
    chat_aberto_ate = models.DateTimeField("Chat aberto até", null=True, blank=True)

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leiloes_criados", verbose_name="Criado por",
    )

    class Meta:
        verbose_name = "Leilão"
        verbose_name_plural = "Leilões"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome

    @classmethod
    def ao_vivo(cls):
        """O leilão que está acontecendo agora (ou `None`)."""
        return cls.objects.filter(status="ao_vivo").order_by("-criado_em").first()

    @property
    def chat_aberto(self):
        """O chat fica aberto a noite inteira, enquanto o leilão está no ar.

        Antes ele só abria **no intervalo**, por um tempo contado
        (`chat_segundos`/`chat_aberto_ate`), e fechava quando um item ia a
        pregão. O clube pediu o contrário: conversa aberta direto, sem
        contagem. Quem quer falar fala; quem está dando lance não olha para a
        caixa de texto, e o botão de lance nunca dividiu espaço com ela.

        Sobrou UMA condição, que é a que importa e que já era lei aqui: leilão
        fora do ar não tem chat — a tela mostrava a caixa de conversa e o
        servidor recusava toda mensagem, a pessoa digitando contra uma porta
        fechada. Agora a condição da tela e a do servidor são a MESMA
        expressão, o que torna a divergência impossível por construção.

        Dormentes: `chat_segundos`, `chat_aberto_ate` e `chat_aberto_em`.
        """
        return self.status == "ao_vivo"

    @property
    def lote_atual(self):
        return self.lotes.filter(status="aberto").order_by("ordem").first()

    def ja_comecou(self):
        """Algum item já foi a pregão nesta noite?

        É o que separa **espera** de **intervalo**: antes do primeiro item a
        tela diz "bem-vindo"; entre um item e outro, "já já abrimos o próximo".
        Dizer "intervalo" a quem acabou de chegar é dar a impressão de que ela
        perdeu o começo.
        """
        return self.lotes.exclude(status="fila").exists()


# ---------------------------------------------------------------------------
# Quem dá lance
# ---------------------------------------------------------------------------
class Participante(models.Model):
    """Quem entrou pelo link e vai dar lance. **Não precisa ser do clube.**

    Sem senha: a pessoa é reconhecida por um `token` guardado na sessão do
    navegador. É deliberado — pedir cadastro com senha na porta de um leilão de
    uma noite espanta gente.

    O endereço fica aqui porque é o que entrega o item ao arrematante. **É dado
    pessoal**: mora só neste banco, nunca no Git, e as telas que o exibem são
    restritas ao locutor.
    """

    nome = models.CharField("Nome completo", max_length=150)
    whatsapp = models.CharField("WhatsApp", max_length=20)

    cep = models.CharField("CEP", max_length=9, blank=True)
    logradouro = models.CharField("Rua / Avenida", max_length=150, blank=True)
    numero = models.CharField("Número", max_length=20, blank=True)
    complemento = models.CharField("Complemento", max_length=60, blank=True)
    bairro = models.CharField("Bairro", max_length=80, blank=True)
    cidade = models.CharField("Cidade", max_length=80, blank=True)
    estado = models.CharField("UF", max_length=2, blank=True)

    token = models.CharField("Token", max_length=64, unique=True, default=_novo_token, editable=False)
    bloqueado = models.BooleanField(
        "Bloqueado", default=False,
        help_text="Bloqueia novos lances (ex.: arrematou e não pagou).",
    )
    observacao = models.CharField("Observação do locutor", max_length=200, blank=True)

    criado_em = models.DateTimeField("Entrou em", auto_now_add=True)
    ultimo_visto_em = models.DateTimeField("Visto por último", null=True, blank=True)

    class Meta:
        verbose_name = "Participante"
        verbose_name_plural = "Participantes"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def nome_curto(self):
        """Primeiro nome + último sobrenome.

        A tela mostra quem está ganhando em letra **enorme**; nome completo com
        quatro sobrenomes quebraria o destaque, que é o efeito mais importante
        da tela do participante.
        """
        partes = (self.nome or "").split()
        if not partes:
            return "—"
        if len(partes) == 1:
            return partes[0]
        return f"{partes[0]} {partes[-1]}"

    @property
    def telefone_normalizado(self):
        """Só os dígitos, sem o DDI do Brasil — para comparar duas entradas.

        A mesma pessoa digita "(11) 90000-0000" num aparelho e "5511900000000"
        no outro; sem normalizar, viram dois telefones diferentes.
        """
        digitos = re.sub(r"\D", "", self.whatsapp or "")
        if len(digitos) > 11 and digitos.startswith("55"):
            digitos = digitos[2:]
        return digitos

    @property
    def chave_pessoa(self):
        """Identidade **estável** da pessoa, segura para ir no broadcast.

        É um hash do telefone: serve para a tela saber "o líder sou eu" mesmo
        quando a pessoa entrou de novo em outro aparelho (e virou outro
        registro), **sem** expor o número para as outras 50 pessoas.
        """
        tel = self.telefone_normalizado
        if not tel:
            return f"id{self.pk}"
        return hashlib.sha256(tel.encode("utf-8")).hexdigest()[:12]

    @property
    def whatsapp_link(self):
        """Link que abre a conversa com esta pessoa no WhatsApp.

        O caixa precisa falar com quem arrematou — e digitar número no celular,
        com o leilão rolando, é onde a conversa morre. Sem DDI cadastrado, o
        **55** do Brasil é acrescentado aqui: o cadastro pede só DDD + número.
        """
        tel = self.telefone_normalizado
        if len(tel) < 10:
            return ""
        return f"https://wa.me/55{tel}"

    @property
    def endereco_uma_linha(self):
        rua = " ".join(p for p in [self.logradouro, self.numero] if p)
        partes = [rua, self.complemento, self.bairro, self.cidade, self.estado, self.cep]
        return " · ".join(p for p in partes if p)


# ---------------------------------------------------------------------------
# O item leiloado
# ---------------------------------------------------------------------------
class Lote(models.Model):
    """Um item do leilão.

    O ciclo é `fila → aberto → vendido` (ou `sem_lance`, voltando para a fila).
    Um lote **volta para a fila** quando o arrematante não paga no prazo — por
    isso `voltas`, e por isso o arremate é FK e não OneToOne: o mesmo lote pode
    ser arrematado mais de uma vez, em tentativas diferentes.
    """

    STATUS_CHOICES = [
        ("fila", "Na fila"),
        ("aberto", "Em pregão"),
        ("vendido", "Vendido"),
        ("sem_lance", "Sem lance"),
        ("cancelado", "Cancelado"),
    ]

    leilao = models.ForeignKey(Leilao, on_delete=models.CASCADE, related_name="lotes")
    ordem = models.PositiveIntegerField("Ordem na fila", default=0)

    # O número que vai COLADO no objeto físico, para a equipe achar na prateleira
    # o item que está na tela. Nasce sozinho (1, 2, 3… dentro de cada leilão) e
    # não é digitado: numeração escrita à mão repete, pula e desencontra, e o
    # desencontro só aparece na hora de entregar.
    #
    # `ordem` é OUTRA coisa e as duas não andam juntas de propósito: a ordem é a
    # fila e muda quando o locutor reorganiza a noite; o número é a etiqueta do
    # objeto e **não muda nunca** — se mudasse, a etiqueta na caixa passaria a
    # apontar para outro item.
    numero = models.PositiveIntegerField("Nº do item", default=0, editable=False)

    nome = models.CharField("Item", max_length=120)
    descricao = models.CharField(
        "Descrição curta", max_length=240, blank=True,
        help_text="Uma linha: é o que cabe na tela do celular embaixo da foto.",
    )
    foto = models.ImageField("Foto", upload_to="lotes/", blank=True)
    foto_mini = models.ImageField("Miniatura", upload_to="lotes/mini/", blank=True)

    # PESO E DIMENSÕES existem por causa da ENTREGA, que é a parte do leilão que
    # acontece depois e longe: o voluntário escolhe o carro antes de sair, e
    # descobrir na porta que o item não cabe custa a viagem inteira. De quebra,
    # quem dá lance passa a saber o tamanho do que está comprando.
    #
    # São **obrigatórios no cadastro** — a exigência está no `LoteForm`, não
    # aqui. No banco eles aceitam vazio de propósito: os itens cadastrados antes
    # desta migration não têm a informação, e gravar `0` neles seria inventar um
    # dado — a tela prefere dizer "—" a mentir uma medida para quem vai dirigir.
    # Os tetos (1.000 kg e 1.000 cm = 10 m) não são regra de negócio: são o
    # freio do dígito a mais. Sem eles o campo aceita `999999999999`, e uma
    # medida assim **quebra a tela do pregão para as 100 pessoas** que estão
    # olhando. Nenhum item de leilão de clube chega perto disso; o que chega
    # perto é o dedo escorregando no teclado do celular.
    MAX_PESO_KG = Decimal("1000")
    MAX_LADO_CM = 1000

    peso_kg = models.DecimalField(
        "Peso (kg)", max_digits=7, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(MAX_PESO_KG)],
        help_text="Aproximado, em quilos. Pode usar vírgula (ex.: 1,5).",
    )
    altura_cm = models.PositiveIntegerField(
        "Altura (cm)", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_LADO_CM)],
    )
    largura_cm = models.PositiveIntegerField(
        "Largura (cm)", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_LADO_CM)],
    )
    profundidade_cm = models.PositiveIntegerField(
        "Profundidade (cm)", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_LADO_CM)],
    )

    lance_inicial = models.DecimalField(
        "Lance inicial (R$)", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    # DORMENTE, como o do leilão: o incremento é fixo em R$ 5,00.
    incremento = models.DecimalField(
        "Incremento próprio (R$)", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="DORMENTE — o incremento é fixo em R$ 5,00.",
    )

    status = models.CharField("Situação", max_length=12, choices=STATUS_CHOICES, default="fila")
    valor_atual = models.DecimalField(
        "Valor atual (R$)", max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    lider = models.ForeignKey(
        Participante, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lotes_liderando", verbose_name="Quem está ganhando",
    )

    aberto_em = models.DateTimeField("Aberto em", null=True, blank=True)
    fecha_em = models.DateTimeField(
        "Fecha em", null=True, blank=True,
        help_text="Data/hora ABSOLUTA do fim do cronômetro. O cliente só desenha a diferença.",
    )
    # Coluna dormente: "pausar lances" saiu da mesa. Para segurar o pregão,
    # o locutor simplesmente não abre o próximo item.
    pausado_restante = models.PositiveIntegerField(
        "Segundos restantes (pausado)", null=True, blank=True,
        help_text="Preenchido só enquanto o locutor pausa o cronômetro.",
    )
    fechado_em = models.DateTimeField("Fechado em", null=True, blank=True)
    voltas = models.PositiveIntegerField(
        "Voltas para a fila", default=0,
        help_text="Quantas vezes voltou por falta de pagamento.",
    )

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ["ordem", "id"]
        constraints = [
            # Dois itens com a mesma etiqueta é o erro que estraga a entrega:
            # ninguém descobre qual caixa é de quem. Melhor falhar no cadastro.
            models.UniqueConstraint(
                fields=["leilao", "numero"], name="numero_unico_por_leilao"
            ),
        ]

    def __str__(self):
        return f"{self.numero}. {self.nome}"

    def save(self, *args, **kwargs):
        """Dá o número na criação, a partir do contador do leilão.

        Dentro do leilão, e não global: a etiqueta é do evento daquela noite, e
        começar o leilão de dezembro no item 87 não diz nada a ninguém.

        O número sai de `Leilao.ultimo_numero_item`, **não** do maior número em
        uso. Pelo maior, apagar o último item faria o próximo cadastro
        reaproveitar aquele número — e ele pode já estar colado numa caixa. O
        contador só sobe; número usado não volta.

        O incremento é feito no banco (`F()`), dentro de uma transação: dois
        cadastros ao mesmo tempo não podem ler o mesmo valor. A constraint de
        unicidade é a última linha de defesa.
        """
        if not self.numero and self.leilao_id:
            with transaction.atomic():
                Leilao.objects.filter(pk=self.leilao_id).update(
                    ultimo_numero_item=F("ultimo_numero_item") + 1
                )
                self.numero = Leilao.objects.values_list(
                    "ultimo_numero_item", flat=True
                ).get(pk=self.leilao_id)
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    @property
    def peso_numero(self):
        """Só o número, como se escreve em português: `1,5` (sem a unidade).

        É o que volta para dentro do campo quando alguém edita o item. Os zeros
        à direita caem (`15,00` vira `15`) porque peso arredondado com duas
        casas fixas parece precisão de balança de farmácia, que não é o caso.
        O ponto sobrevive ao `rstrip` e por isso `10,00` não vira `1`.
        """
        if self.peso_kg is None:
            return ""
        texto = f"{self.peso_kg:.2f}".rstrip("0").rstrip(".")
        return texto.replace(".", ",")

    @property
    def peso_gramas(self):
        """O peso em GRAMAS, inteiro — é assim que ele é digitado.

        O banco guarda quilos (e continua guardando: os itens já cadastrados
        valem como estão), mas quem cadastra pensa em grama. Pedir "0,35" para
        uma caneca é convidar ao erro de vírgula; pedir "350" não tem como sair
        errado.
        """
        if self.peso_kg is None:
            return ""
        return str(int(round(self.peso_kg * 1000)))

    @property
    def peso_texto(self):
        """`350 g` ou `1,5 kg` — a unidade segue o tamanho da coisa.

        Quem digitou 350 quer ler *350 g*, não *0,35 kg*: a segunda forma faz o
        voluntário parar para converter, e ele está decidindo se o item cabe no
        carro. Acima de 1 kg vale o contrário, e por isso o corte é aí.
        """
        if self.peso_kg is None:
            return ""
        if self.peso_kg < 1:
            gramas = int(round(self.peso_kg * 1000))
            return f"{gramas} g" if gramas else ""
        return f"{self.peso_numero} kg" if self.peso_numero else ""

    @property
    def dimensoes(self):
        """`40 × 30 × 25 cm`. Vazio quando falta qualquer uma das três.

        Meia medida não ajuda ninguém a escolher o carro, e "40 × ? × 25" na
        tela parece defeito do sistema em vez de item antigo sem cadastro.
        """
        lados = [self.altura_cm, self.largura_cm, self.profundidade_cm]
        if not all(lados):
            return ""
        return " × ".join(str(x) for x in lados) + " cm"

    @property
    def medidas_texto(self):
        """Peso e dimensões numa linha só — o formato que TODA tela usa.

        O texto é montado aqui, num lugar só, e não em cada template/JS: a tela
        do público, a mesa, o caixa e o roteiro de entrega precisam dizer a
        mesma coisa do mesmo jeito, senão a equipe compara medidas escritas de
        formas diferentes e desconfia do número.
        """
        partes = [x for x in (self.peso_texto, self.dimensoes) if x]
        return " · ".join(partes)

    @property
    def incremento_efetivo(self):
        """O incremento é FIXO (R$ 5), e por isso não consulta o banco.

        A property continua existindo porque é o nome que o estado, o serviço
        de lance e as telas usam — trocá-la por um literal espalhado seria pôr
        o número em oito lugares. Os campos `Lote.incremento` e
        `Leilao.incremento_padrao` estão dormentes e **nada os lê**.
        """
        return INCREMENTO_PADRAO

    @property
    def tem_lance(self):
        return self.lider_id is not None

    @property
    def proximo_valor(self):
        """Quanto custa o próximo toque no botão.

        Sem nenhum lance ainda, o primeiro vale **o lance inicial** — não o
        inicial + incremento. Somar aqui faria o item nunca sair pelo preço
        anunciado.
        """
        if not self.tem_lance:
            return self.lance_inicial
        return self.valor_atual + self.incremento_efetivo

    @property
    def pausado(self):
        return self.status == "aberto" and self.pausado_restante is not None

    @property
    def parado_ha(self):
        """Segundos desde o último lance (ou desde a abertura, se não houve).

        Conta para **cima**, não para baixo: sem fechamento automático não existe
        prazo, e o que o locutor precisa saber é *há quanto tempo a sala está
        calada* — é isso que diz a hora de bater o martelo.
        """
        if self.status != "aberto" or not self.aberto_em:
            return 0
        ultimo = (
            self.lances_da_rodada().order_by("-criado_em").values_list("criado_em", flat=True).first()
        )
        base = ultimo or self.aberto_em
        return max(0, int((timezone.now() - base).total_seconds()))

    def lances_da_rodada(self):
        """Os lances **desta** vez que o item foi a pregão.

        Um lote pode voltar para a fila (quem arrematou não pagou) e ser
        leiloado de novo. Os lances da rodada anterior continuam no banco — é
        histórico e não se apaga —, mas mostrá-los na tela junto com os de agora
        confunde: aparecem dois "R$ 35,00" e ninguém entende qual vale.
        """
        qs = self.lances.filter(cancelado=False)
        if self.aberto_em:
            qs = qs.filter(criado_em__gte=self.aberto_em)
        return qs

    @property
    def segundos_restantes(self):
        """Quanto falta, em segundos (0 quando estourou). Só para exibição."""
        if self.status != "aberto":
            return 0
        if self.pausado_restante is not None:
            return self.pausado_restante
        if not self.fecha_em:
            return 0
        return max(0, int((self.fecha_em - timezone.now()).total_seconds()))


# ---------------------------------------------------------------------------
# O lance
# ---------------------------------------------------------------------------
class Lance(models.Model):
    """Um toque no botão. Nasce e não muda — exceto para ser **desfeito**.

    `cancelado` existe porque o locutor erra: registra um lance no balcão para a
    pessoa errada, ou alguém toca duas vezes. Desfazer é mais honesto do que
    apagar: o histórico do pregão continua auditável.
    """

    ORIGEM_CHOICES = [
        ("botao", "Botão do participante"),
        ("locutor", "Registrado pelo locutor"),
    ]

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="lances")
    participante = models.ForeignKey(
        Participante, on_delete=models.CASCADE, related_name="lances"
    )
    valor = models.DecimalField("Valor (R$)", max_digits=10, decimal_places=2)
    origem = models.CharField("Origem", max_length=10, choices=ORIGEM_CHOICES, default="botao")
    cancelado = models.BooleanField("Desfeito", default=False)
    criado_em = models.DateTimeField("Em", auto_now_add=True)

    class Meta:
        verbose_name = "Lance"
        verbose_name_plural = "Lances"
        ordering = ["-criado_em", "-id"]
        indexes = [models.Index(fields=["lote", "-criado_em"])]

    def __str__(self):
        return f"{self.participante} — R$ {self.valor}"


# ---------------------------------------------------------------------------
# Pagamento (Pix pelo Mercado Pago)
# ---------------------------------------------------------------------------
class PagamentoLeilao(models.Model):
    """Uma cobrança Pix. Espelha o `Pagamento` do clube, mas **neste** banco.

    Guarda o QR pronto (`qr_code` copia e cola + `qr_code_base64` imagem) porque
    a tela do arrematante precisa mostrá-lo sem sair do leilão e sem gerador de
    QR no navegador — o Mercado Pago já devolve os dois.
    """

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
        ("cancelado", "Cancelado"),
        ("estornado", "Estornado"),
    ]

    referencia = models.CharField("Referência", max_length=60, unique=True)
    mp_payment_id = models.CharField("ID no Mercado Pago", max_length=40, blank=True, db_index=True)
    status = models.CharField("Situação", max_length=12, choices=STATUS_CHOICES, default="pendente")

    valor_bruto = models.DecimalField("Valor (R$)", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    taxa = models.DecimalField("Taxa (R$)", max_digits=10, decimal_places=2, default=Decimal("0.00"))
    valor_liquido = models.DecimalField("Líquido (R$)", max_digits=10, decimal_places=2, default=Decimal("0.00"))

    qr_code = models.TextField("Pix copia e cola", blank=True)
    qr_code_base64 = models.TextField("QR (imagem base64)", blank=True)
    ticket_url = models.URLField("Link do Mercado Pago", blank=True, max_length=500)
    payload = models.TextField("Retorno bruto (JSON)", blank=True)

    finalizado = models.BooleanField(
        "Já processado", default=False,
        help_text="Trava de idempotência: o webhook do MP repete o aviso.",
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        verbose_name = "Pagamento do leilão"
        verbose_name_plural = "Pagamentos do leilão"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.referencia} — {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Arremate (quem levou o item e se pagou)
# ---------------------------------------------------------------------------
class Arremate(models.Model):
    """O item foi batido para alguém. **Sem relógio.**

    Quem arremata não paga na hora: os itens se acumulam e a pessoa paga TUDO
    de uma vez, num Pix só, quando o locutor libera. O prazo de 15 minutos
    existia para ela não sair do leilão para pagar — e era justamente o que ele
    provocava, tirando do pregão quem estava no meio dos lances.

    Não é OneToOne com o lote de propósito: o mesmo item pode ser arrematado de
    novo se a venda for desfeita, e o histórico das tentativas é o que embasa
    bloquear alguém.
    """

    STATUS_CHOICES = [
        ("aguardando", "Aguardando pagamento"),
        # A pessoa foi contatada e combinou pagar depois. NÃO vence, então o
        # item não volta para a fila — mas também não está pago, então não vai
        # para a entrega. Sem este estado, quem combinou de pagar amanhã perdia
        # o item para o relógio.
        ("combinado", "Combinado — vai pagar depois"),
        ("pago", "Pago"),
        ("expirado", "Não pago (venceu o prazo)"),
        ("cancelado", "Cancelado"),
    ]

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="arremates")
    participante = models.ForeignKey(
        Participante, on_delete=models.CASCADE, related_name="arremates"
    )
    valor = models.DecimalField("Valor (R$)", max_digits=10, decimal_places=2)

    status = models.CharField("Situação", max_length=12, choices=STATUS_CHOICES, default="aguardando")
    criado_em = models.DateTimeField("Arrematado em", auto_now_add=True)
    # DORMENTE: não há mais prazo para pagar. Fica nulo nos arremates novos e
    # preenchido nos antigos, que continuam válidos como histórico.
    expira_em = models.DateTimeField("Prazo para pagar", null=True, blank=True)

    pago_em = models.DateTimeField("Pago em", null=True, blank=True)
    pago_manual = models.BooleanField(
        "Baixa manual", default=False,
        help_text="Marcado pelo caixa (pagou em dinheiro, transferência, etc.).",
    )
    observacao = models.CharField(
        "Observação", max_length=200, blank=True,
        help_text="O que foi combinado com a pessoa sobre o pagamento.",
    )
    combinado_em = models.DateTimeField("Combinado em", null=True, blank=True)
    combinado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="acertos_leilao", verbose_name="Quem falou com a pessoa",
    )

    # --- Entrega ---
    # O item é entregue **depois**, na casa da pessoa (decisão do clube), por
    # isso o que importa aqui é o endereço — que já está no `Participante` — e
    # uma marca de "saiu". Sem `quantidade`: um arremate é sempre um item.
    entregue_em = models.DateTimeField("Entregue em", null=True, blank=True)
    entregue_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entregas_leilao", verbose_name="Entregue por",
    )
    entrega_obs = models.CharField(
        "Observação da entrega", max_length=200, blank=True,
        help_text="Quem recebeu, código de rastreio, combinado de retirada…",
    )

    pagamento = models.ForeignKey(
        PagamentoLeilao, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="arremates", verbose_name="Cobrança Pix",
    )

    # --- Devolução ao leilão ---
    # O item volta para a fila e é leiloado de novo. Dois casos, e o dinheiro
    # se comporta diferente em cada um:
    #
    # - **não pago**: a pessoa desistiu, então a dívida some junto (o status
    #   vira `cancelado`) — cobrar por um item que ela não vai receber seria
    #   errado;
    # - **pago**: ela **doou o item de volta** para o clube leiloar outra vez.
    #   O status continua `pago`, porque o dinheiro entrou e é do clube; o que
    #   muda é que ela não recebe nada (sai da entrega).
    #
    # O motivo é **obrigatório** na view: um item reaparecendo na fila depois de
    # batido é a coisa mais estranha que pode acontecer num leilão, e quem
    # abrir a lista amanhã precisa saber por quê sem ter de perguntar.
    devolvido_em = models.DateTimeField("Devolvido ao leilão em", null=True, blank=True)
    devolvido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="devolucoes_leilao", verbose_name="Quem devolveu",
    )
    motivo_devolucao = models.CharField(
        "Por que voltou ao leilão", max_length=200, blank=True,
        help_text="Aparece no histórico do item e na tela do caixa.",
    )

    class Meta:
        verbose_name = "Arremate"
        verbose_name_plural = "Arremates"
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["participante", "-criado_em"])]

    def __str__(self):
        return f"{self.lote.nome} → {self.participante} (R$ {self.valor})"

    @property
    def aguardando(self):
        return self.status == "aguardando"

    @property
    def em_aberto(self):
        """Devendo: ou o relógio está correndo, ou ficou combinado para depois."""
        return self.status in {"aguardando", "combinado"}

    @property
    def entregue(self):
        return self.entregue_em is not None

    @property
    def devolvido(self):
        return self.devolvido_em is not None

    @property
    def a_entregar(self):
        """Pago, não entregue e **não devolvido** — é isto que vira a lista de envio.

        Só entra quem **pagou**: mandar o item antes de o dinheiro cair é o erro
        que a regra "só se entrega o que foi pago" existe para evitar.

        E quem **devolveu** sai da lista mesmo tendo pago: o caso é a pessoa
        doar o item de volta para ser leiloado outra vez, então não há o que
        levar na casa dela. Sem esta parte, o voluntário sairia para entregar um
        objeto que já está de volta na prateleira do clube.
        """
        return self.status == "pago" and self.entregue_em is None and self.devolvido_em is None

    # `segundos_para_pagar` NÃO EXISTE MAIS: não há prazo. Quem arremata
    # acumula os itens e paga no fim, e `expira_em` ficou nulo nos arremates
    # novos — a property devolveria TypeError em cima de None.


# ---------------------------------------------------------------------------
# Chat entre lotes
# ---------------------------------------------------------------------------
class MensagemChat(models.Model):
    """Mensagem do chat que abre no intervalo entre um lote e outro.

    `participante` vazio = mensagem do **locutor/sistema** (aviso, boas-vindas).
    `removida` em vez de apagar: moderar sem perder o registro do que foi dito.
    """

    leilao = models.ForeignKey(Leilao, on_delete=models.CASCADE, related_name="mensagens")
    participante = models.ForeignKey(
        Participante, on_delete=models.CASCADE, null=True, blank=True, related_name="mensagens"
    )
    texto = models.CharField("Mensagem", max_length=300)
    removida = models.BooleanField("Removida", default=False)
    criado_em = models.DateTimeField("Em", auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem do chat"
        verbose_name_plural = "Mensagens do chat"
        ordering = ["criado_em", "id"]
        indexes = [models.Index(fields=["leilao", "criado_em"])]

    def __str__(self):
        quem = self.participante.nome_curto if self.participante_id else "Locutor"
        return f"{quem}: {self.texto[:40]}"

    @property
    def autor(self):
        return self.participante.nome_curto if self.participante_id else "Locutor"


# ---------------------------------------------------------------------------
# Contas da equipe
# ---------------------------------------------------------------------------
class ContaEquipe(models.Model):
    """O que o leilão sabe sobre uma conta da equipe além do `User` do Django.

    Existe por causa de **uma** pergunta que o `User` não responde: *esta pessoa
    ainda está com a senha que o diretor entregou?*

    Não dá para deduzir isso de `last_login`: o Django o preenche **no momento
    do login**, antes de a pessoa trocar a senha. Quem entrasse e fechasse o
    navegador no meio da troca ficaria com a senha padrão para sempre, e o
    sistema acharia que já estava resolvido.

    **Quem não tem registro aqui não é cobrado.** As contas criadas antes desta
    tela (e as do comando `leilao_papel`, que sorteia uma senha forte) não
    passam pela troca obrigatória — elas nunca tiveram senha padrão.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conta_leilao",
        verbose_name="Conta",
    )
    nome = models.CharField(
        "Nome da pessoa", max_length=150, blank=True,
        help_text="Como o diretor escreveu no cadastro — é o que a equipe lê na lista.",
    )
    senha_provisoria = models.BooleanField(
        "Ainda com a senha padrão", default=True,
        help_text="Enquanto verdadeiro, a pessoa só abre a tela de trocar a senha.",
    )
    criado_em = models.DateTimeField("Criada em", auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contas_leilao_criadas", verbose_name="Criada por",
    )

    class Meta:
        verbose_name = "Conta da equipe"
        verbose_name_plural = "Contas da equipe"
        ordering = ["nome"]

    def __str__(self):
        return self.nome or self.usuario.get_username()


# ---------------------------------------------------------------------------
# Quadro de entregas — quem leva o quê
#
# A divisão automática (`entregas.dividir`) agrupa por bairro e equilibra o
# número de paradas, mas **não sabe que um bairro é perto do outro**: ela só
# compara o nome do bairro, e nomes iguais ou diferentes é tudo o que ela vê.
# Quem sabe que "isso aqui é tudo o mesmo lado" é a equipe.
#
# Por isso a divisão virou ponto de partida, e a palavra final é do quadro: a
# equipe arrasta as paradas entre os entregadores e o resultado fica salvo.
# Estes dois models são o que ela arrasta e onde isso para em pé.
# ---------------------------------------------------------------------------
class EntregadorLeilao(models.Model):
    """Uma coluna do quadro: o voluntário que vai rodar a cidade.

    É **rótulo, não cadastro**: o nome é digitado na hora e vale só para aquele
    leilão. Guardar uma agenda de entregadores seria uma tela a mais para manter
    o ano inteiro, quando o que a equipe precisa é escrever "Marcos" na coluna 2
    e mandar a rota — os voluntários mudam a cada evento.
    """

    leilao = models.ForeignKey(
        Leilao, on_delete=models.CASCADE, related_name="entregadores",
        verbose_name="Leilão",
    )
    numero = models.PositiveSmallIntegerField("Entregador")
    nome = models.CharField("Nome", max_length=80, blank=True)

    class Meta:
        verbose_name = "Entregador"
        verbose_name_plural = "Entregadores"
        unique_together = [("leilao", "numero")]
        ordering = ["numero"]

    def __str__(self):
        return self.rotulo

    @property
    def rotulo(self):
        """O que aparece na coluna e no topo da mensagem do WhatsApp."""
        return (self.nome or "").strip() or f"Entregador {self.numero}"


class AtribuicaoEntrega(models.Model):
    """Para qual entregador ficou uma parada do quadro.

    A parada é a **PESSOA**, não o item — dois itens da mesma casa são uma
    visita só, e é assim que a divisão automática também conta. Por isso a chave
    é o participante: arrastar a pessoa leva tudo o que ela arrematou junto.

    `entregador = 0` é "ainda a distribuir", a coluna da esquerda. Vale também
    para quem foi tirado de uma coluna que deixou de existir: a atribuição não é
    apagada quando a equipe diminui o número de entregadores, ela **volta para a
    fila** — o trabalho das outras colunas não pode se perder por causa disso.
    """

    SEM_ENTREGADOR = 0

    leilao = models.ForeignKey(
        Leilao, on_delete=models.CASCADE, related_name="atribuicoes_entrega",
        verbose_name="Leilão",
    )
    participante = models.ForeignKey(
        Participante, on_delete=models.CASCADE, related_name="atribuicoes_entrega",
        verbose_name="Quem recebe",
    )
    entregador = models.PositiveSmallIntegerField("Entregador", default=SEM_ENTREGADOR)
    atualizado_em = models.DateTimeField("Movida em", auto_now=True)

    class Meta:
        verbose_name = "Parada do quadro de entregas"
        verbose_name_plural = "Paradas do quadro de entregas"
        unique_together = [("leilao", "participante")]

    def __str__(self):
        return f"{self.participante} → {self.entregador or 'a distribuir'}"
