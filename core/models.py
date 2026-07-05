"""
Models do app core — cadastro de aventureiros.

Estrutura pensada para que um mesmo usuário (responsável) possa cadastrar
vários aventureiros no futuro. Cada aventureiro tem uma ficha de inscrição
(no próprio model), uma ficha médica e uma autorização de imagem.
"""

import datetime
import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------- Opções (choices) reutilizáveis ----------

SEXO_CHOICES = [
    ("M", "Masculino"),
    ("F", "Feminino"),
]

TAMANHO_CAMISETA_CHOICES = [
    ("PP", "PP"),
    ("P", "P"),
    ("M", "M"),
    ("G", "G"),
    ("GG", "GG"),
    ("XG", "XG"),
    ("INF_P", "Infantil P"),
    ("INF_M", "Infantil M"),
    ("INF_G", "Infantil G"),
]

TIPO_SANGUINEO_CHOICES = [
    ("A+", "A+"),
    ("A-", "A-"),
    ("AB+", "AB+"),
    ("AB-", "AB-"),
    ("B+", "B+"),
    ("B-", "B-"),
    ("O+", "O+"),
    ("O-", "O-"),
    ("NAO_SABE", "Não sabe"),
]


class Aventureiro(models.Model):
    """Ficha de inscrição do aventureiro (dados principais + responsáveis)."""

    # Um usuário/responsável pode ter vários aventureiros.
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="aventureiros",
        verbose_name="Usuário responsável",
    )

    # --- Dados principais ---
    foto = models.ImageField(
        "Foto 3x4", upload_to="aventureiros/fotos/", blank=True, null=True
    )
    nome_completo = models.CharField("Nome completo", max_length=150)
    sexo = models.CharField("Sexo", max_length=1, choices=SEXO_CHOICES)
    data_nascimento = models.DateField("Data de nascimento")
    colegio = models.CharField("Colégio", max_length=150, blank=True)
    serie = models.CharField("Série", max_length=50, blank=True)
    ano = models.CharField("Ano", max_length=20, blank=True)
    bolsa_familia = models.BooleanField("Beneficiado pelo Bolsa Família", default=False)

    # --- Classes investidas (uma ou mais) ---
    classe_abelhinhas = models.BooleanField("Abelhinhas", default=False)
    classe_luminares = models.BooleanField("Luminares", default=False)
    classe_edificadores = models.BooleanField("Edificadores", default=False)
    classe_maos_ajudadoras = models.BooleanField("Mãos Ajudadoras", default=False)

    # --- Endereço ---
    endereco = models.CharField("Endereço", max_length=200, blank=True)
    bairro = models.CharField("Bairro", max_length=100, blank=True)
    cidade = models.CharField("Cidade", max_length=100, blank=True)
    cep = models.CharField("CEP", max_length=15, blank=True)
    estado = models.CharField("Estado", max_length=50, blank=True)

    # --- Documentos e informações pessoais ---
    certidao_nascimento = models.CharField(
        "Certidão de nascimento", max_length=100, blank=True
    )
    religiao = models.CharField("Religião", max_length=100, blank=True)
    rg = models.CharField("RG", max_length=30, blank=True)
    orgao_expedidor = models.CharField("Órgão expedidor", max_length=50, blank=True)
    cpf = models.CharField("CPF", max_length=20)
    tamanho_camiseta = models.CharField(
        "Tamanho da camiseta",
        max_length=10,
        choices=TAMANHO_CAMISETA_CHOICES,
        blank=True,
    )

    # --- Dados do pai ---
    pai_nome = models.CharField("Nome do pai", max_length=150, blank=True)
    pai_email = models.EmailField("E-mail do pai", blank=True)
    pai_cpf = models.CharField("CPF do pai", max_length=20, blank=True)
    pai_celular = models.CharField("Celular do pai", max_length=20, blank=True)
    pai_whatsapp = models.CharField("WhatsApp do pai", max_length=20, blank=True)

    # --- Dados da mãe ---
    mae_nome = models.CharField("Nome da mãe", max_length=150, blank=True)
    mae_email = models.EmailField("E-mail da mãe", blank=True)
    mae_cpf = models.CharField("CPF da mãe", max_length=20, blank=True)
    mae_celular = models.CharField("Celular da mãe", max_length=20, blank=True)
    mae_whatsapp = models.CharField("WhatsApp da mãe", max_length=20, blank=True)

    # --- Responsável legal (nem sempre é o pai ou a mãe) ---
    resp_nome = models.CharField("Nome do responsável legal", max_length=150)
    resp_parentesco = models.CharField("Grau de parentesco", max_length=50, blank=True)
    resp_cpf = models.CharField("CPF do responsável legal", max_length=20)
    resp_email = models.EmailField("E-mail do responsável legal", blank=True)
    resp_whatsapp = models.CharField("WhatsApp do responsável legal", max_length=20)

    # --- Local e data da inscrição ---
    cidade_inscricao = models.CharField(
        "Cidade da inscrição", max_length=100, blank=True
    )
    data_inscricao = models.DateField("Data da inscrição", auto_now_add=True)

    # --- Aceites obrigatórios ---
    declaracao_medica_aceita = models.BooleanField(
        "Declaração médica aceita", default=False
    )
    autorizacao_imagem_aceita = models.BooleanField(
        "Autorização de imagem aceita", default=False
    )

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Aventureiro"
        verbose_name_plural = "Aventureiros"
        ordering = ["nome_completo"]

    def __str__(self):
        return self.nome_completo


