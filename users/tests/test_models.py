# users/tests/test_models.py
#
# Bloque 2: Tests de Modelos
# Cubre: Users, Companies, UserCompany
# Ejecutar: python manage.py test users.tests.test_models

import uuid
from django.utils import timezone
from django.db import IntegrityError

from users.models import Users, Companies, UserCompany
from users.tests.conftest import BaseTestCase, make_user, make_company, make_membership


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2.1 — Users Model
# ─────────────────────────────────────────────────────────────────────────────

class UsersModelTest(BaseTestCase):

    # ── __str__ ──────────────────────────────────────────────────────────────

    def test_str_returns_email(self):
        """__str__ devuelve el email del usuario."""
        self.assertEqual(str(self.employee_user), self.employee_user.email)

    # ── Normalización de campos ───────────────────────────────────────────────

    def test_username_saved_uppercase(self):
        """username se guarda en mayúsculas."""
        user = make_user(username='lowercase', surname='TEST', dni='NORM001')
        self.assertEqual(user.username, 'LOWERCASE')

    def test_surname_saved_uppercase(self):
        """surname se guarda en mayúsculas."""
        user = make_user(username='TEST', surname='lowercase surname', dni='NORM002')
        self.assertEqual(user.surname, 'LOWERCASE SURNAME')

    def test_email_saved_uppercase(self):
        """email se guarda en MAYÚSCULAS en base de datos."""
        user = make_user(email='upper@test.com', dni='NORM003')
        self.assertEqual(user.email, 'UPPER@TEST.COM')

    def test_dni_saved_uppercase(self):
        """dni se guarda en mayúsculas."""
        user = make_user(dni='abcd1234')
        self.assertEqual(user.dni, 'ABCD1234')

    def test_username_stripped_of_whitespace(self):
        """username se guarda sin espacios al inicio/final."""
        user = make_user(username='  SPACED  ', dni='NORM005')
        self.assertEqual(user.username, 'SPACED')

    def test_password_not_uppercased(self):
        """password NO se normaliza (está en uppercase_excluded_fields)."""
        user = make_user(password='TestPass123!')
        # La contraseña debe seguir siendo verificable con el valor original
        self.assertTrue(user.check_password('TestPass123!'))

    # ── Campos por defecto ────────────────────────────────────────────────────

    def test_default_status_is_active(self):
        """status por defecto es 'active'."""
        user = make_user(dni='DEF001')
        self.assertEqual(user.status, Users.StatusChoices.ACTIVE)

    def test_default_is_admin_false(self):
        """is_admin por defecto es False."""
        user = make_user(dni='DEF002')
        self.assertFalse(user.is_admin)

    def test_default_is_auditor_false(self):
        """is_auditor por defecto es False."""
        user = make_user(dni='DEF003')
        self.assertFalse(user.is_auditor)

    def test_default_deleted_at_is_none(self):
        """deleted_at por defecto es None (usuario no eliminado)."""
        user = make_user(dni='DEF004')
        self.assertIsNone(user.deleted_at)

    def test_default_must_change_password_false(self):
        """must_change_password por defecto es False en make_user."""
        user = make_user(dni='DEF005')
        self.assertFalse(user.must_change_password)

    # ── Status choices ────────────────────────────────────────────────────────

    def test_status_active(self):
        """Usuario puede tener status 'active'."""
        user = make_user(status=Users.StatusChoices.ACTIVE, dni='ST001')
        self.assertEqual(user.status, 'active')

    def test_status_inactive(self):
        """Usuario puede tener status 'inactive'."""
        user = make_user(status=Users.StatusChoices.INACTIVE, dni='ST002')
        self.assertEqual(user.status, 'inactive')

    def test_status_suspended(self):
        """Usuario puede tener status 'suspended'."""
        user = make_user(status=Users.StatusChoices.SUSPENDED, dni='ST003')
        self.assertEqual(user.status, 'suspended')

    # ── is_admin / is_auditor flags ───────────────────────────────────────────

    def test_is_admin_flag(self):
        """is_admin=True se persiste correctamente."""
        self.assertTrue(self.admin_user.is_admin)

    def test_is_auditor_flag(self):
        """is_auditor=True se persiste correctamente."""
        self.assertTrue(self.auditor_user.is_auditor)

    def test_admin_and_auditor_are_independent_flags(self):
        """is_admin e is_auditor son independientes entre sí."""
        user = make_user(is_admin=True, is_auditor=True, dni='FLAG001')
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_auditor)

    # ── must_change_password ──────────────────────────────────────────────────

    def test_must_change_password_true(self):
        """must_change_password=True se persiste correctamente."""
        user = make_user(must_change_password=True, dni='MCP001')
        self.assertTrue(user.must_change_password)

    def test_must_change_password_can_be_set_to_false(self):
        """must_change_password puede actualizarse a False."""
        user = make_user(must_change_password=True, dni='MCP002')
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)

    # ── USERNAME_FIELD ────────────────────────────────────────────────────────

    def test_username_field_is_email(self):
        """USERNAME_FIELD del modelo es 'email'."""
        self.assertEqual(Users.USERNAME_FIELD, 'email')

    # ── email uniqueness ──────────────────────────────────────────────────────

    def test_email_must_be_unique(self):
        """No se pueden crear dos usuarios con el mismo email."""
        make_user(email='duplicate@test.com', dni='UNIQ001')
        with self.assertRaises(IntegrityError):
            make_user(email='duplicate@test.com', dni='UNIQ002')

    # ── dni uniqueness ────────────────────────────────────────────────────────

    def test_dni_must_be_unique(self):
        """No se pueden crear dos usuarios con el mismo DNI."""
        make_user(dni='SAMEID1')
        with self.assertRaises(IntegrityError):
            make_user(dni='SAMEID1')

    # ── Soft-delete ───────────────────────────────────────────────────────────

    def test_soft_delete_sets_deleted_at(self):
        """soft_delete marca deleted_at con timestamp."""
        user = make_user(dni='SD001')
        Users.objects.soft_delete(user)
        user.refresh_from_db()
        self.assertIsNotNone(user.deleted_at)

    def test_soft_delete_sets_status_suspended(self):
        """soft_delete cambia status a 'suspended'."""
        user = make_user(dni='SD002')
        Users.objects.soft_delete(user)
        user.refresh_from_db()
        self.assertEqual(user.status, Users.StatusChoices.SUSPENDED)

    def test_soft_deleted_user_excluded_from_default_queryset(self):
        """Usuario soft-deleted no aparece en Users.objects.all()."""
        user = make_user(dni='SD003')
        Users.objects.soft_delete(user)
        self.assertFalse(Users.objects.filter(id=user.id).exists())

    def test_soft_deleted_user_visible_with_all_with_deleted(self):
        """Usuario soft-deleted sí aparece en all_with_deleted()."""
        user = make_user(dni='SD004')
        Users.objects.soft_delete(user)
        self.assertTrue(Users.objects.all_with_deleted().filter(id=user.id).exists())

    def test_restore_clears_deleted_at(self):
        """restore() limpia deleted_at."""
        user = make_user(dni='SD005')
        Users.objects.soft_delete(user)
        Users.objects.restore(user)
        user.refresh_from_db()
        self.assertIsNone(user.deleted_at)

    def test_restore_sets_status_active(self):
        """restore() devuelve status a 'active'."""
        user = make_user(dni='SD006')
        Users.objects.soft_delete(user)
        Users.objects.restore(user)
        user.refresh_from_db()
        self.assertEqual(user.status, Users.StatusChoices.ACTIVE)

    def test_only_deleted_returns_only_deleted_users(self):
        """only_deleted() devuelve solo usuarios eliminados."""
        active_user = make_user(dni='SD007')
        deleted_user = make_user(dni='SD008')
        Users.objects.soft_delete(deleted_user)

        only_deleted = Users.objects.only_deleted()
        self.assertIn(deleted_user, only_deleted)
        self.assertNotIn(active_user, only_deleted)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2.2 — Companies Model
