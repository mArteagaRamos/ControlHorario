import uuid
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from users.models import Users, Companies
from audit.models import AuditLog
from timetracking.models import TimeEntries
from corrections.models import CorrectionRequests

class AdminViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para AdminViewsAuditTest...")
        self.client = Client()
        
        # 1. Creamos el usuario administrador
        # Se asignan permisos para saltar el decorador @admin_only_required
        self.admin_user = Users.objects.create(
            username="super_jefe",
            email="admin@test.com",
            dni="99999999X",
            is_admin=True, 
        )
        
        # 2. Creamos un usuario marcado como eliminado para probar la exportación
        self.deleted_user = Users.objects.create(
            username="usuario_fantasma",
            email="borrado@test.com",
            dni="88888888Y",
            deleted_at=timezone.now()
        )

    def test_auditoria_en_admin_dashboard(self):
        print("\n[TEST] Verificando que el acceso al dashboard genera log de auditoria...")
        self.client.force_login(self.admin_user)
        
        # Realizamos la peticion GET a la vista del panel
        response = self.client.get(reverse('admin_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        
        # Verificamos que se haya creado el log correspondiente en la tabla AuditLog
        log = AuditLog.objects.filter(user=self.admin_user, table_name='user_action').first()
        
        self.assertIsNotNone(log, "Error: No se encontro el registro de auditoria")
        self.assertEqual(log.reason, 'Acceso al panel de administración')
        self.assertEqual(log.after['rol'], 'administrador')
        print("OK: Auditoria registrada correctamente al entrar al dashboard.")

    def test_auditoria_en_exportacion_csv(self):
        print("\n[TEST] Verificando auditoria al exportar registros eliminados...")
        self.client.force_login(self.admin_user)
        
        # Simulamos la exportacion mediante POST
        response = self.client.post(reverse('exportar_deleted_records'), {
            'record_type': 'users'
        })
        
        # Comprobamos que la respuesta es exitosa y devuelve un CSV
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Buscamos el log generado por la accion de exportar
        log = AuditLog.objects.filter(reason__contains='Exportación').first()
        
        self.assertIsNotNone(log, "Error: No se creo el log para la exportacion")
        self.assertEqual(log.after['tipo'], 'Registros Eliminados (USERS)')
        
        # Verificamos que el conteo de registros en el log coincide con los datos (1 usuario eliminado)
        self.assertEqual(log.after['cantidad'], 1) 
        self.assertIn(str(self.deleted_user.id), log.after['ids'])
        print("OK: Exportacion a CSV auditada con exito.")


class CorrectionsViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando BD temporal para CorrectionsViewsAuditTest...")
        self.client = Client()
        
        # 1. Crear empresa de prueba
        self.company = Companies.objects.create(
            id=uuid.uuid4(), 
            name="Tech Corp Audit"
        )
        
        # 2. Crear usuario administrador
        self.admin_user = Users.objects.create(
            id=uuid.uuid4(),
            username="admin_correcciones",
            email="admincorr@test.com",
            dni="77777777C",
            is_admin=True 
        )
        
        # 3. Crear empleado base
        self.employee = Users.objects.create(
            id=uuid.uuid4(),
            username="empleado_base",
            email="empleado@test.com",
            dni="66666666D"
        )
        
        # 4. Crear un fichaje original sobre el que solicitar correcciones
        self.time_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=self.employee,
            company=self.company,
            date=timezone.now().date(),
            clock_in=timezone.now() - timedelta(hours=8),
            clock_out=timezone.now() - timedelta(hours=1),
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=25200
        )
        
        # 5. Crear una incidencia pendiente
        self.incidencia_pendiente = CorrectionRequests.objects.create(
            id=uuid.uuid4(),
            requester=self.employee,
            time_entry=self.time_entry,
            new_clock_in=timezone.now() - timedelta(hours=8),
            new_clock_out=timezone.now(),
            reason="Se me olvido fichar a la salida",
            status='pending'
        )
        
        # 6. Crear una incidencia previamente rechazada
        self.incidencia_rechazada = CorrectionRequests.objects.create(
            id=uuid.uuid4(),
            requester=self.employee,
            time_entry=self.time_entry,
            new_clock_in=timezone.now() - timedelta(hours=9),
            new_clock_out=timezone.now(),
            reason="Error al iniciar turno",
            status='rejected'
        )

    def test_auditoria_al_resolver_incidencia(self):
        print("\n[TEST] Verificando auditoria al resolver (aceptar) una incidencia...")
        self.client.force_login(self.admin_user)
        
        response = self.client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(self.incidencia_pendiente.id),
            'accion': 'aceptar',
            'nota_resolucion': 'Comprobado con el manager local.'
        })
        
        # Verificamos la redireccion esperada
        self.assertEqual(response.status_code, 302)
        
        # Comprobamos que el AuditLog fue generado
        log = AuditLog.objects.filter(
            table_name='timetracking_correctionrequest',
            record_id=str(self.incidencia_pendiente.id),
            action_type='update'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se creo el log tras resolver la incidencia.")
        self.assertEqual(log.reason, 'Incidencia aceptarda por manager')
        self.assertEqual(log.after['status'], 'approved')
        self.assertEqual(log.after['correction_note'], 'Comprobado con el manager local.')
        print("OK: Auditoria generada correctamente al aceptar incidencia.")

    def test_auditoria_al_exportar_rechazadas(self):
        print("\n[TEST] Verificando auditoria al exportar incidencias rechazadas a CSV...")
        self.client.force_login(self.admin_user)
        
        response = self.client.post(reverse('exportar_logs_rechazadas'), {
            'incidencia_id': [str(self.incidencia_rechazada.id)]
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        
        # Comprobamos el AuditLog
        log = AuditLog.objects.filter(
            table_name='user_action',
            action_type=AuditLog.AuditAction.CREATE,
            reason__contains='Exportación de 1 incidencias rechazadas'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se registro la auditoria al exportar a CSV.")
        self.assertEqual(log.after['tipo'], 'Incidencias Rechazadas')
        self.assertEqual(log.after['cantidad'], 1)
        self.assertIn(str(self.incidencia_rechazada.id), log.after['ids'])
        print("OK: Auditoria de exportacion a CSV funciona correctamente.")

    def test_auditoria_al_editar_incidencia_rechazada(self):
        print("\n[TEST] Verificando auditoria al editar una incidencia rechazada...")
        self.client.force_login(self.admin_user)
        
        # CORRECCIÓN: Usar strftime para generar un formato amigable para el formulario
        nuevo_inicio = (timezone.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')
        nuevo_fin = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        response = self.client.post(reverse('editar_incidencia_rechazada'), {
            'incidencia_id': str(self.incidencia_rechazada.id),
            'new_clock_in': nuevo_inicio,
            'new_clock_out': nuevo_fin,
            'reason': 'Corregido tras revision con RRHH'
        })
        
        self.assertEqual(response.status_code, 302)
        
        log = AuditLog.objects.filter(
            table_name='timetracking_correctionrequest',
            record_id=str(self.incidencia_rechazada.id),
            reason='Edición de incidencia rechazada para volver a revisión'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se audito la edicion de la incidencia rechazada.")
        self.assertEqual(log.after['status'], 'pending')
        self.assertEqual(log.after['reason'], 'Corregido tras revision con RRHH')
        print("OK: Edicion de incidencia rechazada auditada con exito.")

    def test_auditoria_al_eliminar_incidencia_rechazada(self):
        print("\n[TEST] Verificando auditoria al hacer soft-delete de una incidencia rechazada...")
        self.client.force_login(self.admin_user)
        
        response = self.client.post(reverse('eliminar_incidencia_rechazada'), {
            'incidencia_id': str(self.incidencia_rechazada.id)
        })
        
        self.assertEqual(response.status_code, 302)
        
        log = AuditLog.objects.filter(
            table_name='timetracking_correctionrequest',
            record_id=str(self.incidencia_rechazada.id),
            action_type='voided'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se audito la eliminacion (soft-delete).")
        self.assertIsNotNone(log.after['deleted_at'], "Error: El payload JSON no registro el borrado logico.")
        self.assertEqual(log.reason, 'Eliminación (soft-delete) de incidencia rechazada')
        print("OK: Eliminacion de incidencia rechazada auditada de forma segura.")