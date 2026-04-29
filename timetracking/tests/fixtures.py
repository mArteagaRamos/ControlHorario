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


class TimeTrackingTestBase(TransactionTestCase):
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
        
        # Create a company using raw SQL to bypass migration issues
        if HAS_COMPANIES:
            try:
                # Intentar crear una empresa normalmente
                from users.models import Companies
                self.company = Companies.objects.create(
                    id=uuid4(),
                    name='Test Company',
                    legal_name='Test Company Legal',
                    tax_id='A12345678'
                )
            except Exception:
                # Si falla, usar un ID ficticio
                self.company_id = uuid4()
                # Insertarlo directamente usando raw SQL
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO companies (id, name, legal_name, tax_id, created_at, updated_at, is_deleted)
                        VALUES (%s, %s, %s, %s, NOW(), NOW(), FALSE)
                        """,
                        [str(self.company_id), 'Test Company', 'Test Company Legal', 'A12345678']
                    )
                # Crear objeto mock
                class MockCompany:
                    id = self.company_id
                self.company = MockCompany()
        else:
            # Si Companies no existe, usar un UUID ficticio
            class MockCompany:
                id = uuid4()
            self.company = MockCompany()
        
        # Create test client
        self.client = Client()
