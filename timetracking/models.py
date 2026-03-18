from django.db import models
from django.contrib.postgres.fields import ArrayField


class TimeEntry(models.Model):
    class StatusChoices(models.TextChoices):
        ONGOING = 'ongoing'
        CONFIRMED = 'confirmed'
        AUTO_CLOSED = 'auto_closed'
        CORRECTED = 'corrected'

    id = models.UUIDField(primary_key=True)
    user_id = models.UUIDField()
    company_id = models.UUIDField()
    date = models.DateField()
    clock_in = models.DateTimeField()
    clock_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices,  default=StatusChoices.ONGOING)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'time_entries'

class TimeEntryEvent(models.Model):
    class EventChoices(models.TextChoices):
        ONGOING = 'ongoing'
        CONFIRMED = 'confirmed'
        AUTO_CLOSED = 'auto_closed'
        CORRECTED = 'corrected'

    id = models.AutoField(primary_key=True)
    time_entry = models.ForeignKey(TimeEntry, on_delete=models.CASCADE, db_column='time_entry_id')
    event_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey
    note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'time_entry_events'


