import uuid
from datetime import time, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

# Importación de Modelos
from users.models import Users, Companies, UserCompany
from admin.models import CompanySettings
from audit.models import AuditLog
from timetracking.models import TimeEntries
from requests.models import LeaveRequest
from requests.models import CorrectionRequests

class AdminViewsAuditTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 3.1. TESTS DE VISTAS ADMIN (AdminViewsAuditTest)")
        print("█"*70)
        
        cls.admin_user = Users.objects.create(
            id=uuid.uuid4(),
            username="super_jefe",
            email="admin@test.com",
            dni="99999999X",
            is_admin=True, 
        )
        print("  -> Usuario Admin creado. Setup finalizado.")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_1_auditoria_en_admin_dashboard(self):
        print("\n[TEST 1] Inicio: Verificando que el acceso al dashboard genera log de auditoría.")
        print("  -> Acción: Ejecutando GET hacia el dashboard de administración...")
        response = self.client.get(reverse('admin_dashboard'))
        
        self.assertEqual(response.status_code, 200, "Error: El acceso al dashboard falló o fue denegado.")
        
        print("  -> Validación: Comprobando log de auditoría del usuario...")
        log = AuditLog.objects.filter(
            user=self.admin_user, 
            table_name='user_action'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se encontró el registro de auditoría tras el acceso.")
        self.assertEqual(log.reason, 'Acceso al panel de administración')
        self.assertEqual(log.after['rol'], 'administrador')
        print("  [OK] Éxito: Auditoría registrada correctamente al entrar al dashboard.")


class CorrectionsViewsAuditTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 3.2. TESTS DE CORRECCIONES (CorrectionsViewsAuditTest)")
        print("█"*70)
        
        cls.company = Companies.objects.create(
            id=uuid.uuid4(), 
            name="Tech Corp Audit"
        )
        
        cls.admin_user = Users.objects.create(
            id=uuid.uuid4(),
            username="admin_correcciones",
            email="admincorr@test.com",
            dni="77777777C",
            is_admin=True 
        )
        
        cls.employee = Users.objects.create(
            id=uuid.uuid4(),
            username="empleado_base",
            email="empleado@test.com",
            dni="66666666D"
        )
        
        cls.time_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=cls.employee,
            company=cls.company,
            date=timezone.now().date(),
            clock_in=timezone.now() - timedelta(hours=8),
            clock_out=timezone.now() - timedelta(hours=1),
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=25200
        )
        
        cls.incidencia_pendiente = CorrectionRequests.objects.create(
            id=uuid.uuid4(),
            requester=cls.employee,
            time_entry=cls.time_entry,
            new_clock_in=timezone.now() - timedelta(hours=8),
            new_clock_out=timezone.now(),
            reason="Se me olvido fichar a la salida",
            status='pending'
        )
        
        cls.incidencia_rechazada = CorrectionRequests.objects.create(
            id=uuid.uuid4(),
            requester=cls.employee,
            time_entry=cls.time_entry,
            new_clock_in=timezone.now() - timedelta(hours=9),
            new_clock_out=timezone.now(),
            reason="Error al iniciar turno",
            status='rejected'
        )
        print("  -> Empresa, Usuarios, Fichajes e Incidencias creados. Setup finalizado.")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_1_auditoria_al_resolver_incidencia(self):
        print("\n[TEST 1] Inicio: Verificando auditoría al resolver (aceptar) una incidencia.")
        print("  -> Acción: Ejecutando POST para aceptar incidencia...")
        response = self.client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(self.incidencia_pendiente.id),
            'accion': 'aceptar',
            'nota_resolucion': 'Comprobado con el manager local.'
        })
        
        self.assertEqual(response.status_code, 302, "Error: La redirección tras resolver falló.")
        
        print("  -> Validación: Comprobando log de auditoría...")
        log = AuditLog.objects.filter(
            table_name='timetracking_correctionrequest',
            record_id=str(self.incidencia_pendiente.id),
            action_type='update'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se creó el log tras resolver la incidencia.")
        self.assertEqual(log.reason, 'Incidencia aceptarda por manager')
        self.assertEqual(log.after['status'], 'approved')
        self.assertEqual(log.after['correction_note'], 'Comprobado con el manager local.')
        print("  [OK] Éxito: Auditoría generada correctamente al aceptar incidencia.")        

    def test_2_auditoria_al_editar_incidencia_rechazada(self):
        print("\n[TEST 2] Inicio: Verificando auditoría al editar una incidencia rechazada.")
        nuevo_inicio = (timezone.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M:%S')
        nuevo_fin = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print("  -> Acción: Ejecutando POST para editar incidencia y devolverla a revisión...")
        response = self.client.post(reverse('editar_incidencia_rechazada'), {
            'incidencia_id': str(self.incidencia_rechazada.id),
            'new_clock_in': nuevo_inicio,
            'new_clock_out': nuevo_fin,
            'reason': 'Corregido tras revision con RRHH'
        })
        
        self.assertEqual(response.status_code, 302, "Error: La redirección tras editar falló.")
        
        print("  -> Validación: Comprobando log de auditoría...")
        log = AuditLog.objects.filter(
            table_name='timetracking_correctionrequest',
            record_id=str(self.incidencia_rechazada.id),
            reason='Edición de incidencia rechazada para volver a revisión'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se auditó la edición de la incidencia rechazada.")
        self.assertEqual(log.after['status'], 'pending')
        self.assertEqual(log.after['reason'], 'Corregido tras revision con RRHH')
        print("  [OK] Éxito: Edición de incidencia rechazada auditada con éxito.")

    def test_3_auditoria_al_eliminar_incidencia_rechazada(self):
        print("\n[TEST 3] Inicio: Verificando auditoría al hacer soft-delete de incidencia rechazada.")
        print("  -> Acción: Ejecutando POST para eliminar incidencia lógicamente...")
        response = self.client.post(reverse('eliminar_incidencia_rechazada'), {
            'incidencia_id': str(self.incidencia_rechazada.id)
        })
        
        self.assertEqual(response.status_code, 302, "Error: La redirección tras eliminar falló.")
        
        print("  -> Validación: Comprobando log de auditoría y payload JSON...")
        log = AuditLog.objects.filter(
            table_name='timetracking_correctionrequest',
            record_id=str(self.incidencia_rechazada.id),
            action_type='voided'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se auditó la eliminación (soft-delete).")
        self.assertIsNotNone(log.after['deleted_at'], "Error: El payload JSON no registró el borrado lógico.")
        self.assertEqual(log.reason, 'Eliminación (soft-delete) de incidencia rechazada')
        print("  [OK] Éxito: Eliminación de incidencia rechazada auditada de forma segura.")


class DashboardAndTeamViewsTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 3.3. TESTS DE DASHBOARD Y EQUIPO (DashboardAndTeamViewsTest)")
        print("█"*70)
        
        cls.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Test SA",
            tax_id="B12345678"
        )
        
        cls.settings = CompanySettings.objects.create(
            company=cls.company,
            work_start=time(9, 0),
            work_end=time(18, 0),
            max_tolerance=timedelta(minutes=15),
            weekend_days=[5, 6],
            auto_close_hours=2,
            holidays=[]
        )
        
        cls.admin_user = Users.objects.create_user(
            email="admin@test.com",
            username="admin_global",
            dni="12345678A",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=True
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.admin_user, 
            company=cls.company, 
            role=UserCompany.RoleChoices.MANAGER
        )
        
        cls.employee = Users.objects.create_user(
            email="empleado@test.com",
            username="empleado_raso",
            dni="87654321B",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=False
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.employee, 
            company=cls.company, 
            role=UserCompany.RoleChoices.EMPLOYEE
        )
        print("  -> Empresa, Ajustes y Usuarios creados. Setup finalizado.")

    def setUp(self):
        self.client = Client()

    def _login_and_set_company(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    def test_1_calendar_post_crear_solicitud_y_auditoria(self):
        print("\n[TEST 1] Inicio: Verificando solicitud de ausencia (Empleado).")
        self._login_and_set_company(self.employee)
        
        start_date = timezone.now().date().strftime('%Y-%m-%d')
        end_date = (timezone.now().date() + timedelta(days=2)).strftime('%Y-%m-%d')

        print("  -> Acción: Ejecutando POST para solicitar vacaciones...")
        response = self.client.post(reverse('calendar'), {
            'leave_type': 'annual',
            'leave_reason': 'Vacaciones de verano',
            'start_date': start_date,
            'end_date': end_date,
            'reason_note': 'Necesito descanso'
        })
        
        self.assertEqual(response.status_code, 302, "Error: La redirección tras solicitar ausencia falló.")
        
        print("  -> Validación: Comprobando creación en base de datos...")
        leave_exists = LeaveRequest.objects.filter(user=self.employee, leave_type='annual').exists()
        self.assertTrue(leave_exists, "Error: La solicitud de ausencia no se guardó en la BD.")
        
        print("  -> Validación: Comprobando log de auditoría...")
        log = AuditLog.objects.filter(user=self.employee, action_type=AuditLog.AuditAction.CREATE).first()
        self.assertIsNotNone(log, "Error: No se generó auditoría para la creación de la ausencia.")
        print("  [OK] Éxito: Solicitud de ausencia y auditoría correctas.")

    def test_2_entity_info_post_actualizar_datos_y_auditoria(self):
        print("\n[TEST 2] Inicio: Verificando actualización de empresa y ajustes (Manager).")
        self._login_and_set_company(self.admin_user)
        
        print("  -> Acción: Ejecutando POST para actualizar jornada y empresa...")
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

        self.assertEqual(response.status_code, 302, "Error: La redirección tras actualizar entidad falló.")
        
        print("  -> Validación: Comprobando actualización en modelos de BD...")
        self.company.refresh_from_db()
        self.settings.refresh_from_db()
        
        self.assertIn(self.company.name, ['Empresa Editada SA', 'Empresa Editada Sa'])
        self.assertEqual(str(self.settings.work_start), '08:00:00')
        self.assertEqual(self.settings.auto_close_hours, 4)

        print("  -> Validación: Comprobando auditorías múltiples...")
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
        print("  [OK] Éxito: Actualización de ajustes y sus auditorías comprobados correctamente.")


class ManagementViewsAuditTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 3.4. TESTS DE MANAGEMENT (ManagementViewsAuditTest)")
        print("█"*70)
        
        cls.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Management SA",
            tax_id="M12345678"
        )
        
        cls.admin_user = Users.objects.create_user(
            email="manager@test.com",
            username="admin_management",
            dni="11111111A",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=True
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.admin_user, 
            company=cls.company, 
            role=UserCompany.RoleChoices.MANAGER
        )
        
        cls.employee = Users.objects.create_user(
            email="empleado_mgmt@test.com",
            username="empleado_management",
            dni="22222222B",
            password="testpassword123",
            id=uuid.uuid4(),
            is_admin=False
        )
        UserCompany.objects.create(
            id=uuid.uuid4(),
            user=cls.employee, 
            company=cls.company, 
            role=UserCompany.RoleChoices.EMPLOYEE
        )

        cls.time_entry = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=cls.employee,
            company=cls.company,
            date=timezone.now().date(),
            clock_in=timezone.now() - timedelta(hours=8),
            clock_out=timezone.now(),
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=28800
        )
        print("  -> Usuarios y TimeEntry base creados. Setup finalizado.")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    def test_1_editar_registro_post_auditoria(self):
        print("\n[TEST 1] Inicio: Verificando edición manual de registro y su auditoría.")
        hoy = timezone.now().strftime('%Y-%m-%d')
        clock_in = f"{hoy}T09:00"
        clock_out = f"{hoy}T17:00"

        print("  -> Acción: Ejecutando POST para editar fichaje...")
        response = self.client.post(reverse('editar_registro'), {
            'registro_id': str(self.time_entry.id),
            'clock_in': clock_in,
            'clock_out': clock_out
        })

        self.assertEqual(response.status_code, 302, "Error: La redirección tras editar falló.")
        
        print("  -> Validación: Comprobando actualización en base de datos...")
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
        
        print("  -> Validación: Comprobando log de auditoría...")
        log = AuditLog.objects.filter(
            table_name='timetracking_timeentries',
            action_type='update',
            reason__contains='Edición manual de fichaje'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se generó auditoría para la edición.")
        print("  [OK] Éxito: Edición y auditoría verificadas correctamente.")

    def test_2_anular_registro_post_auditoria(self):
        print("\n[TEST 2] Inicio: Verificando anulación (soft-delete) de registro y su auditoría.")
        print("  -> Acción: Ejecutando POST para anular fichaje...")
        response = self.client.post(reverse('anular_registro'), {
            'registro_id': str(self.time_entry.id)
        })

        self.assertEqual(response.status_code, 302, "Error: La redirección tras anular falló.")
        
        print("  -> Validación: Comprobando estado 'voided' y fecha de borrado...")
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, 'voided')
        self.assertIsNotNone(self.time_entry.deleted_at)
        
        print("  -> Validación: Comprobando log de auditoría...")
        log = AuditLog.objects.filter(
            table_name='timetracking_timeentries',
            action_type='voided',
            reason__contains='Anulación directa de registro'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se generó auditoría para la anulación.")
        print("  [OK] Éxito: Anulación y auditoría verificadas correctamente.")


class TimeTrackingViewsAuditTest(TestCase):
    
    # En esta clase NO usamos setUpTestData porque el ciclo de vida altera 
    # muchos estados y preferimos que se cree todo limpio por cada test.
    def setUp(self):
        # Como no hay setUpTestData, imprimimos el bloque aquí si es el primer test
        print("\n\n" + "█"*70)
        print(" 3.5. TESTS DE TIMETRACKING (TimeTrackingViewsAuditTest)")
        print("█"*70)
        
        self.client = Client()
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Timetracking SA"
        )
        self.employee = Users.objects.create(
            id=uuid.uuid4(),
            username="empleado_reloj",
            email="reloj@test.com",
            dni="44444444E",
            is_admin=False
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
        self.client.force_login(self.employee)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()
        print("  -> Sesión configurada y usuario autenticado.")

    def test_1_auditoria_ciclo_completo_fichaje(self):
        print("\n[TEST INICIO] Ejecutando ciclo completo de auditoría de fichajes...")
        self._setup_session()
        
        url = reverse('time_entries')
        active_entry_id = None

        with self.subTest("Paso 1: Fichaje de entrada (Clock-in)"):
            print("  -> [Paso 1] Simulando petición POST para 'clock_in'...")
            response = self.client.post(url, {'action': 'clock_in'})
            self.assertEqual(response.status_code, 302)
            
            log_in = AuditLog.objects.filter(
                user=self.employee,
                table_name='timetracking_registro',
                action_type=AuditLog.AuditAction.CREATE,
                reason='Fichaje de entrada (Clock-in)'
            ).order_by('-id').first() 
            
            self.assertIsNotNone(log_in, "Fallo: No se encontró el AuditLog para Clock-in.")
            self.assertEqual(log_in.source, 'web')
            active_entry_id = log_in.record_id 
            print(f"     [OK] Log de Clock-in validado (Record ID: {active_entry_id})")

        with self.subTest("Paso 2: Inicio de pausa"):
            print("  -> [Paso 2] Simulando petición POST para 'pause_start'...")
            response = self.client.post(url, {'action': 'pause_start'})
            self.assertEqual(response.status_code, 302)
            
            log_pause_start = AuditLog.objects.filter(
                user=self.employee,
                table_name='timetracking_pausa',
                action_type=AuditLog.AuditAction.CREATE,
                reason='Inicio de pausa'
            ).order_by('-id').first()
            
            self.assertIsNotNone(log_pause_start, "Fallo: No se encontró el AuditLog para inicio de pausa.")
            self.assertIn('event_type', log_pause_start.after)
            print("     [OK] Log de Inicio de Pausa validado.")

        with self.subTest("Paso 3: Fin de pausa"):
            print("  -> [Paso 3] Simulando petición POST para 'pause_end'...")
            response = self.client.post(url, {'action': 'pause_end'})
            self.assertEqual(response.status_code, 302)
            
            log_pause_end = AuditLog.objects.filter(
                user=self.employee,
                table_name='timetracking_pausa',
                action_type=AuditLog.AuditAction.CREATE,
                reason='Fin de pausa'
            ).order_by('-id').first()
            
            self.assertIsNotNone(log_pause_end, "Fallo: No se encontró el AuditLog para fin de pausa.")
            print("     [OK] Log de Fin de Pausa validado.")

        with self.subTest("Paso 4: Fichaje de salida (Clock-out)"):
            print("  -> [Paso 4] Simulando petición POST para 'clock_out'...")
            response = self.client.post(url, {'action': 'clock_out'})
            self.assertEqual(response.status_code, 302)
            
            log_out = AuditLog.objects.filter(
                user=self.employee,
                table_name='timetracking_registro',
                record_id=str(active_entry_id),
                action_type=AuditLog.AuditAction.UPDATE,
                reason='Fichaje de salida (Clock-out)'
            ).order_by('-id').first()
            
            self.assertIsNotNone(log_out, "Fallo: No se encontró el AuditLog para Clock-out.")
            self.assertIsNotNone(log_out.before, "Fallo: El estado previo ('before') no se registró.")
            self.assertEqual(log_out.after['status'], TimeEntries.EntryStatus.CONFIRMED)
            print("     [OK] Log de Clock-out validado (Cambio de estado guardado).")
            
        print("  [TEST FIN] Ciclo completo de fichaje auditado correctamente.")


class UserViewsAuditTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 3.6. TESTS DE USUARIOS/LOGIN (UserViewsAuditTest)")
        print("█"*70)
        
        cls.password = "password_segura_123"
        cls.active_user = Users.objects.create_user(
            id=uuid.uuid4(),
            email="activo@test.com",
            username="usuario_activo",
            dni="11111111A",
            password=cls.password,
            status=Users.StatusChoices.ACTIVE
        )
        print("  -> Usuario base creado. Setup finalizado.")

    def setUp(self):
        self.client = Client()

    def test_1_auditoria_login_fallido(self):
        print("\n[TEST 1] Inicio: Verificación de auditoría para login fallido.")
        print("  -> Acción: Enviando petición POST con contraseña incorrecta...")
        self.client.post(reverse('login'), {
            'step': 'credentials',
            'username': 'activo@test.com',
            'password': 'password_incorrecta'
        })
        
        print("  -> Validación: Consultando base de datos de auditoría...")
        log = AuditLog.objects.filter(
            table_name='user_action',
            action_type=AuditLog.AuditAction.CREATE,
            reason__contains='Intento de login fallido'
        ).first()
        
        self.assertIsNotNone(log, "Error: No se auditó el intento de login fallido.")
        self.assertIsNone(log.user, "Error: El log no debería asignar usuario en un fallo.")
        print("  [OK] Éxito: Auditoría de login fallido registrada correctamente.")


    def test_2_auditoria_flujo_login_y_logout_exitoso(self):
        print("\n[TEST 2] Inicio: Verificación de flujo completo (Login exitoso -> Logout).")
        
        print("  -> Paso 1 [Login]: Enviando petición POST con credenciales correctas...")
        self.client.post(reverse('login'), {
            'step': 'credentials',
            'username': 'activo@test.com',
            'password': self.password
        })
        
        print("  -> Paso 1 [Validación]: Comprobando registro de auditoría de login...")
        log_login = AuditLog.objects.filter(
            table_name='user_action',
            action_type=AuditLog.AuditAction.CREATE,
            reason='Login exitoso'
        ).first()
        
        self.assertIsNotNone(log_login, "Error: No se auditó el login exitoso.")
        self.assertEqual(log_login.user, self.active_user)
        print("     [OK] Login exitoso auditado y vinculado al usuario.")

        print("  -> Paso 2 [Logout]: Solicitando cierre de sesión mediante GET...")
        self.client.get(reverse('logout'))
        
        print("  -> Paso 2 [Validación]: Comprobando registro de auditoría de logout...")
        log_logout = AuditLog.objects.filter(
            user=self.active_user,
            table_name='user_action',
            reason='Logout'
        ).first()
        
        self.assertIsNotNone(log_logout, "Error: No se auditó el cierre de sesión.")
        print("  [OK] Éxito: Flujo completo de auditoría registrado correctamente.")