# ─────────────────────────────────────────────────────────────────────────────

class CompaniesModelTest(BaseTestCase):

    # ── Creación básica ───────────────────────────────────────────────────────

    def test_company_created_with_correct_fields(self):
        """Company se crea con los campos correctos."""
        company = make_company(
            name='Mi Empresa',
            legal_name='Mi Empresa S.L.',
            tax_id='ESC11111111',
        )
        self.assertEqual(company.name, 'Mi Empresa')
        self.assertEqual(company.legal_name, 'Mi Empresa S.L.')
        self.assertEqual(company.tax_id, 'ESC11111111')

    def test_company_id_is_uuid(self):
        """El id de Company es un UUID."""
        self.assertIsInstance(self.company1.id, uuid.UUID)

    def test_company_created_at_set_on_creation(self):
        """created_at se establece al crear la empresa."""
        company = make_company()
        self.assertIsNotNone(company.created_at)

    def test_company_updated_at_set_on_creation(self):
        """updated_at se establece al crear la empresa."""
        company = make_company()
        self.assertIsNotNone(company.updated_at)

    def test_company_deleted_at_none_by_default(self):
        """deleted_at es None por defecto."""
        company = make_company()
        self.assertIsNone(company.deleted_at)

    # ── tax_id uniqueness ─────────────────────────────────────────────────────

    def test_tax_id_must_be_unique(self):
        """No se pueden crear dos empresas con el mismo tax_id."""
        make_company(tax_id='ESUNIQUE01')
        with self.assertRaises(IntegrityError):
            make_company(tax_id='ESUNIQUE01')

    def test_tax_id_can_be_null(self):
        """tax_id puede ser nulo."""
        company = Companies.objects.create(
            id=uuid.uuid4(),
            name='Sin CIF',
            legal_name='Sin CIF S.L.',
            tax_id=None,
        )
        self.assertIsNone(company.tax_id)

    # ── Soft-delete ───────────────────────────────────────────────────────────

    def test_soft_delete_sets_deleted_at(self):
        """soft_delete marca deleted_at en Company."""
        company = make_company()
        Companies.objects.soft_delete(company)
        company.refresh_from_db()
        self.assertIsNotNone(company.deleted_at)

    def test_soft_deleted_company_excluded_from_default_queryset(self):
        """Company soft-deleted no aparece en Companies.objects.all()."""
        company = make_company()
        Companies.objects.soft_delete(company)
        self.assertFalse(Companies.objects.filter(id=company.id).exists())

    def test_soft_deleted_company_visible_with_all_with_deleted(self):
        """Company soft-deleted sí aparece en all_with_deleted()."""
        company = make_company()
        Companies.objects.soft_delete(company)
        self.assertTrue(Companies.objects.all_with_deleted().filter(id=company.id).exists())

    def test_restore_company(self):
        """restore() limpia deleted_at en Company."""
        company = make_company()
        Companies.objects.soft_delete(company)
        Companies.objects.restore(company)
        company.refresh_from_db()
        self.assertIsNone(company.deleted_at)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2.3 — UserCompany Model
