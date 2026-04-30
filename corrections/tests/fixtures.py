"""
Base fixtures para tests de la app corrections
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from uuid import uuid4
from users.models import Companies, UserCompany
from timetracking.models import TimeEntries

User = get_user_model()


class CorrectionsTestBase(TestCase):
    """Base class with common setup for corrections tests"""
    
    def setUp(self):
        """Create base test data"""
        # Create Django user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        
        # Create manager user for approvals
        self.manager = User.objects.create_user(
            username='testmanager',
            email='manager@example.com',
            password='managerpass123'
        )
        
        # Create company
        self.company = Companies.objects.create(
            id=uuid4(),
            name='Test Company',
            active=True
        )
        
        # Create UserCompany relationships
        UserCompany.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            role=UserCompany.RoleChoices.USER,
            active=True
        )
        
        UserCompany.objects.create(
            id=uuid4(),
            user=self.manager,
            company=self.company,
            role=UserCompany.RoleChoices.MANAGER,
            active=True
        )
        
        # Create a test time entry for correction requests
        self.time_entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        # Setup client for view tests
        self.client.login(username='testuser', password='testpass123')
