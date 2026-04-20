# ---------- Backend Models: dashboard/models.py ----------
from django.db import models
from users.models import Companies, Users, UserCompany
from django.utils import timezone
import uuid
    
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