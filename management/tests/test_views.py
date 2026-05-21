import uuid
from datetime import datetime, timedelta, date
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages.storage.fallback import FallbackStorage

# ⚠️ IMPORTANTE: Ajusta los imports según la ubicación real de tus modelos
from users.models import Users, Companies, UserCompany
from timetracking.models import TimeEntries
from requests.models import CorrectionRequests
from admin.models import CompanySettings

class ManagementViewTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        # Encabezado gigante para los tests de vistas
        print("\n\n" + "█" * 70)
        print(" 3. TESTS DE VISTAS (test_views.py) - ManagementViewTest")
        print("█" * 70)
        print("\n[INFO] Validando el comportamiento de las vistas de gestión.")
        print("       (Edición de empleados, registros, exportaciones, etc.)\n")

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
        print("\n[TEST 1] Inicio: Verificando la edición de datos de un empleado.")
        print("  -> Acción: Ejecutando POST a edit_employee con nuevos datos...")
        
        response = self.client.post(reverse('edit_employee'), {
            'user_id': str(self.employee.id),
            'username': 'Nuevo Nombre',
            'surname': 'Nuevo Apellido',
            'role': UserCompany.RoleChoices.MANAGER,
            'status': Users.StatusChoices.ACTIVE
        })
        
        self.assertEqual(response.status_code, 302) # Redirige a 'staff'
        print(f"  -> Validación: Redirección exitosa (HTTP {response.status_code}).")
        
        self.employee.refresh_from_db()
        self.membership_employee.refresh_from_db()
        
        self.assertEqual(self.employee.username, 'NUEVO NOMBRE') # Por la normalización del modelo
        self.assertEqual(self.membership_employee.role, UserCompany.RoleChoices.MANAGER)
        print("  -> Validación: Nombre normalizado a mayúsculas y rol actualizado.")
        print("  [OK] Éxito: Empleado editado correctamente.")

    def test_delete_employee_soft_delete(self):
        print("\n[TEST 2] Inicio: Verificando el borrado lógico (soft delete) de un empleado.")
        print("  -> Acción: Ejecutando POST a delete_employee...")
        
        response = self.client.post(reverse('delete_employee'), {
            'user_id': str(self.employee.id),
            'company_id': str(self.company.id)
        })
        
        self.assertEqual(response.status_code, 302)
        print(f"  -> Validación: Redirección exitosa (HTTP {response.status_code}).")
        
        self.membership_employee.refresh_from_db()
        self.employee.refresh_from_db()
        
        # Verificamos que se ha marcado con fecha de borrado
        self.assertIsNotNone(self.membership_employee.deleted_at)
        # Como era su única empresa activa, el estado del usuario debe cambiar a suspendido
        self.assertEqual(self.employee.status, 'suspended')
        self.assertIsNotNone(self.employee.deleted_at)
        print("  -> Validación: Membresía y usuario marcados con deleted_at y estado suspendido.")
        print("  [OK] Éxito: Empleado borrado lógicamente de forma correcta.")

    def test_editar_registro_manual(self):
        print("\n[TEST 3] Inicio: Verificando la edición manual de un registro de tiempo.")
        
        # Preparamos las nuevas horas
        new_in = timezone.now() - timedelta(hours=5)
        new_out = timezone.now()
        
        print("  -> Acción: Ejecutando POST a editar_registro con nuevo horario...")
        response = self.client.post(reverse('editar_registro'), {
            'registro_id': str(self.time_entry.id),
            'clock_in': new_in.strftime('%Y-%m-%dT%H:%M'),
            'clock_out': new_out.strftime('%Y-%m-%dT%H:%M')
        })
        
        self.assertEqual(response.status_code, 302)
        print(f"  -> Validación: Redirección exitosa (HTTP {response.status_code}).")
        
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
        print("  -> Validación: Registro original marcado como CORRECTED.")
        
        # Comprobamos que existe un nuevo registro confirmado para ese empleado
        nuevo_registro = TimeEntries.objects.filter(
            user=self.employee, 
            status=TimeEntries.EntryStatus.CONFIRMED,
            notes__contains="Editado manualmente"
        ).first()
        
        self.assertIsNotNone(nuevo_registro)
        print("  -> Validación: Nuevo registro CONFIRMED creado exitosamente.")
        print("  [OK] Éxito: Registro editado y auditado correctamente.")

    def test_anular_registro(self):
        print("\n[TEST 4] Inicio: Verificando la anulación de un registro de tiempo.")
        print("  -> Acción: Ejecutando POST a anular_registro...")
        
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })
        
        self.assertEqual(response.status_code, 302)
        print(f"  -> Validación: Redirección exitosa (HTTP {response.status_code}).")
        
        self.time_entry.refresh_from_db()
        
        self.assertEqual(self.time_entry.status, 'voided')
        self.assertEqual(self.time_entry.total_seconds, 0)
        self.assertIsNotNone(self.time_entry.deleted_at)
        print("  -> Validación: Estado cambiado a 'voided' y total_seconds puesto a 0.")
        print("  [OK] Éxito: Registro anulado correctamente.")

    def test_exportar_staff_csv(self):
        print("\n[TEST 5] Inicio: Verificando la exportación de la plantilla a CSV.")
        print("  -> Acción: Ejecutando POST a exportar_staff...")
        
        response = self.client.post(reverse('exportar_staff'), {
            'employee_id': [str(self.membership_employee.id)]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="reporte_empleados_', response['Content-Disposition'])
        print(f"  -> Validación: Respuesta HTTP {response.status_code} con tipo text/csv.")
        
        # Verificamos que el contenido tiene al empleado
        content = response.content.decode('utf-8')
        self.assertIn(self.employee.email.lower(), content)
        print("  -> Validación: El contenido del CSV incluye los datos del empleado.")
        print("  [OK] Éxito: Archivo CSV generado correctamente.")

    def test_anular_registro_concurrencia(self):
        print("\n[TEST 6] Inicio: Verificando protección contra concurrencia al anular registro.")
        print("  -> Acción: Simulando anulación previa por otro administrador...")
        
        # 1. Simulamos que otro admin ya ha anulado el registro un segundo antes
        self.time_entry.status = 'voided'
        self.time_entry.deleted_at = timezone.now()
        self.time_entry.save()
        
        # 2. El admin actual intenta anular el mismo registro
        print("  -> Acción: Intentando anular el mismo registro...")
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })
        
        # 3. Al estar borrado, Django protege el registro y nos devuelve un 404
        self.assertEqual(response.status_code, 404)
        print(f"  -> Validación: Django protege el registro y devuelve HTTP {response.status_code} (No Encontrado).")
        print("  [OK] Éxito: Concurrencia manejada correctamente.")

    def test_entity_info_post_update(self):
        print("\n[TEST 7] Inicio: Verificando la actualización de la información de la empresa.")
        print("  -> Acción: Ejecutando POST a manager_entity_info con nuevos ajustes...")
        
        # Hacemos POST a la vista con los nuevos datos de la empresa y configuración
        response = self.client.post(reverse('manager_entity_info'), { 
            'name': 'Super Tech Corp',
            'legal_name': 'Super Tech Corp SL',
            'tax_id': 'B98765432',
            'work_start': '09:00',
            'work_end': '18:00',
            'max_tolerance': '15',
            'weekend_days': ['6', '0'], # Sábado y Domingo
            'auto_close_hours': '12'
        })
        
        self.assertEqual(response.status_code, 302) # Debería redirigir tras guardar con éxito
        print(f"  -> Validación: Redirección exitosa tras guardar (HTTP {response.status_code}).")
        
        # Refrescamos la empresa y settings de la base de datos
        self.company.refresh_from_db()
        settings_obj = CompanySettings.objects.get(company=self.company)
        
        # Comprobamos que los datos se han guardado correctamente
        self.assertEqual(self.company.name, 'Super Tech Corp')
        self.assertEqual(self.company.tax_id, 'B98765432')
        self.assertEqual(str(settings_obj.work_start), '09:00:00')
        self.assertEqual(settings_obj.max_tolerance, timedelta(minutes=15))
        self.assertEqual(settings_obj.weekend_days, [5, 6])
        print("  -> Validación: Nombre, NIF y horarios actualizados correctamente en la BBDD.")
        print("  [OK] Éxito: Configuración de la empresa guardada perfectamente.")