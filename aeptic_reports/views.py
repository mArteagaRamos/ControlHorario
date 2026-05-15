# aeptic_reports/views.py

import calendar
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages

from users.models import Users, UserCompany, Companies
from timetracking.models import TimeEntries
from requests.models import LeaveRequest
from admin.models import CompanySettings
from core.services import get_effective_context

# ─── Constante: Tax ID de la empresa AEPTIC ────────────────────────────────────
AEPTIC_TAX_ID = 'B90143645'


def _is_aeptic_member(user):
    """Devuelve True si el usuario pertenece a la empresa AEPTIC (o es admin)."""
    if user.is_admin:
        return True
    return UserCompany.objects.filter(
        user=user,
        company__tax_id=AEPTIC_TAX_ID,
        deleted_at__isnull=True
    ).exists()


@login_required
def aeptic_summary(request):
    """
    Resumen mensual para empleados/managers de AEPTIC (y admins).
    Muestra horas trabajadas, vacaciones, ausencias, festivos y horas extra.
    """

    # ── 1. Control de acceso ────────────────────────────────────────────────────
    if request.user.is_auditor:
        return render(request, 'error/403.html', status=403)

    if not _is_aeptic_member(request.user):
        messages.error(request, 'No tienes acceso a esta sección.')
        return redirect('home_timetracking')

    # ── 2. Contexto de delegación (admin puede ver a otro usuario) ──────────────
    delegation_context = get_effective_context(request)

    if delegation_context['is_delegating']:
        target_user = Users.objects.filter(
            id=delegation_context['delegated_user_id']
        ).first()
        company = Companies.objects.filter(
            id=delegation_context['delegated_company_id']
        ).first()
    else:
        target_user = request.user
        # Tomamos la empresa AEPTIC directamente
        membership = UserCompany.objects.filter(
            user=target_user,
            company__tax_id=AEPTIC_TAX_ID,
            deleted_at__isnull=True
        ).select_related('company').first()

        if not membership and not request.user.is_admin:
            messages.error(request, 'No tienes empresa AEPTIC asignada.')
            return redirect('home_timetracking')

        company = membership.company if membership else None

    if not target_user:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('home_timetracking')

    # ── 3. Selector de mes/año ──────────────────────────────────────────────────
    today = timezone.localdate()
    try:
        selected_year  = int(request.GET.get('year',  today.year))
        selected_month = int(request.GET.get('month', today.month))
        # Validación básica
        if not (1 <= selected_month <= 12):
            selected_month = today.month
        if not (2020 <= selected_year <= today.year + 1):
            selected_year = today.year
    except (ValueError, TypeError):
        selected_year  = today.year
        selected_month = today.month

    # Primer y último día del mes seleccionado
    first_day = date(selected_year, selected_month, 1)
    last_day  = date(selected_year, selected_month,
                     calendar.monthrange(selected_year, selected_month)[1])

    # ── 4. Configuración de empresa (jornada + festivos) ───────────────────────
    settings_obj = None
    if company:
        settings_obj = CompanySettings.objects.filter(company=company).first()

    # Jornada diaria en segundos (por defecto 7h si no hay configuración)
    if settings_obj and settings_obj.work_start and settings_obj.work_end:
        ws = settings_obj.work_start
        we = settings_obj.work_end
        jornada_seconds = (
            (we.hour * 3600 + we.minute * 60 + we.second) -
            (ws.hour * 3600 + ws.minute * 60 + ws.second)
        )
        jornada_seconds = max(jornada_seconds, 0)
    else:
        jornada_seconds = 7 * 3600  # 7 horas por defecto

    # Tolerancia en segundos
    if settings_obj and settings_obj.max_tolerance:
        tolerance_seconds = int(settings_obj.max_tolerance.total_seconds())
    else:
        tolerance_seconds = 15 * 60  # 15 min por defecto

    # Festivos del mes
    holidays_in_month = []
    if settings_obj and settings_obj.holidays:
        holidays_in_month = [
            h for h in settings_obj.holidays
            if first_day <= h <= last_day
        ]

    # Días de fin de semana configurados (0=Lunes…6=Domingo en Python weekday)
    weekend_days = list(settings_obj.weekend_days) if settings_obj and settings_obj.weekend_days else [5, 6]

    # ── 5. Días laborables del mes ─────────────────────────────────────────────
    all_days = [first_day + timedelta(days=i)
                for i in range((last_day - first_day).days + 1)]
    working_days = [
        d for d in all_days
        if d.weekday() not in weekend_days and d not in holidays_in_month
    ]
    num_working_days = len(working_days)

    # ── 6. Fichajes del mes ────────────────────────────────────────────────────
    entries_qs = TimeEntries.objects.filter(
        user=target_user,
        date__gte=first_day,
        date__lte=last_day,
        deleted_at__isnull=True,
    ).exclude(status='voided')

    if company:
        entries_qs = entries_qs.filter(company=company)

    total_worked_seconds = sum(e.total_seconds or 0 for e in entries_qs)
    days_with_entry = entries_qs.values('date').distinct().count()

    # Horas extra: segundos trabajados por encima de la jornada + tolerancia
    extra_seconds = 0
    for entry in entries_qs:
        worked = entry.total_seconds or 0
        if worked > jornada_seconds + tolerance_seconds:
            extra_seconds += worked - jornada_seconds

    # ── 7. Vacaciones y ausencias ──────────────────────────────────────────────
    leaves_qs = LeaveRequest.objects.filter(
        user=target_user,
        status=LeaveRequest.LeaveStatus.APPROVED,
        start_date__lte=last_day,
        end_date__gte=first_day,
    )
    if company:
        leaves_qs = leaves_qs.filter(company=company)

    # Contar días de cada tipo recortando al mes seleccionado
    vacation_days  = 0
    absence_days   = 0
    for leave in leaves_qs:
        start = max(leave.start_date, first_day)
        end   = min(leave.end_date,   last_day)
        days  = (end - start).days + 1
        if leave.leave_type == LeaveRequest.LeaveType.VACATION:
            vacation_days += days
        else:
            absence_days += days

    # ── 8. Rol en AEPTIC ───────────────────────────────────────────────────────
    user_role = 'Admin' if target_user.is_admin else 'Empleado'
    if company:
        uc = UserCompany.objects.filter(
            user=target_user, company=company, deleted_at__isnull=True
        ).first()
        if uc:
            user_role = uc.get_role_display().capitalize()

    # ── 9. Helpers de formato ──────────────────────────────────────────────────
    def fmt_time(seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m:02d}m"

    # ── 10. Lista de meses y años para el selector ─────────────────────────────
    month_names = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    available_years = list(range(2024, today.year + 1))

    # ── 11. Contexto final ─────────────────────────────────────────────────────
    context = {
        # Empleado
        'target_user':     target_user,
        'user_role':       user_role,
        'company':         company,
        # Periodo
        'selected_year':   selected_year,
        'selected_month':  selected_month,
        'month_name':      month_names[selected_month - 1],
        'month_names':     list(enumerate(month_names, start=1)),
        'available_years': available_years,
        # Métricas
        'total_worked':       fmt_time(total_worked_seconds),
        'total_worked_raw':   total_worked_seconds,
        'extra_time':         fmt_time(extra_seconds),
        'extra_time_raw':     extra_seconds,
        'vacation_days':      vacation_days,
        'absence_days':       absence_days,
        'holidays_count':     len(holidays_in_month),
        'holidays_list':      holidays_in_month,
        'days_with_entry':    days_with_entry,
        'num_working_days':   num_working_days,
        'jornada_daily':      fmt_time(jornada_seconds),
        # Objetivo del mes (solo días laborables sin vacaciones ni ausencias)
        'target_seconds': max(0, (num_working_days - vacation_days - absence_days) * jornada_seconds),
        'target_time':    fmt_time(max(0, (num_working_days - vacation_days - absence_days) * jornada_seconds)),
        # Delegación
        **delegation_context,
    }

    return render(request, 'aeptic_reports/aeptic_summary.html', context)