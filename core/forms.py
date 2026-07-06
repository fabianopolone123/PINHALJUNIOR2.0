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
    CampoInscricao,
    CustoClube,
    CustoEvento,
    Evento,
    FaixaEtariaPreco,
    FichaMedica,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Os aceites são validados/mostrados nas etapas 5 e 6, não aqui.
        self.fields["declaracao_medica_aceita"].required = False
        self.fields["autorizacao_imagem_aceita"].required = False
        self._aplicar_estilo()


class FichaMedicaForm(EstiloFormMixin, forms.ModelForm):
    """Dados médicos do aventureiro (etapa 4)."""

    class Meta:
        model = FichaMedica
        exclude = ["aventureiro"]
        widgets = {
            "outros_problemas": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    class Meta:
        model = AutorizacaoImagem
        exclude = ["aventureiro"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
