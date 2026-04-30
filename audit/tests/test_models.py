import uuid
from django.test import TestCase
from audit.models import AuditLog
from users.models import Users

class AuditLogModelTest(TestCase):
    def setUp(self):
        print("\n Preparando BD temporal para AuditLogModelTest...")
        self.user = Users.objects.create(
            username="auditor_test", 
            email="auditor@test.com",
            dni="33333333C"
        )

    def test_creacion_y_calculo_de_hash(self):
        print("\n TEST: Verificando creación y cálculo de hash...")
        log = AuditLog(
            id=uuid.uuid4(),
            table_name="timetracking_registro",
            record_id=uuid.uuid4(),
            user=self.user,
            action_type=AuditLog.AuditAction.CREATE,
            before={},
            after={"status": "present"},
            source="web"
        )
        log.save()
        
        self.assertIsNotNone(log.event_hash)
        self.assertIsNone(log.previous_hash)
        print(f"  [OK] Éxito: Primer log creado con hash '{log.event_hash}' y previous_hash es None.")

    def test_cadena_de_hashes_consecutivos(self):
        print("\n TEST: Verificando la cadena de herencia de hashes...")
        log1 = AuditLog(id=uuid.uuid4(), table_name="tabla1", record_id=uuid.uuid4(), action_type="create")
        log1.save()
        print(f"  -> Log 1 creado. Hash: {log1.event_hash}")

        log2 = AuditLog(id=uuid.uuid4(), table_name="tabla2", record_id=uuid.uuid4(), action_type="update")
        log2.save()
        print(f"  -> Log 2 creado. Previous Hash: {log2.previous_hash}")

        self.assertEqual(log2.previous_hash, log1.event_hash)
        print("  [OK] Éxito: El log 2 heredó perfectamente el hash del log 1.")

    def test_inmutabilidad_del_registro(self):
        print("\n TEST: Verificando que no se puedan modificar los registros auditados...")
        log = AuditLog(id=uuid.uuid4(), table_name="test", record_id=uuid.uuid4(), action_type="create")
        log.save()

        log.reason = "Intento de hackeo"
        
        with self.assertRaises(PermissionError):
            log.save()
        print("  [OK] Éxito: El sistema bloqueó la modificación lanzando un PermissionError.")