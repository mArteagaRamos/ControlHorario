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
    
    @classmethod
    def setUpTestData(cls):

        print("[SETUP] Generando BD temporal para DashboardAndTeamViewsTest...")
        
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

    def setUp(self):
        self.client = Client()

    def _login_and_set_company(self, user):
        """
        Método auxiliar (DRY): Loguea al usuario inyectado y asocia la sesión a la empresa.
        """
        self.client.force_login(user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    # ── TESTS DE CALENDARIO (CALENDAR) ──────────────────────────────────────────
    def test_1_calendar_post_crear_solicitud_y_auditoria(self):
        print("[TEST 1] Inicio: Verificando solicitud de ausencia (Empleado).")
        
        # Logueamos como empleado
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
        
        print("[TEST 1] Éxito: Solicitud de ausencia y auditoría correctas.\n")

    # ── TESTS DE INFORMACIÓN DE ENTIDAD (ENTITY_INFO) ───────────────────────────
    def test_2_entity_info_post_actualizar_datos_y_auditoria(self):
        print("[TEST 2] Inicio: Verificando actualización de empresa y ajustes (Manager).")
        
        # Logueamos como administrador/manager
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
        
        print("[TEST 2] Éxito: Actualización de ajustes y sus auditorías comprobados correctamente.\n")

class ManagementViewsAuditTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        
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

    def setUp(self):

        self.client = Client()
        self.client.force_login(self.admin_user)
        
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

    # TESTS DE ACCIONES DE MANAGEMENT
    def test_1_editar_registro_post_auditoria(self):
        print("[TEST 1] Inicio: Verificando edición manual de registro y su auditoría.")
        
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
        print("[TEST 1] Éxito: Edición y auditoría verificadas correctamente.\n")

    def test_2_anular_registro_post_auditoria(self):
        print("[TEST 2] Inicio: Verificando anulación (soft-delete) de registro y su auditoría.")
        
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
        print("[TEST 2] Éxito: Anulación y auditoría verificadas correctamente.\n")

class TimeTrackingViewsAuditTest(TestCase):
    """
    Suite de pruebas para verificar la correcta generación de logs de auditoría 
    durante el ciclo de vida completo de un registro de tiempo (Time Tracking).
    
    El flujo evalúa los 4 estados principales simulando peticiones HTTP reales:
    1. Fichaje de entrada (Clock-in)
    2. Inicio de pausa (Pause Start)
    3. Fin de pausa (Pause End)
    4. Fichaje de salida (Clock-out)
    """

    def setUp(self):

        self.client = Client()
        
        # 1. Creación de la empresa base
        self.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Empresa Timetracking SA"
        )
        
        # 2. Creación del usuario (empleado) que realizará los fichajes
        self.employee = Users.objects.create(
            id=uuid.uuid4(),
            username="empleado_reloj",
            email="reloj@test.com",
            dni="44444444E",
            is_admin=False
        )
        self.employee.set_password("testpassword123")
        self.employee.save()

        # 3. Vinculación del empleado con la empresa
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

    def test_auditoria_ciclo_completo_fichaje(self):
        """
        Verifica que cada acción del ciclo de fichaje genera el registro de 
        auditoría (AuditLog) correspondiente, con los campos exactos esperados.
        """
        print("\n[TEST INICIO] Ejecutando ciclo completo de auditoría de fichajes...")
        self._setup_session()
        
        url = reverse('time_entries')
        active_entry_id = None # Variable para almacenar el ID del fichaje durante el ciclo

        # PASO 1: CLOCK IN (Entrada)
        with self.subTest("Paso 1: Fichaje de entrada (Clock-in)"):
            print("  -> [Paso 1] Simulando petición POST para 'clock_in'...")
            response = self.client.post(url, {'action': 'clock_in'})
            
            # Verificamos que la vista responde correctamente (ej. redirección)
            self.assertEqual(response.status_code, 302)
            
            # Buscamos el log de auditoría generado por esta acción específica
            log_in = AuditLog.objects.filter(
                user=self.employee,
                table_name='timetracking_registro',
                action_type=AuditLog.AuditAction.CREATE,
                reason='Fichaje de entrada (Clock-in)'
            ).order_by('-id').first() 
            
            # Validaciones del log
            self.assertIsNotNone(log_in, "Fallo: No se encontró el AuditLog para Clock-in.")
            self.assertEqual(log_in.source, 'web')
            
            # Guardamos el ID del registro de tiempo recién creado. 
            # Lo necesitaremos para validar el Clock-out al final.
            active_entry_id = log_in.record_id 
            print(f"     OK: Log de Clock-in validado (Record ID: {active_entry_id})")

        # PASO 2: PAUSE START (Inicio de pausa)
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
            # Verificamos que el payload guardado en 'after' contenga los datos del evento
            self.assertIn('event_type', log_pause_start.after)
            print("     OK: Log de Inicio de Pausa validado.")

        # PASO 3: PAUSE END (Fin de pausa)
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
            print("     OK: Log de Fin de Pausa validado.")

        # PASO 4: CLOCK OUT (Salida)
        with self.subTest("Paso 4: Fichaje de salida (Clock-out)"):
            print("  -> [Paso 4] Simulando petición POST para 'clock_out'...")
            response = self.client.post(url, {'action': 'clock_out'})
            self.assertEqual(response.status_code, 302)
            
            # Para la salida, buscamos un UPDATE sobre el registro de entrada original
            log_out = AuditLog.objects.filter(
                user=self.employee,
                table_name='timetracking_registro',
                record_id=str(active_entry_id),
                action_type=AuditLog.AuditAction.UPDATE,
                reason='Fichaje de salida (Clock-out)'
            ).order_by('-id').first()
            
            # Validaciones de que se guardó el antes y el después correctamente
            self.assertIsNotNone(log_out, "Fallo: No se encontró el AuditLog para Clock-out.")
            self.assertIsNotNone(log_out.before, "Fallo: El estado previo ('before') no se registró.")
            # Verificamos que el estado final en el log refleje que el registro está confirmado/cerrado
            self.assertEqual(log_out.after['status'], TimeEntries.EntryStatus.CONFIRMED)
            print("     OK: Log de Clock-out validado (Cambio de estado guardado).")
            
        print("\n[TEST FIN] Ciclo completo de fichaje auditado correctamente.")

