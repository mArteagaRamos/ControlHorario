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


class VacationPeriodMultiplier(UppercaseNormalizationMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    company = models.ForeignKey(Companies, on_delete=models.CASCADE, db_column='company_id')
    name = models.CharField(max_length=100)
    date_from = models.DateField()
    date_to = models.DateField()
    multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)

    created_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='created_by',
        related_name='vacation_multipliers_created'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

    objects = SoftDeleteManager()

    class Meta:
        managed = False
        db_table = 'vacation_period_multipliers'

    def __str__(self):
        return f"{self.name} ({self.date_from} - {self.date_to}) x{self.multiplier}"

    @staticmethod
    def get_multiplier_for_range(company_id, start_date, end_date):
        period = VacationPeriodMultiplier.objects.filter(
            company_id=company_id,
            date_from__lte=end_date,
            date_to__gte=start_date,
            deleted_at__isnull=True
        ).first()

        if period:
            return float(period.multiplier)
        return 1.0


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
    start_time = models.TimeField(null=True, blank=True)
    end_time   = models.TimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)

    attachment_path     = models.CharField(max_length=500, blank=True, null=True)
    attachment_verified = models.BooleanField(default=False)
    force_proof         = models.BooleanField(default=False)

    reviewed_by = models.ForeignKey(
        Users, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leaves'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, null=True)

    hour_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} | {self.leave_type} | {self.start_date} → {self.end_date} [{self.status}]"

    @staticmethod
    def get_consumed_days(user_id, company_id, year):
        from datetime import date
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        leave_requests = LeaveRequest.objects.filter(
            user_id=user_id,
            company_id=company_id,
            leave_type='vacation',
            status='approved',
            start_date__gte=year_start,
            end_date__lte=year_end,
            deleted_at__isnull=True
        )

        total_days = 0.0
        for leave in leave_requests:
            days = (leave.end_date - leave.start_date).days + 1
            total_days += days

        return total_days