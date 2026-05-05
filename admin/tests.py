from django.test import TestCase, Client
from users.tests.conftest import make_user, make_company, make_membership


# ============================================
# Access control (admin_only_required)
# ============================================

class AdminAccessTest(TestCase):
    """
    Tests for `admin_only_required` decorator that protects all admin views.
    This is the central access control of the app.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = make_user(
            email='admin@test.com',
            username='ADMIN',
            surname='ADMINUSER',
            dni='ADMIN001',
            password='TestPass123!',
            is_admin=True,
            must_change_password=False,
        )
        cls.manager_user = make_user(
            email='manager@test.com',
            username='MANAGER',
            surname='MANAGERUSER',
            dni='MANAGER01',
            password='TestPass123!',
            must_change_password=False,
        )
        cls.company1 = make_company(
            name='Company One',
            legal_name='Company One S.L.',
            tax_id='ESA12345678',
        )
        make_membership(cls.manager_user, cls.company1, role='manager')

    def setUp(self):
        self.client = Client()

    def test_admin_dashboard_requires_admin_role(self):
        """
        Verifies that a non-admin user (manager) receives 403
        when trying to access a view protected by @admin_only_required
        """
        self.client.force_login(self.manager_user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_accessible_by_admin(self):
        """
        Verifies that an admin user can access correctly (200)
        the admin dashboard
        """
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)



# ============================================
# Cascade soft-delete (delete_company)
# ============================================

class DeleteCompanyTest(TestCase):
    """
    Tests for cascade deletion of companies.
    Verifies that delete_company correctly soft-deletes memberships
    and suspends users who have no other active company.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = make_user(
            email='admin_delete@test.com',
            username='ADMIN_DEL',
            surname='ADMINUSER',
            dni='ADMIN999',
            password='TestPass123!',
            is_admin=True,
            must_change_password=False,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_delete_company_soft_deletes_memberships(self):
        """
        Verifies that when deleting a company, all its memberships
        are marked with deleted_at != null
        """
        from users.models import UserCompany

        company = make_company(name='Test Company 1', tax_id='ES00000001')
        manager = make_user(email='mgr1@test.com', username='MGR1', dni='MGR10001')
        employee = make_user(email='emp1@test.com', username='EMP1', dni='EMP10001')
        make_membership(manager, company, role='manager')
        make_membership(employee, company, role='employee')

        response = self.client.post(
            '/admin/delete-company/',
            {'company_id': str(company.id)},
            follow=True
        )

        self.assertEqual(response.status_code, 200)

        all_memberships = UserCompany.objects.all_with_deleted().filter(company=company)
        active_memberships = all_memberships.filter(deleted_at__isnull=True)
        deleted_memberships = all_memberships.filter(deleted_at__isnull=False)

        self.assertEqual(active_memberships.count(), 0)
        self.assertGreater(deleted_memberships.count(), 0)

    def test_delete_company_suspends_users_with_no_other_membership(self):
        """
        Verifies that a user whose only company is deleted
        is set to status='suspended'
        """
        company = make_company(name='Test Company 2', tax_id='ES00000002')
        user_only = make_user(
            email='onlycompany@test.com',
            username='ONLYC',
            dni='ONLY0002'
        )
        make_membership(user_only, company, role='employee')

        self.client.post(
            '/admin/delete-company/',
            {'company_id': str(company.id)}
        )

        user_only.refresh_from_db()
        self.assertEqual(user_only.status, 'suspended')

    def test_delete_company_does_not_suspend_user_with_other_membership(self):
        """
        Verifies that a user with another active company maintains
        status='active' even if one of their companies is deleted
        """
        company1 = make_company(name='Test Company 3', tax_id='ES00000003')
        company2 = make_company(name='Test Company 4', tax_id='ES00000004')
        user_multi = make_user(
            email='multicompany@test.com',
            username='MULTI',
            dni='MULT0003'
        )
        make_membership(user_multi, company1, role='employee')
        make_membership(user_multi, company2, role='employee')

        user_multi.refresh_from_db()
        self.assertEqual(user_multi.status, 'active')

        self.client.post(
            '/admin/delete-company/',
            {'company_id': str(company1.id)}
        )

        user_multi.refresh_from_db()
        self.assertEqual(user_multi.status, 'active')



# ============================================
# Conditional restore (restore_record)
# ============================================

class RestoreRecordTest(TestCase):
    """
    Tests for conditional restoration of deleted records.
    Verifies that restore_record correctly handles membership restoration
    and reactivation of suspended users.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = make_user(
            email='admin_restore@test.com',
            username='ADMIN_REST',
            surname='ADMINUSER',
            dni='ADMIN888',
            password='TestPass123!',
            is_admin=True,
            must_change_password=False,
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_restore_membership_reactivates_suspended_user(self):
        """
        Verifies that restoring a membership reactivates a suspended user
        who has active memberships after the restoration
        """
        from users.models import UserCompany
        from django.utils import timezone

        company1 = make_company(name='Test Restore 1', tax_id='ES00000005')
        company2 = make_company(name='Test Restore 2', tax_id='ES00000006')
        user = make_user(
            email='suspendtest@test.com',
            username='SUSPTEST',
            dni='SUSP0001'
        )
        membership1 = make_membership(user, company1, role='employee')
        membership2 = make_membership(user, company2, role='employee')

        user.status = 'suspended'
        user.save(update_fields=['status'])

        membership1.deleted_at = timezone.now()
        membership1.save(update_fields=['deleted_at'])

        user.refresh_from_db()
        self.assertEqual(user.status, 'suspended')

        response = self.client.post(
            '/admin/restore/',
            {
                'record_type': 'user_companies',
                'record_id': str(membership1.id)
            },
            follow=True
        )

        user.refresh_from_db()
        membership1.refresh_from_db()

        self.assertIsNone(membership1.deleted_at)
        self.assertEqual(user.status, 'active')

    def test_restore_membership_blocked_if_company_is_deleted(self):
        """
        Verifies that a membership cannot be restored if its company
        is soft-deleted. Should show an error.
        """
        from users.models import UserCompany
        from django.utils import timezone

        company = make_company(name='Test Restore 3', tax_id='ES00000007')
        user = make_user(
            email='blockedrestore@test.com',
            username='BLOCKED',
            dni='BLOCK0001'
        )
        membership = make_membership(user, company, role='employee')

        self.client.post(
            '/admin/delete-company/',
            {'company_id': str(company.id)}
        )

        response = self.client.post(
            '/admin/restore/',
            {
                'record_type': 'user_companies',
                'record_id': str(membership.id)
            },
            follow=True
        )

        self.assertIn('deleted-records', response.request['PATH_INFO'])

        membership.refresh_from_db()
        self.assertIsNotNone(membership.deleted_at)