class FichaMedica(models.Model):
    """Dados médicos do aventureiro (uma ficha por aventureiro)."""

    aventureiro = models.OneToOneField(
        Aventureiro,
        on_delete=models.CASCADE,
        related_name="ficha_medica",
        verbose_name="Aventureiro",
    )

    # Plano de saúde
    possui_plano_saude = models.BooleanField("Possui plano de saúde", default=False)
    qual_plano_saude = models.CharField("Qual plano de saúde", max_length=150, blank=True)
    cartao_sus = models.CharField(
        "Número da Carteira Nacional do SUS", max_length=50, blank=True
    )

    # Doenças que já teve ou tem
    catapora = models.BooleanField("Catapora", default=False)
    meningite = models.BooleanField("Meningite", default=False)
    hepatite = models.BooleanField("Hepatite", default=False)
    dengue = models.BooleanField("Dengue", default=False)
    pneumonia = models.BooleanField("Pneumonia", default=False)
    malaria = models.BooleanField("Malária", default=False)
    febre_amarela = models.BooleanField("Febre amarela", default=False)
    h1n1 = models.BooleanField("H1N1", default=False)
    colera = models.BooleanField("Cólera", default=False)
    rubeola = models.BooleanField("Rubéola", default=False)
    sarampo = models.BooleanField("Sarampo", default=False)
    tetano = models.BooleanField("Tétano", default=False)

    # Alergias
    alergia_pele = models.BooleanField("Possui alergia cutânea/de pele", default=False)
    alergia_pele_qual = models.CharField("Qual alergia de pele", max_length=200, blank=True)
    alergia_alimentar = models.BooleanField("Possui alergia alimentar", default=False)
    alergia_alimentar_qual = models.CharField(
        "Qual alergia alimentar", max_length=200, blank=True
    )
    alergia_medicamentos = models.BooleanField(
        "Possui alergia a medicamentos", default=False
    )
    alergia_medicamentos_qual = models.CharField(
        "Qual alergia a medicamentos", max_length=200, blank=True
    )

    # Condições de saúde
    cardiaco = models.BooleanField("Possui problemas cardíacos", default=False)
    cardiaco_medicamentos = models.CharField(
        "Medicamentos (cardíacos)", max_length=200, blank=True
    )
    diabetico = models.BooleanField("É diabético", default=False)
    diabetico_medicamentos = models.CharField(
        "Medicamentos (diabetes)", max_length=200, blank=True
    )
    renais = models.BooleanField("Possui problemas renais", default=False)
    renais_medicamentos = models.CharField(
        "Medicamentos (renais)", max_length=200, blank=True
    )
    psicologicos = models.BooleanField("Possui problemas psicológicos", default=False)
    psicologicos_medicamentos = models.CharField(
        "Medicamentos (psicológicos)", max_length=200, blank=True
    )

    # Outras informações médicas
    outros_problemas = models.TextField(
        "Outros problemas de saúde ou medicamentos", blank=True
    )
    problema_recente = models.BooleanField(
        "Teve problemas de saúde recentemente", default=False
    )
    problema_recente_qual = models.CharField(
        "Qual problema recente", max_length=200, blank=True
    )
    medicamento_recente = models.BooleanField(
        "Usou medicamentos recentemente", default=False
    )
    medicamento_recente_qual = models.CharField(
        "Qual medicamento recente", max_length=200, blank=True
    )
    ferimento_recente = models.BooleanField(
        "Teve ferimentos graves ou fraturas recentes", default=False
    )
    ferimento_recente_qual = models.CharField(
        "Qual ferimento/fratura", max_length=200, blank=True
    )
    cirurgia = models.BooleanField("Passou por cirurgia", default=False)
    cirurgia_qual = models.CharField("Qual cirurgia", max_length=200, blank=True)
    internado_5anos = models.BooleanField(
        "Foi internado nos últimos cinco anos", default=False
    )
    internado_5anos_motivo = models.CharField(
        "Motivo da internação", max_length=200, blank=True
    )

    tipo_sanguineo = models.CharField(
        "Tipo sanguíneo", max_length=10, choices=TIPO_SANGUINEO_CHOICES, blank=True
    )

    class Meta:
        verbose_name = "Ficha médica"
        verbose_name_plural = "Fichas médicas"

    def __str__(self):
        return f"Ficha médica de {self.aventureiro.nome_completo}"


