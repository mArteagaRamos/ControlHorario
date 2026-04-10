# ---------- Backend Models: users/models.py ----------

from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from core.model_normalization import UppercaseNormalizationMixin
from core.managers import UsersManager, SoftDeleteManager
import uuid

class Users(UppercaseNormalizationMixin, AbstractBaseUser):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        INACTIVE = 'inactive', 'Inactivo'
        SUSPENDED = 'suspended', 'Suspendido'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, unique=True)
    surname = models.CharField(max_length=100)
    is_admin = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    date_joined = models.DateTimeField(default=timezone.now)
    password = models.CharField(db_column='password_hash', max_length=255)
    is_authenticated = models.BooleanField(default=False)
    dni = models.CharField(max_length=20, unique=True, blank=False, null=False, default='')
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    uppercase_fields = {'username', 'surname', 'email', 'dni'}
    uppercase_excluded_fields = {'password'}

    objects = UsersManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'dni']

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.username = self.username.upper().strip() if self.username else self.username
        self.surname  = self.surname.upper().strip()  if self.surname  else self.surname
        self.email    = self.email.lower().strip()    if self.email    else self.email
        self.dni      = self.dni.upper().strip()      if self.dni      else self.dni
        super().save(*args, **kwargs)

# Company / membership models section
class Companies(UppercaseNormalizationMixin, models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=100)
    legal_name = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'companies'


class UserCompany(UppercaseNormalizationMixin, models.Model):
    class RoleChoices(models.TextChoices):
        MANAGER = 'manager'
        EMPLOYEE = 'employee'

    id = models.UUIDField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id')
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.EMPLOYEE)
    joined_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'user_company'
        unique_together = (('user', 'company'),)


class CompanySettings(UppercaseNormalizationMixin, models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    work_start = models.TimeField(default='08:00:00')
    work_end = models.TimeField(default='15:00:00')
    max_tolerance = models.DurationField(default='00:15:00')
    auto_close_hours = models.IntegerField(default=12)
    weekend_days = ArrayField(models.IntegerField(), default=list, blank=True)
    holidays = ArrayField(models.DateField(), default=list, blank=True)
    updated_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'company_settings'


# Correction requests section for time corrections
class CorrectionRequests(UppercaseNormalizationMixin, models.Model):
    class CorrectionStatus(models.TextChoices):
        PENDING = 'pending'
        APPROVED = 'approved'
        REJECTED = 'rejected'

    id = models.UUIDField(primary_key=True)
    time_entry = models.ForeignKey('timetracking.TimeEntries', on_delete=models.CASCADE, db_column='time_entry_id', null=True, blank=True)
    requester = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='requester_id', null=True, blank=True)
    request_date = models.DateTimeField(default=timezone.now)
    reason = models.TextField()
    new_clock_in = models.DateTimeField(blank=True, null=True)
    new_clock_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=CorrectionStatus.choices, default=CorrectionStatus.PENDING)
    approver = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='correctionrequests_approver_set', db_column='approver_id', blank=True, null=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    correction_note = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'correction_requests'