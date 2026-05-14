from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class MonthlyReport(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('signed', 'Firmado'),
        ('archived', 'Archivado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_reports')
    # Si tienes el modelo Company, asegúrate de importarlo o usar 'companies.Company'
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE) 
    
    report_date = models.DateField()  # Primer día del mes correspondiente
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    generated_at = models.DateTimeField(auto_now_add=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    
    document_path = models.FileField(upload_to='reports/aeptic/%Y/%m/', null=True, blank=True)

    class Meta:
        db_table = 'monthly_reports'
        unique_together = ['user', 'company', 'report_date']
        verbose_name = 'Informe Mensual'
        verbose_name_plural = 'Informes Mensuales'

    def __str__(self):
        return f"{self.user.surname} - {self.report_date.strftime('%m/%Y')}"