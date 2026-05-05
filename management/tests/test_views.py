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

class ManagementViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "pass_segura_123"
        
        self.company = Companies.objects.create(id=uuid.uuid4(), name="Tech Corp", tax_id="B12345678")
        
        # Le pasamos el timedelta explícitamente para blindar el test de SQLite
        CompanySettings.objects.create(company=self.company, max_tolerance=timedelta(minutes=15))
        
        self.manager = Users.objects.create_user(
            email="manager@test.com", username="manager", dni="333C", password=self.password
        )
        self.membership_manager = UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.manager, company=self.company, role=UserCompany.RoleChoices.MANAGER
        )
        
        self.employee = Users.objects.create_user(
            email="trabajador@test.com", username="trabajador", dni="444D", password=self.password
        )
        self.membership_employee = UserCompany.objects.create(
            id=uuid.uuid4(),
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
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })
        
        self.assertEqual(response.status_code, 302)
        self.time_entry.refresh_from_db()
        
        self.assertEqual(self.time_entry.status, 'voided')
        self.assertEqual(self.time_entry.total_seconds, 0)
        self.assertIsNotNone(self.time_entry.deleted_at)

    def test_exportar_staff_csv(self):
        response = self.client.post(reverse('exportar_staff'), {
            'employee_id': [str(self.membership_employee.id)]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="reporte_empleados_', response['Content-Disposition'])
        
        # Verificamos que el contenido tiene al empleado
        content = response.content.decode('utf-8')
        self.assertIn(self.employee.email.lower(), content)

    def test_anular_registro_concurrencia(self):
        # 1. Simulamos que otro admin ya ha anulado el registro un segundo antes
        self.time_entry.status = 'voided'
        self.time_entry.deleted_at = timezone.now()
        self.time_entry.save()
        
        # 2. El admin actual intenta anular el mismo registro
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })
        
        # 3. Al estar borrado, Django protege el registro y nos devuelve un 404
        self.assertEqual(response.status_code, 404)

    def test_entity_info_post_update(self):
        # Hacemos POST a la vista con los nuevos datos de la empresa y configuración
        response = self.client.post(reverse('manager_entity_info'), { 
            'name': 'Super Tech Corp',
            'legal_name': 'Super Tech Corp SL',
            'tax_id': 'B98765432',
            'work_start': '09:00',
            'work_end': '18:00',
            'max_tolerance': '15',
            'weekend_days': ['5', '6'], # Sábado y Domingo
            'auto_close_hours': '12'
        })
        
        self.assertEqual(response.status_code, 302) # Debería redirigir tras guardar con éxito
        
        # Refrescamos la empresa y settings de la base de datos
        self.company.refresh_from_db()
        settings_obj = CompanySettings.objects.get(company=self.company)
        
        # Comprobamos que los datos se han guardado correctamente
        self.assertEqual(self.company.name, 'Super Tech Corp')
        self.assertEqual(self.company.tax_id, 'B98765432')
        self.assertEqual(str(settings_obj.work_start), '09:00:00')
        self.assertEqual(settings_obj.max_tolerance, timedelta(minutes=15))
        self.assertEqual(settings_obj.weekend_days, [5, 6])