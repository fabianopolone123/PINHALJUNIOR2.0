"""
Formulários do cadastro de aventureiros.

São quatro formulários combinados no mesmo envio (com prefixos diferentes):
- ContaForm            -> cria o usuário de acesso
- AventureiroForm      -> ficha de inscrição + responsáveis
- FichaMedicaForm      -> dados médicos
- AutorizacaoImagemForm-> termo de uso de imagem
"""

from django import forms
from django.contrib.auth.models import User

from .models import (
    Aventureiro,
    AutorizacaoImagem,
    CaixaClube,
    CampoInscricao,
    CustoClube,
    CustoEvento,
    Evento,
    FaixaEtariaPreco,
    FichaMedica,
    FichaMedicaDiretoria,
    MembroDiretoria,
    ProdutoEvento,
    ProdutoLoja,
)


class EstiloFormMixin:
    """Adiciona classes CSS automáticas aos widgets, conforme o tipo."""

    def _aplicar_estilo(self):
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "campo-check")
            elif isinstance(widget, (forms.Select,)):
                widget.attrs.setdefault("class", "campo-select")
            elif isinstance(widget, (forms.Textarea,)):
                widget.attrs.setdefault("class", "campo-input campo-textarea")
            elif isinstance(widget, (forms.ClearableFileInput,)):
                widget.attrs.setdefault("class", "campo-file")
            else:
                widget.attrs.setdefault("class", "campo-input")


SIM_NAO_CHOICES = [("sim", "Sim"), ("nao", "Não")]


def campo_sim_nao(label, required=True):
    """Campo Sim/Não obrigatório (radio) que grava num BooleanField do model."""
    return forms.TypedChoiceField(
        label=label,
        choices=SIM_NAO_CHOICES,
        coerce=lambda v: v == "sim",
        empty_value=None,
        widget=forms.RadioSelect,
        required=required,
    )


# Ficha médica: pares (pergunta booleana -> campo de detalhe obrigatório se "Sim").
MED_PARES = [
    ("possui_plano_saude", "qual_plano_saude"),
    ("alergia_pele", "alergia_pele_qual"),
    ("alergia_alimentar", "alergia_alimentar_qual"),
    ("alergia_medicamentos", "alergia_medicamentos_qual"),
    ("cardiaco", "cardiaco_medicamentos"),
    ("diabetico", "diabetico_medicamentos"),
    ("renais", "renais_medicamentos"),
    ("psicologicos", "psicologicos_medicamentos"),
    ("problema_recente", "problema_recente_qual"),
    ("medicamento_recente", "medicamento_recente_qual"),
    ("ferimento_recente", "ferimento_recente_qual"),
    ("cirurgia", "cirurgia_qual"),
    ("internado_5anos", "internado_5anos_motivo"),
]
MED_DOENCAS = [
    "catapora", "meningite", "hepatite", "dengue", "pneumonia", "malaria",
    "febre_amarela", "h1n1", "colera", "rubeola", "sarampo", "tetano",
    "variola", "coqueluche", "difteria", "caxumba", "rinite", "bronquite",
]
MED_DEFICIENCIAS = [
    "deficiente_cadeirante", "deficiente_visual", "deficiente_auditivo", "deficiente_fala",
]


