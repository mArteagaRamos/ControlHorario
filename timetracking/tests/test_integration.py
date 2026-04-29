"""
Tests de integración para flujos completos
"""
from django.utils import timezone
from uuid import uuid4
import datetime

from timetracking.models import TimeEntries, TimeEntryEvent
from .fixtures import TimeTrackingTestBase


# ========================================================================
# INTEGRATION TESTS
# ========================================================================

class TimeTrackingIntegrationTest(TimeTrackingTestBase):
    """Integration tests for complete workflows"""
    
    def test_complete_work_day_workflow(self):
        """Test a complete work day: clock-in -> pause -> clock-out"""
        # Clock-in
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        clock_in_event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.CLOCK_IN,
            timestamp=timezone.now(),
            actor=self.user
        )
        
        # Pause start (after some work)
        pause_start_time = timezone.now() + datetime.timedelta(hours=2)
        pause_start_event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_START,
            timestamp=pause_start_time,
            actor=self.user
        )
        
        # Pause end (after lunch)
        pause_end_time = pause_start_time + datetime.timedelta(minutes=60)
        pause_end_event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_END,
            timestamp=pause_end_time,
            actor=self.user
        )
        
        # Clock-out
        clock_out_time = pause_end_time + datetime.timedelta(hours=4)
        entry.clock_out = clock_out_time
        entry.status = TimeEntries.EntryStatus.CONFIRMED
        entry.total_seconds = (clock_out_time - entry.clock_in).total_seconds() - 3600  # minus 1 hour pause
        entry.save()
        
        clock_out_event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.CLOCK_OUT,
            timestamp=clock_out_time,
            actor=self.user
        )
        
        # Verify workflow
        self.assertEqual(entry.status, TimeEntries.EntryStatus.CONFIRMED)
        self.assertIsNotNone(entry.clock_out)
        self.assertGreater(entry.total_seconds, 0)
        
        events = TimeEntryEvent.objects.filter(time_entry=entry).order_by('timestamp')
        self.assertEqual(events.count(), 4)  # clock-in, pause-start, pause-end, clock-out
    
    def test_multiple_entries_per_user(self):
        """Test that user can have multiple time entries (different days)"""
        # Create entry for today
        entry1 = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.CONFIRMED,
            clock_out=timezone.now() + datetime.timedelta(hours=8),
            total_seconds=28800
        )
        
        # Create entry for yesterday
        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        entry2 = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=yesterday,
            clock_in=timezone.now() - datetime.timedelta(days=1),
            status=TimeEntries.EntryStatus.CONFIRMED,
            clock_out=timezone.now() - datetime.timedelta(days=1, hours=-8),
            total_seconds=28800
        )
        
        # Verify both entries exist
        entries = TimeEntries.objects.filter(user=self.user).order_by('-date')
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries[0].date, timezone.localdate())
        self.assertEqual(entries[1].date, yesterday)