class AutorizacaoImagem(models.Model):
    """Termo de autorização de uso de imagem (um por aventureiro)."""

    aventureiro = models.OneToOneField(
        Aventureiro,
        on_delete=models.CASCADE,
        related_name="autorizacao_imagem",
        verbose_name="Aventureiro",
    )

    # Dados do menor
    nome_menor = models.CharField("Nome completo do menor", max_length=150)
    nacionalidade_menor = models.CharField(
        "Nacionalidade do menor", max_length=80, blank=True
    )

    # Dados do responsável legal (para o termo)
    resp_nome = models.CharField("Nome completo do responsável legal", max_length=150)
    resp_nacionalidade = models.CharField(
        "Nacionalidade do responsável legal", max_length=80, blank=True
    )
    resp_estado_civil = models.CharField("Estado civil", max_length=50, blank=True)
    resp_rg = models.CharField("RG", max_length=30, blank=True)
    resp_cpf = models.CharField("CPF", max_length=20, blank=True)
    resp_endereco = models.CharField("Endereço", max_length=200, blank=True)
    resp_numero = models.CharField("Número", max_length=20, blank=True)
    resp_bairro = models.CharField("Bairro", max_length=100, blank=True)
    resp_cidade = models.CharField("Cidade", max_length=100, blank=True)
    resp_estado = models.CharField("Estado", max_length=50, blank=True)

    class Meta:
        verbose_name = "Autorização de imagem"
        verbose_name_plural = "Autorizações de imagem"

    def __str__(self):
        return f"Autorização de imagem de {self.aventureiro.nome_completo}"


TIPO_EVENTO_CHOICES = [
    ("simples", "Evento simples"),
    ("inscricao", "Evento com inscrição"),
]


