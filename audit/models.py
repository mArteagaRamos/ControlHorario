from django.db import models
from users.models import Users
from django.utils import timezone
from core.model_normalization import UppercaseNormalizationMixin

class AuditLog(UppercaseNormalizationMixin, models.Model):
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
