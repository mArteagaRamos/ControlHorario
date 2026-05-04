# corrections/tests/fixtures.py
import uuid
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from users.models import Users, Companies, UserCompany
from timetracking.models import TimeEntries # <--- Nombre real: TimeEntries

class CorrectionsTestBase(TestCase):
    def setUp(self):
        # 1. Crear Empresa
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name='EMPRESA TEST',
            legal_name='TEST COMPANY S.L.',
            tax_id='B12345678'
        )

        # 2. Crear Usuario Empleado
        self.user = Users.objects.create_user(
            username='EMPLEADO_TEST',
            email='testuser@example.com',
            password='testpass123',
            dni='12345678A',
            surname='APELLIDO_TEST',
            is_admin=False
        )

        # 3. Crear Usuario Manager
        self.manager = Users.objects.create_user(
            username='MANAGER_TEST',
            email='manager@example.com',
            password='managerpass123',
            dni='87654321B',
            surname='MANAGER_APELLIDO',
            is_admin=True
        )

        # 4. Vincular roles
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.user,
            company=self.company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )

        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.manager,
            company=self.company,
            role=UserCompany.RoleChoices.MANAGER
        )

        # 5. Crear el fichaje (TimeEntries)
        # Los edge cases necesitan que clock_in y clock_out existan para calcular diferencias
        start_time = timezone.now() - timedelta(hours=8)
        end_time = timezone.now() - timedelta(hours=1)
        
        self.time_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=self.user,
            company=self.company,
            date=start_time.date(),
            clock_in=start_time,
            clock_out=end_time,
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=int((end_time - start_time).total_seconds())
        )

        from django.test import Client
        self.client = Client()