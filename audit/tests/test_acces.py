import uuid
from django.test import TestCase, Client
from django.urls import reverse
from audit.models import AuditLog
from users.models import Users

class AuditViewsTest(TestCase):
    def setUp(self):
        print("\n Preparando BD temporal para AuditViewsTest...")
        self.client = Client()
        
        self.empleado = Users.objects.create(
            username="empleado", 
            email="empleado@test.com",
            dni="11111111A",
            is_admin=False 
        )
        
        self.auditor = Users.objects.create(
            username="jefe_auditor", 
            email="jefe@test.com",
            dni="22222222B",
            is_admin=True 
        )

        self.log_id = uuid.uuid4()
        AuditLog.objects.create(
            id=self.log_id,
            table_name="timetracking_registro",
            record_id=uuid.uuid4(),
            user=self.empleado,
            action_type="create",
            after={"user": str(self.empleado.id), "status": "present"} 
        )

    def test_acceso_denegado_a_usuario_normal(self):
        print("\n TEST: Intentando acceder al dashboard como usuario base...")
        self.client.force_login(self.empleado)
        response = self.client.get(reverse('audit_dashboard'))
        
        self.assertNotEqual(response.status_code, 200) 
        print(f"  [OK] Éxito: Acceso denegado. Código HTTP devuelto: {response.status_code}")

    def test_acceso_permitido_a_auditor(self):
        print("\n TEST: Intentando acceder al dashboard como auditor...")
        self.client.force_login(self.auditor)
        response = self.client.get(reverse('audit_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'audit/audit_dashboard.html')
        print("  [OK] Éxito: Acceso concedido (HTTP 200) y plantilla correcta cargada.")

