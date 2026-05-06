import uuid
from django.test import TestCase
from users.models import Users, Companies, UserCompany


class ManagementModelsTest(TestCase):
    """
    Test suite para la aplicación 'management'.
    
    NOTA IMPORTANTE:
    La aplicación 'management' NO TIENE MODELOS PROPIOS.
    Esta aplicación es una capa de vistas de gestión que utiliza modelos de otras apps:
    - users.models: Companies, UserCompany, Users
    - timetracking.models: TimeEntries
    - requests.models: CorrectionRequests, LeaveRequest
    - audit.models: AuditLog
    
    Por lo tanto, este archivo de tests valida que los modelos utilizados
    funcionan correctamente en el contexto de la aplicación management.
    """

    @classmethod
    def setUpTestData(cls):
        # Encabezado gigante para los tests de modelos
        print("\n\n" + "█" * 70)
        print(" 2. TESTS DE MODELOS (test_models.py) - ManagementModelsTest")
        print("█" * 70)
        print("\n[INFO] Management no tiene modelos propios.")
        print("       Validando modelos relacionados: Companies, UserCompany, Users")
        print()

        cls.company = Companies.objects.create(
            id=uuid.uuid4(),
            name="Tech Corp",
            tax_id="B12345678"
        )

        cls.user_manager = Users.objects.create(
            username="manager_test",
            email="manager@test.com",
            dni="33333333C"
        )

        cls.user_employee = Users.objects.create(
            username="employee_test",
            email="employee@test.com",
            dni="44444444D"
        )

    def test_1_creacion_de_empresa(self):
        print("\n[TEST 1] Inicio: Verificando creación de una empresa.")
        print("  -> Acción: Creando una nueva empresa...")

        empresa = Companies.objects.create(
            id=uuid.uuid4(),
            name="Nueva Empresa S.L.",
            tax_id="B87654321"
        )

        self.assertIsNotNone(empresa.id)
        self.assertEqual(empresa.name, "Nueva Empresa S.L.")
        self.assertEqual(empresa.tax_id, "B87654321")
        print(f"  -> Validación: Empresa creada con ID '{empresa.id}'.")
        print("  [OK] Éxito: Empresa creada correctamente.")

    def test_2_asignacion_usuario_a_empresa(self):
        print("\n[TEST 2] Inicio: Verificando asignación de usuarios a empresa.")
        print("  -> Acción: Asignando manager a la empresa como MANAGER...")

        user_company_manager = UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.user_manager,
            company=self.company,
            role=UserCompany.RoleChoices.MANAGER
        )

        print(f"  -> Acción: Asignando employee a la empresa como EMPLOYEE...")
        user_company_employee = UserCompany.objects.create(
            id=uuid.uuid4(),
            user=self.user_employee,
            company=self.company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )

        self.assertEqual(user_company_manager.role, UserCompany.RoleChoices.MANAGER)
        self.assertEqual(user_company_employee.role, UserCompany.RoleChoices.EMPLOYEE)

        print("  -> Validación: Roles asignados correctamente.")
        print("  [OK] Éxito: Usuarios asignados a la empresa con sus roles.")
