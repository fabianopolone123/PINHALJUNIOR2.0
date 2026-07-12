"""Envia a mensagem de reengajamento aos contatos inativos do WhatsApp.

Pensado para rodar por cron (ex.: 1x ao dia). Faz o mesmo que o botão "Reengajar
inativos agora" na tela WhatsApp → aba Liberação. Idempotente no período: quem já
foi reengajado dentro da janela de `reengajar_dias` não recebe de novo.

    python manage.py reengajar_inativos
"""

from django.core.management.base import BaseCommand

from core.models import WhatsappConfig
from core.views import _reengajar_inativos


class Command(BaseCommand):
    help = "Envia a mensagem de reengajamento aos contatos inativos (WhatsApp)."

    def handle(self, *args, **options):
        config = WhatsappConfig.get_solo()
        if not config.configurado:
            self.stdout.write("WhatsApp não configurado; nada a fazer.")
            return
        enviados, falhas = _reengajar_inativos(config)
        self.stdout.write(self.style.SUCCESS(f"Reengajados: {enviados}."))
        if falhas:
            self.stdout.write(f"Falhas: {len(falhas)}.")
            for f in falhas:
                self.stdout.write("  - " + f)