class FichaMedicaCamposMixin:
    """Transforma a ficha médica num formulário de Sim/Não OBRIGATÓRIO + detalhe.

    Cada pergunta (plano, alergias, condições, histórico recente) vira um Sim/Não
    obrigatório; o detalhe correspondente só é exigido quando "Sim". As listas de
    doenças e de deficiências ganham um Sim/Não obrigatório na frente (`teve_doencas`
    / `tem_deficiencia`); se "Sim", ao menos um item deve ser marcado; se "Não", a
    lista é zerada. Reutilizado pelo aventureiro e pela diretoria."""

    def _preparar_ficha_medica(self):
        # 1) Perguntas Sim/Não obrigatórias (substituem os checkboxes dos booleanos).
        for booleano, detalhe in MED_PARES:
            self.fields[booleano] = campo_sim_nao(self.fields[booleano].label)
            self.fields[detalhe].required = False  # exigido no clean() só se "Sim"
        # 2) Doenças/deficiências: a lista fica VISÍVEL + opção "Nenhuma" (exige ao
        #    menos uma marcação). Assim a pessoa vê a lista antes de responder.
        self.fields["sem_doencas"] = forms.BooleanField(
            label="Não teve/tem nenhuma dessas doenças", required=False
        )
        self.fields["sem_deficiencia"] = forms.BooleanField(
            label="Não possui deficiência física", required=False
        )
        # 3) Cartão do SUS e tipo sanguíneo obrigatórios.
        self.fields["cartao_sus"].required = True
        self.fields["tipo_sanguineo"].required = True

    def clean(self):
        cleaned = super().clean()
        for booleano, detalhe in MED_PARES:
            if cleaned.get(booleano) is True and not (cleaned.get(detalhe) or "").strip():
                self.add_error(detalhe, "Informe o detalhe, já que marcou Sim.")
        if not any(cleaned.get(d) for d in MED_DOENCAS) and not cleaned.get("sem_doencas"):
            self.add_error("sem_doencas", "Marque as doenças ou selecione 'Nenhuma'.")
        if not any(cleaned.get(x) for x in MED_DEFICIENCIAS) and not cleaned.get("sem_deficiencia"):
            self.add_error("sem_deficiencia", "Marque a(s) deficiência(s) ou selecione 'Nenhuma'.")
        return cleaned


class ContaForm(EstiloFormMixin, forms.Form):
    """Conta de acesso (etapa 1)."""

    username = forms.CharField(
        label="Usuário",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Escolha um nome de usuário"}),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"placeholder": "Crie uma senha"}),
    )
    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"placeholder": "Repita a senha"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso.")
        return username

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get("senha")
        confirmar = cleaned.get("confirmar_senha")
        if senha and confirmar and senha != confirmar:
            self.add_error("confirmar_senha", "As senhas não conferem.")
        return cleaned


