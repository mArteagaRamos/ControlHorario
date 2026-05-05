# users/tests/conftest.py
#
# Shared fixtures and base test case for all users app tests.
# Import BaseTestCase instead of django.test.TestCase in every test file.

import uuid
from django.test import TestCase, Client
from django.utils import timezone

from users.models import Users, Companies, UserCompany


# ─────────────────────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS  (standalone functions, usable anywhere)
# ─────────────────────────────────────────────────────────────────────────────

def make_company(name='Test Company', legal_name='Test Company S.L.', tax_id=None):
    """
    Create and return a Companies instance.
    tax_id is auto-generated if not provided so each call produces a unique row.
    """
    return Companies.objects.create(
        id=uuid.uuid4(),
        name=name,
        legal_name=legal_name,
        tax_id=tax_id or f'ES{uuid.uuid4().hex[:8].upper()}',
    )


def make_user(
    email=None,
    username='TESTUSER',
    surname='TESTSURNAME',
    dni=None,
    password='TestPass123!',
    is_admin=False,
    is_auditor=False,
    status=Users.StatusChoices.ACTIVE,
    must_change_password=False,
):
    """
    Create and return a Users instance with a hashed password.
    email and dni are auto-generated if not provided.
    """
    email = email or f'user_{uuid.uuid4().hex[:8]}@test.com'
    dni = dni or f'TEST{uuid.uuid4().hex[:6].upper()}'

    user = Users(
        id=uuid.uuid4(),
        email=email,
        username=username,
        surname=surname,
        dni=dni,
        is_admin=is_admin,
        is_auditor=is_auditor,
        status=status,
        must_change_password=must_change_password,
    )
    user.set_password(password)
    # Save bypassing the manager so we can set is_admin / is_auditor freely
    user.save()
    return user


def make_membership(user, company, role=UserCompany.RoleChoices.EMPLOYEE):
    """Create and return a UserCompany membership."""
    return UserCompany.objects.create(
        id=uuid.uuid4(),
        user=user,
        company=company,
        role=role,
    )


def make_user_with_company(role=UserCompany.RoleChoices.EMPLOYEE, **user_kwargs):
    """
    Convenience: create a user + a company + the membership in one call.
    Returns (user, company, membership).
    """
    company = make_company()
    user = make_user(**user_kwargs)
    membership = make_membership(user, company, role=role)
    return user, company, membership


# ─────────────────────────────────────────────────────────────────────────────
# BASE TEST CASE
# ─────────────────────────────────────────────────────────────────────────────

class BaseTestCase(TestCase):
    """
    Base class for all users-app tests.

    Provides:
      - self.client  (Django test Client)
      - self.company1, self.company2
      - self.admin_user
      - self.manager_user  (manager in company1)
      - self.employee_user (employee in company1)
      - self.auditor_user  (no company membership)
      - Helper methods: login(), assert_status(), assert_redirects_to()

    Each test gets a fresh database (Django rolls back after every test method).
    """

    # Default raw password used for all fixture users — override per test if needed
    DEFAULT_PASSWORD = 'TestPass123!'

    def setUp(self):
        self.client = Client()

        # ── Companies ────────────────────────────────────────────────────────
        self.company1 = make_company(
            name='Company One',
            legal_name='Company One S.L.',
            tax_id='ESA12345678',
        )
        self.company2 = make_company(
            name='Company Two',
            legal_name='Company Two S.L.',
            tax_id='ESB87654321',
        )

        # ── Admin (global, no company membership required by business logic) ─
        self.admin_user = make_user(
            email='admin@test.com',
            username='ADMIN',
            surname='ADMINUSER',
            dni='ADMIN001',
            password=self.DEFAULT_PASSWORD,
            is_admin=True,
            must_change_password=False,
        )

        # ── Manager (company1) ───────────────────────────────────────────────
        self.manager_user = make_user(
            email='manager@test.com',
            username='MANAGER',
            surname='MANAGERUSER',
            dni='MANAGER01',
            password=self.DEFAULT_PASSWORD,
            must_change_password=False,
        )
        self.manager_membership = make_membership(
            self.manager_user, self.company1,
            role=UserCompany.RoleChoices.MANAGER,
        )

        # ── Employee (company1) ──────────────────────────────────────────────
        self.employee_user = make_user(
            email='employee@test.com',
            username='EMPLOYEE',
            surname='EMPLOYEEUSER',
            dni='EMPLOY01',
            password=self.DEFAULT_PASSWORD,
            must_change_password=False,
        )
        self.employee_membership = make_membership(
            self.employee_user, self.company1,
            role=UserCompany.RoleChoices.EMPLOYEE,
        )

        # ── Auditor (no company membership) ─────────────────────────────────
        self.auditor_user = make_user(
            email='auditor@test.com',
            username='AUDITOR',
            surname='AUDITORUSER',
            dni='AUDIT001',
            password=self.DEFAULT_PASSWORD,
            is_auditor=True,
            must_change_password=False,
        )

    # ── Auth helpers ─────────────────────────────────────────────────────────

    def login(self, user, set_company=True):
        """
        Force-login a user and optionally set company_id in session.
        Uses force_login so password hashing is not involved.
        """
        self.client.force_login(user)
        if set_company:
            # Grab first active membership for this user
            membership = UserCompany.objects.filter(user=user).first()
            if membership:
                session = self.client.session
                session['company_id'] = str(membership.company.id)
                session.save()

    def login_with_credentials(self, email, password):
        """POST to login view with real credentials (tests the full auth flow)."""
        return self.client.post('/', {'email': email, 'password': password})

    # ── Assertion helpers ────────────────────────────────────────────────────

    def assert_status(self, response, expected_status, msg=None):
        """Assert HTTP response status code."""
        self.assertEqual(
            response.status_code,
            expected_status,
            msg or f'Expected {expected_status}, got {response.status_code}',
        )

    def assert_redirects_to(self, response, url_name):
        """Assert response redirects to a named URL."""
        from django.urls import reverse
        self.assertRedirects(response, reverse(url_name), fetch_redirect_response=False)

    def assert_json_ok(self, response):
        """Assert response is JSON with status 200."""
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    # ── Factory shortcuts (for tests that need extra users/companies) ────────

    def make_company(self, **kwargs):
        return make_company(**kwargs)

    def make_user(self, **kwargs):
        kwargs.setdefault('password', self.DEFAULT_PASSWORD)
        return make_user(**kwargs)

    def make_membership(self, user, company, role=UserCompany.RoleChoices.EMPLOYEE):
        return make_membership(user, company, role=role)

    def make_user_with_company(self, role=UserCompany.RoleChoices.EMPLOYEE, **user_kwargs):
        user_kwargs.setdefault('password', self.DEFAULT_PASSWORD)
        return make_user_with_company(role=role, **user_kwargs)