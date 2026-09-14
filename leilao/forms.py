"""Formulários do leilão.

Segue o padrão do sistema do clube: `ModelForm` sempre que dá, estilo dos
widgets centralizado num mixin (nada de classe CSS espalhada pelo template) e a
validação autoritativa no servidor.
"""

import re

from django import forms

from .models import ConfigLeilao, Leilao, Lote, Participante

# O clube é de SP e o leilão é dele. A UF deixou de ser digitada — está aqui,
# num lugar só, para o dia em que isso mudar.
UF_PADRAO = "SP"


class EstiloMixin:
    """Classes CSS automáticas por tipo de widget (igual ao `core/forms.py`)."""

    def _aplicar_estilo(self):
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "campo-check")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "campo-select")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "campo-input campo-textarea")
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "campo-file")
            else:
                widget.attrs.setdefault("class", "campo-input")


def so_digitos(valor):
    return re.sub(r"\D", "", valor or "")


class EntrarForm(EstiloMixin, forms.ModelForm):
    """Porta de entrada do participante: nome, WhatsApp e endereço.

    Sem senha (ver `sessao.py`). O endereço é pedido aqui por decisão do
    usuário — é o que entrega o item a quem arremata.
    """

    class Meta:
        model = Participante
        fields = [
            "nome", "whatsapp",
            "logradouro", "numero", "complemento", "bairro", "cidade", "estado",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Seu nome completo", "autocomplete": "name"}),
            "whatsapp": forms.TextInput(
                attrs={
                    "placeholder": "(00) 00000-0000",
                    "inputmode": "tel",
                    "autocomplete": "tel",
                }
            ),
            "logradouro": forms.TextInput(attrs={"placeholder": "Rua, avenida…"}),
            "numero": forms.TextInput(attrs={"placeholder": "Nº", "inputmode": "numeric"}),
            "complemento": forms.TextInput(attrs={"placeholder": "Apto, bloco… (opcional)"}),
            "bairro": forms.TextInput(attrs={"placeholder": "Bairro"}),
            "cidade": forms.TextInput(attrs={"placeholder": "Cidade"}),
            # A UF não é digitada: o leilão é do clube, e o clube é de SP. Um
            # campo a menos numa tela que a pessoa preenche com pressa, ao vivo,
            # vale mais do que a chance remota de alguém ser de outro estado.
            # Continua no formulário como campo oculto para o roteiro de entrega
            # não sair sem estado — e para o dia em que valer a pena voltar.
            "estado": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Endereço é obrigatório (menos o complemento): é por ele que o item chega.
        # Sem CEP: rua, número, bairro e cidade entregam o item, e cada campo a
        # menos é uma desistência a menos numa tela preenchida com o leilão já
        # rolando. O campo continua no model, em branco — quem precisar dele um
        # dia não perde o que já foi cadastrado.
        for nome in ["logradouro", "numero", "bairro", "cidade"]:
            self.fields[nome].required = True
        self.fields["complemento"].required = False
        self.fields["estado"].required = False
        self.fields["estado"].initial = UF_PADRAO
        self._aplicar_estilo()

    def clean_whatsapp(self):
        bruto = so_digitos(self.cleaned_data.get("whatsapp"))
        if len(bruto) < 10:
            raise forms.ValidationError("Informe o WhatsApp com DDD.")
        if len(bruto) > 13:
            raise forms.ValidationError("WhatsApp inválido.")
        return bruto

    def clean_nome(self):
        nome = " ".join((self.cleaned_data.get("nome") or "").split())
        if len(nome.split()) < 2:
            raise forms.ValidationError("Digite o nome e o sobrenome.")
        return nome

    def clean_estado(self):
        """Campo oculto: vem vazio se alguém mexer no HTML — cai no padrão."""
        return (self.cleaned_data.get("estado") or "").upper()[:2] or UF_PADRAO


class LeilaoForm(EstiloMixin, forms.ModelForm):
    """Cadastro/configuração de uma noite de leilão."""

    class Meta:
        model = Leilao
        fields = [
            # Sem `segundos_por_lote`, `segundos_extra` nem `reiniciar_cronometro`:
            # não há cronômetro no pregão, e campo de configuração para um
            # recurso que não existe só confunde quem monta o leilão.
            "nome", "descricao", "incremento_padrao",
            "minutos_para_pagar", "chat_segundos",
        ]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aplicar_estilo()


class LoteForm(EstiloMixin, forms.ModelForm):
    """Cadastro de item.

    A foto abre a **câmera do celular** direto (`capture`), sem biblioteca: é
    atributo nativo do `<input type="file">`.
    """

    class Meta:
        model = Lote
        fields = ["nome", "descricao", "lance_inicial", "incremento", "foto"]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Cesta de café da manhã"}),
            "descricao": forms.TextInput(
                attrs={"placeholder": "Uma linha sobre o item (aparece embaixo da foto)"}
            ),
            "foto": forms.ClearableFileInput(
                attrs={"accept": "image/*", "capture": "environment"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["incremento"].required = False
        self.fields["descricao"].required = False
        # Campo de valor em R$ usa a máscara pt-BR do projeto, no modo "inline"
        # (o próprio campo é enviado, normalizado pouco antes do submit).
        for nome in ["lance_inicial", "incremento"]:
            self.fields[nome].widget = forms.TextInput(
                attrs={"data-moeda": "1", "inputmode": "decimal", "placeholder": "0,00"}
            )
        self._aplicar_estilo()


class ConfigLeilaoForm(EstiloMixin, forms.ModelForm):
    """Credenciais do Mercado Pago e configuração do áudio.

    Segredo em branco **não sobrescreve** o guardado (mesma regra do módulo
    WhatsApp do clube): dá para ajustar o resto sem redigitar o token.
    """

    class Meta:
        model = ConfigLeilao
        fields = [
            "modo",
            "access_token_teste", "webhook_secret_teste",
            "access_token_prod", "webhook_secret_prod",
            "site_url",
            "audio_ativo", "audio_caminho", "audio_publicar_usuario",
            "audio_publicar_senha", "audio_externo_url",
        ]

    SEGREDOS = [
        "access_token_teste", "webhook_secret_teste",
        "access_token_prod", "webhook_secret_prod",
        "audio_publicar_senha",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in self.SEGREDOS:
            self.fields[nome].required = False
            self.fields[nome].widget = forms.PasswordInput(
                attrs={"placeholder": "não muda se deixar em branco"}, render_value=False
            )
        self._aplicar_estilo()

    def clean(self):
        dados = super().clean()
        for nome in self.SEGREDOS:
            if not (dados.get(nome) or "").strip():
                dados[nome] = getattr(self.instance, nome, "")
        return dados
