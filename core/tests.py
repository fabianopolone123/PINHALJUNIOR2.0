from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import WhatsappConfig


class WhatsappConfigTests(TestCase):
    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.user = User.objects.create_user(username="diretor", password="123456")
        self.user.groups.add(grupo)

    def test_configuracao_persiste_quando_campos_sensiveis_vem_vazios(self):
        config = WhatsappConfig.get_solo()
        config.instance_id = "INSTANCIA-SALVA"
        config.token = "TOKEN-SALVO"
        config.base_url = "https://api.w-api.app/v1"
        config.save()

        self.client.login(username="diretor", password="123456")
        response = self.client.post(
            reverse("core:whatsapp_config"),
            {
                "instance_id": "",
                "token": "",
                "base_url": "https://api.w-api.app/v1",
            },
        )

        self.assertRedirects(response, reverse("core:whatsapp"))
        config.refresh_from_db()
        self.assertEqual(config.instance_id, "INSTANCIA-SALVA")
        self.assertEqual(config.token, "TOKEN-SALVO")
