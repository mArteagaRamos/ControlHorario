import uuid
from datetime import time, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

# Importación de Modelos
from users.models import Users, Companies, UserCompany
from admin.models import CompanySettings
from audit.models import AuditLog
from dashboard.models import Note
from timetracking.models import TimeEntries, TimeEntryEvent
from corrections.models import LeaveRequest
from corrections.models import CorrectionRequests

class AdminViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para AdminViewsAuditTest...")
        self.client = Client()
        
        # 1. Creamos el usuario administrador
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
        
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        log = AuditLog.objects.filter(user=self.admin_user, table_name='user_action').first()
        
        self.assertIsNotNone(log, "Error: No se encontro el registro de auditoria")
        self.assertEqual(log.reason, 'Acceso al panel de administración')
        self.assertEqual(log.after['rol'], 'administrador')
        print("OK: Auditoria registrada correctamente al entrar al dashboard.")


class CorrectionsViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando BD temporal para CorrectionsViewsAuditTest...")
        self.client = Client()
        
        self.company = Companies.objects.create(
            id=uuid.uuid4(), 
            name="Tech Corp Audit"
        )
        
        self.admin_user = Users.objects.create(
            id=uuid.uuid4(),
            username="admin_correcciones",
            email="admincorr@test.com",
            dni="77777777C",
            is_admin=True 
        )
        
        self.employee = Users.objects.create(
            id=uuid.uuid4(),
            username="empleado_base",
            email="empleado@test.com",
            dni="66666666D"
        )
        
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
        
        self.incidencia_pendiente = CorrectionRequests.objects.create(
            id=uuid.uuid4(),
            requester=self.employee,
            time_entry=self.time_entry,
            new_clock_in=timezone.now() - timedelta(hours=8),
            new_clock_out=timezone.now(),
            reason="Se me olvido fichar a la salida",
            status='pending'
        )
        
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
        
        self.assertEqual(response.status_code, 302)
        
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

    def test_auditoria_al_editar_incidencia_rechazada(self):
        print("\n[TEST] Verificando auditoria al editar una incidencia rechazada...")
        self.client.force_login(self.admin_user)
        
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


class DashboardAndTeamViewsTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para DashboardAndTeamViewsTest...")
        self.client = Client()
        
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Test SA",
            tax_id="B12345678"
        )
        
        self.admin_user = Users.objects.create_user(
            email="admin@test.com",
            username="admin_global",
            dni="12345678A",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=True
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.admin_user, 
            company=self.company, 
            role=UserCompany.RoleChoices.MANAGER
        )
        
        self.employee = Users.objects.create_user(
            email="empleado@test.com",
            username="empleado_raso",
            dni="87654321B",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=False
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.employee, 
            company=self.company, 
            role=UserCompany.RoleChoices.EMPLOYEE
        )

    # ── TESTS DE CALENDARIO (CALENDAR) ──────────────────────────────────────────

    def test_calendar_post_crear_solicitud_y_auditoria(self):
        print("\n[TEST] Verificando solicitud de ausencia desde el calendario...")
        self.client.force_login(self.employee)
        
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        start_date = timezone.now().date().strftime('%Y-%m-%d')
        end_date = (timezone.now().date() + timedelta(days=2)).strftime('%Y-%m-%d')

        response = self.client.post(reverse('calendar'), {
            'leave_type': 'annual',
            'leave_reason': 'Vacaciones de verano',
            'start_date': start_date,
            'end_date': end_date,
            'reason_note': 'Necesito descanso'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LeaveRequest.objects.filter(user=self.employee, leave_type='annual').exists())
        
        log = AuditLog.objects.filter(user=self.employee, action_type=AuditLog.AuditAction.CREATE).first()
        self.assertIsNotNone(log, "No se generó el registro de auditoría para la ausencia.")

    # ── TESTS DE INFORMACIÓN DE ENTIDAD (ENTITY_INFO) ───────────────────────────

    def test_entity_info_post_actualizar_datos_y_auditoria(self):
        print("\n[TEST] Verificando actualización de empresa y auditoría de jornada...")
        
        
        self.settings = CompanySettings.objects.create(
            company=self.company,
            work_start=time(9, 0),
            work_end=time(18, 0),
            max_tolerance=timedelta(minutes=15),
            weekend_days=[5, 6],
            auto_close_hours=2,
            holidays=[]
        )
        
        self.client.force_login(self.admin_user)
        
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        response = self.client.post(reverse('manager_entity_info'), {
            'name': 'Empresa Editada SA',
            'legal_name': 'Empresa Editada Sociedad Anonima',
            'tax_id': 'B12345678',
            'work_start': '08:00:00',
            'work_end': '15:00:00',
            'max_tolerance': '30',
            'auto_close_hours': '4',
            'weekend_days': ['5', '6']
        })

        self.assertEqual(response.status_code, 302)
        
        self.company.refresh_from_db()
        self.settings.refresh_from_db()
        
        self.assertIn(self.company.name, ['Empresa Editada SA', 'Empresa Editada Sa'])
        self.assertEqual(str(self.settings.work_start), '08:00:00')
        self.assertEqual(self.settings.auto_close_hours, 4)

        log_jornada = AuditLog.objects.filter(
            table_name='company_settings',
            reason__contains='Modificación de jornada laboral'
        ).first()
        self.assertIsNotNone(log_jornada, "Error: No se auditó el cambio de jornada.")
        
        log_cierre = AuditLog.objects.filter(
            table_name='company_settings',
            reason__contains='Modificación de cierre automático'
        ).first()
        self.assertIsNotNone(log_cierre, "Error: No se auditó el cambio de cierre automático.")

class ManagementViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para ManagementViewsAuditTest...")
        self.client = Client()
        
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Management SA",
            tax_id="M12345678"
        )
        
        self.admin_user = Users.objects.create_user(
            email="manager@test.com",
            username="admin_management",
            dni="11111111A",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=True
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.admin_user, 
            company=self.company, 
            role=UserCompany.RoleChoices.MANAGER
        )
        
        self.employee = Users.objects.create_user(
            email="empleado_mgmt@test.com",
            username="empleado_management",
            dni="22222222B",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=False
        )
        self.membership = UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.employee, 
            company=self.company, 
            role=UserCompany.RoleChoices.EMPLOYEE
        )

        # Fichaje necesario para poder editarlo/anularlo o exportarlo
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

    def test_editar_registro_post_auditoria(self):
        print("\n[TEST] Verificando edición manual de registro y su auditoría...")
        self.client.force_login(self.admin_user)
        
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        hoy = timezone.now().strftime('%Y-%m-%d')
        clock_in = f"{hoy}T09:00"
        clock_out = f"{hoy}T17:00"

        response = self.client.post(reverse('editar_registro'), {
            'registro_id': str(self.time_entry.id),
            'clock_in': clock_in,
            'clock_out': clock_out
        })

        self.assertEqual(response.status_code, 302)
        
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
        
        log = AuditLog.objects.filter(
            table_name='timetracking_timeentries',
            action_type='update',
            reason__contains='Edición manual de fichaje'
        ).first()
        self.assertIsNotNone(log, "No se generó el registro de auditoría para la edición del fichaje.")

    def test_anular_registro_post_auditoria(self):
        print("\n[TEST] Verificando anulación de registro y su auditoría...")
        self.client.force_login(self.admin_user)
        
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })

        self.assertEqual(response.status_code, 302)
        
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, 'voided')
        self.assertIsNotNone(self.time_entry.deleted_at)
        
        log = AuditLog.objects.filter(
            table_name='timetracking_timeentries',
            action_type='voided',
            reason__contains='Anulación directa de registro'
        ).first()
        self.assertIsNotNone(log, "No se generó el registro de auditoría para la anulación del fichaje.")

class TimeTrackingViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para TimeTrackingViewsAuditTest...")
        self.client = Client()
        
        # 1. Crear empresa
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Timetracking SA"
        )
        
        # 2. Crear empleado para fichar
        self.employee = Users.objects.create(
            id=uuid.uuid4(),
            username="empleado_reloj",
            email="reloj@test.com",
            dni="44444444E",
            is_admin=False
            # Asegúrate de que no esté en status INACTIVE, 
            # ya que tu view bloquea los fichajes en ese caso
        )
        self.employee.set_password("testpassword123")
        self.employee.save()

        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.employee, 
            company=self.company, 
            role=UserCompany.RoleChoices.EMPLOYEE
        )

    def _setup_session(self):
        """Helper para loguear y setear la empresa en sesión"""
        self.client.force_login(self.employee)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    def test_auditoria_clock_in(self):
        print("\n[TEST] Verificando auditoría al registrar entrada (Clock-in)...")
        self._setup_session()

        # Ajusta 'time_entries' si tu urls.py tiene otro nombre para esta view
        response = self.client.post(reverse('time_entries'), {
            'action': 'clock_in'
        })

        self.assertEqual(response.status_code, 302)
        
        log = AuditLog.objects.filter(
            user=self.employee,
            table_name='timetracking_registro',
            action_type=AuditLog.AuditAction.CREATE,
            reason='Fichaje de entrada (Clock-in)'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se generó el log de auditoría para el Clock-in.")
        self.assertEqual(log.source, 'web')

    def test_auditoria_pause_start(self):
        print("\n[TEST] Verificando auditoría al iniciar una pausa...")
        self._setup_session()

        # Creamos un fichaje activo reciente para poder pausarlo
        active_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=self.employee,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now() - timedelta(hours=2),
            status=TimeEntries.EntryStatus.ONGOING
        )

        response = self.client.post(reverse('time_entries'), {
            'action': 'pause_start'
        })

        self.assertEqual(response.status_code, 302)
        
        log = AuditLog.objects.filter(
            user=self.employee,
            table_name='timetracking_pausa',
            action_type=AuditLog.AuditAction.CREATE,
            reason='Inicio de pausa'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se generó el log de auditoría al iniciar la pausa.")
        self.assertIn('event_type', log.after) # Verifica que capturó el payload del evento

    def test_auditoria_pause_end(self):
        print("\n[TEST] Verificando auditoría al finalizar una pausa...")
        self._setup_session()

        # Creamos fichaje activo y un evento de pausa previo
        active_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=self.employee,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now() - timedelta(hours=3),
            status=TimeEntries.EntryStatus.ONGOING
        )
        TimeEntryEvent.objects.create(
            id=uuid.uuid4(),
            time_entry=active_entry,
            event_type=TimeEntryEvent.EventType.PAUSE_START,
            timestamp=timezone.now() - timedelta(minutes=30),
            actor=self.employee
        )

        response = self.client.post(reverse('time_entries'), {
            'action': 'pause_end'
        })

        self.assertEqual(response.status_code, 302)
        
        log = AuditLog.objects.filter(
            user=self.employee,
            table_name='timetracking_pausa',
            action_type=AuditLog.AuditAction.CREATE,
            reason='Fin de pausa'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se generó el log de auditoría al finalizar la pausa.")

    def test_auditoria_clock_out(self):
        print("\n[TEST] Verificando auditoría al registrar salida (Clock-out)...")
        self._setup_session()

        # Creamos un fichaje activo reciente
        active_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=self.employee,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now() - timedelta(hours=4),
            status=TimeEntries.EntryStatus.ONGOING
        )

        response = self.client.post(reverse('time_entries'), {
            'action': 'clock_out'
        })

        self.assertEqual(response.status_code, 302)
        
        log = AuditLog.objects.filter(
            user=self.employee,
            table_name='timetracking_registro',
            record_id=str(active_entry.id),
            action_type=AuditLog.AuditAction.UPDATE,
            reason='Fichaje de salida (Clock-out)'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se generó el log de auditoría para el Clock-out.")
        self.assertIsNotNone(log.before, "Error: El payload 'before' está vacío en el update.")
        self.assertEqual(log.after['status'], TimeEntries.EntryStatus.CONFIRMED)

class UserViewsAuditTest(TestCase):
    def setUp(self):
        print("\n[SETUP] Preparando base de datos temporal para UserViewsAuditTest...")
        self.client = Client()
        self.password = "password_segura_123"
        
        # ── 1. Datos para tests de Auth ──
        self.active_user = Users.objects.create_user(
            id=uuid.uuid4(),
            email="activo@test.com",
            username="usuario_activo",
            dni="11111111A",
            password=self.password,
            status=Users.StatusChoices.ACTIVE
        )
        
        self.suspended_user = Users.objects.create_user(
            id=uuid.uuid4(),
            email="suspendido@test.com",
            username="usuario_suspendido",
            dni="22222222B",
            password=self.password,
            status='suspended' # Asegúrate de usar el valor real de tus choices
        )

        # ── 2. Datos para test de Registro Unificado ──
        self.admin_user = Users.objects.create_user(
            id=uuid.uuid4(),
            email="admin@test.com",
            username="admin_unificado",
            dni="33333333C",
            password=self.password,
            is_admin=True
        )
        
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Original",
            tax_id="A12345678"
        )

        # ── 3. Datos para tests de Workday (Empleado, Fichajes e Incidencias) ──
        self.employee = Users.objects.create_user(
            id=uuid.uuid4(),
            email="empleado@test.com",
            username="empleado",
            dni="44444444D",
            password=self.password,
            is_admin=False
        )
        
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.employee, 
            company=self.company, 
            role=UserCompany.RoleChoices.EMPLOYEE
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
        
        self.correction_request = CorrectionRequests.objects.create(
            id=uuid.uuid4(),
            time_entry=self.time_entry,
            requester=self.employee,
            reason="Prueba inicial",
            new_clock_in=timezone.now() - timedelta(hours=8),
            status='pending'
        )

    # ── Utilidad para iniciar sesión en los tests de Workday ──
    def _setup_employee_session(self):
        self.client.force_login(self.employee)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    # ==========================================
    # TESTS DE AUTENTICACIÓN (LOGIN/LOGOUT)
    # ==========================================

    def test_login_exitoso_auditoria(self):
        print("\n[TEST] Verificando auditoría al hacer login exitoso...")
        self.client.post(reverse('login'), {
            'step': 'credentials',
            'username': 'activo@test.com',
            'password': self.password
        })
        
        log = AuditLog.objects.filter(
            table_name='user_action',
            action_type=AuditLog.AuditAction.CREATE,
            reason='Login exitoso'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se audito el login exitoso.")
        self.assertEqual(log.user, self.active_user)

    def test_login_fallido_auditoria(self):
        print("\n[TEST] Verificando auditoría al hacer login fallido (contraseña incorrecta)...")
        self.client.post(reverse('login'), {
            'step': 'credentials',
            'username': 'activo@test.com',
            'password': 'password_incorrecta'
        })
        
        log = AuditLog.objects.filter(
            table_name='user_action',
            action_type=AuditLog.AuditAction.CREATE,
            reason__contains='Intento de login fallido'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se audito el intento de login fallido.")
        self.assertIsNone(log.user)

    def test_logout_auditoria(self):
        print("\n[TEST] Verificando auditoría al hacer logout...")
        self.client.force_login(self.active_user)
        self.client.get(reverse('logout'))
        
        log = AuditLog.objects.filter(
            user=self.active_user,
            table_name='user_action',
            reason='Logout'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se audito el cierre de sesión.")

    