"""
Tests para casos extremos y condiciones de error en corrections
"""
from django.utils import timezone
from uuid import uuid4
import datetime

from corrections.models import CorrectionRequests, LeaveRequest
from timetracking.models import TimeEntries
from .fixtures import CorrectionsTestBase


# ========================================================================
# EDGE CASE TESTS
# ========================================================================

class CorrectionsEdgeCasesTest(CorrectionsTestBase):
    """Test edge cases and error conditions"""
    
    def test_correction_with_partial_new_times(self):
        """Test correction where only one new time is specified"""
        # Only new_clock_in is set
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Only clock-in needs correction',
            new_clock_in=timezone.now(),
            new_clock_out=None,  # Not specified
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        self.assertIsNotNone(correction.new_clock_in)
        self.assertIsNone(correction.new_clock_out)
    
    def test_correction_seconds_calculation(self):
        """Test that correction calculates seconds correctly"""
        clock_in = timezone.now()
        clock_out = clock_in + datetime.timedelta(hours=7, minutes=45, seconds=30)
        
        # Expected: 7*3600 + 45*60 + 30 = 27930 seconds
        expected_seconds = 27930
        
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Correction with specific duration',
            new_clock_in=clock_in,
            new_clock_out=clock_out,
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        # Manually calculate what the approval would create
        delta = correction.new_clock_out - correction.new_clock_in
        calculated_seconds = int(delta.total_seconds())
        
        self.assertEqual(calculated_seconds, expected_seconds)
    
    def test_leave_spanning_multiple_days(self):
        """Test leave request spanning multiple days"""
        start_date = timezone.localdate()
        end_date = start_date + datetime.timedelta(days=30)  # 31 days total
        
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.VACATION,
            leave_reason=LeaveRequest.LeaveReason.ANNUAL,
            start_date=start_date,
            end_date=end_date,
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        # Calculate duration
        duration = (leave.end_date - leave.start_date).days + 1  # +1 to include both start and end
        
        self.assertEqual(leave.start_date, start_date)
        self.assertEqual(leave.end_date, end_date)
        self.assertEqual(duration, 31)
    
    def test_leave_request_single_day(self):
        """Test leave request for a single day"""
        start_date = timezone.localdate()
        
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.ABSENCE,
            leave_reason=LeaveRequest.LeaveReason.SICK,
            start_date=start_date,
            end_date=start_date,  # Same day
            status=LeaveRequest.LeaveStatus.PENDING
        )
        
        duration = (leave.end_date - leave.start_date).days + 1
        self.assertEqual(duration, 1)
    
    def test_leave_request_with_attachment(self):
        """Test leave request with attachment path"""
        attachment_path = 'media/justificantes/sick_leave_2024.pdf'
        
        leave = LeaveRequest.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            leave_type=LeaveRequest.LeaveType.ABSENCE,
            leave_reason=LeaveRequest.LeaveReason.SICK,
            attachment_path=attachment_path,
            start_date=timezone.localdate(),
            end_date=timezone.localdate() + datetime.timedelta(days=2),
            status=LeaveRequest.LeaveStatus.PENDING,
            force_proof=True
        )
        
        self.assertEqual(leave.attachment_path, attachment_path)
        self.assertTrue(leave.force_proof)
        self.assertFalse(leave.attachment_verified)
    
    def test_correction_with_zero_duration(self):
        """Test correction where clock_in and clock_out are the same"""
        now = timezone.now()
        
        correction = CorrectionRequests.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            requester=self.user,
            request_date=timezone.now(),
            reason='Zero duration correction',
            new_clock_in=now,
            new_clock_out=now,  # Same time = 0 seconds
            status=CorrectionRequests.CorrectionStatus.PENDING
        )
        
        delta = correction.new_clock_out - correction.new_clock_in
        self.assertEqual(int(delta.total_seconds()), 0)
    
    def test_leave_with_review_timestamp(self):
        """Test that review timestamp is properly recorded"""
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
        
        # Approve
        review_time = timezone.now()
        leave.status = LeaveRequest.LeaveStatus.APPROVED
        leave.reviewed_by = self.manager
        leave.reviewed_at = review_time
        leave.save()
        
        leave.refresh_from_db()
        
        # Verify timestamps
        self.assertIsNotNone(leave.created_at)
        self.assertIsNotNone(leave.updated_at)
        self.assertEqual(leave.reviewed_at, review_time)