class Evento(models.Model):
    """Evento do clube (reunião, acampamento, festa, venda de alimentos, etc.).

    Por enquanto só o tipo "simples" é cadastrável pela interface; o tipo
    "com inscrição" (com pagamento, custos, presença, etc.) virá depois.
    """

    tipo = models.CharField(
        "Tipo do evento", max_length=20, choices=TIPO_EVENTO_CHOICES, default="simples"
    )
    nome = models.CharField("Nome do evento", max_length=150)
    local = models.CharField("Local do evento", max_length=200, blank=True)
    descricao = models.TextField("Descrição do evento", blank=True)
    data = models.DateField("Data do evento")
    # Data de término (eventos de vários dias, ex.: acampamento). No evento
    # simples fica vazia (evento de um dia só).
    data_fim = models.DateField("Data de término", null=True, blank=True)
    horario_inicio = models.TimeField("Horário de início", null=True, blank=True)
    horario_fim = models.TimeField("Horário de término", null=True, blank=True)

    # --- Configuração de inscrição (só usada em eventos "com inscrição") ---
    # Se True, qualquer pessoa pode se inscrever; se False, apenas membros do
    # clube (usuários com aventureiros cadastrados).
    inscricao_aberta_publico = models.BooleanField(
        "Aberto ao público geral", default=False
    )
    # Prazo limite para se inscrever. Passada esta data/hora, as inscrições
    # travam automaticamente. Se vazio, usa o fim do evento como limite.
    inscricao_limite = models.DateTimeField(
        "Prazo limite de inscrição", null=True, blank=True
    )
    # Valor único que a diretoria paga na inscrição (independe da faixa etária).
    # Vazio = sem valor especial para a diretoria.
    valor_diretoria = models.DecimalField(
        "Valor para a diretoria",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_criados",
        verbose_name="Criado por",
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ["-data", "-horario_inicio"]

    def __str__(self):
        return self.nome

    @property
    def eh_complexo(self):
        return self.tipo == "inscricao"

    def fim_datetime(self):
        """Data/hora de término do evento (aware). Usa `data_fim` ou `data`, e
        `horario_fim` ou o fim do dia (23:59). Retorna None se não houver data."""
        dia = self.data_fim or self.data
        if not dia:
            return None
        hora = self.horario_fim or datetime.time(23, 59, 59)
        dt = datetime.datetime.combine(dia, hora)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def prazo_inscricao(self):
        """Prazo efetivo das inscrições: `inscricao_limite` se definido; senão,
        o término do evento."""
        return self.inscricao_limite or self.fim_datetime()

    def inscricoes_abertas(self):
        """True se ainda dá para se inscrever (prazo não passou)."""
        prazo = self.prazo_inscricao()
        if prazo is None:
            return True
        return timezone.now() <= prazo

    def ja_terminou(self):
        """True se o evento já acabou (passou o término)."""
        fim = self.fim_datetime()
        return fim is not None and timezone.now() > fim

    def loja_aberta(self):
        """A lojinha vende enquanto o evento não terminou (independe do prazo de
        inscrição — dá para comprar no dia do evento)."""
        return not self.ja_terminou()

    def preco_participante(self, idade, eh_diretoria, faixas=None):
        """(valor, faixa) de um participante: valor da diretoria (se marcado e
        configurado) ou a faixa etária que casa com a idade; senão, 0."""
        if eh_diretoria and self.valor_diretoria is not None:
            return self.valor_diretoria, None
        if faixas is None:
            faixas = self.faixas_preco.all()
        if idade is not None:
            for faixa in faixas:
                if faixa.idade_min <= idade <= faixa.idade_max:
                    return faixa.valor, faixa
        return Decimal("0"), None


class CustoEvento(models.Model):
    """Custo/despesa de um evento (entra no resultado financeiro do evento)."""

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="custos",
        verbose_name="Evento",
    )
    nome = models.CharField("Título do custo", max_length=150)
    descricao = models.TextField("Descrição", blank=True)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)
    comprovante = models.FileField(
        "Comprovante", upload_to="eventos/custos/", blank=True, null=True
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custos_evento_criados",
        verbose_name="Criado por",
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Custo do evento"
        verbose_name_plural = "Custos do evento"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} — {self.evento.nome}"


