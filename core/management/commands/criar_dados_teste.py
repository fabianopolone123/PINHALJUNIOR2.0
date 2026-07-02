"""
Comando de gerenciamento para popular o banco local com dados fictícios.

Cria (ou atualiza, se já existirem) uma conta de teste com 2 aventureiros
completos: ficha de inscrição, ficha médica, autorização de imagem e fotos
fictícias geradas com Pillow (sem usar pessoas reais nem imagens externas).

Uso:
    python manage.py criar_dados_teste

É seguro rodar mais de uma vez: usa get_or_create/update_or_create e nunca
apaga dados de outros usuários.
"""

import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Aventureiro, AutorizacaoImagem, FichaMedica

# Conta de teste
USERNAME_TESTE = "teste_responsavel"
SENHA_TESTE = "123456"
EMAIL_TESTE = "teste.responsavel@example.com"

# Pasta (relativa ao MEDIA_ROOT) onde as fotos fictícias ficam salvas.
PASTA_FOTOS_TESTE = os.path.join("aventureiros", "fotos_teste")


# --- Dados fictícios compartilhados dos responsáveis (mesma família) ---
DADOS_PAI = {
    "pai_nome": "Roberto Carlos Santos",
    "pai_email": "roberto.santos@example.com",
    "pai_cpf": "111.222.333-44",
    "pai_celular": "(16) 99999-1111",
    "pai_whatsapp": "(16) 99999-1111",
}
DADOS_MAE = {
    "mae_nome": "Mariana Oliveira Santos",
    "mae_email": "mariana.santos@example.com",
    "mae_cpf": "222.333.444-55",
    "mae_celular": "(16) 98888-2222",
    "mae_whatsapp": "(16) 98888-2222",
}
# Responsável legal = mãe.
DADOS_RESP = {
    "resp_nome": "Mariana Oliveira Santos",
    "resp_parentesco": "Mãe",
    "resp_cpf": "222.333.444-55",
    "resp_email": "mariana.santos@example.com",
    "resp_whatsapp": "(16) 98888-2222",
}


def _dados_aventureiro_1():
    dados = {
        "nome_completo": "Lucas Henrique Oliveira Santos",
        "sexo": "M",
        "data_nascimento": "2018-04-15",
        "colegio": "Escola Municipal Jardim Pinhal",
        "serie": "2º ano",
        "ano": "2026",
        "bolsa_familia": False,
        "classe_abelhinhas": True,
        "classe_luminares": False,
        "classe_edificadores": False,
        "classe_maos_ajudadoras": False,
        "endereco": "Rua das Acácias, 120",
        "bairro": "Jardim Pinhal",
        "cidade": "São Carlos",
        "cep": "13560-000",
        "estado": "SP",
        "certidao_nascimento": "123456 01 55 2020 1 00012 123 0001234 12",
        "religiao": "Adventista",
        "rg": "55.123.456-7",
        "orgao_expedidor": "SSP-SP",
        "cpf": "123.456.789-10",
        "tamanho_camiseta": "INF_M",
        "cidade_inscricao": "São Carlos",
        "declaracao_medica_aceita": True,
        "autorizacao_imagem_aceita": True,
    }
    dados.update(DADOS_PAI)
    dados.update(DADOS_MAE)
    dados.update(DADOS_RESP)
    return dados


def _dados_aventureiro_2():
    dados = {
        "nome_completo": "Ana Clara Oliveira Santos",
        "sexo": "F",
        "data_nascimento": "2016-09-22",
        "colegio": "Escola Municipal Jardim Pinhal",
        "serie": "4º ano",
        "ano": "2026",
        "bolsa_familia": False,
        "classe_abelhinhas": True,
        "classe_luminares": True,
        "classe_edificadores": False,
        "classe_maos_ajudadoras": False,
        "endereco": "Rua das Acácias, 120",
        "bairro": "Jardim Pinhal",
        "cidade": "São Carlos",
        "cep": "13560-000",
        "estado": "SP",
        "certidao_nascimento": "223456 01 55 2020 1 00022 223 0002234 22",
        "religiao": "Adventista",
        "rg": "56.987.654-3",
        "orgao_expedidor": "SSP-SP",
        "cpf": "987.654.321-00",
        "tamanho_camiseta": "INF_G",
        "cidade_inscricao": "São Carlos",
        "declaracao_medica_aceita": True,
        "autorizacao_imagem_aceita": True,
    }
    dados.update(DADOS_PAI)
    dados.update(DADOS_MAE)
    dados.update(DADOS_RESP)
    return dados


