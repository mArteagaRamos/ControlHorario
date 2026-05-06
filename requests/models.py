# requests/models.py

import uuid
from django.db import models
from django.utils import timezone
from core.model_normalization import UppercaseNormalizationMixin
from core.managers import SoftDeleteManager
from users.models import Users, Companies


class CorrectionRequests(UppercaseNormalizationMixin, models.Model):
    class CorrectionStatus(models.TextChoices):
        PENDING = 'pending'
        APPROVED = 'approved'
        REJECTED = 'rejected'

    id = models.UUIDField(primary_key=True)
    time_entry = models.ForeignKey('timetracking.TimeEntries', on_delete=models.CASCADE, db_column='time_entry_id', null=True, blank=True)
    requester = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='requester_id', null=True, blank=True)
    request_date = models.DateTimeField(default=timezone.now)
    reason = models.TextField()
    new_clock_in = models.DateTimeField(blank=True, null=True)
    new_clock_out = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=CorrectionStatus.choices, default=CorrectionStatus.PENDING)
    approver = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='correctionrequests_approver_set', db_column='approver_id', blank=True, null=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    correction_note = models.TextField(blank=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'correction_requests'


class LeaveRequest(models.Model):
 
    class LeaveType(models.TextChoices):
        VACATION = 'vacation', 'Vacaciones'
        ABSENCE  = 'absence',  'Ausencia'
 
    class LeaveReason(models.TextChoices):
        ANNUAL              = 'annual',              'Vacaciones anuales'
        SICK                = 'sick',                'Baja por enfermedad'
        MATERNITY           = 'maternity',           'Maternidad / Paternidad'
        WEDDING             = 'wedding',             'Matrimonio'
        BEREAVEMENT         = 'bereavement',         'Fallecimiento familiar'
        MEDICAL_APPOINTMENT = 'medical_appointment', 'Cita médica'
        LEGAL_DUTY          = 'legal_duty',          'Deber público / legal'
        PERSONAL            = 'personal',            'Asuntos propios'
        OTHER               = 'other',               'Otro'
 
    class LeaveStatus(models.TextChoices):
        PENDING  = 'pending',  'Pendiente'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
        CANCELED = 'canceled', 'Cancelada'
 
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='leave_requests')
    company      = models.ForeignKey(Companies, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type   = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.ABSENCE)
    leave_reason = models.CharField(max_length=30, choices=LeaveReason.choices, default=LeaveReason.OTHER)
    reason_note  = models.TextField(blank=True, null=True)
    attachment_path = models.CharField(max_length=255, null=True, blank=True)
    start_date = models.DateField()
    end_date   = models.DateField()
 
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
 
    attachment_path     = models.CharField(max_length=500, blank=True, null=True)
    attachment_verified = models.BooleanField(default=False)
    force_proof         = models.BooleanField(default=False)
 
    reviewed_by = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leaves'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, null=True)
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.user} | {self.leave_type} | {self.start_date} → {self.end_date} [{self.status}]"