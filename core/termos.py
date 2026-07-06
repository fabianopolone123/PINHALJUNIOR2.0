"""
Textos canônicos dos termos assinados na inscrição do aventureiro.

Fonte única do conteúdo de cada documento: usada tanto para exibir o termo no
cadastro quanto para gravar o "snapshot" (texto preenchido) no momento da
assinatura, para que o Diretor consiga reconstruir depois o termo assinado
fielmente, mesmo que os dados do cadastro mudem.

Cada função recebe o(s) objeto(s) já salvos e devolve o texto pronto (com os
dados reais no lugar dos "[...]").
"""

# Chaves dos documentos (batem com AssinaturaDocumento.DOC_CHOICES).
DOC_INSCRICAO = "inscricao"
DOC_DECLARACAO_MEDICA = "declaracao_medica"
DOC_AUTORIZACAO_IMAGEM = "autorizacao_imagem"

TITULOS = {
    DOC_INSCRICAO: "Ficha de inscrição",
    DOC_DECLARACAO_MEDICA: "Declaração médica",
    DOC_AUTORIZACAO_IMAGEM: "Termo de Autorização de Uso de Imagem",
}


def _ou_traco(valor):
    """Devolve o valor limpo ou um traço, para não deixar buraco no termo."""
    valor = (valor or "").strip()
    return valor if valor else "—"


def texto_inscricao(aventureiro):
    """Termo da ficha de inscrição (declaração de veracidade + concordância)."""
    return (
        "Declaro que todas as informações prestadas nesta ficha de inscrição são "
        "verdadeiras e concordo com a participação do(a) menor {menor} nas "
        "atividades do Clube de Aventureiros Pinhal Júnior, comprometendo-me a "
        "manter os dados atualizados. Na qualidade de responsável legal, assino a "
        "presente inscrição."
    ).format(menor=_ou_traco(aventureiro.nome_completo))


def texto_declaracao_medica(aventureiro):
    """Termo da declaração médica (veracidade das informações de saúde)."""
    return (
        "Atesto serem verdadeiras todas as informações médicas preenchidas e me "
        "responsabilizo por quaisquer acidentes que venham a ocorrer em decorrência "
        "de não informar problema médico ou de qualquer natureza referente ao(à) "
        "menor {menor}."
    ).format(menor=_ou_traco(aventureiro.nome_completo))


def texto_autorizacao_imagem(aventureiro, autorizacao):
    """Termo de autorização de uso de imagem, com os dados do responsável e do
    menor preenchidos (equivale ao texto mostrado na etapa 6 do cadastro)."""
    a = autorizacao
    return (
        "Eu, {resp_nome}, {resp_nac}, {resp_civil}, portador(a) da cédula de "
        "identidade RG nº {resp_rg} e inscrito(a) no CPF sob nº {resp_cpf}, "
        "residente e domiciliado(a) na {resp_end}, nº {resp_num}, bairro "
        "{resp_bairro}, município de {resp_cidade} - {resp_estado}, na qualidade de "
        "responsável legal pelo(a) menor {menor}, {menor_nac}, autorizo o Clube de "
        "Aventureiros Pinhal Júnior a utilizar sua imagem, voz e nome em fotos, "
        "vídeos, materiais impressos, redes sociais, apresentações, divulgações "
        "internas, eventos, relatórios e demais materiais institucionais "
        "relacionados às atividades do clube, sem finalidade comercial e sem "
        "qualquer ônus para ambas as partes.\n\n"
        "A presente autorização é concedida de forma gratuita, abrangendo o uso da "
        "imagem em todo território nacional, por prazo indeterminado, exclusivamente "
        "para fins institucionais, educativos, informativos e de divulgação das "
        "atividades do Clube de Aventureiros Pinhal Júnior."
    ).format(
        resp_nome=_ou_traco(a.resp_nome),
        resp_nac=_ou_traco(a.resp_nacionalidade),
        resp_civil=_ou_traco(a.resp_estado_civil),
        resp_rg=_ou_traco(a.resp_rg),
        resp_cpf=_ou_traco(a.resp_cpf),
        resp_end=_ou_traco(a.resp_endereco),
        resp_num=_ou_traco(a.resp_numero),
        resp_bairro=_ou_traco(a.resp_bairro),
        resp_cidade=_ou_traco(a.resp_cidade),
        resp_estado=_ou_traco(a.resp_estado),
        menor=_ou_traco(a.nome_menor or aventureiro.nome_completo),
        menor_nac=_ou_traco(a.nacionalidade_menor),
    )


def montar_texto(documento, aventureiro, autorizacao=None):
    """Devolve (titulo, texto) do documento pedido, já preenchido."""
    titulo = TITULOS.get(documento, documento)
    if documento == DOC_INSCRICAO:
        return titulo, texto_inscricao(aventureiro)
    if documento == DOC_DECLARACAO_MEDICA:
        return titulo, texto_declaracao_medica(aventureiro)
    if documento == DOC_AUTORIZACAO_IMAGEM:
        autorizacao = autorizacao or getattr(aventureiro, "autorizacao_imagem", None)
        if autorizacao is None:
            return titulo, ""
        return titulo, texto_autorizacao_imagem(aventureiro, autorizacao)
    return titulo, ""