def _ficha_medica_1():
    return {
        "possui_plano_saude": True,
        "qual_plano_saude": "Unimed Infantil",
        "cartao_sus": "700000000000001",
        "catapora": True,
        "meningite": False,
        "hepatite": False,
        "dengue": False,
        "pneumonia": False,
        "malaria": False,
        "febre_amarela": False,
        "h1n1": False,
        "colera": False,
        "rubeola": False,
        "sarampo": False,
        "tetano": False,
        "alergia_pele": False,
        "alergia_pele_qual": "",
        "alergia_alimentar": True,
        "alergia_alimentar_qual": "Lactose",
        "alergia_medicamentos": False,
        "alergia_medicamentos_qual": "",
        "cardiaco": False,
        "diabetico": False,
        "renais": False,
        "psicologicos": False,
        "outros_problemas": "Nenhum informado.",
        "problema_recente": False,
        "problema_recente_qual": "",
        "medicamento_recente": False,
        "medicamento_recente_qual": "",
        "ferimento_recente": False,
        "cirurgia": False,
        "internado_5anos": False,
        "tipo_sanguineo": "O+",
    }


def _ficha_medica_2():
    return {
        "possui_plano_saude": True,
        "qual_plano_saude": "Unimed Infantil",
        "cartao_sus": "700000000000002",
        "catapora": True,
        "meningite": False,
        "hepatite": False,
        "dengue": True,
        "pneumonia": False,
        "malaria": False,
        "febre_amarela": False,
        "h1n1": False,
        "colera": False,
        "rubeola": False,
        "sarampo": False,
        "tetano": False,
        "alergia_pele": True,
        "alergia_pele_qual": "Dermatite leve",
        "alergia_alimentar": False,
        "alergia_alimentar_qual": "",
        "alergia_medicamentos": True,
        "alergia_medicamentos_qual": "Dipirona",
        "cardiaco": False,
        "diabetico": False,
        "renais": False,
        "psicologicos": False,
        "outros_problemas": "Evitar medicamentos com dipirona.",
        "problema_recente": True,
        "problema_recente_qual": "Gripe leve há duas semanas",
        "medicamento_recente": True,
        "medicamento_recente_qual": "Xarope infantil",
        "ferimento_recente": False,
        "cirurgia": False,
        "internado_5anos": False,
        "tipo_sanguineo": "A+",
    }


def _autorizacao_imagem(nome_menor):
    """Autorização de imagem: dados do menor + responsável legal (mãe)."""
    return {
        "nome_menor": nome_menor,
        "nacionalidade_menor": "Brasileira",
        "resp_nome": "Mariana Oliveira Santos",
        "resp_nacionalidade": "Brasileira",
        "resp_estado_civil": "Casada",
        "resp_rg": "44.555.666-7",
        "resp_cpf": "222.333.444-55",
        "resp_endereco": "Rua das Acácias",
        "resp_numero": "120",
        "resp_bairro": "Jardim Pinhal",
        "resp_cidade": "São Carlos",
        "resp_estado": "SP",
    }


