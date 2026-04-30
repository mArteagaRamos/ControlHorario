"""
Tests para las vistas de corrections
"""
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from uuid import uuid4
import datetime

from corrections.models import CorrectionRequests, LeaveRequest
from timetracking.models import TimeEntries
from .fixtures import CorrectionsTestBase


# ========================================================================
# VIEW TESTS
# ========================================================================

class CorrectionsViewsTest(CorrectionsTestBase):
    """Test cases for corrections views"""
    
    def test_resolver_incidencia_approve_successful(self):
        """Test approving a correction request via view"""
        # Create a correction request
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Clock-in was wrong',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Login as manager
        client = Client()
        client.login(username='testmanager', password='managerpass123')
        
        # Submit approval
        response = client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(correction.id),
            'accion': 'aceptar',
            'nota_resolucion': 'Approved after review'
        }, follow=True)
        
        # Verify correction was approved
        correction.refresh_from_db()
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.APPROVED)
        self.assertEqual(correction.approver, self.manager)
        self.assertEqual(correction.correction_note, 'Approved after review')
    
    def test_resolver_incidencia_reject_successful(self):
        """Test rejecting a correction request via view"""
        # Create a correction request
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Clock-out was wrong',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Login as manager
        client = Client()
        client.login(username='testmanager', password='managerpass123')
        
        # Submit rejection
        response = client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(correction.id),
            'accion': 'denegar',
            'nota_resolucion': 'Cannot verify times'
        }, follow=True)
        
        # Verify correction was rejected
        correction.refresh_from_db()
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.REJECTED)
        self.assertEqual(correction.approver, self.manager)
    
    def test_resolver_incidencia_approve_creates_new_entry(self):
        """Test that approving creates a new confirmed TimeEntry"""
        new_clock_in = timezone.now()
        new_clock_out = new_clock_in + datetime.timedelta(hours=8, minutes=30)
        
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Correction needed',
            new_clock_in=new_clock_in,
            new_clock_out=new_clock_out,
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        initial_entries = TimeEntries.objects.count()
        
        # Login as manager and approve
        client = Client()
        client.login(username='testmanager', password='managerpass123')
        
        response = client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(correction.id),
            'accion': 'aceptar',
            'nota_resolucion': 'Approved'
        }, follow=True)
        
        # Verify a new entry was created
        self.assertEqual(TimeEntries.objects.count(), initial_entries + 1)
        
        # Verify the original entry is marked as corrected
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
        
        # Verify new entry has correct times
        new_entry = TimeEntries.objects.exclude(id=self.time_entry.id).first()
        self.assertEqual(new_entry.status, TimeEntries.EntryStatus.CONFIRMED)
        self.assertEqual(new_entry.clock_in, new_clock_in)
        self.assertEqual(new_entry.clock_out, new_clock_out)
    
    def test_resolver_incidencia_reject_no_new_entry(self):
        """Test that rejecting doesn't create a new TimeEntry"""
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Wrong time',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        initial_entries = TimeEntries.objects.count()
        
        # Login as manager and reject
        client = Client()
        client.login(username='testmanager', password='managerpass123')
        
        response = client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(correction.id),
            'accion': 'denegar',
            'nota_resolucion': 'Cannot verify'
        }, follow=True)
        
        # Verify no new entry was created
        self.assertEqual(TimeEntries.objects.count(), initial_entries)
        
        # Verify original entry is NOT marked as corrected
        self.time_entry.refresh_from_db()
        self.assertNotEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
    
    def test_only_manager_can_resolve(self):
        """Test that only managers can access resolver_incidencia"""
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Wrong time',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Try accessing as regular user
        client = Client()
        client.login(username='testuser', password='testpass123')
        
        response = client.post(reverse('resolver_incidencia'), {
            'incidencia_id': str(correction.id),
            'accion': 'aceptar',
            'nota_resolucion': 'Test'
        })
        
        # Should be denied or redirected
        # (The actual view returns HttpResponse("Método no permitido."))
        self.assertEqual(response.status_code, 403)
