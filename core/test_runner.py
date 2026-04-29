from django.test.runner import DiscoverRunner
from django.apps import apps

class ManagedModelTestRunner(DiscoverRunner):
    """
    Fuerza a todos los modelos a comportarse como managed=True 
    únicamente durante la ejecución de los tests.
    """
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        
        # Recorremos todos los modelos del proyecto y les quitamos la protección temporalmente
        for model in apps.get_models():
            model._meta.managed = True