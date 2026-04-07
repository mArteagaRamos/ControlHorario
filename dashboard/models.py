# ---------- Backend Models: dashboard/models.py ----------
from django.db import models
from users.models import Companies, Users, UserCompany, CompanySettings
from django.utils import timezone
import uuid
from django.db import models
from users.models import Companies, Users
 
 
class WorkSchedule(models.Model):
    """
    Horario laboral individual por empleado.
    Sobreescribe el horario global de CompanySettings para un empleado concreto.
    Los días usan ISO weekday: 1=Lun, 2=Mar, 3=Mié, 4=Jue, 5=Vie, 6=Sáb, 7=Dom.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='schedules')
    company    = models.ForeignKey(Companies, on_delete=models.CASCADE, related_name='schedules')
    work_days  = models.JSONField(default=list)   # e.g. [1,2,3,4,5]
    start_time = models.TimeField()
    end_time   = models.TimeField()
    valid_from = models.DateField()
    valid_to   = models.DateField(null=True, blank=True)  # NULL = vigente indefinidamente
    created_by = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_schedules'
    )
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = 'work_schedules'
        ordering = ['-valid_from']
 
    def __str__(self):
        return f"Schedule {self.user} | {self.valid_from} → {self.valid_to or '∞'}"
 
 
class LeaveRequest(models.Model):
 
    class LeaveType(models.TextChoices):
        VACATION  = 'vacation',  'Vacaciones'
        SICK      = 'sick',      'Baja por enfermedad'
        PERSONAL  = 'personal',  'Asunto personal'
        MATERNITY = 'maternity', 'Maternidad/Paternidad'
        OTHER     = 'other',     'Otro'
 
    class LeaveStatus(models.TextChoices):
        PENDING  = 'pending',  'Pendiente'
        APPROVED = 'approved', 'Aprobada'
        REJECTED = 'rejected', 'Rechazada'
        CANCELED = 'canceled', 'Cancelada'
 
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='leave_requests')
    company     = models.ForeignKey(Companies, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type  = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.OTHER)
    start_date  = models.DateField()
    end_date    = models.DateField()
    reason      = models.TextField(blank=True, null=True)
    status      = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    reviewed_by = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leaves'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
 
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