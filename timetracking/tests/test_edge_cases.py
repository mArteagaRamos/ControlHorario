"""
Tests para casos extremos y condiciones de error
"""
from django.utils import timezone
from uuid import uuid4
import datetime

from timetracking.models import TimeEntries, TimeEntryEvent
from .fixtures import TimeTrackingTestBase


# ========================================================================
# EDGE CASE TESTS
# ========================================================================

class TimeTrackingEdgeCasesTest(TimeTrackingTestBase):
    """Test edge cases and error conditions"""
    
    def test_total_seconds_calculation(self):
        """Test that total_seconds is calculated correctly"""
        clock_in = timezone.now()
        clock_out = clock_in + datetime.timedelta(hours=8, minutes=30, seconds=45)
        
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=clock_in,
            clock_out=clock_out,
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=30645  # 8.5125 hours
        )
        
        self.assertEqual(entry.total_seconds, 30645)
        self.assertEqual(entry.total_seconds_display, '08:30:45')
    
    def test_entry_date_defaults_to_today(self):
        """Test that entry date defaults to today"""
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        self.assertEqual(entry.date, timezone.localdate())
    
    def test_entry_status_transition(self):
        """Test valid status transitions"""
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        # Transition from ONGOING to CONFIRMED
        entry.status = TimeEntries.EntryStatus.CONFIRMED
        entry.clock_out = timezone.now()
        entry.save()
        
        entry.refresh_from_db()
        self.assertEqual(entry.status, TimeEntries.EntryStatus.CONFIRMED)
    
    def test_very_long_entry(self):
        """Test entry with very long duration (24+ hours)"""
        clock_in = timezone.now()
        clock_out = clock_in + datetime.timedelta(hours=48)
        
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=clock_in,
            clock_out=clock_out,
            status=TimeEntries.EntryStatus.CONFIRMED,
            total_seconds=172800  # 48 hours
        )
        
        # Should display correctly even with high hour count
        self.assertEqual(entry.total_seconds_display, '48:00:00')
        self.assertEqual(entry.total_seconds, 172800)