class FaixaEtariaPreco(models.Model):
    """Faixa etária com valor de inscrição, definida por evento.

    Cada evento com inscrição pode ter faixas diferentes (ex.: 6 a 10 anos =
    R$ 30,00). O valor da diretoria fica no próprio `Evento` (`valor_diretoria`),
    pois independe da idade.
    """

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="faixas_preco",
        verbose_name="Evento",
    )
    rotulo = models.CharField(
        "Rótulo da faixa", max_length=60, blank=True,
        help_text="Opcional. Ex.: \"Crianças\". Se vazio, mostra a faixa de idades.",
    )
    idade_min = models.PositiveIntegerField("Idade mínima", default=0)
    idade_max = models.PositiveIntegerField("Idade máxima", default=0)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Faixa etária (preço)"
        verbose_name_plural = "Faixas etárias (preços)"
        ordering = ["ordem", "idade_min", "id"]

    @property
    def faixa_txt(self):
        """Descrição da faixa de idades (ex.: "6 a 10 anos")."""
        return f"{self.idade_min} a {self.idade_max} anos"

    def __str__(self):
        return f"{self.rotulo or self.faixa_txt} — {self.evento.nome}"


TIPO_CAMPO_INSCRICAO_CHOICES = [
    ("texto", "Texto curto"),
    ("texto_longo", "Texto longo"),
    ("numero", "Número"),
    ("escolha_unica", "Escolha única"),
    ("escolha_multipla", "Escolha múltipla"),
    ("sim_nao", "Sim/Não"),
    ("data", "Data"),
]


class CampoInscricao(models.Model):
    """Campo personalizado do formulário de inscrição de um evento (Fase 2.2).

    O Diretor monta, por evento, os campos extras que quer perguntar na
    inscrição. O preenchimento/envio (respostas) virá na Fase 2.4.
    """

    # Tipos que exigem uma lista de opções.
    TIPOS_COM_OPCOES = ("escolha_unica", "escolha_multipla")

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="campos_inscricao",
        verbose_name="Evento",
    )
    rotulo = models.CharField("Pergunta / rótulo", max_length=150)
    tipo = models.CharField(
        "Tipo do campo",
        max_length=20,
        choices=TIPO_CAMPO_INSCRICAO_CHOICES,
        default="texto",
    )
    opcoes = models.TextField(
        "Opções",
        blank=True,
        help_text="Uma opção por linha (só para escolha única/múltipla).",
    )
    obrigatorio = models.BooleanField("Obrigatório", default=False)
    # Se True, o campo é perguntado para CADA participante; se False, uma única
    # vez na inscrição (junto dos dados do responsável).
    por_participante = models.BooleanField(
        "Perguntar para cada participante", default=False
    )
    ordem = models.PositiveIntegerField("Ordem", default=0)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Campo de inscrição"
        verbose_name_plural = "Campos de inscrição"
        ordering = ["ordem", "id"]

    @property
    def usa_opcoes(self):
        return self.tipo in self.TIPOS_COM_OPCOES

    @property
    def opcoes_lista(self):
        """Opções como lista (ignora linhas vazias)."""
        return [ln.strip() for ln in (self.opcoes or "").splitlines() if ln.strip()]

    def __str__(self):
        return f"{self.rotulo} ({self.get_tipo_display()}) — {self.evento.nome}"


STATUS_INSCRICAO_CHOICES = [
    ("confirmada", "Confirmada"),
    ("cancelada", "Cancelada"),
]

FORMA_PAGAMENTO_CHOICES = [
    ("online", "Online (site)"),
    ("dinheiro", "Dinheiro"),
    ("pix", "Pix"),
    ("cartao", "Cartão"),
    ("cortesia", "Cortesia"),
]

ORIGEM_PEDIDO_CHOICES = [
    ("online", "Online"),
    ("pdv", "PDV (balcão)"),
]


