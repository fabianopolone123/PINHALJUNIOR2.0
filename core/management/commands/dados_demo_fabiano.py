"""
Popula o usuário Diretor (Fabiano) com TODOS os perfis + dados FICTÍCIOS de
responsável, para testar o seletor de perfil sem outra conta.

O que faz (idempotente):
1. Garante os 5 perfis (grupos) e adiciona TODOS ao usuário `Fabiano`.
2. Cria 2 aventureiros FICTÍCIOS (`demo=True`) vinculados ao Fabiano (com foto,
   ficha médica e autorização), tendo o próprio Fabiano como responsável legal.
3. Gera mensalidades do ano (algumas pagas, o restante em aberto/atrasado) para a
   tela de Mensalidades do responsável ter conteúdo e o "pagar" funcionar.
4. Cria 2 eventos FICTÍCIOS (`demo=True`) com presença marcada, para o relatório
   de Presença do responsável mostrar frequência/faltas.

IMPORTANTE: por serem `demo=True`, esses aventureiros e eventos NÃO entram em
NENHUMA contagem/relatório do clube (Usuários, Mensalidades do Diretor, Presença
do Diretor, Financeiro). São só do perfil de responsável do Fabiano.

Uso:
    python manage.py dados_demo_fabiano
"""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.management.commands.criar_dados_teste import _gerar_foto_ficticia
from core.models import (
    Aventureiro,
    AutorizacaoImagem,
    Evento,
    FichaMedica,
    Mensalidade,
    PresencaEvento,
)
from core.menus import ORDEM_PERFIS

DIRETOR_USERNAME = "Fabiano"

# Responsável legal (o próprio Fabiano), compartilhado pelos 2 aventureiros demo.
DADOS_RESP = {
    "resp_nome": "Fabiano Polone",
    "resp_parentesco": "Pai",
    "resp_cpf": "000.111.222-33",
    "resp_email": "fabiano.demo@example.com",
    "resp_whatsapp": "(16) 99000-0001",
    "pai_nome": "Fabiano Polone",
    "pai_whatsapp": "(16) 99000-0001",
}

AVENTUREIROS_DEMO = [
    {
        "cpf": "DEMO-001",
        "nome_completo": "Miguel Polone (fictício)",
        "sexo": "M", "data_nascimento": "2017-03-12",
        "colegio": "Escola Demo", "serie": "3º ano", "ano": "2026",
        "cidade": "São Carlos", "estado": "SP",
        "tamanho_camiseta": "INF_M",
        "classe_abelhinhas": True,
        "iniciais": "MP", "cor": (37, 99, 150), "foto": "demo_miguel.png",
        "presencas": [True, True],   # esteve nos 2 eventos
    },
    {
        "cpf": "DEMO-002",
        "nome_completo": "Sofia Polone (fictícia)",
        "sexo": "F", "data_nascimento": "2019-08-25",
        "colegio": "Escola Demo", "serie": "1º ano", "ano": "2026",
        "cidade": "São Carlos", "estado": "SP",
        "tamanho_camiseta": "INF_P",
        "classe_abelhinhas": True,
        "iniciais": "SP", "cor": (47, 143, 78), "foto": "demo_sofia.png",
        "presencas": [True, False],  # faltou no 2º
    },
]

EVENTOS_DEMO = [
    {"nome": "Reunião de demonstração (fictício)", "data": "2026-03-08"},
    {"nome": "Acampamento de demonstração (fictício)", "data": "2026-05-10"},
]


