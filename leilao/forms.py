"""Formulários do leilão.

Segue o padrão do sistema do clube: `ModelForm` sempre que dá, estilo dos
widgets centralizado num mixin (nada de classe CSS espalhada pelo template) e a
validação autoritativa no servidor.
"""

import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

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


def peso_para_decimal(texto):
    """`"1,5"` e `"1.5"` viram `Decimal("1.5")`. Vazio ou lixo devolve `None`.

    Os **dois** separadores valem. Quem cadastra item está no celular, e o
    teclado numérico de boa parte dos aparelhos oferece o ponto, não a vírgula
    do português — recusar "1.5" faria a pessoa brigar com o teclado no meio do
    cadastro.

    Separador de MILHAR não entra na conta, e é por isso que este helper existe
    em vez do `localize=True` do Django: em pt-BR ele lê "1.5" como milhar e
    devolve **15**, transformando um item de 1,5 kg num de 15 kg sem avisar
    ninguém. O clube não leiloa nada de mil quilos; trocar essa hipótese
    impossível por um erro real de peso não vale a pena.
    """
    texto = (texto or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    # `Decimal("nan")` **não** levanta na conversão — levanta depois, na
    # primeira comparação de ordem (`peso <= 0`), e aí já é um 500 na tela de
    # cadastro. `"inf"` converte e compara, mas não é peso de coisa nenhuma.
    # Os dois saem aqui, virando a mesma recusa educada de `"abc"`.
    if not valor.is_finite():
        return None
    return valor


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
            # Sem `segundos_por_lote`, `segundos_extra`, `reiniciar_cronometro`
            # nem `minutos_para_pagar`: não há cronômetro no pregão e não há
            # prazo para pagar (o dinheiro fecha no fim, numa cobrança só).
            # Campo de configuração para recurso que não existe só confunde
            # quem monta o leilão — e este ainda aparecia como "15 min para
            # pagar" na lista, prometendo uma regra revogada.
            "nome", "descricao",
            "boas_vindas_titulo", "boas_vindas_texto",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "boas_vindas_texto": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Uma informação por linha…"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campo com `default` no model continua OBRIGATÓRIO no ModelForm — e a
        # tela de CRIAR leilão nem mostra estes dois (é a tela curta; quem
        # escreve as boas-vindas é a de editar). Sem isto, criar leilão passa a
        # falhar por um campo que não está na tela. Um teste pegou.
        self.fields["boas_vindas_titulo"].required = False
        self.fields["boas_vindas_texto"].required = False
        self._aplicar_estilo()

    def clean_boas_vindas_titulo(self):
        """Vazio cai no padrão — a tela de espera nunca fica sem título."""
        titulo = (self.cleaned_data.get("boas_vindas_titulo") or "").strip()
        return titulo or Leilao._meta.get_field("boas_vindas_titulo").default


class LoteForm(EstiloMixin, forms.ModelForm):
    """Cadastro de item.

    A foto deixa o celular escolher: **tirar na hora ou pegar da galeria**. O
    `accept="image/*"` sozinho é o que dá as duas opções — o `capture`, que
    estava aqui antes, **forçava a câmera** e escondia a galeria, e quem já
    tinha fotografado o item (ou recebeu a foto por WhatsApp) não conseguia
    cadastrá-lo pelo celular. Continua sem biblioteca: é atributo nativo do
    `<input type="file">`.

    **Peso e dimensões são obrigatórios AQUI**, e não no model. No banco eles
    aceitam vazio porque os itens cadastrados antes deles existem e continuam
    válidos; o que não pode mais acontecer é um item **novo** chegar na entrega
    sem medida. Editar item antigo, portanto, pede o preenchimento — é a hora
    natural de completar o que falta.
    """

    # Peso é texto, não `DecimalField`: o campo precisa aceitar a vírgula do
    # teclado português E o ponto do teclado numérico, e nenhum dos dois
    # caminhos prontos do Django faz isso sem ler "1.5" como milhar. Ver
    # `peso_para_decimal`.
    peso_kg = forms.CharField(
        label="Peso (g)",
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "placeholder": "Ex.: 1500"}
        ),
        help_text="Aproximado, em gramas. 1 kg = 1000 g.",
    )

    class Meta:
        model = Lote
        fields = [
            "nome", "descricao", "lance_inicial",
            "peso_kg", "altura_cm", "largura_cm", "profundidade_cm", "foto",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Cesta de café da manhã"}),
            "descricao": forms.TextInput(
                attrs={"placeholder": "Uma linha sobre o item (aparece embaixo da foto)"}
            ),
            # Sem `capture`: ele forçaria a câmera e tiraria a galeria da
            # frente. `accept="image/*"` deixa o celular oferecer os dois
            # caminhos e o computador abrir o seletor de arquivo normal.
            "foto": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    LADOS = ["altura_cm", "largura_cm", "profundidade_cm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descricao"].required = False
        # Campo de valor em R$ usa a máscara pt-BR do projeto, no modo "inline"
        # (o próprio campo é enviado, normalizado pouco antes do submit).
        for nome in ["lance_inicial"]:
            self.fields[nome].widget = forms.TextInput(
                attrs={"data-moeda": "1", "inputmode": "decimal", "placeholder": "0,00"}
            )
        # Centímetro é número inteiro e NÃO leva a máscara de moeda: ela é de
        # valor em R$ (regra do projeto) e leria "40" como R$ 0,40.
        for nome in self.LADOS:
            campo = self.fields[nome]
            campo.required = True
            # `min_value=1` explícito: o `PositiveIntegerField` entrega o campo
            # com `min_value=0`, e é ESSE validador que responde primeiro a um
            # número negativo — a pessoa digitava `-5` e lia "maior ou igual a
            # 0", quando o mínimo de verdade é 1.
            campo.min_value = 1
            campo.max_value = Lote.MAX_LADO_CM
            campo.validators = [
                v for v in campo.validators
                if not isinstance(v, (MinValueValidator, MaxValueValidator))
            ]
            campo.validators += [
                MinValueValidator(1), MaxValueValidator(Lote.MAX_LADO_CM)
            ]
            campo.widget.attrs.update({
                "min": "1", "max": str(Lote.MAX_LADO_CM),
                "inputmode": "numeric", "placeholder": "0",
            })
        # Na edição o campo volta em GRAMAS ("1500"), que é como ele foi
        # digitado — e não o `Decimal` cru do banco ("1.50").
        if self.instance and self.instance.pk:
            self.initial["peso_kg"] = self.instance.peso_gramas
        self._aplicar_estilo()

    def clean_peso_kg(self):
        """Lê GRAMAS e guarda quilos.

        Quem cadastra pensa em grama — pedir "0,35" para uma caneca é convidar
        ao erro de vírgula, e no celular a vírgula é justamente a tecla que o
        teclado numérico de muitos aparelhos não mostra. Em grama o campo é
        **inteiro**: não há separador para errar.

        O banco continua em **quilos** de propósito: os itens já cadastrados
        valem como estão e nenhuma tela que lê `peso_kg` precisou mudar.
        """
        # Vírgula e ponto continuam aceitos: quem está acostumado com o campo
        # antigo pode digitar "1,5" pensando em quilo, e `peso_para_decimal`
        # segue sendo o único lugar que interpreta número escrito à mão.
        gramas = peso_para_decimal(self.cleaned_data.get("peso_kg"))
        if gramas is None:
            raise forms.ValidationError("Informe o peso em gramas (ex.: 1500).")
        if gramas <= 0:
            raise forms.ValidationError("O peso precisa ser maior que zero.")

        maximo_g = Lote.MAX_PESO_KG * 1000
        if gramas > maximo_g:
            raise forms.ValidationError(
                # `int`, e não `normalize()`: este devolve `Decimal("1E+6")`
                # e a mensagem sairia "Peso acima de 1E+6 g".
                "Peso acima de %d g — confira se não sobrou um dígito."
                % int(maximo_g)
            )

        # O campo do banco tem duas casas, então o menor passo representável em
        # quilos é **10 g**. Ninguém carrega item pela diferença de 5 g, mas
        # quem digitar 5 precisa ouvir isso em vez de salvar um peso zerado.
        quilos = (gramas / Decimal(1000)).quantize(Decimal("0.01"))
        if quilos <= 0:
            raise forms.ValidationError("Peso muito pequeno — informe ao menos 10 g.")
        return quilos


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


class UsuarioEquipeForm(EstiloMixin, forms.Form):
    """Cadastro de uma pessoa da equipe: nome e função.

    **O usuário de acesso é opcional.** Em branco, o sistema tira do nome
    (`equipe.usuario_sugerido`) — o diretor cadastra com dois campos, que é o
    que se consegue fazer com o leilão já rolando. Quem quiser escolher o login
    escolhe.
    """

    nome = forms.CharField(
        label="Nome da pessoa", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Ex.: Maria Souza", "autocomplete": "off"}),
    )
    usuario = forms.CharField(
        label="Usuário de acesso", max_length=150, required=False,
        help_text="Deixe em branco para o sistema criar a partir do nome.",
        widget=forms.TextInput(
            attrs={"placeholder": "em branco = automático", "autocapitalize": "none",
                   "autocomplete": "off"}
        ),
    )
    papeis = forms.MultipleChoiceField(
        label="O que ela vai fazer", choices=[], widget=forms.CheckboxSelectMultiple,
        help_text="Pode marcar mais de uma — no evento pequeno a mesma pessoa faz duas coisas.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import tardio: `equipe.py` lê os papéis, e o `forms` é importado pelo
        # `views` antes de tudo estar de pé.
        from .equipe import escolhas_de_papel

        self.fields["papeis"].choices = escolhas_de_papel()
        # `CheckboxSelectMultiple` herda de `Select`, então o mixin o trataria
        # como lista suspensa e daria `campo-select` a CADA caixinha — que é
        # largura total e padding de campo. Resultado: o quadradinho vira uma
        # barra e o rótulo cai para a linha de baixo. Definir antes basta, o
        # mixin usa `setdefault`.
        self.fields["papeis"].widget.attrs["class"] = "campo-check"
        self._aplicar_estilo()

    def clean_nome(self):
        return " ".join((self.cleaned_data.get("nome") or "").split())

    def clean_usuario(self):
        from django.contrib.auth import get_user_model

        from .equipe import limpar_usuario

        bruto = (self.cleaned_data.get("usuario") or "").strip()
        if not bruto:
            return ""
        login = limpar_usuario(bruto)
        if not login:
            raise forms.ValidationError("Use letras e números, sem espaço nem acento.")
        if get_user_model().objects.filter(username__iexact=login).exists():
            raise forms.ValidationError(f"Já existe alguém com o usuário “{login}”.")
        return login


class TrocarSenhaForm(forms.Form):
    """A troca obrigatória do primeiro acesso.

    **Não passa pelos validadores do Django** (`validate_password`), e isso é
    decisão do clube: quem digita aqui é um voluntário, no celular, no meio de
    um evento, numa conta que abre telas de leilão. Exigir oito caracteres com
    número e símbolo ali produz senha anotada em papel — que é pior do que uma
    senha curta que a pessoa lembra.

    A única senha recusada é **a padrão**: aceitá-la faria a troca não trocar
    nada, e a conta seguiria com a senha que a mesa inteira ouviu.
    """

    senha = forms.CharField(
        label="Sua nova senha", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    repetir = forms.CharField(
        label="Repita a senha", strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "campo-input")

    def clean(self):
        from .equipe import SENHA_PADRAO, TAMANHO_MINIMO_SENHA

        dados = super().clean()
        senha = dados.get("senha") or ""
        repetir = dados.get("repetir") or ""

        if len(senha) < TAMANHO_MINIMO_SENHA:
            self.add_error(
                "senha", f"Use pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
            )
        elif senha == SENHA_PADRAO:
            self.add_error(
                "senha",
                "Essa é a senha que todo mundo recebe. Escolha outra, "
                "qualquer uma que você lembre.",
            )
        elif senha != repetir:
            self.add_error("repetir", "As duas senhas não são iguais.")
        return dados
