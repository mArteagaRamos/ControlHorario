import uuid
from django.test import TestCase
from audit.models import AuditLog
from users.models import Users

class AuditLogModelTest(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        # Encabezado gigante para los tests de modelos
        print("\n\n" + "█"*70)
        print(" 2. TESTS DE MODELOS (test_models.py) - AuditLogModelTest")
        print("█"*70)
        
        cls.user = Users.objects.create(
            username="auditor_test", 
            email="auditor@test.com",
            dni="33333333C"
        )

    def test_1_creacion_y_calculo_de_hash(self):
        print("\n[TEST 1] Inicio: Verificando creación y cálculo de hash inicial.")
        print("  -> Acción: Creando un nuevo log de auditoría...")
        
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
        print(f"  -> Validación: Log creado con hash '{log.event_hash[:15]}...'. previous_hash es None.")
        print("  [OK] Éxito: Hash generado correctamente en el primer log.")

    def test_2_cadena_de_hashes_consecutivos(self):
        print("\n[TEST 2] Inicio: Verificando la cadena de herencia de hashes (Blockchain).")
        
        log1 = AuditLog(id=uuid.uuid4(), table_name="tabla1", record_id=uuid.uuid4(), action_type="create")
        log1.save()
        print(f"  -> Acción: Log 1 creado. Hash generado: {log1.event_hash[:15]}...")

        log2 = AuditLog(id=uuid.uuid4(), table_name="tabla2", record_id=uuid.uuid4(), action_type="update")
        log2.save()
        print(f"  -> Acción: Log 2 creado. Previous Hash asignado: {log2.previous_hash[:15]}...")

        print("  -> Validación: Comprobando que el Log 2 hereda del Log 1...")
        self.assertEqual(log2.previous_hash, log1.event_hash)
        print("  [OK] Éxito: La cadena de herencia funciona a la perfección.")

    def test_3_inmutabilidad_del_registro(self):
        print("\n[TEST 3] Inicio: Verificando inmutabilidad (evitar modificaciones).")
        
        log = AuditLog(id=uuid.uuid4(), table_name="test", record_id=uuid.uuid4(), action_type="create")
        log.save()

        print("  -> Acción: Intentando sobrescribir la 'razón' de un registro guardado...")
        log.reason = "Intento de hackeo"
        
        with self.assertRaises(PermissionError):
            log.save()
            
        print("  -> Validación: Se detectó el intento y se lanzó un PermissionError.")
        print("  [OK] Éxito: El sistema es inmutable y bloqueó la modificación.")