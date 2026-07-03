"""
Cria os perfis de acesso do sistema e o usuário diretor inicial.

Perfis (grupos nativos do Django, para depois receberem permissões):
    Diretor, Responsável, Professor, Tesoureiro, Secretário

Usuário diretor inicial:
    username: Fabiano   |   senha: 1234   |   grupo: Diretor

ATENÇÃO: a senha "1234" é apenas para desenvolvimento — trocar em produção.

Uso:
    python manage.py configurar_perfis

É seguro rodar mais de uma vez (get_or_create nos grupos e no usuário; a senha
do diretor é (re)definida a cada execução). Não apaga nada.
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

# Nome dos perfis de acesso (grupos).
PERFIS = ["Diretor", "Responsável", "Professor", "Tesoureiro", "Secretário"]

# Usuário diretor inicial.
DIRETOR_USERNAME = "Fabiano"
DIRETOR_SENHA = "1234"  # dev — trocar em produção
DIRETOR_PERFIL = "Diretor"


class Command(BaseCommand):
    help = (
        "Cria os 5 perfis de acesso (Diretor, Responsável, Professor, "
        "Tesoureiro, Secretário) e o usuário diretor inicial (Fabiano)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        # 1) Perfis de acesso (grupos).
        grupos = {}
        criados = []
        for nome in PERFIS:
            grupo, novo = Group.objects.get_or_create(name=nome)
            grupos[nome] = grupo
            if novo:
                criados.append(nome)

        # 2) Usuário diretor inicial.
        usuario, usuario_novo = User.objects.get_or_create(username=DIRETOR_USERNAME)
        usuario.set_password(DIRETOR_SENHA)
        usuario.is_active = True
        usuario.save()
        usuario.groups.add(grupos[DIRETOR_PERFIL])

        # 3) Saída.
        self.stdout.write(self.style.SUCCESS("Perfis de acesso configurados."))
        self.stdout.write("Perfis: " + ", ".join(PERFIS))
        if criados:
            self.stdout.write("Perfis criados agora: " + ", ".join(criados))
        else:
            self.stdout.write("Perfis já existiam (nenhum novo criado).")
        estado = "criado" if usuario_novo else "atualizado"
        self.stdout.write(
            f"Usuário diretor '{DIRETOR_USERNAME}' {estado} e vinculado ao perfil {DIRETOR_PERFIL}."
        )