class UserViewsAuditTest(TestCase):
    
    def setUp(self):

        print("[SETUP] Inicializando entorno para test de autenticación...")
        self.client = Client()
        self.password = "password_segura_123"
        
        self.active_user = Users.objects.create_user(
            id=uuid.uuid4(),
            email="activo@test.com",
            username="usuario_activo",
            dni="11111111A",
            password=self.password,
            status=Users.StatusChoices.ACTIVE
        )

    # TESTS DE AUTENTICACIÓN (LOGIN/LOGOUT)
    def test_1_auditoria_login_fallido(self):
        print("[TEST 1] Inicio: Verificación de auditoría para login fallido.")
        
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
        
        print("[TEST 1] Éxito: Auditoría de login fallido registrada correctamente.")


    def test_2_auditoria_flujo_login_y_logout_exitoso(self):
        print("[TEST 2] Inicio: Verificación de flujo completo (Login exitoso -> Logout).")
        
        # --- PASO 1: Login Exitoso ---
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

        # --- PASO 2: Logout ---
        print("  -> Paso 2 [Logout]: Solicitando cierre de sesión mediante GET...")
        self.client.get(reverse('logout'))
        
        print("  -> Paso 2 [Validación]: Comprobando registro de auditoría de logout...")
        log_logout = AuditLog.objects.filter(
            user=self.active_user,
            table_name='user_action',
            reason='Logout'
        ).first()
        
        self.assertIsNotNone(log_logout, "Error: No se auditó el cierre de sesión.")
        print("[TEST 2] Éxito: Flujo completo de auditoría registrado correctamente.")