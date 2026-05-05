import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from users.models import Users, Companies, UserCompany
from timetracking.models import TimeEntries


class ManagementAccessTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 1. TESTS DE ACCESOS (test_acces.py) - ManagementAccessTest")
        print("█"*70)
        
        cls.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Tech Corp",
            tax_id="B12345678"
        )
        
        cls.empleado = Users.objects.create(
            username="empleado", 
            email="empleado@test.com",
            dni="11111111A",
            is_admin=False 
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.empleado,
            company=cls.company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )
        
        cls.manager = Users.objects.create(
            username="jefe_area", 
            email="manager@test.com",
            dni="22222222B",
            is_admin=False 
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.manager,
            company=cls.company,
            role=UserCompany.RoleChoices.MANAGER
        )

        cls.admin = Users.objects.create(
            username="admin_system", 
            email="admin@test.com",
            dni="33333333C",
            is_admin=True 
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.admin,
            company=cls.company,
            role=UserCompany.RoleChoices.MANAGER
        )

        cls.time_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=cls.empleado,
            company=cls.company,
            date=timezone.now().date(),
            clock_in=timezone.now() - timezone.timedelta(hours=8),
            clock_out=timezone.now(),
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=28800
        )

    def setUp(self):
        self.client = Client()

    def _setup_session(self, user, company):
        """Helper para configurar sesión con usuario y empresa seleccionada"""
        self.client.force_login(user)
        session = self.client.session
        session['company_id'] = str(company.id)
        session.save()

    def test_1_acceso_denegado_a_empleado(self):
        print("\n[TEST 1] Inicio: Intentando acceder como empleado a vistas de gestión.")
        self._setup_session(self.empleado, self.company)
        
        print("  -> Acción: Ejecutando GET a manager_logs...")
        response = self.client.get(reverse('manager_logs'))
        
        self.assertIn(response.status_code, [403, 302])
        print(f"  -> Validación: Código HTTP devuelto es {response.status_code} (Acceso denegado).")
        
        print("  -> Acción: Ejecutando GET a staff...")
        response = self.client.get(reverse('staff'))
        
        self.assertIn(response.status_code, [403, 302])
        print(f"  -> Validación: Código HTTP devuelto es {response.status_code} (Acceso denegado).")
        
        print("  -> Acción: Ejecutando POST a editar_registro...")
        response = self.client.post(reverse('editar_registro'), {
            'registro_id': str(self.time_entry.id),
            'clock_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'clock_out': (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
        })
        
        self.assertIn(response.status_code, [403, 302])
        print(f"  -> Validación: Código HTTP devuelto es {response.status_code} (Acceso denegado).")
        
        print("  -> Acción: Ejecutando POST a anular_registro...")
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })
        
        self.assertIn(response.status_code, [403, 302])
        print(f"  -> Validación: Código HTTP devuelto es {response.status_code} (Acceso denegado).")
        
        print("  [OK] Éxito: Empleado bloqueado en todas las operaciones de gestión.")

    def test_2_acceso_permitido_a_manager_y_admin(self):
        print("\n[TEST 2] Inicio: Intentando acceder como manager y admin a vistas de gestión.")
        
        for user in [self.manager, self.admin]:
            self._setup_session(user, self.company)
            print(f"\n  -> Acción: Probando con usuario {user.username}...")
            
            response = self.client.get(reverse('manager_logs'))
            self.assertEqual(response.status_code, 200)
            print(f"  -> Validación: manager_logs - Código HTTP 200 - Acceso concedido.")
            
            response = self.client.get(reverse('staff'))
            self.assertEqual(response.status_code, 200)
            print(f"  -> Validación: staff - Código HTTP 200 - Acceso concedido.")
            
            response = self.client.post(reverse('editar_registro'), {
                'registro_id': str(self.time_entry.id),
                'clock_in': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'clock_out': (timezone.now() + timezone.timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M')
            })
            self.assertIn(response.status_code, [200, 302])
            print(f"  -> Validación: editar_registro - Código HTTP {response.status_code} - Acción permitida.")
        
        print("\n  [OK] Éxito: Manager y Admin tienen permisos completos de gestión.")