class Command(BaseCommand):
    help = (
        "Dá todos os perfis ao usuário Fabiano e cria dados FICTÍCIOS de "
        "responsável (2 aventureiros demo + mensalidades + presença) que não "
        "entram nas contagens do clube."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        fabiano = User.objects.filter(username=DIRETOR_USERNAME).first()
        if fabiano is None:
            self.stderr.write(
                f"Usuário '{DIRETOR_USERNAME}' não existe. Rode "
                f"'python manage.py configurar_perfis' primeiro."
            )
            return

        # 1) Todos os perfis (grupos) no Fabiano.
        for nome in ORDEM_PERFIS:
            grupo, _ = Group.objects.get_or_create(name=nome)
            fabiano.groups.add(grupo)
        self.stdout.write(f"Perfis dados a {DIRETOR_USERNAME}: " + ", ".join(ORDEM_PERFIS))

        # 2) Eventos fictícios (demo) — criados uma vez.
        eventos = []
        for ev in EVENTOS_DEMO:
            evento, _ = Evento.objects.get_or_create(
                nome=ev["nome"], demo=True,
                defaults={"tipo": "simples", "data": ev["data"]},
            )
            eventos.append(evento)

        # 3) Aventureiros fictícios + ficha + autorização + foto + mensalidades + presença.
        ano = timezone.localdate().year
        mes_atual = timezone.localdate().month
        from django.conf import settings
        import os
        pasta = os.path.join("aventureiros", "fotos_teste")

        for cfg in AVENTUREIROS_DEMO:
            defaults = {
                "usuario": fabiano, "demo": True, "ativo": True,
                **{k: cfg[k] for k in (
                    "nome_completo", "sexo", "data_nascimento", "colegio", "serie",
                    "ano", "cidade", "estado", "tamanho_camiseta", "classe_abelhinhas")},
                **DADOS_RESP,
            }
            av, _ = Aventureiro.objects.update_or_create(
                usuario=fabiano, cpf=cfg["cpf"], defaults=defaults,
            )

            # Foto fictícia (avatar Pillow).
            caminho_rel = f"{pasta}/{cfg['foto']}".replace(os.sep, "/")
            caminho_abs = os.path.join(settings.MEDIA_ROOT, pasta, cfg["foto"])
            if not (av.foto and av.foto.name == caminho_rel and os.path.exists(caminho_abs)):
                _gerar_foto_ficticia(caminho_abs, cfg["iniciais"], cfg["cor"])
                av.foto.name = caminho_rel
                av.save(update_fields=["foto"])

            FichaMedica.objects.get_or_create(
                aventureiro=av, defaults={"tipo_sanguineo": "O+"}
            )
            AutorizacaoImagem.objects.get_or_create(
                aventureiro=av,
                defaults={"nome_menor": av.nome_completo, "resp_nome": DADOS_RESP["resp_nome"]},
            )

            # Mensalidades do ano: Jan = inscrição; até o mês atual em aberto,
            # menos os 2 primeiros meses, que ficam PAGOS (mostra "pago no ano").
            self._gerar_mensalidades_demo(av, ano, mes_atual)

            # Presença nos eventos demo, conforme o padrão do aventureiro.
            for evento, esteve in zip(eventos, cfg["presencas"]):
                if esteve:
                    PresencaEvento.objects.get_or_create(evento=evento, aventureiro=av)
                else:
                    evento.presencas.filter(aventureiro=av).delete()

        self.stdout.write(self.style.SUCCESS(
            "Dados fictícios do responsável (Fabiano) prontos. "
            "Entre como Fabiano e use o seletor 'Ver como' no menu."
        ))

    def _gerar_mensalidades_demo(self, av, ano, mes_atual):
        """Cria as cobranças de Jan..mês atual (Jan = inscrição). Os 2 primeiros
        meses ficam PAGOS; o resto em aberto (mês atual + atrasados)."""
        for mes in range(1, mes_atual + 1):
            tipo = "inscricao" if mes == 1 else "mensalidade"
            m, _ = Mensalidade.objects.get_or_create(
                aventureiro=av, ano=ano, mes=mes,
                defaults={"tipo": tipo, "valor": Decimal("30.00"), "status": "aberta"},
            )
            if mes <= 2 and m.status != "paga":
                m.status = "paga"
                m.forma_pagamento = "dinheiro"
                m.valor_pago = m.valor
                m.pago_em = timezone.now()
                m.save(update_fields=["status", "forma_pagamento", "valor_pago", "pago_em"])
