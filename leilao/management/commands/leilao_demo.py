"""Popula o leilão com dados fictícios para testar e ensaiar.

    DJANGO_SETTINGS_MODULE=config.settings_leilao python manage.py leilao_demo

Idempotente (pode rodar de novo). **Só dados fictícios** — nada de pessoa real,
nada de foto de criança (regra do projeto). As fotos dos itens são desenhadas
com Pillow na hora, como já se faz nos dados de teste do clube.
"""

from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from leilao.models import Leilao, Lote, Participante

# Nome, descrição, lance inicial, cor da foto fictícia, peso (kg) e as três
# medidas em cm. O peso e o tamanho entram aqui porque o cadastro passou a
# exigi-los: dados de demonstração sem eles mostrariam "sem peso/medidas" em
# todas as telas e dariam a impressão de recurso quebrado.
ITENS = [
    ("Cesta de café da manhã", "Pães, geleias, frios e um bolo caseiro.", "40.00",
     (214, 160, 92), "3.5", 25, 40, 30),
    ("Bolo de cenoura com brigadeiro", "Feito no dia, tamanho família.", "25.00",
     (166, 106, 62), "1.2", 10, 30, 22),
    ("Kit churrasco", "Tábua, faca e garfo em madeira.", "60.00",
     (122, 92, 72), "2.8", 8, 45, 25),
    ("Almoço para duas pessoas", "Vale para o restaurante do clube.", "50.00",
     (92, 138, 108), "0.05", 1, 21, 10),
    ("Camiseta do Pinhal Júnior", "Tamanho à escolha do arrematante.", "30.00",
     (58, 110, 165), "0.25", 4, 30, 25),
    ("Caixa de chocolates", "Sortidos, 500 g.", "35.00",
     (110, 72, 96), "0.6", 7, 24, 18),
]

PESSOAS = [
    ("Ana Paula Demonstração", "5511900000001"),
    ("Bruno Teste da Silva", "5511900000002"),
    ("Carla Exemplo Souza", "5511900000003"),
]


def _foto_ficticia(titulo, cor):
    """Desenha uma imagem de item — sem baixar nada da internet (regra do projeto)."""
    img = Image.new("RGB", (800, 600), cor)
    d = ImageDraw.Draw(img)
    for i in range(0, 800, 40):
        d.line([(i, 0), (i - 200, 600)], fill=(255, 255, 255, 20), width=1)
    d.rectangle([40, 40, 760, 560], outline=(255, 255, 255), width=4)
    d.text((60, 280), titulo[:28], fill=(255, 255, 255))
    d.text((60, 310), "(imagem fictícia de teste)", fill=(235, 235, 235))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Cria um leilão de demonstração com itens e participantes fictícios."

    def add_arguments(self, parser):
        parser.add_argument(
            "--locutor", action="store_true",
            help="Cria também o usuário locutor 'locutor' com senha '1234' (desenvolvimento).",
        )

    def handle(self, *args, **opcoes):
        leilao, criado = Leilao.objects.get_or_create(
            nome="Leilão de demonstração",
            defaults={
                "descricao": "Leilão fictício para testar a tela e ensaiar o pregão.",
                "status": "ao_vivo",
                "incremento_padrao": Decimal("5.00"),
                "minutos_para_pagar": 15,
                "chat_segundos": 120,
            },
        )
        if criado:
            Leilao.objects.filter(status="ao_vivo").exclude(pk=leilao.pk).update(status="encerrado")
        self.stdout.write(self.style.SUCCESS(
            f"{'Criado' if criado else 'Reaproveitado'}: {leilao.nome} ({leilao.get_status_display()})"
        ))

        for i, (nome, descricao, valor, cor, peso, alt, larg, prof) in enumerate(
            ITENS, start=1
        ):
            lote, novo = Lote.objects.get_or_create(
                leilao=leilao, nome=nome,
                defaults={
                    "descricao": descricao,
                    "lance_inicial": Decimal(valor),
                    "ordem": i,
                    "peso_kg": Decimal(peso),
                    "altura_cm": alt,
                    "largura_cm": larg,
                    "profundidade_cm": prof,
                },
            )
            # O comando é idempotente: item já criado numa rodada anterior
            # (antes destes campos existirem) recebe as medidas agora.
            if lote.peso_kg is None:
                lote.peso_kg = Decimal(peso)
                lote.altura_cm, lote.largura_cm, lote.profundidade_cm = alt, larg, prof
                lote.save(update_fields=[
                    "peso_kg", "altura_cm", "largura_cm", "profundidade_cm"
                ])
            if novo or not lote.foto:
                lote.foto.save(
                    f"demo-{lote.pk}.jpg", ContentFile(_foto_ficticia(nome, cor)), save=True
                )
                from leilao.imagens import preparar_foto

                preparar_foto(lote)
            self.stdout.write(f"  {'+' if novo else '='} lote {lote.ordem}: {lote.nome}")

        for nome, whatsapp in PESSOAS:
            p, novo = Participante.objects.get_or_create(
                nome=nome,
                defaults={
                    "whatsapp": whatsapp,
                    "cep": "00000-000",
                    "logradouro": "Rua Fictícia",
                    "numero": "100",
                    "bairro": "Centro",
                    "cidade": "Cidade Exemplo",
                    "estado": "SP",
                },
            )
            self.stdout.write(f"  {'+' if novo else '='} participante: {p.nome}")

        if opcoes["locutor"]:
            User = get_user_model()
            user, novo = User.objects.get_or_create(
                username="locutor", defaults={"is_staff": True, "is_superuser": True}
            )
            user.is_staff = True
            user.set_password("1234")
            user.save()
            self.stdout.write(self.style.WARNING(
                "  locutor / 1234 (senha de DESENVOLVIMENTO — trocar em produção)"
            ))

        self.stdout.write(self.style.SUCCESS("Pronto. Abra /locutor/ para conduzir."))
