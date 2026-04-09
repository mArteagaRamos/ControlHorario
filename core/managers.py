# ---------- Consolidated Managers: core/managers.py ----------

from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone


# ────────────────────────────────────────────────────────────────────
# SOFT DELETE MANAGER
# ────────────────────────────────────────────────────────────────────

class SoftDeleteManager(models.Manager):
    """
    Custom manager that automatically filters out deleted records.
    Provides soft-delete functionality instead of hard deletes.
    """

    def get_queryset(self):
        """Override to only return non-deleted records by default"""
        return super().get_queryset().filter(deleted_at__isnull=True)

    def all_with_deleted(self):
        """Get all records including deleted ones"""
        return super().get_queryset()

    def only_deleted(self):
        """Get only deleted records"""
        return super().get_queryset().filter(deleted_at__isnull=False)

    def restore(self, obj):
        """Restore a deleted record"""
        obj.deleted_at = None
        obj.save(update_fields=['deleted_at'])

    def hard_delete(self, obj):
        """Permanently delete a record (only for admin)"""
        super().get_queryset().model.objects.filter(pk=obj.pk).delete()


# ────────────────────────────────────────────────────────────────────
# USERS MANAGER with Soft Delete
# ────────────────────────────────────────────────────────────────────

class UsersManager(SoftDeleteManager):
    """Custom manager for Users model - handles user creation with email, username, and dni."""

    def create_user(self, email, username, dni, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        if not dni:
            raise ValueError('DNI is required')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, dni=dni, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def normalize_email(self, email):
        """Normalize email using Django's built-in method"""
        return BaseUserManager.normalize_email(BaseUserManager, email)

    def get_by_natural_key(self, email):
        """Get user by email (natural key)"""
        return self.get(email=email)
