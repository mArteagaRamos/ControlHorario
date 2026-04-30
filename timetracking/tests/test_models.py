"""
Tests para los modelos TimeEntries y TimeEntryEvent
"""
from django.utils import timezone
from uuid import uuid4
import datetime

from timetracking.models import TimeEntries, TimeEntryEvent
from .fixtures import TimeTrackingTestBase


# ========================================================================
# MODEL TESTS: TimeEntries
# ========================================================================

class TimeEntriesModelTest(TimeTrackingTestBase):
    """Test cases for TimeEntries model"""
    
    def test_create_time_entry(self):
        """Test creating a basic time entry"""
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.status, TimeEntries.EntryStatus.ONGOING)
        self.assertIsNone(entry.clock_out)
    
    def test_entry_status_choices(self):
        """Test all valid status choices"""
        statuses = [
            TimeEntries.EntryStatus.ONGOING,
            TimeEntries.EntryStatus.CONFIRMED,
            TimeEntries.EntryStatus.AUTO_CLOSED,
            TimeEntries.EntryStatus.CORRECTED,
            TimeEntries.EntryStatus.VOIDED
        ]
        
        for status in statuses:
            entry = TimeEntries.objects.create(
                id=uuid4(),
                user=self.user,
                company=self.company,
                date=timezone.localdate(),
                clock_in=timezone.now(),
                status=status
            )
            self.assertEqual(entry.status, status)

# ========================================================================
# MODEL TESTS: TimeEntryEvent
# ========================================================================

class TimeEntryEventModelTest(TimeTrackingTestBase):
    """Test cases for TimeEntryEvent model"""
    
    def setUp(self):
        """Setup for TimeEntryEvent tests"""
        super().setUp()
        self.time_entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
    
    def test_create_clock_in_event(self):
        """Test creating a clock-in event"""
        event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            event_type=TimeEntryEvent.EventType.CLOCK_IN,
            timestamp=timezone.now(),
            actor=self.user
        )
        
        self.assertEqual(event.event_type, TimeEntryEvent.EventType.CLOCK_IN)
        self.assertEqual(event.time_entry, self.time_entry)
        self.assertEqual(event.actor, self.user)
    
    def test_create_clock_out_event(self):
        """Test creating a clock-out event"""
        event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            event_type=TimeEntryEvent.EventType.CLOCK_OUT,
            timestamp=timezone.now(),
            actor=self.user
        )
        
        self.assertEqual(event.event_type, TimeEntryEvent.EventType.CLOCK_OUT)
    
    def test_create_pause_events(self):
        """Test creating pause start and pause end events"""
        pause_start = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            event_type=TimeEntryEvent.EventType.PAUSE_START,
            timestamp=timezone.now(),
            actor=self.user
        )
        
        pause_end = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            event_type=TimeEntryEvent.EventType.PAUSE_END,
            timestamp=timezone.now(),
            actor=self.user
        )
        
        self.assertEqual(pause_start.event_type, TimeEntryEvent.EventType.PAUSE_START)
        self.assertEqual(pause_end.event_type, TimeEntryEvent.EventType.PAUSE_END)
    
    def test_event_with_note(self):
        """Test creating an event with a note"""
        event = TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=self.time_entry,
            event_type=TimeEntryEvent.EventType.MANUAL_ADJUST,
            timestamp=timezone.now(),
            actor=self.user,
            note='Manual adjustment for lunch break'
        )
        
        self.assertEqual(event.note, 'Manual adjustment for lunch break')