# ─────────────────────────────────────────────────────────────────────────────

class UserCompanyModelTest(BaseTestCase):

    # ── Creación básica ───────────────────────────────────────────────────────

    def test_membership_created_with_correct_role(self):
        """Membresía se crea con el rol correcto."""
        self.assertEqual(
            self.manager_membership.role,
            UserCompany.RoleChoices.MANAGER,
        )

    def test_membership_id_is_uuid(self):
        """El id de UserCompany es un UUID."""
        self.assertIsInstance(self.manager_membership.id, uuid.UUID)

    def test_membership_joined_at_set_on_creation(self):
        """joined_at se establece al crear la membresía."""
        self.assertIsNotNone(self.employee_membership.joined_at)

    def test_membership_deleted_at_none_by_default(self):
        """deleted_at es None por defecto."""
        self.assertIsNone(self.employee_membership.deleted_at)

    # ── Role choices ──────────────────────────────────────────────────────────

    def test_role_manager(self):
        """Rol MANAGER se persiste correctamente."""
        membership = make_membership(
            self.employee_user, self.company2,
            role=UserCompany.RoleChoices.MANAGER,
        )
        self.assertEqual(membership.role, 'manager')

    def test_role_employee(self):
        """Rol EMPLOYEE se persiste correctamente."""
        membership = make_membership(
            self.admin_user, self.company2,
            role=UserCompany.RoleChoices.EMPLOYEE,
        )
        self.assertEqual(membership.role, 'employee')

    def test_default_role_is_employee(self):
        """El rol por defecto es EMPLOYEE."""
        user = make_user(dni='ROLE001')
        membership = UserCompany.objects.create(
            id=uuid.uuid4(),
            user=user,
            company=self.company2,
        )
        self.assertEqual(membership.role, UserCompany.RoleChoices.EMPLOYEE)

    # ── unique_together ───────────────────────────────────────────────────────

    def test_unique_together_user_company(self):
        """No se puede crear dos membresías para el mismo user+company."""
        with self.assertRaises(IntegrityError):
            make_membership(self.employee_user, self.company1)

    def test_same_user_can_belong_to_different_companies(self):
        """El mismo usuario puede tener membresías en distintas empresas."""
        membership2 = make_membership(self.employee_user, self.company2)
        self.assertIsNotNone(membership2.id)

    # ── Soft-delete ───────────────────────────────────────────────────────────

    def test_soft_delete_sets_deleted_at(self):
        """soft_delete marca deleted_at en UserCompany."""
        membership = make_membership(self.admin_user, self.company1)
        UserCompany.objects.soft_delete(membership)
        membership.refresh_from_db()
        self.assertIsNotNone(membership.deleted_at)

    def test_soft_deleted_membership_excluded_from_default_queryset(self):
        """Membresía soft-deleted no aparece en UserCompany.objects.all()."""
        user = make_user(dni='UCSD01')
        membership = make_membership(user, self.company1)
        UserCompany.objects.soft_delete(membership)
        self.assertFalse(UserCompany.objects.filter(id=membership.id).exists())

    def test_soft_deleted_membership_visible_with_all_with_deleted(self):
        """Membresía soft-deleted sí aparece en all_with_deleted()."""
        user = make_user(dni='UCSD02')
        membership = make_membership(user, self.company1)
        UserCompany.objects.soft_delete(membership)
        self.assertTrue(
            UserCompany.objects.all_with_deleted().filter(id=membership.id).exists()
        )

    def test_restore_membership(self):
        """restore() limpia deleted_at en UserCompany."""
        user = make_user(dni='UCSD03')
        membership = make_membership(user, self.company1)
        UserCompany.objects.soft_delete(membership)
        UserCompany.objects.restore(membership)
        membership.refresh_from_db()
        self.assertIsNone(membership.deleted_at)