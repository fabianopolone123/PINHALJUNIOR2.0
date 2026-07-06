from django.contrib.auth.models import Group, User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from .models import WhatsappConfig
from .views import whatsapp_config_view


class WhatsappConfigTests(TestCase):
    def setUp(self):
        grupo = Group.objects.create(name="Diretor")
        self.user = User.objects.create_user(username="diretor", password="123456")
        self.user.groups.add(grupo)
        self.factory = RequestFactory()

    def test_configuracao_persiste_quando_campos_sensiveis_vem_vazios(self):
        config = WhatsappConfig.get_solo()
        config.instance_id = "INSTANCIA-SALVA"
        config.token = "TOKEN-SALVO"
        config.base_url = "https://api.w-api.app/v1"
        config.save()

        request = self.factory.post(
            "/whatsapp/config/",
            {
                "instance_id": "",
                "token": "",
                "base_url": "https://api.w-api.app/v1",
            },
        )
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)

        response = whatsapp_config_view(request)

        self.assertEqual(response.status_code, 302)
        config.refresh_from_db()
        self.assertEqual(config.instance_id, "INSTANCIA-SALVA")
        self.assertEqual(config.token, "TOKEN-SALVO")
