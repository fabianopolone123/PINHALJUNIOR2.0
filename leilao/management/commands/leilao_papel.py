"""Cria contas da equipe do leilão e distribui os papéis.

    python manage.py leilao_papel --listar
    python manage.py leilao_papel maria --dar preparacao --dar caixa
    python manage.py leilao_papel joao --dar locutor --senha
    python manage.py leilao_papel maria --tirar caixa

Papéis: **preparacao** (itens e configurações), **locutor** (o pregão),
**caixa** (pagamentos e entrega) e **diretor** (enxerga tudo e distribui).

Papéis **acumulam**: no evento pequeno o mesmo voluntário faz duas coisas, e
fazer a pessoa trocar de login no meio do pregão seria pior do que não ter
separação nenhuma.
"""

import secrets
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from leilao.papeis import AREAS, DIRETOR, papeis_do

VALIDOS = sorted(list(AREAS) + [DIRETOR])


class Command(BaseCommand):
    help = "Cria contas da equipe do leilão e dá/tira papéis."

    def add_arguments(self, parser):
        parser.add_argument("usuario", nargs="?", help="Nome de usuário da pessoa.")
        parser.add_argument("--dar", action="append", default=[], metavar="PAPEL",
                            help=f"Papel a conceder. Um de: {', '.join(VALIDOS)}")
        parser.add_argument("--tirar", action="append", default=[], metavar="PAPEL",
                            help="Papel a remover.")
        parser.add_argument("--senha", action="store_true",
                            help="Gera uma senha nova e mostra na tela (uma vez).")
        parser.add_argument("--listar", action="store_true",
                            help="Mostra a equipe e os papéis de cada um.")

    def handle(self, *args, **o):
        User = get_user_model()

        if o["listar"]:
            equipe = User.objects.filter(is_staff=True).order_by("username")
            if not equipe:
                self.stdout.write("Ninguém na equipe ainda.")
                return
            self.stdout.write(self.style.SUCCESS("Equipe do leilão:"))
            for u in equipe:
                meus = papeis_do(u)
                rotulos = ", ".join(sorted(meus)) if meus else "— sem papel —"
                extra = " (superusuário)" if u.is_superuser else ""
                self.stdout.write(f"  {u.username:<20} {rotulos}{extra}")
            return

        if not o["usuario"]:
            raise CommandError("Informe o usuário, ou use --listar.")

        for papel in o["dar"] + o["tirar"]:
            if papel not in VALIDOS:
                raise CommandError(f"Papel inválido: {papel}. Use um de: {', '.join(VALIDOS)}")

        user, novo = User.objects.get_or_create(username=o["usuario"])
        # `is_staff` é o que separa a equipe de quem só dá lance — sem ele, os
        # papéis não valem nada (ver `papeis.papeis_do`).
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        if novo or o["senha"]:
            alfabeto = string.ascii_letters + string.digits
            senha = "".join(secrets.choice(alfabeto) for _ in range(14))
            user.set_password(senha)
            user.save()
            self.stdout.write(self.style.WARNING(
                f"  senha de {user.username}: {senha}  (anote — não aparece de novo)"
            ))
        elif novo:
            self.stdout.write(self.style.WARNING("  conta sem senha: use --senha"))

        for papel in o["dar"]:
            grupo, _ = Group.objects.get_or_create(name=papel)
            user.groups.add(grupo)
            self.stdout.write(f"  + {papel}")

        for papel in o["tirar"]:
            grupo = Group.objects.filter(name=papel).first()
            if grupo:
                user.groups.remove(grupo)
            self.stdout.write(f"  - {papel}")

        meus = papeis_do(user)
        self.stdout.write(self.style.SUCCESS(
            f"{user.username}: {', '.join(sorted(meus)) if meus else '— sem papel —'}"
        ))
        if not meus:
            self.stdout.write(self.style.WARNING(
                "  Sem papel, a pessoa entra e não vê tela nenhuma. Use --dar."
            ))
