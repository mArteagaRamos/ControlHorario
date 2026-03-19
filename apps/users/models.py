from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

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
    last_login = models.DateTimeField(default=timezone.now)

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