class Inscricao(models.Model):
    """Inscrição de um responsável em um evento com inscrição (Fase 2.4).

    Uma inscrição tem um ou mais participantes (cada um com um valor por faixa
    etária ou pelo valor da diretoria) e as respostas dos campos personalizados.
    O pagamento é **simulado** por ora (a inscrição já nasce confirmada).
    """

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="inscricoes",
        verbose_name="Evento",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inscricoes",
        verbose_name="Usuário (se logado)",
    )
    responsavel_nome = models.CharField("Nome do responsável", max_length=150)
    responsavel_whatsapp = models.CharField("WhatsApp", max_length=20, blank=True)
    responsavel_email = models.EmailField("E-mail", blank=True)
    responsavel_cpf = models.CharField("CPF", max_length=20, blank=True)
    codigo = models.CharField("Código da inscrição", max_length=20, unique=True)
    status = models.CharField(
        "Situação", max_length=12, choices=STATUS_INSCRICAO_CHOICES, default="confirmada"
    )
    origem = models.CharField(
        "Origem", max_length=10, choices=ORIGEM_PEDIDO_CHOICES, default="online"
    )
    forma_pagamento = models.CharField(
        "Forma de pagamento", max_length=12, choices=FORMA_PAGAMENTO_CHOICES,
        default="online",
    )
    # Valor recebido na transação do balcão (inscrição + itens da lojinha juntos).
    valor_recebido = models.DecimalField(
        "Valor recebido", max_digits=10, decimal_places=2, null=True, blank=True
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inscricoes_registradas",
        verbose_name="Registrado por",
    )
    valor_total = models.DecimalField(
        "Valor total", max_digits=10, decimal_places=2, default=0
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Inscrição"
        verbose_name_plural = "Inscrições"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.codigo} — {self.responsavel_nome} ({self.evento.nome})"

    @property
    def total_com_loja(self):
        """Total da inscrição + pedidos da lojinha confirmados vinculados a ela."""
        loja = sum(
            (p.valor_total for p in self.pedidos.all() if p.status == "confirmado"),
            Decimal("0"),
        )
        return self.valor_total + loja

    @property
    def troco(self):
        """Troco da transação do balcão (só no pagamento em dinheiro)."""
        if self.valor_recebido is None:
            return None
        return self.valor_recebido - self.total_com_loja

    @staticmethod
    def gerar_codigo_unico():
        """Código curto e único (ex.: 'A3K9Q2')."""
        alfabeto = string.ascii_uppercase + string.digits
        while True:
            codigo = "".join(random.choices(alfabeto, k=6))
            if not Inscricao.objects.filter(codigo=codigo).exists():
                return codigo


class ParticipanteInscricao(models.Model):
    """Cada participante (pessoa) de uma inscrição, com o valor aplicado."""

    inscricao = models.ForeignKey(
        Inscricao,
        on_delete=models.CASCADE,
        related_name="participantes",
        verbose_name="Inscrição",
    )
    nome = models.CharField("Nome do participante", max_length=150)
    idade = models.PositiveIntegerField("Idade", null=True, blank=True)
    eh_diretoria = models.BooleanField("É da diretoria", default=False)
    # Faixa aplicada (nulo se pagou como diretoria ou se nenhuma faixa casou).
    faixa = models.ForeignKey(
        FaixaEtariaPreco,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="participantes",
        verbose_name="Faixa aplicada",
    )
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Participante da inscrição"
        verbose_name_plural = "Participantes da inscrição"
        ordering = ["id"]

    def __str__(self):
        return f"{self.nome} — {self.inscricao.codigo}"


class ProdutoEvento(models.Model):
    """Produto da lojinha de um evento (Fase 4.1). O preço fica nas variações."""

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="produtos",
        verbose_name="Evento",
    )
    nome = models.CharField("Nome do produto", max_length=150)
    descricao = models.TextField("Descrição", blank=True)
    foto = models.ImageField(
        "Foto", upload_to="eventos/produtos/", blank=True, null=True
    )
    controla_estoque = models.BooleanField("Controlar estoque", default=False)
    ativo = models.BooleanField("À venda", default=True)
    ordem = models.PositiveIntegerField("Ordem", default=0)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Produto da lojinha"
        verbose_name_plural = "Produtos da lojinha"
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.nome} — {self.evento.nome}"


