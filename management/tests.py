import uuid
from datetime import datetime, timedelta, date
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages.storage.fallback import FallbackStorage

# ⚠️ IMPORTANTE: Ajusta los imports según la ubicación real de tus modelos
from users.models import Users, Companies, UserCompany
from timetracking.models import TimeEntries
from corrections.models import CorrectionRequests
from admin.models import CompanySettings


# ═════════════════════════════════════════════════════════════════════════════
# 1. MODEL TESTS (Pruebas del Modelo Users)
# ═════════════════════════════════════════════════════════════════════════════

class UsersModelTest(TestCase):
    def test_normalizacion_guardado_completo(self):
        print("\n[TEST MODEL] Verificando normalización al hacer un save() completo...")
        user = Users.objects.create(
            email="USUARIO@TEST.COM",
            username="   juan perez  ",
            surname="  gomez   ",
            dni="12345678a",
            password="password123"
        )
        
        # El save() debería haber limpiado y normalizado todo
        self.assertEqual(user.email, "usuario@test.com")
        self.assertEqual(user.username, "JUAN PEREZ")
        self.assertEqual(user.surname, "GOMEZ")
        self.assertEqual(user.dni, "12345678A")

    def test_normalizacion_guardado_parcial(self):
        print("\n[TEST MODEL] Verificando normalización con update_fields (save parcial)...")
        user = Users.objects.create(
            email="test@test.com",
            username="TESTER",
            surname="TESTER",
            dni="11111111A",
            password="password123"
        )
        
        # Modificamos directamente sin pasar por el ORM normal para simular datos sucios
        Users.objects.filter(id=user.id).update(username="sucio", dni="22222222b")
        user.refresh_from_db()
        
        # Aplicamos save() solo en username
        user.save(update_fields=['username'])
        user.refresh_from_db()
        
        # El username debe haberse puesto en mayúsculas, pero el DNI debe seguir sucio (minúscula) 
        # porque no estaba en update_fields
        self.assertEqual(user.username, "SUCIO")
        self.assertEqual(user.dni, "22222222b")


# ═════════════════════════════════════════════════════════════════════════════
# 2. ACCESS TESTS (Pruebas de Permisos y Roles)
# ═════════════════════════════════════════════════════════════════════════════

class ManagementAccessTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para Access Tests...")
        self.client = Client()
        self.password = "pass_segura_123"
        
        self.company = Companies.objects.create(id=uuid.uuid4(), name="Tech Corp")
        
        # Usuario Empleado
        self.employee = Users.objects.create_user(
            email="empleado@test.com", username="empleado", dni="111A", password=self.password
        )
        UserCompany.objects.create(user=self.employee, company=self.company, role=UserCompany.RoleChoices.EMPLOYEE)
        
        # Usuario Manager
        self.manager = Users.objects.create_user(
            email="manager@test.com", username="manager", dni="222B", password=self.password
        )
        UserCompany.objects.create(user=self.manager, company=self.company, role=UserCompany.RoleChoices.MANAGER)

    def _setup_session(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    def test_empleado_rechazado(self):
        print("\n[TEST ACCESS] Verificando que un empleado NO puede entrar a manager_logs...")
        self._setup_session(self.employee)
        response = self.client.get(reverse('manager_logs'))
        # Dependiendo de tu middleware, esto devolverá 403 Forbidden o un redirect (302)
        self.assertIn(response.status_code, [403, 302])

    def test_manager_permitido(self):
        print("\n[TEST ACCESS] Verificando que un manager SÍ puede entrar a manager_logs...")
        self._setup_session(self.manager)
        response = self.client.get(reverse('manager_logs'))
        self.assertEqual(response.status_code, 200)


# ═════════════════════════════════════════════════════════════════════════════
# 3. VIEW TESTS (Pruebas Lógicas de las Vistas)
# ═════════════════════════════════════════════════════════════════════════════

class ManagementViewTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para View Tests...")
        self.client = Client()
        self.password = "pass_segura_123"
        
        self.company = Companies.objects.create(id=uuid.uuid4(), name="Tech Corp", tax_id="B12345678")
        CompanySettings.objects.create(company=self.company)
        
        self.manager = Users.objects.create_user(
            email="manager@test.com", username="manager", dni="333C", password=self.password
        )
        self.membership_manager = UserCompany.objects.create(
            user=self.manager, company=self.company, role=UserCompany.RoleChoices.MANAGER
        )
        
        self.employee = Users.objects.create_user(
            email="trabajador@test.com", username="trabajador", dni="444D", password=self.password
        )
        self.membership_employee = UserCompany.objects.create(
            user=self.employee, company=self.company, role=UserCompany.RoleChoices.EMPLOYEE
        )

        self.time_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=self.employee,
            company=self.company,
            date=timezone.now().date(),
            clock_in=timezone.now() - timedelta(hours=8),
            clock_out=timezone.now(),
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=28800
        )

        # Iniciar sesión como manager y establecer variable de sesión
        self.client.force_login(self.manager)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    def test_edit_employee(self):
        print("\n[TEST VIEW] Verificando edición de datos de un empleado...")
        response = self.client.post(reverse('edit_employee'), {
            'user_id': str(self.employee.id),
            'username': 'Nuevo Nombre',
            'surname': 'Nuevo Apellido',
            'role': UserCompany.RoleChoices.MANAGER,
            'status': Users.StatusChoices.ACTIVE
        })
        
        self.assertEqual(response.status_code, 302) # Redirige a 'staff'
        self.employee.refresh_from_db()
        self.membership_employee.refresh_from_db()
        
        self.assertEqual(self.employee.username, 'NUEVO NOMBRE') # Por la normalización del modelo
        self.assertEqual(self.membership_employee.role, UserCompany.RoleChoices.MANAGER)

    def test_delete_employee_soft_delete(self):
        print("\n[TEST VIEW] Verificando soft-delete de un empleado...")
        response = self.client.post(reverse('delete_employee'), {
            'user_id': str(self.employee.id),
            'company_id': str(self.company.id)
        })
        
        self.assertEqual(response.status_code, 302)
        self.membership_employee.refresh_from_db()
        self.employee.refresh_from_db()
        
        # Verificamos que se ha marcado con fecha de borrado
        self.assertIsNotNone(self.membership_employee.deleted_at)
        # Como era su única empresa activa, el estado del usuario debe cambiar a suspendido
        self.assertEqual(self.employee.status, 'suspended')
        self.assertIsNotNone(self.employee.deleted_at)

    def test_editar_registro_manual(self):
        print("\n[TEST VIEW] Verificando edición manual de fichaje (anula anterior y crea nuevo)...")
        # Preparamos las nuevas horas
        new_in = timezone.now() - timedelta(hours=5)
        new_out = timezone.now()
        
        response = self.client.post(reverse('editar_registro'), {
            'registro_id': str(self.time_entry.id),
            'clock_in': new_in.strftime('%Y-%m-%dT%H:%M'),
            'clock_out': new_out.strftime('%Y-%m-%dT%H:%M')
        })
        
        self.assertEqual(response.status_code, 302)
        
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
        
        # Comprobamos que existe un nuevo registro confirmado para ese empleado
        nuevo_registro = TimeEntries.objects.filter(
            user=self.employee, 
            status=TimeEntries.EntryStatus.CONFIRMED,
            notes__contains="Editado manualmente"
        ).first()
        
        self.assertIsNotNone(nuevo_registro)

    def test_anular_registro(self):
        print("\n[TEST VIEW] Verificando anulación directa de un fichaje...")
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })
        
        self.assertEqual(response.status_code, 302)
        self.time_entry.refresh_from_db()
        
        self.assertEqual(self.time_entry.status, 'voided')
        self.assertEqual(self.time_entry.total_seconds, 0)
        self.assertIsNotNone(self.time_entry.deleted_at)

    def test_exportar_staff_csv(self):
        print("\n[TEST VIEW] Verificando exportación de lista de empleados a CSV...")
        response = self.client.post(reverse('exportar_staff'), {
            'employee_id': [str(self.membership_employee.id)]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="reporte_empleados_', response['Content-Disposition'])
        
        # Verificamos que el contenido tiene al empleado
        content = response.content.decode('utf-8')
        self.assertIn(self.employee.email.lower(), content)