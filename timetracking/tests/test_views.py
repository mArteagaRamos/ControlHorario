"""
Tests para las vistas de timetracking
"""
from django.utils import timezone
from uuid import uuid4
import datetime
from django.urls import reverse
from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users
from .fixtures import TimeTrackingTestBase


# ========================================================================
# VIEW TESTS: Clock-in / Clock-out / Pause functionality
# ========================================================================

class TimeTrackingViewsTest(TimeTrackingTestBase):
    """Test cases for timetracking views"""
    
    def test_clock_in_successful(self):
        """Test successful clock-in action"""
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post(reverse('home_timetracking'), {
            'action': 'clock_in'
        }, HTTP_X_FORWARDED_FOR='127.0.0.1')
        
        # Check that entry was created
        entry = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.ONGOING
        ).first()
        
        self.assertIsNotNone(entry)
        self.assertIsNotNone(entry.clock_in)
        self.assertIsNone(entry.clock_out)
    
    def test_cannot_clock_in_twice(self):
        """Test that user cannot have two concurrent clock-in entries"""
        # Create first ongoing entry
        TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post('/timetracking/time_entries/', {
            'action': 'clock_in'
        })
        
        # Count ongoing entries
        ongoing_count = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.ONGOING
        ).count()
        
        # Should still be only 1
        self.assertEqual(ongoing_count, 1)
    
    def test_clock_out_successful(self):
        """Test successful clock-out action"""
        # First, clock in to create an entry
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post(reverse('home_timetracking'), {
            'action': 'clock_in'
        }, follow=True)
        
        # Get the created entry
        entry = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.ONGOING
        ).first()
        
        self.assertIsNotNone(entry)
        
        # Wait a bit to ensure elapsed time > 0
        import time
        time.sleep(1)  # Sleep for 1 second to ensure time difference
        
        # Now clock out
        response = self.client.post(reverse('time_entries'), {
            'action': 'clock_out'
        }, follow=True)
        
        # Refresh entry from database
        entry.refresh_from_db()
        
        # Check that clock-out was set
        self.assertIsNotNone(entry.clock_out)
        self.assertEqual(entry.status, TimeEntries.EntryStatus.CONFIRMED)
        self.assertGreater(entry.total_seconds, 0)
    
    def test_clock_out_without_active_entry(self):
        """Test that clock-out without active entry shows error"""
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post('/timetracking/time_entries/', {
            'action': 'clock_out'
        })
        
        # Should show error message
        # (Check via messages in response or check no new entry created)
        entry_exists = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.CONFIRMED
        ).exists()
        
        self.assertFalse(entry_exists)
    
    def test_pause_start_successful(self):
        """Test successful pause start"""
        # First, clock in to create an entry
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post(reverse('home_timetracking'), {
            'action': 'clock_in'
        }, follow=True)
        
        # Get the created entry
        entry = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.ONGOING
        ).first()
        
        self.assertIsNotNone(entry)
        
        # Now start pause
        response = self.client.post(reverse('time_entries'), {
            'action': 'pause_start'
        }, follow=True)
        
        # Check that pause event was created
        pause_event = TimeEntryEvent.objects.filter(
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_START
        ).first()
        
        self.assertIsNotNone(pause_event)
    
    def test_cannot_start_pause_twice(self):
        """Test that pause cannot be started twice without ending"""
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        # Create first pause start event
        TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_START,
            timestamp=timezone.now(),
            actor=self.user
        )
        
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post('/timetracking/time_entries/', {
            'action': 'pause_start'
        })
        
        # Count pause start events
        pause_count = TimeEntryEvent.objects.filter(
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_START
        ).count()
        
        # Should still be only 1
        self.assertEqual(pause_count, 1)
    
    def test_pause_end_successful(self):
        """Test successful pause end"""
        # First, clock in to create an entry
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post(reverse('home_timetracking'), {
            'action': 'clock_in'
        }, follow=True)
        
        # Get the created entry
        entry = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.ONGOING
        ).first()
        
        self.assertIsNotNone(entry)
        
        # Start pause
        response = self.client.post(reverse('time_entries'), {
            'action': 'pause_start'
        }, follow=True)
        
        # End pause
        response = self.client.post(reverse('time_entries'), {
            'action': 'pause_end'
        }, follow=True)
        
        # Check that pause end event was created
        pause_end_event = TimeEntryEvent.objects.filter(
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_END
        ).first()
        
        self.assertIsNotNone(pause_end_event)
    
    def test_pause_end_without_active_pause(self):
        """Test that pause end without active pause shows error"""
        entry = TimeEntries.objects.create(
            id=uuid4(),
            user=self.user,
            company=self.company,
            date=timezone.localdate(),
            clock_in=timezone.now(),
            status=TimeEntries.EntryStatus.ONGOING
        )
        
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post('/timetracking/time_entries/', {
            'action': 'pause_end'
        })
        
        # Should not create pause end event
        pause_end_event = TimeEntryEvent.objects.filter(
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.PAUSE_END
        ).exists()
        
        self.assertFalse(pause_end_event)
    
    def test_inactive_user_cannot_clock_in(self):
        """Test that inactive user cannot clock in"""
        # Set user as inactive
        self.user.status = Users.StatusChoices.INACTIVE
        self.user.save()
        
        self.client.login(username='testuser@example.com', password='testpass123')
        
        response = self.client.post('/timetracking/time_entries/', {
            'action': 'clock_in'
        })
        
        # Should not create entry
        entry_exists = TimeEntries.objects.filter(
            user=self.user,
            status=TimeEntries.EntryStatus.ONGOING
        ).exists()
        
        self.assertFalse(entry_exists)
