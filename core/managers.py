# ---------- Consolidated Managers: core/managers.py ----------

import email

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

    def soft_delete(self, obj):
        """Soft delete a record (mark as deleted, status changes based on model)"""
        obj.deleted_at = timezone.now()
        obj.save(update_fields=['deleted_at'])

    def restore(self, obj):
        """Restore a deleted record"""
        obj.deleted_at = None
        obj.save(update_fields=['deleted_at'])

    def hard_delete(self, obj):
        """Permanently delete a record (only for admin)"""
        from django.db import connection

        try:
            # Use raw SQL to delete directly, bypassing FK constraints
            with connection.cursor() as cursor:
                table_name = obj._meta.db_table
                pk_name = obj._meta.pk.attname
                pk_value = obj.pk

                # Disable triggers/constraints temporarily
                cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                cursor.execute(
                    f'DELETE FROM "{table_name}" WHERE "{pk_name}" = %s',
                    [pk_value]
                )
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        except Exception as e:
            # If that fails, try a different approach
            try:
                super().get_queryset().filter(pk=obj.pk).delete()
            except Exception:
                # Last resort: use connection.on_delete
                obj.delete()



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
        return BaseUserManager.normalize_email(email)

    def get_by_natural_key(self, email):
        """Get user by email (natural key)"""
        return self.get(email=email)

    def soft_delete(self, obj):
        """
        Soft delete a user: mark as deleted AND set status to 'suspended'.
        This prevents them from logging in and appearing in searches.
        """
        obj.deleted_at = timezone.now()
        obj.status = 'suspended'
        obj.save(update_fields=['deleted_at', 'status'])

    def restore(self, obj):
        """
        Restore a deleted user: clear deletion date AND revert status to 'active'.
        """
        obj.deleted_at = None
        obj.status = 'active'
        obj.save(update_fields=['deleted_at', 'status'])
