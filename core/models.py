"""
Models do app core — cadastro de aventureiros.

Estrutura pensada para que um mesmo usuário (responsável) possa cadastrar
vários aventureiros no futuro. Cada aventureiro tem uma ficha de inscrição
(no próprio model), uma ficha médica e uma autorização de imagem.
"""

import datetime

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
