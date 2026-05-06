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
    
    @classmethod
    def setUpTestData(cls):
        """Create shared test data for all tests (created once per test class)"""
        # Create custom Users entry (Users es el modelo de usuario personalizado)
        cls.user = Users.objects.create_user(
            email='testuser@example.com',
            username='testuser',
            dni='12345678A',
            password='testpass123'
        )
        cls.user.status = Users.StatusChoices.ACTIVE
        cls.user.is_auditor = False
        cls.user.save()
        
        # Create a company
        from users.models import Companies, UserCompany
        cls.company = Companies.objects.create(
            id=uuid4(),
            name='Test Company',
            legal_name='Test Company Legal',
            tax_id='A12345678'
        )
        
        # Create UserCompany relationship
        cls.user_company = UserCompany.objects.create(
            id=uuid4(),
            user=cls.user,
            company=cls.company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )
    
    def setUp(self):
        """Create test client for each test"""
        # Create test client
        self.client = Client()
