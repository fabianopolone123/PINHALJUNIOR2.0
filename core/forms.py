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

from .models import Aventureiro, AutorizacaoImagem, FichaMedica


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


class AutorizacaoImagemForm(EstiloFormMixin, forms.ModelForm):
    """Termo de autorização de uso de imagem (etapa 6)."""

    class Meta:
        model = AutorizacaoImagem
        exclude = ["aventureiro"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()
