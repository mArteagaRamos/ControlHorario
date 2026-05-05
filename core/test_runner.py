# Custom test runner that temporarily sets managed=True on all models that have managed=False. 
# This allows Django to create those tables in the test database without affecting production behavior.
#
# Usage in settings.py:
#   TEST_RUNNER = 'core.test_runner.ManagedModelTestRunner'

from django.test.runner import DiscoverRunner
from django.apps import apps


class ManagedModelTestRunner(DiscoverRunner):
    """
    Test runner that forces managed=True on unmanaged models so Django
    creates their tables in the test DB.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        for model in apps.get_models():
            model._meta.managed = True