class VariacaoProduto(models.Model):
    """Uma variação de um produto (ex.: tamanho/sabor), com preço e estoque."""

    produto = models.ForeignKey(
        ProdutoEvento,
        on_delete=models.CASCADE,
        related_name="variacoes",
        verbose_name="Produto",
    )
    nome = models.CharField("Nome da variação", max_length=80, blank=True)
    valor = models.DecimalField("Preço", max_digits=10, decimal_places=2, default=0)
    estoque = models.PositiveIntegerField("Estoque", default=0)
    ordem = models.PositiveIntegerField("Ordem", default=0)

    class Meta:
        verbose_name = "Variação de produto"
        verbose_name_plural = "Variações de produto"
        ordering = ["ordem", "id"]

    @property
    def rotulo(self):
        return self.nome or "Único"

    @property
    def esgotado(self):
        """Sem estoque (só faz sentido quando o produto controla estoque)."""
        return self.produto.controla_estoque and self.estoque <= 0

    def __str__(self):
        return f"{self.rotulo} — {self.produto.nome}"


STATUS_PEDIDO_CHOICES = [
    ("confirmado", "Confirmado"),
    ("cancelado", "Cancelado"),
]


class PedidoLoja(models.Model):
    """Pedido da lojinha de um evento (Fase 4.2). Pagamento simulado."""

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="pedidos",
        verbose_name="Evento",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_loja",
        verbose_name="Usuário (se logado)",
    )
    # Preenchido quando o pedido foi feito junto de uma inscrição (Fase 4.3).
    inscricao = models.ForeignKey(
        Inscricao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos",
        verbose_name="Inscrição vinculada",
    )
    comprador_nome = models.CharField("Nome do comprador", max_length=150)
    comprador_whatsapp = models.CharField("WhatsApp", max_length=20, blank=True)
    comprador_email = models.EmailField("E-mail", blank=True)
    codigo = models.CharField("Código do pedido", max_length=20, unique=True)
    status = models.CharField(
        "Situação", max_length=12, choices=STATUS_PEDIDO_CHOICES, default="confirmado"
    )
    origem = models.CharField(
        "Origem", max_length=10, choices=ORIGEM_PEDIDO_CHOICES, default="online"
    )
    forma_pagamento = models.CharField(
        "Forma de pagamento", max_length=12, choices=FORMA_PAGAMENTO_CHOICES,
        default="online",
    )
    # Só para pagamento em dinheiro (para calcular/registrar o troco).
    valor_recebido = models.DecimalField(
        "Valor recebido", max_digits=10, decimal_places=2, null=True, blank=True
    )
    # Atendente que registrou a venda no balcão (PDV).
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_registrados",
        verbose_name="Registrado por",
    )
    valor_total = models.DecimalField(
        "Valor total", max_digits=10, decimal_places=2, default=0
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    @property
    def troco(self):
        """Troco (só faz sentido no pagamento em dinheiro)."""
        if self.valor_recebido is None:
            return None
        return self.valor_recebido - self.valor_total

    class Meta:
        verbose_name = "Pedido da lojinha"
        verbose_name_plural = "Pedidos da lojinha"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.codigo} — {self.comprador_nome} ({self.evento.nome})"

    @staticmethod
    def gerar_codigo_unico():
        alfabeto = string.ascii_uppercase + string.digits
        while True:
            codigo = "P" + "".join(random.choices(alfabeto, k=5))
            if not PedidoLoja.objects.filter(codigo=codigo).exists():
                return codigo


class ItemPedidoLoja(models.Model):
    """Um item de um pedido da lojinha (variação + quantidade)."""

    pedido = models.ForeignKey(
        PedidoLoja,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="Pedido",
    )
    variacao = models.ForeignKey(
        VariacaoProduto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="itens_pedido",
        verbose_name="Variação",
    )
    # Snapshots (mantêm o pedido legível mesmo se o produto mudar/for apagado).
    produto_nome = models.CharField("Produto", max_length=150)
    variacao_nome = models.CharField("Variação", max_length=80, blank=True)
    quantidade = models.PositiveIntegerField("Quantidade", default=1)
    valor_unitario = models.DecimalField(
        "Valor unitário", max_digits=10, decimal_places=2, default=0
    )
    valor_total = models.DecimalField(
        "Valor total", max_digits=10, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantidade}x {self.produto_nome} — {self.pedido.codigo}"


