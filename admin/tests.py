from users.tests.conftest import BaseTestCase, make_user, make_company, make_membership


# ============================================
# Access control (admin_only_required)
# ============================================

class AdminAccessTest(BaseTestCase):
    """
    Tests for `admin_only_required` decorator that protects all admin views.
    This is the central access control of the app.
    """

    def test_admin_dashboard_requires_admin_role(self):
        """
        Verifies that a non-admin user (manager) receives 403
        when trying to access a view protected by @admin_only_required
        """
        # Login as manager (non-admin)
        self.login(self.manager_user)

        # Try accessing the admin dashboard
        response = self.client.get('/admin/')

        # Should receive 403 Forbidden
        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_accessible_by_admin(self):
        """
        Verifies that an admin user can access correctly (200)
        the admin dashboard
        """
        # Login as admin
        self.login(self.admin_user)

        # Access the admin dashboard
        response = self.client.get('/admin/')

        # Should receive 200 OK
        self.assertEqual(response.status_code, 200)


# ============================================
# Cascade soft-delete (delete_company)
# ============================================

class DeleteCompanyTest(BaseTestCase):
    """
    Tests for cascade deletion of companies.
    Verifies that delete_company correctly soft-deletes memberships
    and suspends users who have no other active company.
    """

    def test_delete_company_soft_deletes_memberships(self):
        """
        Verifies that when deleting a company, all its memberships
        are marked with deleted_at != null
        """
        # Login as admin and delete company1
        # company1 already has manager_user and employee_user by default in setUp
        self.login(self.admin_user)
        response = self.client.post(
            '/admin/delete-company/',
            {'company_id': str(self.company1.id)},
            follow=True
        )

        # Verify status 200 (redirects after POST)
        self.assertEqual(response.status_code, 200)

        # Use all_with_deleted() to get memberships including deleted ones
        from users.models import UserCompany
        all_memberships = UserCompany.objects.all_with_deleted().filter(company=self.company1)
        active_memberships = all_memberships.filter(deleted_at__isnull=True)
        deleted_memberships = all_memberships.filter(deleted_at__isnull=False)

        # Verify that all company1 memberships are soft-deleted
        self.assertEqual(active_memberships.count(), 0)

        # Verify that there are deleted memberships
        self.assertGreater(deleted_memberships.count(), 0)

    def test_delete_company_suspends_users_with_no_other_membership(self):
        """
        Verifies that a user whose only company is deleted
        is set to status='suspended'
        """
        # Create user only in company1 (without other membership)
        user_only_company1 = self.make_user(
            email='onlycompany1@test.com',
            username='ONLYCOMP1',
            dni='ONLY0001'
        )
        self.make_membership(user_only_company1, self.company1, role='employee')

        # Login as admin and delete company1
        self.login(self.admin_user)
        self.client.post(
            '/admin/delete-company/',
            {'company_id': str(self.company1.id)}
        )

        # Refresh user from DB
        user_only_company1.refresh_from_db()

        # Verify that the user is suspended
        self.assertEqual(user_only_company1.status, 'suspended')

    def test_delete_company_does_not_suspend_user_with_other_membership(self):
        """
        Verifies that a user with another active company maintains
        status='active' even if one of their companies is deleted
        """
        # Create user in company1 AND company2
        user_two_companies = self.make_user(
            email='twocompanies@test.com',
            username='TWOCOMP',
            dni='TWO00001'
        )
        self.make_membership(user_two_companies, self.company1, role='employee')
        self.make_membership(user_two_companies, self.company2, role='employee')

        # Verify that the user is active
        user_two_companies.refresh_from_db()
        self.assertEqual(user_two_companies.status, 'active')

        # Login as admin and delete company1
        self.login(self.admin_user)
        self.client.post(
            '/admin/delete-company/',
            {'company_id': str(self.company1.id)}
        )

        # Refresh user from DB
        user_two_companies.refresh_from_db()

        # Verify that the user is still active (has company2)
        self.assertEqual(user_two_companies.status, 'active')


# ============================================
# Conditional restore (restore_record)
# ============================================

class RestoreRecordTest(BaseTestCase):
    """
    Tests for conditional restoration of deleted records.
    Verifies that restore_record correctly handles membership restoration
    and reactivation of suspended users.
    """

    def test_restore_membership_reactivates_suspended_user(self):
        """
        Verifies that restoring a membership reactivates a suspended user
        who has active memberships after the restoration
        """
        from users.models import UserCompany
        from django.utils import timezone

        # Create user with 2 memberships
        user_test = self.make_user(
            email='suspendtest@test.com',
            username='SUSPTEST',
            dni='SUSP0001'
        )
        membership1 = self.make_membership(user_test, self.company1, role='employee')
        membership2 = self.make_membership(user_test, self.company2, role='employee')

        # Suspend the user manually
        user_test.status = 'suspended'
        user_test.save(update_fields=['status'])

        # Soft-delete the first membership manually
        membership1.deleted_at = timezone.now()
        membership1.save(update_fields=['deleted_at'])

        # Verify previous state
        user_test.refresh_from_db()
        self.assertEqual(user_test.status, 'suspended')

        # Restore the membership (company1 is NOT deleted, only the membership)
        self.login(self.admin_user)
        response = self.client.post(
            '/admin/restore/',
            {
                'record_type': 'user_companies',
                'record_id': str(membership1.id)
            },
            follow=True
        )

        # Refresh and verify
        user_test.refresh_from_db()
        membership1.refresh_from_db()

        # Verify that the membership was restored
        self.assertIsNone(membership1.deleted_at)

        # Verify that the user was reactivated (has active memberships)
        self.assertEqual(user_test.status, 'active')

    def test_restore_membership_blocked_if_company_is_deleted(self):
        """
        Verifies that a membership cannot be restored if its company
        is soft-deleted. Should show an error.
        """
        from users.models import UserCompany
        from django.utils import timezone

        # Create user in company1
        user_test = self.make_user(
            email='blockedrestore@test.com',
            username='BLOCKED',
            dni='BLOCK0001'
        )
        membership = self.make_membership(user_test, self.company1, role='employee')

        # Login as admin and delete company1
        self.login(self.admin_user)
        self.client.post(
            '/admin/delete-company/',
            {'company_id': str(self.company1.id)}
        )

        # Try to restore the membership (should fail because company1 is deleted)
        response = self.client.post(
            '/admin/restore/',
            {
                'record_type': 'user_companies',
                'record_id': str(membership.id)
            },
            follow=True
        )

        # Verify that the response redirects to deleted-records
        self.assertIn('deleted-records', response.request['PATH_INFO'])

        # Verify that the membership is still deleted
        membership.refresh_from_db()
        self.assertIsNotNone(membership.deleted_at)
