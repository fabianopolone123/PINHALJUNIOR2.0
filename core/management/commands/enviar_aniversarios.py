"""
Disparo automático das mensagens de aniversário (cron diário).

Manda para quem faz aniversário HOJE, pelos canais ligados no template de cada
perfil. Idempotente: o `EnvioAniversario` trava um envio por pessoa/ano/canal, então
rodar duas vezes no mesmo dia não duplica nada — e rodar depois de um envio manual
também não.

Como o resto do sistema, pausa **10s entre cada pessoa** para não parecer disparo
em massa (a W-API bloqueia número que dispara em rajada).

Uso no cron (ex.: todo dia às 09:00):

    0 9 * * * cd /var/www/pinhaljunior2/current && set -a && . /etc/pinhaljunior2.env \\
      && set +a && /var/www/pinhaljunior2/.venv/bin/python manage.py enviar_aniversarios \\
      >> /var/www/pinhaljunior2/backup/aniversarios.log 2>&1
"""

import time

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Envia as mensagens de aniversário de hoje (WhatsApp e/ou e-mail)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Só mostra quem receberia, sem enviar nada.",
        )
        parser.add_argument(
            "--pausa", type=int, default=10,
            help="Segundos entre cada pessoa (padrão: 10).",
        )

    def handle(self, *args, **opts):
        # Import tardio: o módulo de views puxa o Django já configurado.
        from core.views import _aniversariantes, _enviar_aniversario

        hoje = timezone.localdate()
        aniversariantes = [p for p in _aniversariantes() if p["faz_hoje"]]

        self.stdout.write(f"[{timezone.now():%Y-%m-%d %H:%M}] aniversariantes de hoje: "
                          f"{len(aniversariantes)}")
        if not aniversariantes:
            return

        if opts["dry_run"]:
            for p in aniversariantes:
                self.stdout.write(
                    f"  (simulação) {p['nome']} — {p['rotulo_perfil']} — {p['idade']} anos"
                )
            return

        enviados = falhas = 0
        for i, p in enumerate(aniversariantes):
            res = _enviar_aniversario(p, ano=hoje.year)
            for canal, (ok, motivo) in res.items():
                if ok:
                    enviados += 1
                    self.stdout.write(f"  OK    {p['nome']} ({canal})")
                else:
                    # "já enviado" não é falha: é a trava funcionando.
                    nivel = "pulado" if motivo == "ja_enviado" else "FALHA "
                    if motivo != "ja_enviado":
                        falhas += 1
                    self.stdout.write(f"  {nivel} {p['nome']} ({canal}): {motivo}")
            if i < len(aniversariantes) - 1 and opts["pausa"] > 0:
                time.sleep(opts["pausa"])

        self.stdout.write(self.style.SUCCESS(
            f"Concluído: {enviados} enviada(s), {falhas} falha(s)."
        ))