class AventureiroForm(EstiloFormMixin, forms.ModelForm):
    """Ficha de inscrição do aventureiro + dados dos responsáveis (etapas 2 e 3)."""

    class Meta:
        model = Aventureiro
        # 'usuario', 'data_inscricao' e 'criado_em' são definidos no servidor.
        exclude = ["usuario", "data_inscricao", "criado_em"]
        widgets = {
            "data_nascimento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "pai_email": forms.EmailInput(),
            "mae_email": forms.EmailInput(),
            "resp_email": forms.EmailInput(),
            "foto": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    OBRIGATORIOS = [
        "foto", "colegio", "serie", "ano", "tamanho_camiseta",
        "endereco", "bairro", "cidade", "cep", "estado",
        "resp_parentesco", "resp_email",
    ]
    PAI_CAMPOS = ["pai_nome", "pai_email", "pai_cpf", "pai_celular", "pai_whatsapp"]
    MAE_CAMPOS = ["mae_nome", "mae_email", "mae_cpf", "mae_celular", "mae_whatsapp"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Os aceites são validados/mostrados nas etapas 5 e 6, não aqui.
        self.fields["declaracao_medica_aceita"].required = False
        self.fields["autorizacao_imagem_aceita"].required = False
        # Isenção/desconto de mensalidade são definidos pelo Diretor depois.
        self.fields["mensalidade_isento"].required = False
        self.fields["mensalidade_desconto_pct"].required = False
        for nome in self.OBRIGATORIOS:
            self.fields[nome].required = True
        # Bolsa Família vira Sim/Não obrigatório.
        self.fields["bolsa_familia"] = campo_sim_nao("Beneficiado pelo Bolsa Família?")
        # Classes: opção "Nenhuma" (exigimos ao menos uma classe OU "nenhuma").
        self.fields["sem_classe"] = forms.BooleanField(
            label="Ainda não foi investido em nenhuma classe", required=False
        )
        # Dados de pai e mãe: "tem os dados?" (Sim/Não obrigatório). Se Sim, todos
        # os campos daquele responsável são exigidos (no clean).
        self.fields["tem_dados_pai"] = campo_sim_nao("Tem os dados do pai?")
        self.fields["tem_dados_mae"] = campo_sim_nao("Tem os dados da mãe?")
        self._aplicar_estilo()

    def clean(self):
        cleaned = super().clean()
        classes = [
            cleaned.get("classe_abelhinhas"), cleaned.get("classe_luminares"),
            cleaned.get("classe_edificadores"), cleaned.get("classe_maos_ajudadoras"),
        ]
        if not any(classes) and not cleaned.get("sem_classe"):
            self.add_error("sem_classe", "Marque ao menos uma classe ou 'Nenhuma'.")
        if cleaned.get("tem_dados_pai") is True:
            for c in self.PAI_CAMPOS:
                if not (cleaned.get(c) or "").strip():
                    self.add_error(c, "Obrigatório (você marcou que tem os dados do pai).")
        if cleaned.get("tem_dados_mae") is True:
            for c in self.MAE_CAMPOS:
                if not (cleaned.get(c) or "").strip():
                    self.add_error(c, "Obrigatório (você marcou que tem os dados da mãe).")
        return cleaned


class FichaMedicaForm(FichaMedicaCamposMixin, EstiloFormMixin, forms.ModelForm):
    """Dados médicos do aventureiro (etapa 4). Sim/Não obrigatório + detalhe."""

    class Meta:
        model = FichaMedica
        exclude = ["aventureiro"]
        widgets = {
            "outros_problemas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_ficha_medica()
        self._aplicar_estilo()


class ResponsavelLegalForm(EstiloFormMixin, forms.Form):
    """Edição dos dados do responsável legal (compartilhados entre aventureiros)."""

    resp_nome = forms.CharField(label="Nome do responsável legal", max_length=150)
    resp_parentesco = forms.CharField(
        label="Grau de parentesco", max_length=50, required=False
    )
    resp_cpf = forms.CharField(label="CPF", max_length=20)
    resp_email = forms.EmailField(label="E-mail", required=False)
    resp_whatsapp = forms.CharField(label="WhatsApp", max_length=20)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()


class AutorizacaoImagemForm(EstiloFormMixin, forms.ModelForm):
    """Termo de autorização de uso de imagem (etapa 6)."""

    OBRIGATORIOS = [
        "nome_menor", "nacionalidade_menor",
        "resp_nome", "resp_nacionalidade", "resp_estado_civil", "resp_rg",
    ]

    class Meta:
        model = AutorizacaoImagem
        exclude = ["aventureiro"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in self.OBRIGATORIOS:
            self.fields[nome].required = True
        self._aplicar_estilo()


class MembroDiretoriaForm(EstiloFormMixin, forms.ModelForm):
    """Ficha "Compromisso para Voluntários" — dados do membro da diretoria.

    Os aceites (compromisso/declaração médica/autorização de imagem) e os campos
    de sistema (usuário, ativo, demo) são tratados no servidor, fora do form.
    """

    class Meta:
        model = MembroDiretoria
        exclude = [
            "usuario", "ativo", "demo", "criado_em",
            "compromisso_aceito", "declaracao_medica_aceita",
            "autorizacao_imagem_aceita",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "email": forms.EmailInput(),
            "foto": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    # Campos obrigatórios da diretoria (o resto: telefones/cônjuge/qtd são
    # opcionais ou condicionais).
    OBRIGATORIOS = [
        "foto", "nacionalidade", "data_nascimento", "igreja", "distrito", "rg",
        "estado_civil", "email", "endereco", "numero", "bairro", "cidade", "cep",
        "estado", "escolaridade",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in self.OBRIGATORIOS:
            self.fields[nome].required = True
        # "Tem filhos?" vira Sim/Não obrigatório; cônjuge/qtd são condicionais.
        self.fields["tem_filhos"] = campo_sim_nao("Tem filhos?")
        self.fields["conjuge_nome"].required = False
        self.fields["qtd_filhos"].required = False
        self._aplicar_estilo()

    def clean(self):
        cleaned = super().clean()
        civil = cleaned.get("estado_civil")
        if civil in ("casado", "uniao_estavel") and not (cleaned.get("conjuge_nome") or "").strip():
            self.add_error("conjuge_nome", "Informe o nome do cônjuge.")
        if cleaned.get("tem_filhos") is True:
            qtd = cleaned.get("qtd_filhos")
            if not qtd or qtd < 1:
                self.add_error("qtd_filhos", "Informe a quantidade de filhos.")
        elif cleaned.get("tem_filhos") is False:
            cleaned["qtd_filhos"] = 0
        if cleaned.get("qtd_filhos") is None:
            cleaned["qtd_filhos"] = 0
        return cleaned


class FichaMedicaDiretoriaForm(FichaMedicaCamposMixin, EstiloFormMixin, forms.ModelForm):
    """Dados médicos do membro da diretoria. Sim/Não obrigatório + detalhe."""

    class Meta:
        model = FichaMedicaDiretoria
        exclude = ["membro"]
        widgets = {
            "outros_problemas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparar_ficha_medica()
        self._aplicar_estilo()


class EventoForm(EstiloFormMixin, forms.ModelForm):
    """Cadastro de um evento simples do clube."""

    class Meta:
        model = Evento
        fields = ["nome", "local", "descricao", "data", "horario_inicio", "horario_fim"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "horario_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "horario_fim": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos obrigatórios do evento simples.
        self.fields["nome"].required = True
        self.fields["data"].required = True
        # Garante que os widgets de hora aceitem o valor já formatado (HH:MM).
        for campo in ("horario_inicio", "horario_fim"):
            self.fields[campo].input_formats = ["%H:%M", "%H:%M:%S"]
        self._aplicar_estilo()


class EventoComplexoForm(EstiloFormMixin, forms.ModelForm):
    """Dados básicos de um evento complexo (com inscrição). Fase 1."""

    class Meta:
        model = Evento
        fields = ["nome", "local", "descricao", "data", "horario_inicio", "data_fim", "horario_fim"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "data_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "horario_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "horario_fim": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "data": "Data de início",
            "horario_inicio": "Horário de início",
            "data_fim": "Data de término",
            "horario_fim": "Horário de término",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].required = True
        self.fields["data"].required = True
        # No evento com inscrição o local é obrigatório (a pessoa precisa saber
        # onde vai acontecer).
        self.fields["local"].required = True
        for campo in ("horario_inicio", "horario_fim"):
            self.fields[campo].input_formats = ["%H:%M", "%H:%M:%S"]
        self._aplicar_estilo()


class EventoInscricaoConfigForm(EstiloFormMixin, forms.ModelForm):
    """Configuração da inscrição de um evento complexo (Parte 2.1)."""

    class Meta:
        model = Evento
        fields = ["local", "inscricao_aberta_publico", "inscricao_limite", "valor_diretoria"]
        widgets = {
            "inscricao_limite": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "valor_diretoria": forms.TextInput(
                attrs={"data-moeda": True, "inputmode": "decimal", "placeholder": "0,00"}
            ),
        }
        help_texts = {
            "inscricao_aberta_publico": "Se desmarcado, só membros do clube podem se inscrever.",
            "inscricao_limite": "Depois desta data/hora as inscrições travam. Vazio = até o fim do evento.",
            "valor_diretoria": "Valor que a diretoria paga. Vazio = sem valor especial; 0 = grátis.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["local"].required = True
        self.fields["inscricao_limite"].input_formats = [
            "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
        ]
        self._aplicar_estilo()


class FaixaEtariaPrecoForm(EstiloFormMixin, forms.ModelForm):
    """Uma faixa etária com valor, dentro de um evento com inscrição."""

    class Meta:
        model = FaixaEtariaPreco
        fields = ["rotulo", "idade_min", "idade_max", "valor"]
        widgets = {
            "idade_min": forms.NumberInput(attrs={"min": "0", "max": "120"}),
            "idade_max": forms.NumberInput(attrs={"min": "0", "max": "120"}),
            "valor": forms.TextInput(
                attrs={"data-moeda": True, "inputmode": "decimal", "placeholder": "0,00"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()

    def clean(self):
        cleaned = super().clean()
        minimo = cleaned.get("idade_min")
        maximo = cleaned.get("idade_max")
        if minimo is not None and maximo is not None and maximo < minimo:
            self.add_error(
                "idade_max", "A idade máxima não pode ser menor que a mínima."
            )
        return cleaned


class CampoInscricaoForm(EstiloFormMixin, forms.ModelForm):
    """Um campo personalizável do formulário de inscrição de um evento (Fase 2.2)."""

    class Meta:
        model = CampoInscricao
        fields = ["rotulo", "tipo", "opcoes", "obrigatorio", "por_participante"]
        widgets = {
            "opcoes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Uma opção por linha (só p/ escolha única ou múltipla)",
            }),
        }
        help_texts = {
            "por_participante": "Marque para perguntar em cada participante; senão, é preenchido uma vez.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rotulo"].required = True
        self._aplicar_estilo()

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")
        linhas = [
            ln.strip() for ln in (cleaned.get("opcoes") or "").splitlines() if ln.strip()
        ]
        if tipo in CampoInscricao.TIPOS_COM_OPCOES:
            if len(linhas) < 2:
                self.add_error(
                    "opcoes",
                    "Informe pelo menos duas opções (uma por linha) para campos de escolha.",
                )
            else:
                cleaned["opcoes"] = "\n".join(linhas)
        else:
            # Tipos sem opções não guardam nada em 'opcoes'.
            cleaned["opcoes"] = ""
        return cleaned


class InscricaoForm(EstiloFormMixin, forms.Form):
    """Formulário de inscrição de um evento: dados do responsável + os campos
    personalizados do evento (adicionados dinamicamente conforme `CampoInscricao`).

    Os participantes (nome/idade/diretoria) são tratados fora deste form, na view
    (linhas repetíveis), pois a quantidade é dinâmica.
    """

    responsavel_nome = forms.CharField(
        label="Nome completo do responsável", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Nome e sobrenome"}),
        help_text="Nome e sobrenome (evite só o primeiro nome).",
    )
    responsavel_whatsapp = forms.CharField(label="WhatsApp", max_length=20)
    responsavel_email = forms.EmailField(label="E-mail")
    responsavel_cpf = forms.CharField(label="CPF", max_length=20)

    def __init__(self, *args, evento=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.evento = evento
        self.campos_extra = []  # lista de (campo, nome_do_field) — só de inscrição única
        if evento is not None:
            # Só os campos "uma vez" viram campos deste form. Os "por participante"
            # são tratados na view (linhas repetíveis).
            for campo in evento.campos_inscricao.filter(por_participante=False):
                nome = f"campo_{campo.id}"
                self.fields[nome] = self._construir_campo(campo)
                self.campos_extra.append((campo, nome))
        self._aplicar_estilo()

    def _construir_campo(self, campo):
        obrig = campo.obrigatorio
        rotulo = campo.rotulo
        if campo.tipo == "texto_longo":
            return forms.CharField(
                label=rotulo, required=obrig, widget=forms.Textarea(attrs={"rows": 3})
            )
        if campo.tipo == "numero":
            return forms.DecimalField(label=rotulo, required=obrig)
        if campo.tipo == "escolha_unica":
            escolhas = [(o, o) for o in campo.opcoes_lista]
            return forms.ChoiceField(label=rotulo, required=obrig, choices=escolhas)
        if campo.tipo == "escolha_multipla":
            escolhas = [(o, o) for o in campo.opcoes_lista]
            return forms.MultipleChoiceField(
                label=rotulo, required=obrig, choices=escolhas,
                widget=forms.CheckboxSelectMultiple,
            )
        if campo.tipo == "sim_nao":
            # 'Não' (desmarcado) é uma resposta válida → nunca obrigar a marcar.
            return forms.BooleanField(label=rotulo, required=False)
        if campo.tipo == "data":
            return forms.DateField(
                label=rotulo, required=obrig,
                widget=forms.DateInput(attrs={"type": "date"}),
            )
        # texto (padrão)
        return forms.CharField(label=rotulo, required=obrig, max_length=255)

    @property
    def campos_personalizados(self):
        """BoundFields dos campos personalizados, para renderizar no template."""
        return [self[nome] for _campo, nome in self.campos_extra]

    def resposta_texto(self, campo, nome):
        """Texto legível da resposta de um campo, para gravar em RespostaInscricao."""
        valor = self.cleaned_data.get(nome)
        if campo.tipo == "sim_nao":
            return "Sim" if valor else "Não"
        if campo.tipo == "escolha_multipla":
            return ", ".join(valor) if valor else ""
        if campo.tipo == "data":
            return valor.strftime("%d/%m/%Y") if valor else ""
        return "" if valor is None else str(valor)


class ProdutoEventoForm(EstiloFormMixin, forms.ModelForm):
    """Dados básicos de um produto da lojinha (Fase 4.1). As variações são
    tratadas na view (linhas repetíveis)."""

    class Meta:
        model = ProdutoEvento
        fields = ["nome", "descricao", "foto", "controla_estoque", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "foto": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].required = True
        self._aplicar_estilo()


class ProdutoLojaForm(EstiloFormMixin, forms.ModelForm):
    """Dados básicos de um produto da loja do clube. Os grupos e variações são
    tratados na view (linhas repetíveis, como na lojinha do evento)."""

    class Meta:
        model = ProdutoLoja
        # As fotos são uma galeria (várias), tratadas na view (upload múltiplo).
        fields = ["nome", "descricao", "composto", "controla_estoque", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].required = True
        self._aplicar_estilo()


class CustoEventoForm(EstiloFormMixin, forms.ModelForm):
    """Custo/despesa de um evento (com anexo de comprovante)."""

    class Meta:
        model = CustoEvento
        fields = ["nome", "descricao", "valor", "comprovante"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "valor": forms.TextInput(
                attrs={"data-moeda": True, "inputmode": "decimal", "placeholder": "0,00"}
            ),
            "comprovante": forms.ClearableFileInput(
                attrs={"accept": "image/*,application/pdf"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].required = True
        self._aplicar_estilo()


class CustoClubeForm(EstiloFormMixin, forms.ModelForm):
    """Custo/despesa geral do clube. A data é a do lançamento (automática) e os
    comprovantes (vários) são tratados na view."""

    class Meta:
        model = CustoClube
        fields = ["nome", "descricao", "valor", "destino"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome"].required = True
        self._aplicar_estilo()


class CaixaClubeForm(EstiloFormMixin, forms.ModelForm):
    """Onde está o dinheiro do clube: saldo na conta. A espécie (caixa físico) é
    calculada na view (resultado − banco)."""

    class Meta:
        model = CaixaClube
        fields = ["saldo_banco"]
        widgets = {
            "saldo_banco": forms.TextInput(
                attrs={"data-moeda": True, "inputmode": "decimal", "placeholder": "0,00"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()