def _gerar_foto_ficticia(caminho_absoluto, iniciais, cor_fundo):
    """Gera uma imagem 3x4 simples (fundo colorido + iniciais + 'Foto teste').

    Não usa imagens externas nem pessoas reais — apenas desenha com Pillow.
    """
    from PIL import Image, ImageDraw, ImageFont

    largura, altura = 300, 400  # proporção 3x4
    imagem = Image.new("RGB", (largura, altura), cor_fundo)
    desenho = ImageDraw.Draw(imagem)

    def carregar_fonte(tamanho, negrito=False):
        # Tenta fontes comuns (Windows/Linux) e a que acompanha o Pillow;
        # se nenhuma for encontrada, cai na fonte padrão (pequena).
        candidatas = (
            ["arialbd.ttf", "DejaVuSans-Bold.ttf"]
            if negrito
            else ["arial.ttf", "DejaVuSans.ttf"]
        )
        for nome in candidatas:
            try:
                return ImageFont.truetype(nome, tamanho)
            except OSError:
                continue
        try:
            # Fonte que acompanha o Pillow, via caminho absoluto do pacote.
            import PIL
            caminho = os.path.join(
                os.path.dirname(PIL.__file__), "fonts", "DejaVuSans.ttf"
            )
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            return ImageFont.load_default()

    fonte_grande = carregar_fonte(130, negrito=True)
    fonte_pequena = carregar_fonte(26)

    def centralizar(texto, fonte, centro_y, cor):
        caixa = desenho.textbbox((0, 0), texto, font=fonte)
        larg_txt = caixa[2] - caixa[0]
        alt_txt = caixa[3] - caixa[1]
        x = (largura - larg_txt) / 2 - caixa[0]
        y = centro_y - alt_txt / 2 - caixa[1]
        desenho.text((x, y), texto, fill=cor, font=fonte)

    centralizar(iniciais, fonte_grande, altura * 0.42, "white")
    centralizar("Foto teste", fonte_pequena, altura * 0.80, "white")

    os.makedirs(os.path.dirname(caminho_absoluto), exist_ok=True)
    imagem.save(caminho_absoluto, "PNG")


class Command(BaseCommand):
    help = (
        "Cria uma conta de teste (teste_responsavel) com 2 aventureiros "
        "fictícios completos, incluindo ficha médica, autorização de imagem "
        "e fotos fictícias. Pode ser executado várias vezes sem duplicar dados."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Conta de teste (reutiliza se já existir).
        usuario, usuario_criado = User.objects.get_or_create(
            username=USERNAME_TESTE,
            defaults={"email": EMAIL_TESTE},
        )
        usuario.email = EMAIL_TESTE
        usuario.set_password(SENHA_TESTE)
        usuario.save()

        # Só consideramos "novo" se nada de teste existia antes.
        havia_aventureiros = usuario.aventureiros.exists()

        # 2) Cada aventureiro (chaveado por usuário + CPF, para não duplicar).
        aventureiros_config = [
            (_dados_aventureiro_1(), _ficha_medica_1(), "LH", (37, 99, 150), "lucas_teste.png"),
            (_dados_aventureiro_2(), _ficha_medica_2(), "AC", (47, 143, 78), "ana_teste.png"),
        ]

        nomes_criados = []
        for dados_av, dados_med, iniciais, cor, arquivo_foto in aventureiros_config:
            cpf = dados_av["cpf"]
            defaults = {k: v for k, v in dados_av.items() if k != "cpf"}

            aventureiro, _ = Aventureiro.objects.update_or_create(
                usuario=usuario, cpf=cpf, defaults=defaults,
            )

            # Foto fictícia (gerada/atualizada a cada execução).
            caminho_rel = os.path.join(PASTA_FOTOS_TESTE, arquivo_foto)
            caminho_abs = os.path.join(settings.MEDIA_ROOT, caminho_rel)
            _gerar_foto_ficticia(caminho_abs, iniciais, cor)
            # Guarda o caminho relativo ao MEDIA_ROOT (barra normal em qualquer SO).
            aventureiro.foto.name = caminho_rel.replace(os.sep, "/")
            aventureiro.save(update_fields=["foto"])

            # Ficha médica (uma por aventureiro).
            FichaMedica.objects.update_or_create(
                aventureiro=aventureiro, defaults=dados_med,
            )

            # Autorização de imagem (uma por aventureiro).
            AutorizacaoImagem.objects.update_or_create(
                aventureiro=aventureiro,
                defaults=_autorizacao_imagem(dados_av["nome_completo"]),
            )

            nomes_criados.append(aventureiro.nome_completo)

        # 3) Mensagem de saída.
        ja_existiam = havia_aventureiros and not usuario_criado
        if ja_existiam:
            self.stdout.write(
                self.style.SUCCESS(
                    "Dados de teste já existiam e foram atualizados com sucesso."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Dados de teste criados com sucesso."))

        self.stdout.write(f"Usuário: {USERNAME_TESTE}")
        self.stdout.write(f"Senha: {SENHA_TESTE}")
        self.stdout.write("Aventureiros criados:")
        for nome in nomes_criados:
            self.stdout.write(f"- {nome}")
