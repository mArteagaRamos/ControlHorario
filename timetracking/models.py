# ---------- Backend Models: timetracking/models.py ----------

from django.db import models
from users.models import Users, Companies
from django.utils import timezone

# Time entry models
class TimeEntries(models.Model):
    class EntryStatus(models.TextChoices):
        ONGOING = 'ongoing'
        CONFIRMED = 'confirmed'
        AUTO_CLOSED = 'auto_closed'
        CORRECTED = 'corrected'
        VOIDED = 'voided'

    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    date = models.DateField(default=timezone.now)
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=EntryStatus.choices, default=EntryStatus.ONGOING)
    notes = models.TextField(blank=True, null=True)
    total_seconds = models.IntegerField(default=0)

    # Cambiar formato y calculo (llamar a este metodo)
    @property
    def total_seconds_display(self):
        if not self.total_seconds:
            return '--'
        h = self.total_seconds // 3600
        m = (self.total_seconds % 3600) // 60
        s = self.total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    class Meta:
        managed = False
        db_table = 'time_entries'


class TimeEntryEvent(models.Model):
    class EventType(models.TextChoices):
        CLOCK_IN = 'clock_in'
        CLOCK_OUT = 'clock_out'
        PAUSE_START = 'pause_start'
        PAUSE_END = 'pause_end'
        MANUAL_ADJUST = 'manual_adjust'
        REOPEN = 'reopen'
        AUTO_CLOSE = 'auto_close'

    id = models.UUIDField(primary_key=True)
    time_entry = models.ForeignKey(TimeEntries, on_delete=models.CASCADE, db_column='time_entry_id')
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    timestamp = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='actor_id', blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'time_entry_event'

# (End of timetracking models)