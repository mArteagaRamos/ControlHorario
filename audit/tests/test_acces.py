import uuid
from django.test import TestCase, Client
from django.urls import reverse
from audit.models import AuditLog
from users.models import Users

class AuditViewsTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        print("\n\n" + "█"*70)
        print(" 1. TESTS DE ACCESOS (test_acces.py) - AuditViewsTest")
        print("█"*70)
        
        cls.empleado = Users.objects.create(
            username="empleado", 
            email="empleado@test.com",
            dni="11111111A",
            is_admin=False 
        )
        
        cls.auditor = Users.objects.create(
            username="jefe_auditor", 
            email="jefe@test.com",
            dni="22222222B",
            is_admin=True 
        )

        cls.log_id = uuid.uuid4()
        AuditLog.objects.create(
            id=cls.log_id,
            table_name="timetracking_registro",
            record_id=uuid.uuid4(),
            user=cls.empleado,
            action_type="create",
            after={"user": str(cls.empleado.id), "status": "present"} 
        )

    def setUp(self):
        self.client = Client()

    def test_1_acceso_denegado_a_usuario_normal(self):
        print("\n[TEST 1] Inicio: Intentando acceder al dashboard como usuario base.")
        self.client.force_login(self.empleado)
        
        print("  -> Acción: Ejecutando GET al dashboard de auditoría...")
        response = self.client.get(reverse('audit_dashboard'))
        
        self.assertNotEqual(response.status_code, 200) 
        print(f"  -> Validación: Código HTTP devuelto es {response.status_code} (Acceso denegado).")
        print("  [OK] Éxito: Acceso bloqueado correctamente.")

    def test_2_acceso_permitido_a_auditor(self):
        print("\n[TEST 2] Inicio: Intentando acceder al dashboard como auditor.")
        self.client.force_login(self.auditor)
        
        print("  -> Acción: Ejecutando GET al dashboard de auditoría...")
        response = self.client.get(reverse('audit_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'audit/audit_dashboard.html')
        print("  -> Validación: Código HTTP 200 y plantilla correcta cargada.")
        print("  [OK] Éxito: Acceso concedido al auditor.")

    def test_3_traduccion_de_uuids_en_vista_fichajes(self):
        print("\n[TEST 3] Inicio: Comprobando traducción de UUID a Nombres Reales.")
        self.client.force_login(self.auditor)
        
        print("  -> Acción: Ejecutando GET a la vista de timetracking...")
        response = self.client.get(reverse('audit_timetracking'))
        self.assertEqual(response.status_code, 200)
        
        logs_en_contexto = response.context['logs']
        primer_log = logs_en_contexto[0]

        print(f"  -> Validación: Analizando JSON final: {primer_log.after}")
        self.assertEqual(primer_log.after['Usuario'], "EMPLEADO")
        self.assertEqual(primer_log.after['Estado'], "Presente")
        print("  [OK] Éxito: Los UUIDs se tradujeron perfectamente.")