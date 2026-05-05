import uuid
import sys
from datetime import timedelta
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from core.model_normalization import UppercaseNormalizationMixin
from core.managers import SoftDeleteManager
from users.models import Companies

# Detectar si estamos ejecutando tests
is_testing = 'test' in sys.argv

# Elegir el tipo de campo según el modo para no tocar producción
if is_testing:
    # En tests con SQLite
    weekend_days_field = models.JSONField(default=list, blank=True)
    holidays_field = models.JSONField(default=list, blank=True)
    tolerance_field = models.DurationField(default=timedelta(minutes=15))
else:
    # En producción con PostgreSQL
    weekend_days_field = ArrayField(models.IntegerField(), default=list, blank=True)
    holidays_field = ArrayField(models.DateField(), default=list, blank=True)
    tolerance_field = models.DurationField(default='00:15:00')

class CompanySettings(UppercaseNormalizationMixin, models.Model):
    id = models.AutoField(primary_key=True)
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    work_start = models.TimeField(default='08:00:00')
    work_end = models.TimeField(default='15:00:00')
    max_tolerance = tolerance_field
    auto_close_hours = models.IntegerField(default=12)
    weekend_days = weekend_days_field
    holidays = holidays_field
    updated_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'company_settings'