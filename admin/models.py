# admin/models.py

import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from core.model_normalization import UppercaseNormalizationMixin
from core.managers import SoftDeleteManager
from users.models import Companies


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
