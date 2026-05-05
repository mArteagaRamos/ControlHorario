"""
Fixtures y base classes para los tests de timetracking
"""
from django.test import TestCase, Client, TransactionTestCase
from uuid import uuid4

from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users

# Crear una clase Company mínima si no existe
try:
    from users.models import Companies
    HAS_COMPANIES = True
except ImportError:
    HAS_COMPANIES = False


class TimeTrackingTestBase(TestCase):
    """Base test class con setup común para timetracking tests"""
    
    def setUp(self):
        """Create test data for each test"""
        # Create custom Users entry (Users es el modelo de usuario personalizado)
        self.user = Users.objects.create_user(
            email='testuser@example.com',
            username='testuser',
            dni='12345678A',
            password='testpass123'
        )
        self.user.status = Users.StatusChoices.ACTIVE
        self.user.is_auditor = False
        self.user.save()
        
        # Create a company
        from users.models import Companies, UserCompany
        self.company = Companies.objects.create(
            id=uuid4(),
            name='Test Company',
            legal_name='Test Company Legal',
            tax_id='A12345678'
        )
        
        # Create UserCompany relationship
        self.user_company = UserCompany.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )
        
        # Create test client and set up session
        self.client = Client()
