"""
Tests de integración para requests
"""
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from uuid import uuid4
import datetime

from requests.models import CorrectionRequests, LeaveRequest
from timetracking.models import TimeEntries
from .fixtures import RequestsTestBase


# ========================================================================
# INTEGRATION TESTS
# ========================================================================

class RequestsIntegrationTest(RequestsTestBase):
    """Test complete workflows and integrations"""
    
    def test_complete_correction_workflow(self):
        """Test complete correction request workflow"""
        # 1. User creates a time entry (already in setUp)
        initial_entries = TimeEntries.objects.filter(user=self.user).count()
        
        # 2. User requests a correction
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Incorrect clock-in time',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.PENDING)
        
        # 3. Manager aprueba la corrección
        # force_login evita problemas con backends de autenticación y USERNAME_FIELD
        self.client.force_login(self.manager) 

        # Imprimimos la URL para estar 100% seguros de que es la que toca
        url = reverse('resolver_incidencia')
        print(f"\nDEBUG: Llamando a URL: {url}")

        response = self.client.post(url, {
            'incidencia_id': str(correction.id),
            'accion': 'aceptar',
            'nota_resolucion': 'Verified and approved'
        }, follow=True)

        # 4. Verificar si hubo redirección al login (que daría un 401/403 camuflado)
        if response.status_code != 200:
            print(f"DEBUG: Error detectado. Status: {response.status_code}")
            # Esto te mostrará si la vista te está escupiendo algún error de permiso
            print(f"DEBUG: Contenido: {response.content.decode()[:200]}")

        self.assertEqual(response.status_code, 200)
        # Original entry should be marked as corrected
        self.time_entry.refresh_from_db()
        self.assertEqual(self.time_entry.status, TimeEntries.EntryStatus.CORRECTED)
        
        # New entry should exist
        new_entries = TimeEntries.objects.filter(user=self.user).count()
        self.assertEqual(new_entries, initial_entries + 1)
    
    def test_complete_leave_request_workflow(self):
        """Test complete leave request workflow from creation to approval"""
        start_date = timezone.localdate()
        end_date = start_date + datetime.timedelta(days=5)
        
        # 1. User creates leave request
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.VACATION,
            leave_reason=LeaveRequest.LeaveReason.ANNUAL,
            reason_note='Summer vacation',
            start_date=start_date,
            end_date=end_date,
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        self.assertEqual(leave.status, LeaveRequest.LeaveStatus.PENDING)
        self.assertIsNone(leave.reviewed_by)
        
        # 2. Manager reviews and approves
        leave.status = LeaveRequest.LeaveStatus.APPROVED
        leave.reviewed_by = self.manager
        leave.reviewed_at = timezone.now()
        leave.review_note = 'Approved'
        leave.save()
        
        # 3. Verify final state
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.LeaveStatus.APPROVED)
        self.assertEqual(leave.reviewed_by, self.manager)
        self.assertIsNotNone(leave.reviewed_at)
    
    def test_multiple_corrections_per_user(self):
        """Test user can have multiple correction requests"""
        # Create second time entry
        time_entry_2 = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate() + datetime.timedelta(days=1),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        # Create multiple correction requests
        correction_1 = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='First correction',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        correction_2 = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=time_entry_2,
            requester=self.user,
            request_date=timezone.now(),
            reason='Second correction',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Both should exist
        user_corrections = CorrectionRequests.objects.filter(requester=self.user)
        self.assertEqual(user_corrections.count(), 2)
        
        # Approve first one
        correction_1.status = CorrectionRequests.CorrectionStatus.APPROVED
        correction_1.save()
        
        # Second one should still be pending
        correction_2.refresh_from_db()
        self.assertEqual(correction_1.status, CorrectionRequests.CorrectionStatus.APPROVED)
        self.assertEqual(correction_2.status, CorrectionRequests.CorrectionStatus.PENDING)
    
    def test_multiple_leaves_per_user(self):
        """Test user can have multiple leave requests"""
        # Create multiple leave requests
        leave_1 = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.VACATION,
            leave_reason=LeaveRequest.LeaveReason.ANNUAL,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + datetime.timedelta(days=5),
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        leave_2 = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.ABSENCE,
            leave_reason=LeaveRequest.LeaveReason.SICK,
            start_date=timezone.localdate() + datetime.timedelta(days=10),
            end_date=timezone.localdate() + datetime.timedelta(days=11),
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        # Both should exist
        user_leaves = LeaveRequest.objects.filter(user=self.user)
        self.assertEqual(user_leaves.count(), 2)
        
        # Approve first one
        leave_1.status = LeaveRequest.LeaveStatus.APPROVED
        leave_1.reviewed_by = self.manager
        leave_1.reviewed_at = timezone.now()
        leave_1.save()
        
        # Second one should still be pending
        leave_2.refresh_from_db()
        self.assertEqual(leave_1.status, LeaveRequest.LeaveStatus.APPROVED)
        self.assertEqual(leave_2.status, LeaveRequest.LeaveStatus.PENDING)
