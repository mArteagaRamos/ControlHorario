# users/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser
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
    last_login = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=True)
    dni = models.CharField(max_length=20, unique=True, blank=False, null=False, default='')
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)
    is_auditor = models.BooleanField(default=False)

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
        # Get update_fields if specified
        update_fields = kwargs.get('update_fields')

        # Only normalize fields that will be saved
        # If update_fields is None, normalize all fields (full save)
        # If update_fields is specified, only normalize fields in that list

        if update_fields is None:
            # Full save: normalize all text fields
            self.username = self.username.upper().strip() if self.username else self.username
            self.surname  = self.surname.upper().strip()  if self.surname  else self.surname
            self.email    = self.email.lower().strip()    if self.email    else self.email
            self.dni      = self.dni.upper().strip()      if self.dni      else self.dni
        else:
            # Partial save: only normalize fields that are being updated
            if 'username' in update_fields:
                self.username = self.username.upper().strip() if self.username else self.username
            if 'surname' in update_fields:
                self.surname  = self.surname.upper().strip()  if self.surname  else self.surname
            if 'email' in update_fields:
                self.email    = self.email.lower().strip()    if self.email    else self.email
            if 'dni' in update_fields:
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


