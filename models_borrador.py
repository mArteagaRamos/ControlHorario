from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class Users(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'active'
        INACTIVE = 'inactive'
        SUSPENDED = 'suspended'

    id = models.UUIDField(primary_key=True)
    username = models.CharField(max_length=50)
    email = models.CharField(max_length=100, unique=True)
    surname = models.CharField(max_length=100)
    is_admin = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    date_joined = models.DateTimeField(default=timezone.now)
    password_hash = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'users'


class Companies(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    legal_name = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'companies'


class UserCompanyMembership(models.Model):
    class RoleChoices(models.TextChoices):
        MANAGER = 'manager'
        EMPLOYEE = 'employee'

    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.EMPLOYEE)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'user_company_membership'
        unique_together = (('user', 'company'),)


class CompanySettings(models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    work_start = models.TimeField(default='08:00:00')
    work_end = models.TimeField(default='15:00:00')
    max_tolerance = models.DurationField(default='00:15:00')
    auto_close_hours = models.IntegerField(default=12)
    weekend_days = ArrayField(models.IntegerField(), default=list, blank=True)
    holidays = ArrayField(models.DateField(), default=list, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'company_settings'


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


class CorrectionRequests(models.Model):
    class CorrectionStatus(models.TextChoices):
        PENDING = 'pending'
        APPROVED = 'approved'
        REJECTED = 'rejected'

    id = models.UUIDField(primary_key=True)
    time_entry = models.ForeignKey(TimeEntries, on_delete=models.CASCADE, db_column='time_entry_id')
    requester = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='requester_id')
    request_date = models.DateTimeField(default=timezone.now)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=CorrectionStatus.choices, default=CorrectionStatus.PENDING)
    approver = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='correctionrequests_approver_set', db_column='approver_id', blank=True, null=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    correction_note = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'correction_requests'


class AuditLog(models.Model):
    class AuditAction(models.TextChoices):
        CREATE = 'create'
        UPDATE = 'update'
        VOIDED = 'voided'
        MANUAL_CORRECTION = 'manual_correction'

    id = models.UUIDField(primary_key=True)
    table_name = models.CharField(max_length=50)
    record_id = models.UUIDField()
    actor = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='actor_id', blank=True, null=True)
    action_type = models.CharField(max_length=20, choices=AuditAction.choices)
    before = models.JSONField(blank=True, null=True)
    after = models.JSONField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'audit_log'