import hashlib
import json
from django.db import models
from users.models import Users
from django.utils import timezone
from core.model_normalization import UppercaseNormalizationMixin

class AuditLog(UppercaseNormalizationMixin, models.Model):
    class AuditAction(models.TextChoices):
        CREATE = 'create'
        UPDATE = 'update'
        DELETE = 'delete'
        VOIDED = 'voided'
        MANUAL_CORRECTION = 'manual_correction'

    id = models.UUIDField(primary_key=True)
    table_name = models.CharField(max_length=50)
    record_id = models.UUIDField()
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='user_id', blank=True, null=True)
    action_type = models.CharField(max_length=20, choices=AuditAction.choices)
    before = models.JSONField(blank=True, null=True)
    after = models.JSONField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    # Field added according to the document
    source = models.CharField(max_length=50, default='web') 

    # New audit fields
    previous_hash = models.CharField(max_length=64, blank=True, null=True)
    event_hash = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        managed = False  # Keep as False since you manage the DB manually
        db_table = 'audit_log'

    def calcular_event_hash(self, payload: dict) -> str:
        """
        Unique function to calculate the hash following the document rules.
        """
        # Strict serialization: sorted keys, no unnecessary ASCII characters and compact separators
        texto = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        # Conversion to UTF-8 bytes and SHA-256
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        # Prevent editing of existing records
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError("Audit records cannot be edited.")

        # 1. Find the last record to get the previous_hash
        last_log = AuditLog.objects.order_by('-timestamp', '-id').first()
        self.previous_hash = last_log.event_hash if last_log else None

        # 2. Prepare the payload with the exact required data
        payload = {
            "id": str(self.id),
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat(),
            "user_id": str(self.user_id) if self.user_id else None,
            "table_name": self.table_name,
            "record_id": str(self.record_id),
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "source": self.source,
            "previous_hash": self.previous_hash
        }

        # 3. Calculate and save the event_hash
        self.event_hash = self.calcular_event_hash(payload)
        
        super().save(*args, **kwargs)