class RespostaInscricao(models.Model):
    """Resposta de um campo personalizado do formulário, numa inscrição."""

    inscricao = models.ForeignKey(
        Inscricao,
        on_delete=models.CASCADE,
        related_name="respostas",
        verbose_name="Inscrição",
    )
    # Preenchido quando a resposta é de um campo "por participante"; nulo quando
    # é um campo respondido uma vez na inscrição.
    participante = models.ForeignKey(
        ParticipanteInscricao,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="respostas",
        verbose_name="Participante",
    )
    campo = models.ForeignKey(
        CampoInscricao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respostas",
        verbose_name="Campo",
    )
    # Snapshot do rótulo (mantém a resposta legível mesmo se o campo for apagado).
    campo_rotulo = models.CharField("Pergunta", max_length=150, blank=True)
    valor = models.TextField("Resposta", blank=True)

    class Meta:
        verbose_name = "Resposta da inscrição"
        verbose_name_plural = "Respostas da inscrição"
        ordering = ["id"]

    def __str__(self):
        return f"{self.campo_rotulo}: {self.valor}"


class PerfilUsuario(models.Model):
    """Dados extras do usuário (Fase 4.4c). Por ora, só a flag de troca de senha
    obrigatória (usada pelas contas temporárias de ajudantes)."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuário",
    )
    precisa_trocar_senha = models.BooleanField(
        "Precisa trocar a senha no próximo login", default=False
    )

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class OperadorEvento(models.Model):
    """Quem pode operar o PDV de um evento (Fase 4.4c): membros da diretoria
    selecionados ou ajudantes externos (conta temporária criada pelo Diretor)."""

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="operadores",
        verbose_name="Evento",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="eventos_operados",
        verbose_name="Operador",
    )
    # True = conta temporária de ajudante de fora (criada só para este evento).
    externo = models.BooleanField("Ajudante externo", default=False)
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Operador do evento"
        verbose_name_plural = "Operadores do evento"
        unique_together = [("evento", "usuario")]
        ordering = ["evento", "usuario__username"]

    def __str__(self):
        return f"{self.usuario.username} @ {self.evento.nome}"


class CupomDesconto(models.Model):
    """Cupom de desconto (Fase 5.3) — vale **somente para inscrição** (não na
    lojinha). Uso único: ao ser usado, aplica o `percentual` em **um** participante
    da inscrição (o de maior valor). Guarda quem usou, quando e quanto foi
    descontado, para acompanhamento no painel."""

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="cupons",
        verbose_name="Evento",
    )
    codigo = models.CharField("Código", max_length=20, unique=True)
    percentual = models.PositiveIntegerField("Percentual de desconto (%)")
    ativo = models.BooleanField("Ativo", default=True)
    # Inscrição que usou o cupom (nulo enquanto disponível).
    inscricao = models.ForeignKey(
        "Inscricao",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cupons",
        verbose_name="Inscrição que usou",
    )
    usado_por = models.CharField("Usado por", max_length=150, blank=True)
    valor_desconto = models.DecimalField(
        "Valor descontado", max_digits=10, decimal_places=2, null=True, blank=True
    )
    usado_em = models.DateTimeField("Usado em", null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cupons_criados",
        verbose_name="Criado por",
    )
    criado_em = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        verbose_name = "Cupom de desconto"
        verbose_name_plural = "Cupons de desconto"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.codigo} ({self.percentual}%)"

    @property
    def usado(self):
        return self.usado_em is not None

    @staticmethod
    def gerar_codigo_unico():
        alfabeto = string.ascii_uppercase + string.digits
        while True:
            codigo = "D" + "".join(random.choices(alfabeto, k=5))
            if not CupomDesconto.objects.filter(codigo=codigo).exists():
                return codigo
