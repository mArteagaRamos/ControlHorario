from django.apps import AppConfig
import os

class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from django.contrib.sessions.models import Session
                Session.objects.all().delete()
            except Exception:
                pass