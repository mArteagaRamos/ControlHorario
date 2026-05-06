"""
Tests para los modelos CorrectionRequests y LeaveRequest
"""
from django.utils import timezone
from uuid import uuid4
import datetime

from requests.models import CorrectionRequests, LeaveRequest
from timetracking.models import TimeEntries
from .fixtures import RequestsTestBase


# ========================================================================
# MODEL TESTS: CorrectionRequests
# ========================================================================

class CorrectionRequestsModelTest(RequestsTestBase):
    """Test cases for CorrectionRequests model"""
    
    def test_create_correction_request(self):
        """Test creating a basic correction request"""
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Clock-in time was incorrect',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        self.assertIsNotNone(correction.id)
        self.assertEqual(correction.requester, self.user)
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.PENDING)
        self.assertIsNone(correction.approver)
        self.assertIsNone(correction.approval_date)
    
    def test_correction_request_status_choices(self):
        """Test all valid status choices"""
        statuses = [
            CorrectionRequests.CorrectionStatus.PENDING,
            CorrectionRequests.CorrectionStatus.APPROVED,
            CorrectionRequests.CorrectionStatus.REJECTED
        ]
        
        for status in statuses:
            correction = CorrectionRequests.objects.create(
                id=uuid4(),
                time_entry=self.time_entry,
                requester=self.user,
                request_date=timezone.now(),
                reason='Test reason',
                new_clock_in=timezone.now(),
                new_clock_out=timezone.now() + datetime.timedelta(hours=8),
                status=status
            )
            self.assertEqual(correction.status, status)
    
    def test_approve_correction_request(self):
        """Test approving a correction request"""
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Correction needed',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Approve the correction
        correction.status = CorrectionRequests.CorrectionStatus.APPROVED
        correction.approver = self.manager
        correction.approval_date = timezone.now()
        correction.correction_note = 'Approved after verification'
        correction.save()
        
        correction.refresh_from_db()
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.APPROVED)
        self.assertEqual(correction.approver, self.manager)
        self.assertIsNotNone(correction.approval_date)
    
    def test_reject_correction_request(self):
        """Test rejecting a correction request"""
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Correction needed',
            new_clock_in=timezone.now(),
            new_clock_out=timezone.now() + datetime.timedelta(hours=8),
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Reject the correction
        correction.status = CorrectionRequests.CorrectionStatus.REJECTED
        correction.approver = self.manager
        correction.approval_date = timezone.now()
        correction.correction_note = 'Cannot verify this correction'
        correction.save()
        
        correction.refresh_from_db()
        self.assertEqual(correction.status, CorrectionRequests.CorrectionStatus.REJECTED)
        self.assertEqual(correction.approver, self.manager)


# ========================================================================
# MODEL TESTS: LeaveRequest
# ========================================================================

class LeaveRequestModelTest(RequestsTestBase):
    """Test cases for LeaveRequest model"""
    
    def test_create_leave_request(self):
        """Test creating a basic leave request"""
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.VACATION,
            leave_reason=LeaveRequest.LeaveReason.ANNUAL,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + datetime.timedelta(days=5),
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        self.assertIsNotNone(leave.id)
        self.assertEqual(leave.user, self.user)
        self.assertEqual(leave.status, LeaveRequest.LeaveStatus.PENDING)
        self.assertIsNone(leave.reviewed_by)
        self.assertIsNone(leave.reviewed_at)
    
    def test_leave_request_status_choices(self):
        """Test all valid leave status choices"""
        statuses = [
            LeaveRequest.LeaveStatus.PENDING,
            LeaveRequest.LeaveStatus.APPROVED,
            LeaveRequest.LeaveStatus.REJECTED,
            LeaveRequest.LeaveStatus.CANCELED
        ]
        
        for status in statuses:
            leave = LeaveRequest.objects.create(
                id=uuid4(),
                user=self.user,
                company=self.company,
                leave_type=LeaveRequest.LeaveType.ABSENCE,
                leave_reason=LeaveRequest.LeaveReason.SICK,
                start_date=timezone.localdate(),
                end_date=timezone.localdate() + datetime.timedelta(days=1),
                status=status
            )
            self.assertEqual(leave.status, status)
    
    def test_leave_reason_choices(self):
        """Test all valid leave reason choices"""
        reasons = [
            LeaveRequest.LeaveReason.ANNUAL,
            LeaveRequest.LeaveReason.SICK,
            LeaveRequest.LeaveReason.MATERNITY,
            LeaveRequest.LeaveReason.WEDDING,
            LeaveRequest.LeaveReason.BEREAVEMENT,
            LeaveRequest.LeaveReason.MEDICAL_APPOINTMENT,
            LeaveRequest.LeaveReason.LEGAL_DUTY,
            LeaveRequest.LeaveReason.PERSONAL,
            LeaveRequest.LeaveReason.OTHER
        ]
        
        for reason in reasons:
            leave = LeaveRequest.objects.create(
                id=uuid4(),
                user=self.user,
                company=self.company,
                leave_type=LeaveRequest.LeaveType.ABSENCE,
                leave_reason=reason,
                start_date=timezone.localdate(),
                end_date=timezone.localdate() + datetime.timedelta(days=1),
                status=LeaveRequest.LeaveStatus.PENDING
            )
            self.assertEqual(leave.leave_reason, reason)
    
    def test_leave_request_with_reason_note(self):
        """Test creating a leave request with reason note"""
        reason_note = 'Dentist appointment in the morning'
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.ABSENCE,
            leave_reason=LeaveRequest.LeaveReason.MEDICAL_APPOINTMENT,
            reason_note=reason_note,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        self.assertEqual(leave.reason_note, reason_note)
    
    def test_approve_leave_request(self):
        """Test approving a leave request"""
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.VACATION,
            leave_reason=LeaveRequest.LeaveReason.ANNUAL,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + datetime.timedelta(days=5),
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        # Approve the leave
        leave.status = LeaveRequest.LeaveStatus.APPROVED
        leave.reviewed_by = self.manager
        leave.reviewed_at = timezone.now()
        leave.review_note = 'Approved'
        leave.save()
        
        leave.refresh_from_db()
        self.assertEqual(leave.status, LeaveRequest.LeaveStatus.APPROVED)
        self.assertEqual(leave.reviewed_by, self.manager)
        self.assertIsNotNone(leave.reviewed_at)
