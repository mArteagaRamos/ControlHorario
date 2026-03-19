from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
import uuid

class UsersManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

class Users(AbstractBaseUser):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'active'
        INACTIVE = 'inactive'
        SUSPENDED = 'suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, unique=True)
    surname = models.CharField(max_length=100)
    is_admin = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    date_joined = models.DateTimeField(default=timezone.now)
    password = models.CharField(db_column='password_hash', max_length=255)

    objects = UsersManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.email


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

class CorrectionRequests(models.Model):
    class CorrectionStatus(models.TextChoices):
        PENDING = 'pending'
        APPROVED = 'approved'
        REJECTED = 'rejected'

    id = models.UUIDField(primary_key=True)
    time_entry = models.ForeignKey('timetracking.TimeEntries', on_delete=models.CASCADE, db_column='time_entry_id')
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