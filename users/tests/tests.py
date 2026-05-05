from django.test import TestCase, Client
from django.contrib.messages import get_messages
from users.tests.conftest import make_user, make_company, make_membership
from users.models import Users, UserCompany


# ============================================
# Login and authentication
# ============================================

class AuthFlowTest(TestCase):
    """
    Tests for the login flow with 3 internal steps:
    - credentials: validate email + password
    - set_password: change password if must_change_password=True
    - select_company: choose company if user has >1 membership
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = make_company(name='Auth Company', tax_id='ES00001111')
        cls.user_normal = make_user(
            email='normal@test.com',
            username='NORMAL',
            surname='NORMALUSER',
            dni='NOR00001',
            password='TestPass123!',
            must_change_password=False,
        )
        cls.user_must_change = make_user(
            email='mustchange@test.com',
            username='MUSTCHG',
            surname='MUSTCHANGEUSER',
            dni='MUST0001',
            password='TestPass123!',
            must_change_password=True,
        )
        cls.user_suspended = make_user(
            email='suspended@test.com',
            username='SUSPEND',
            surname='SUSPENDUSER',
            dni='SUSP0001',
            password='TestPass123!',
            status='suspended',
        )
        cls.user_no_membership = make_user(
            email='nomembership@test.com',
            username='NOMEMB',
            surname='NOMEMBUSER',
            dni='NOMB0001',
            password='TestPass123!',
            must_change_password=False,
        )
        make_membership(cls.user_normal, cls.company, role='employee')
        make_membership(cls.user_must_change, cls.company, role='employee')
        make_membership(cls.user_suspended, cls.company, role='employee')

    def setUp(self):
        self.client = Client()

    def test_valid_login_redirects_to_home(self):
        """
        Verifies that valid credentials with must_change_password=False
        redirect to home_timetracking with company_id in session.
        """
        response = self.client.post('/', {
            'username': 'normal@test.com',
            'password': 'TestPass123!',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('/home/', response.request['PATH_INFO'])
        self.assertIsNotNone(self.client.session.get('company_id'))

    def test_suspended_user_is_blocked(self):
        """
        Verifies that a user with status='suspended' cannot login
        even if the password is correct. Should see an error message.
        """
        response = self.client.post('/', {
            'username': 'suspended@test.com',
            'password': 'TestPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login/login.html')

        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any('suspendida' in str(m).lower() for m in messages_list),
            'Should show an error message about suspended account'
        )

    def test_user_without_active_memberships_is_blocked(self):
        """
        Verifies that a user without active memberships cannot complete
        login even if credentials are valid.
        """
        response = self.client.post('/', {
            'username': 'nomembership@test.com',
            'password': 'TestPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login/login.html')

        messages_list = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any('membresía' in str(m).lower() for m in messages_list),
            'Should show an error message about lack of memberships'
        )

    def test_must_change_password_shows_set_password_form(self):
        """
        Verifies that a user with must_change_password=True sees the password
        change form instead of being redirected to home.
        """
        response = self.client.post('/', {
            'username': 'mustchange@test.com',
            'password': 'TestPass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login/login.html')
        self.assertIn('set_password_form', response.context)
        self.assertTrue(response.context.get('show_set_password'))

    def test_set_password_completes_login_and_clears_flag(self):
        """
        Verifies that changing the password correctly:
        - Sets must_change_password=False in DB
        - Authenticates the user with the new password
        - Redirects to home_timetracking
        """
        # Step 1: Initial login (should show set_password form)
        response1 = self.client.post('/', {
            'username': 'mustchange@test.com',
            'password': 'TestPass123!',
        })
        self.assertTrue(response1.context.get('show_set_password'))

        # Step 2: Change the password
        response2 = self.client.post('/', {
            'step': 'set_password',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, follow=True)

        self.assertEqual(response2.status_code, 200)
        self.assertIn('/home/', response2.request['PATH_INFO'])

        # Step 3: Verify that the flag was cleared in DB
        self.user_must_change.refresh_from_db()
        self.assertFalse(self.user_must_change.must_change_password)

        # Step 4: Verify that can login with the new password
        self.client.logout()
        response3 = self.client.post('/', {
            'username': 'mustchange@test.com',
            'password': 'NewPass456!',
        }, follow=True)
        self.assertEqual(response3.status_code, 200)
        self.assertIn('/home/', response3.request['PATH_INFO'])


# ============================================
# Role access control
# ============================================

class RoleAccessTest(TestCase):
    """
    Tests to verify that role permissions are applied correctly:
    - Employee cannot access register_unified
    - Manager can access register_unified
    - User without membership cannot switch to company
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = make_company(name='Role Company', tax_id='ES00002222')
        cls.employee_user = make_user(
            email='employee@test.com',
            username='EMPLOYEE',
            surname='EMPLOYEEUSER',
            dni='EMP00001',
            password='TestPass123!',
            must_change_password=False,
        )
        cls.manager_user = make_user(
            email='manager@test.com',
            username='MANAGER',
            surname='MANAGERUSER',
            dni='MGR00001',
            password='TestPass123!',
            must_change_password=False,
        )
        cls.other_company = make_company(name='Other Company', tax_id='ES00009999')
        make_membership(cls.employee_user, cls.company, role='employee')
        make_membership(cls.manager_user, cls.company, role='manager')

    def setUp(self):
        self.client = Client()

    def test_register_unified_employee_gets_403(self):
        """
        Verifies that an authenticated employee cannot access register_unified.
        Should be redirected to home_timetracking with an error message.
        """
        self.client.force_login(self.employee_user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        response = self.client.get('/register/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/home/', response.url)

        messages_list = list(get_messages(response.wsgi_request)) if hasattr(response, 'wsgi_request') else []
        self.assertTrue(
            any('No tienes permisos' in str(m) for m in messages_list),
            'Should show an error message about permissions'
        )

    def test_register_unified_manager_can_access(self):
        """
        Verifies that a manager can access register_unified
        and sees the registration form.
        """
        self.client.force_login(self.manager_user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        response = self.client.get('/register/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('company_form', response.context)
        self.assertIn('worker_create', response.context)

    def test_switch_company_without_membership_fails(self):
        """
        Verifies that a user cannot switch to a company
        where they don't have membership, even if the company_id is valid.
        Should be redirected with an error message and session should not change.
        """
        self.client.force_login(self.employee_user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        # Attempts to switch to a company without membership
        response = self.client.get(f'/switch-company/{self.other_company.id}/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/home/', response.url)

        # Verifies that session didn't change (still the original company)
        self.assertEqual(str(self.client.session.get('company_id')), str(self.company.id))


# ============================================
# Critical business logic
# ============================================

class BusinessLogicTest(TestCase):
    """
    Tests to verify critical business logic:
    - Validation of manager role change
    - Soft-deleted memberships in login
    - User and membership creation in register_unified
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = make_company(name='Business Company', tax_id='ES00003333')
        cls.admin_user = make_user(
            email='admin@test.com',
            username='ADMIN',
            surname='ADMINUSER',
            dni='ADM00001',
            password='TestPass123!',
            is_admin=True,
            must_change_password=False,
        )
        cls.manager1 = make_user(
            email='manager1@test.com',
            username='MGR1',
            surname='MANAGER1USER',
            dni='MGR10001',
            password='TestPass123!',
            must_change_password=False,
        )
        cls.manager2 = make_user(
            email='manager2@test.com',
            username='MGR2',
            surname='MANAGER2USER',
            dni='MGR20001',
            password='TestPass123!',
            must_change_password=False,
        )
        cls.employee = make_user(
            email='emp@test.com',
            username='EMP',
            surname='EMPUSER',
            dni='EMP00001',
            password='TestPass123!',
            must_change_password=False,
        )
        make_membership(cls.manager1, cls.company, role='manager')
        make_membership(cls.manager2, cls.company, role='manager')
        make_membership(cls.employee, cls.company, role='employee')

    def setUp(self):
        self.client = Client()

    def test_last_manager_cannot_change_role(self):
        """
        Verifies that validate_manager_role_change blocks role change
        if they are the only manager of the company. First deletes the second manager.
        """
        from core.services import validate_manager_role_change

        # Setup: delete the second manager (soft-delete)
        membership2 = UserCompany.objects.filter(user=self.manager2, company=self.company).first()
        from django.utils import timezone
        membership2.deleted_at = timezone.now()
        membership2.save()

        # Attempt to change manager1 to employee when it's the only active manager
        is_valid, message = validate_manager_role_change(
            self.manager1,
            self.company,
            'employee'
        )

        self.assertFalse(is_valid)
        self.assertIn('único Manager', message)

    def test_manager_can_change_role_if_another_exists(self):
        """
        Verifies that validate_manager_role_change allows the change
        when another active manager exists in the company.
        """
        from core.services import validate_manager_role_change

        # Cambiar manager1 a employee cuando manager2 sigue activo
        is_valid, message = validate_manager_role_change(
            self.manager1,
            self.company,
            'employee'
        )

        self.assertTrue(is_valid)
        self.assertIsNone(message)

    def test_soft_deleted_membership_not_counted_as_active(self):
        """
        Verifies that a membership with deleted_at != null is not counted
        as active in the login flow. Tested indirectly through
        validation of active managers.
        """
        from core.services import validate_manager_role_change
        from django.utils import timezone

        # Soft-delete manager2
        membership2 = UserCompany.objects.filter(user=self.manager2, company=self.company).first()
        membership2.deleted_at = timezone.now()
        membership2.save()

        # manager1 cannot change because manager2 (although soft-deleted) is not counted
        is_valid, message = validate_manager_role_change(
            self.manager1,
            self.company,
            'employee'
        )

        self.assertFalse(is_valid)

        # Restore manager2
        membership2.deleted_at = None
        membership2.save()

        # Now it can change
        is_valid, message = validate_manager_role_change(
            self.manager1,
            self.company,
            'employee'
        )

        self.assertTrue(is_valid)

    def test_register_new_user_creates_user_and_membership(self):
        """
        Verifies that register_unified (admin) correctly processes
        a POST request for user creation: accepts parameters and processes the request.
        """
        self.client.force_login(self.admin_user)
        session = self.client.session
        session['company_id'] = str(self.company.id)
        session.save()

        initial_user_count = Users.objects.count()

        response = self.client.post('/register/', {
            'company_mode': 'select',
            'company_id': str(self.company.id),
            'worker_action': 'create',
            'is_auditor': 'off',
            'username': 'NEWUSER',
            'email': 'newuser@test.com',
            'surname': 'NEWUSERSURNAME',
            'dni': 'NEW00001',
            'status': 'active',
            'password': 'TempPass123!',
            'role': 'employee',
        })

        # Verify that it redirects (success in creation or redirection by result)
        self.assertEqual(response.status_code, 302)

        # Verify that a new user was created
        new_user_count = Users.objects.count()
        self.assertGreater(new_user_count, initial_user_count,
                          "At least one new user should have been created")


# ============================================
# Auditor flow
# ============================================

class AuditorFlowTest(TestCase):
    """
    Tests to verify auditor access flow:
    - Login redirects to audit_dashboard
    - Auditor is blocked from regular views
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = make_company(name='Audit Company', tax_id='ES00004444')
        cls.auditor_user = make_user(
            email='auditor@test.com',
            username='AUDITOR',
            surname='AUDITORUSER',
            dni='AUD00001',
            password='TestPass123!',
            is_auditor=True,
            must_change_password=False,
        )
        cls.normal_user = make_user(
            email='normaluser@test.com',
            username='NORMAL',
            surname='NORMALUSER',
            dni='NOR00001',
            password='TestPass123!',
            must_change_password=False,
        )
        make_membership(cls.auditor_user, cls.company, role='employee')
        make_membership(cls.normal_user, cls.company, role='employee')

    def setUp(self):
        self.client = Client()

    def test_auditor_login_redirects_to_audit_dashboard(self):
        """
        Verifies that an auditor logging in with must_change_password=False
        is redirected to audit_dashboard instead of home_timetracking.
        """
        response = self.client.post('/', {
            'username': 'auditor@test.com',
            'password': 'TestPass123!',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn('/audit/', response.url)

    def test_auditor_blocked_from_regular_views(self):
        """
        Verifies that a logged-in auditor receives 403 when attempting to access
        a regular view decorated with @auditor_cannot_access.
        """
        self.client.force_login(self.auditor_user)

        response = self.client.get('/calendar/')

        self.assertEqual(response.status_code, 403)


# ============================================
# Unit tests
# ============================================

class SoftDeleteManagerTest(TestCase):
    """
    Unit tests for SoftDeleteManager.
    Verifies that the manager correctly filters soft-deleted records
    and provides access to all via all_with_deleted().
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = make_company(name='SoftDelete Company', tax_id='ES00005555')
        cls.user = make_user(
            email='softdelete@test.com',
            username='SOFTDEL',
            surname='SOFTDELUSER',
            dni='SOF00001',
        )
        cls.membership = make_membership(cls.user, cls.company, role='employee')

    def test_soft_delete_manager_filters_deleted_records(self):
        """
        Verifies that:
        - get_queryset() excludes records with deleted_at != null
        - all_with_deleted() includes soft-deleted records
        - After restore, the record appears in get_queryset()
        """
        from django.utils import timezone

        # Step 1: Verify that the membership is active (deleted_at = null)
        active_count = UserCompany.objects.filter(user=self.user, company=self.company).count()
        self.assertEqual(active_count, 1, "Membership should be active")

        # Step 2: Soft-delete the membership
        self.membership.deleted_at = timezone.now()
        self.membership.save()

        # Step 3: Verify that it doesn't appear in get_queryset()
        active_count = UserCompany.objects.filter(user=self.user, company=self.company).count()
        self.assertEqual(active_count, 0, "Soft-deleted membership should not appear in get_queryset()")

        # Step 4: Verify that it appears in all_with_deleted()
        all_count = UserCompany.objects.all_with_deleted().filter(user=self.user, company=self.company).count()
        self.assertEqual(all_count, 1, "Soft-deleted membership should appear in all_with_deleted()")

        # Step 5: Restore the membership
        self.membership.deleted_at = None
        self.membership.save()

        # Step 6: Verify that it appears again in get_queryset()
        active_count = UserCompany.objects.filter(user=self.user, company=self.company).count()
        self.assertEqual(active_count, 1, "Restored membership should appear in get_queryset()")


# ============================================
# Edge cases
# ============================================

class EdgeCaseTest(TestCase):
    """
    Tests for edge cases in the authentication flow:
    - User with multiple companies (soft-delete one)
    - Concurrent login (two simultaneous sessions)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company1 = make_company(name='Edge Company 1', tax_id='ES00006666')
        cls.company2 = make_company(name='Edge Company 2', tax_id='ES00007777')
        cls.user = make_user(
            email='edgecase@test.com',
            username='EDGE',
            surname='EDGEUSER',
            dni='EDGE0001',
            password='TestPass123!',
            must_change_password=False,
        )
        make_membership(cls.user, cls.company1, role='employee')
        make_membership(cls.user, cls.company2, role='employee')

    def setUp(self):
        self.client = Client()

    def test_user_last_active_membership_deleted(self):
        """
        Verifies that when a user has 2 active companies,
        one membership is soft-deleted, and then logs in,
        they can access the other company without issues.
        """
        from django.utils import timezone

        # Step 1: Soft-delete the membership of company1
        membership1 = UserCompany.objects.filter(user=self.user, company=self.company1).first()
        membership1.deleted_at = timezone.now()
        membership1.save()

        # Step 2: Login
        response = self.client.post('/', {
            'username': 'edgecase@test.com',
            'password': 'TestPass123!',
        }, follow=True)

        # Step 3: Verify that login was successful (status 200)
        self.assertEqual(response.status_code, 200)

        # Step 4: Verify that company_id was set in session (from company2)
        self.assertIsNotNone(self.client.session.get('company_id'))
        # Should be company2 since it's the only active membership
        session_company_id = self.client.session.get('company_id')
        self.assertEqual(session_company_id, str(self.company2.id))

        # Step 5: Restore the membership for next test
        membership1.deleted_at = None
        membership1.save()

    def test_concurrent_login_session_isolation(self):
        """
        Verifies that when a user opens multiple sessions simultaneously,
        only the last one remains active. Previous sessions are invalidated
        automatically to guarantee a single session per user.
        """
        from django.contrib.auth import get_user_model

        # Step 1: Create client1 for the first session
        client1 = Client()

        # Step 2: Login in client1 (first session)
        response1 = client1.post('/', {
            'username': 'edgecase@test.com',
            'password': 'TestPass123!',
        }, follow=True)

        self.assertEqual(response1.status_code, 200)
        user1_session_id = client1.session.session_key
        user1_auth_id = client1.session.get('_auth_user_id')

        self.assertIsNotNone(user1_session_id, "Client1 should have session_key after login")
        self.assertIsNotNone(user1_auth_id, "Client1 should be authenticated")

        # Step 3: Login in client2 with the same user (second session)
        client2 = Client()
        response2 = client2.post('/', {
            'username': 'edgecase@test.com',
            'password': 'TestPass123!',
        }, follow=True)

        self.assertEqual(response2.status_code, 200)
        user2_session_id = client2.session.session_key
        user2_auth_id = client2.session.get('_auth_user_id')

        self.assertIsNotNone(user2_session_id, "Client2 should have session_key after login")
        self.assertIsNotNone(user2_auth_id, "Client2 should be authenticated")

        # Step 4: Verify that sessions have different IDs
        self.assertNotEqual(user1_session_id, user2_session_id,
                           "Both sessions should have different session_key")

        # Step 5: Verify that client1 is authenticated at this moment
        # (before it potentially gets invalidated)
        response_check1_before = client1.get('/home/')
        self.assertIn(response_check1_before.status_code, [200, 302, 404],
                     "Client1 should be able to make requests after login")

        # Step 6: Now try to make a request with client1
        # If the system implements single-session-per-user, this session should be invalid
        response_check1_after = client1.get('/home/')

        # Step 7: Verify that client1 was disconnected (redirects to login)
        self.assertEqual(response_check1_after.status_code, 302,
                        "Client1 should be redirected to login (session invalidated)")

        # Step 8: Verify that client2 is still the valid session
        user2_auth_id_check = client2.session.get('_auth_user_id')
        self.assertEqual(user2_auth_id_check, user2_auth_id,
                        "Client2 should maintain its authentication as the active session")

        # Step 9: Make a final request with client2 to confirm it's active
        response_final = client2.get('/home/')
        self.assertIn(response_final.status_code, [200, 302, 404],
                     "Client2 should be the valid and active session")
