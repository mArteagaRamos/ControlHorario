from django.db import models

import uuid
from django.db import models
from users.models import Users, Companies 


class MonthlyReport(models.Model):

    class ReportStatus(models.TextChoices):
        DRAFT     = 'draft',     'Borrador'
        GENERATED = 'generated', 'Generado'
        SIGNED    = 'signed',    'Firmado'
        ARCHIVED  = 'archived',  'Archivado'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(Users,     on_delete=models.CASCADE, related_name='monthly_reports')
    company    = models.ForeignKey(Companies, on_delete=models.CASCADE, related_name='monthly_reports')

    # Primer día del mes representado (ej: 2026-05-01 para mayo 2026)
    report_date = models.DateField()

    status       = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.DRAFT)
    generated_at = models.DateTimeField(auto_now_add=True)
    signed_at    = models.DateTimeField(null=True, blank=True)

    document_path = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        managed         = False
        db_table        = 'monthly_reports'
        unique_together = ('user', 'company', 'report_date')
        indexes         = [
            models.Index(fields=['user', 'report_date'], name='idx_reports_user_date'),
            models.Index(fields=['company'],              name='idx_reports_company'),
        ]
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.user} | {self.company} | {self.report_date.strftime('%B %Y')} [{self.status}]"

    # --- Propiedades de utilidad ---

    @property
    def is_signed(self):
        return self.status == self.ReportStatus.SIGNED

    @property
    def month(self):
        return self.report_date.month

    @property
    def year(self):
        return self.report_date.year
