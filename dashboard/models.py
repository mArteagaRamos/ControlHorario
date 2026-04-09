# ---------- Backend Models: dashboard/models.py ----------
from django.db import models
from users.models import Companies, Users, UserCompany, CompanySettings
from django.utils import timezone
import uuid
 
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
    
class Note(models.Model):
    class NoteType(models.TextChoices):
        URGENT  = 'urgent',  'Urgente'
        GENERAL = 'general', 'General'
        TASK    = 'task',    'Tarea'
        OTHER   = 'other',   'Otro'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company    = models.ForeignKey(Companies, on_delete=models.CASCADE, related_name='notes')
    author     = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, related_name='notes')
    type       = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.GENERAL)
    title      = models.CharField(max_length=200)
    body       = models.TextField(blank=True, null=True)
    tasks      = models.JSONField(default=list)
    pinned     = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notes'
        ordering = ['-pinned', '-created_at']