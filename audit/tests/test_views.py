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


