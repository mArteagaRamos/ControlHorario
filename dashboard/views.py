import json
from datetime import date,timedelta
from urllib import request

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.utils.dateparse import parse_date
from users.forms import ProfilePasswordChangeForm
from users.models import Companies, Users, UserCompany, CompanySettings
from audit.views import manager_or_admin_required
from dashboard.models import LeaveRequest, WorkSchedule, Note
from django.views.decorators.http import require_POST
from django.db.models import Q

# ── helpers ────────────────────────────────────────────────────────────────────
 
def _get_company(request):
    company_id = request.session.get('company_id')
    return Companies.objects.filter(id=company_id).first()
 
 
def _is_manager(request, company):
    if request.user.is_admin:
        return True
    uc = UserCompany.objects.filter(user=request.user, company=company).first()
    return uc and uc.role == UserCompany.RoleChoices.MANAGER
 
WEEKDAY = [
    (0, 'Domingo'),
    (1, 'Lunes'),
    (2, 'Martes'),
    (3, 'Miércoles'),
    (4, 'Jueves'),
    (5, 'Viernes'),
    (6, 'Sábado'),
]



@login_required
def calendar(request):
    company = _get_company(request)
    is_manager = _is_manager(request, company)
 
    team = []
    if is_manager and company:
        team = (
            UserCompany.objects
            .filter(company=company)
            .exclude(user=request.user)
            .select_related('user')
        )
 
    pending_count = 0
    if is_manager and company:
        pending_count = LeaveRequest.objects.filter(
            company=company, status=LeaveRequest.LeaveStatus.PENDING
        ).count()
 
    return render(request, 'user_panel/calendar.html', {
        'is_manager':    is_manager,
        'team':          team,
        'leave_types':   LeaveRequest.LeaveType.choices,
        'pending_count': pending_count,
    })
# User management views

@login_required
def calendar(request):
    company = _get_company(request)
    is_manager = _is_manager(request, company)
 
    team = []
    if is_manager and company:
        team = (
            UserCompany.objects
            .filter(company=company)
            .exclude(user=request.user)
            .select_related('user')
        )
 
    pending_count = 0
    if is_manager and company:
        pending_count = LeaveRequest.objects.filter(
            company=company, status=LeaveRequest.LeaveStatus.PENDING
        ).count()
 
    return render(request, 'user_panel/calendar.html', {
        'is_manager':    is_manager,
        'team':          team,
        'leave_types':   LeaveRequest.LeaveType.choices,
        'pending_count': pending_count,
    })

@login_required
def profile(request):
    password_form = ProfilePasswordChangeForm(user=request.user)
    show_password_form = False

    if request.method == 'POST':
        password_form = ProfilePasswordChangeForm(user=request.user, data=request.POST)
        show_password_form = True
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Tu contraseña se ha actualizado correctamente.')
            return redirect('profile')

        messages.error(request, 'Revisa los errores del formulario y vuelve a intentarlo.')

    return render(request, 'user_panel/profile.html', {
        'password_form': password_form,
        'show_password_form': show_password_form,
    })

@login_required
def absence(request):
    return render(request, 'user_panel/absence.html')

@login_required
def request_correction(request):
    return render(request, 'user_panel/requests.html')   


# Team management views

@login_required
@manager_or_admin_required
def entity_info(request):
    company_id = request.session.get('company_id')
    if not company_id:
        messages.error(request, 'No tienes empresa asignada.')
        return redirect('home_timetracking')

    company = Companies.objects.filter(id=company_id).first()
    if not company:
        messages.error(request, 'Empresa no encontrada.')
        return redirect('home_timetracking')
    
    membership = UserCompany.objects.filter(
    user=request.user, 
    company=company
    ).first()

    # Global admin can always edit, regardless of their role in the company
    if request.user.is_admin:
        user_role = 'admin'
    elif membership and membership.role == UserCompany.RoleChoices.MANAGER:
        user_role = 'manager'
    else:
        user_role = 'employee'

    can_edit = user_role in ('admin', 'manager')

    settings_obj = CompanySettings.objects.filter(company=company).first()


    if request.method == 'POST' and can_edit:
 
        # Update company info
        company.name       = request.POST.get('name', company.name).strip()
        company.legal_name = request.POST.get('legal_name', company.legal_name).strip()
        company.tax_id     = request.POST.get('tax_id', '').strip() or None
        company.updated_at = timezone.now()
        company.save(update_fields=['name', 'legal_name', 'tax_id', 'updated_at'])

        # Workday settings
        
        if settings_obj:
            work_start = request.POST.get('work_start')
            if work_start:
                settings_obj.work_start = work_start

            work_end = request.POST.get('work_end')
            if work_end:
                settings_obj.work_end = work_end

            tolerance_min = request.POST.get('max_tolerance')
            if tolerance_min is not None and tolerance_min != '':
               settings_obj.max_tolerance = timedelta(minutes=int(tolerance_min))

            auto_close = request.POST.get('auto_close_hours')
            if auto_close is not None and auto_close != '':
                settings_obj.auto_close_hours = int(auto_close)

            settings_obj.weekend_days = [
                int(day) for day in request.POST.getlist('weekend_days')
            ]

            holidays = []

            for raw in request.POST.get('holidays', '').split(','):
                raw = raw.strip()
                if raw:
                    parsed = parse_date(raw)
                    if parsed:
                        holidays.append(parsed)
            settings_obj.holidays = holidays
            settings_obj.updated_at = timezone.now()
            settings_obj.save()

        #messages.success(request, "Información de la empresa actualizada correctamente.")
        return redirect('entity_info')
             
    return render(request, 'team/entity_info.html',{

        'company': company,
        'user_role': user_role,
        'settings': settings_obj,
        'weekdays': WEEKDAY,

                  })

# ── API: eventos del calendario (FullCalendar JSON feed) ─────────────────────
 
@login_required
def api_calendar_events(request):
    """
    GET /dashboard/api/calendar/events/?user_id=<uuid>&start=YYYY-MM-DD&end=YYYY-MM-DD
    Devuelve eventos en formato FullCalendar.
    El manager puede pedir eventos de cualquier empleado de su empresa.
    """
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)
 
    target_user = request.user
    user_id = request.GET.get('user_id')
    if user_id and _is_manager(request, company):
        target_user = get_object_or_404(Users, id=user_id)
        # Verificar que el empleado pertenece a la empresa del manager
        if not UserCompany.objects.filter(user=target_user, company=company).exists():
            return JsonResponse({'error': 'Empleado no pertenece a esta empresa'}, status=403)
 
    start_str = request.GET.get('start', str(date.today()))
    end_str   = request.GET.get('end',   str(date.today() + timedelta(days=30)))
    try:
        start = date.fromisoformat(start_str[:10])
        end   = date.fromisoformat(end_str[:10])
    except ValueError:
        return JsonResponse({'error': 'Invalid dates'}, status=400)
 
    events = []
 
    # ── 1. Horario laboral ─────────────────────────────────────────────────────
    schedules = WorkSchedule.objects.filter(
        user=target_user, company=company,
        valid_from__lte=end,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=start)
    )
 
    company_settings = CompanySettings.objects.filter(company=company).first()
 
    cursor = start
    while cursor <= end:
        iso_weekday = cursor.isoweekday()  # 1=Mon … 7=Sun
 
        sched = next(
            (
                s for s in schedules
                if s.valid_from <= cursor
                   and (s.valid_to is None or s.valid_to >= cursor)
                   and iso_weekday in (s.work_days or [])
            ),
            None,
        )
 
        if sched is None and company_settings:
            weekend = [(d if d != 0 else 7) for d in (company_settings.weekend_days or [])]
            if iso_weekday not in weekend:
                events.append({
                    'id':        f'work-{cursor}',
                    'title':     f'🕐 {company_settings.work_start.strftime("%H:%M")} – {company_settings.work_end.strftime("%H:%M")}',
                    'start':     f'{cursor}T{company_settings.work_start}',
                    'end':       f'{cursor}T{company_settings.work_end}',
                    'color':     '#3b82f6',
                    'classNames': ['event-work'],
                    'extendedProps': {'type': 'work'},
                })
        elif sched:
            events.append({
                'id':        f'work-{cursor}',
                'title':     f'🕐 {sched.start_time.strftime("%H:%M")} – {sched.end_time.strftime("%H:%M")}',
                'start':     f'{cursor}T{sched.start_time}',
                'end':       f'{cursor}T{sched.end_time}',
                'color':     '#3b82f6',
                'classNames': ['event-work'],
                'extendedProps': {'type': 'work'},
            })
 
        cursor += timedelta(days=1)
 
    # ── 2. Ausencias / vacaciones ──────────────────────────────────────────────
    STATUS_COLOR = {
        'pending':  '#f59e0b',
        'approved': '#10b981',
        'rejected': '#ef4444',
        'canceled': '#6b7280',
    }
    leaves = LeaveRequest.objects.filter(
        user=target_user, company=company,
        start_date__lte=end, end_date__gte=start,
    )
    for leave in leaves:
        events.append({
            'id':        f'leave-{leave.id}',
            'title':     f'{leave.get_leave_type_display()} ({leave.get_status_display()})',
            'start':     str(leave.start_date),
            'end':       str(leave.end_date + timedelta(days=1)),  # FullCalendar end is exclusive
            'color':     STATUS_COLOR.get(leave.status, '#6b7280'),
            'allDay':    True,
            'classNames': ['event-leave'],
            'extendedProps': {
                'type':     'leave',
                'status':   leave.status,
                'leave_id': str(leave.id),
                'reason':   leave.reason or '',
            },
        })
 
    return JsonResponse(events, safe=False)
 
 
# ── API: solicitar ausencia ────────────────────────────────────────────────────
 
@login_required
@require_POST
def api_leave_request_create(request):
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)
 
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
 
    start_date = data.get('start_date')
    end_date   = data.get('end_date')
    leave_type = data.get('leave_type', 'other')
    reason     = data.get('reason', '')
 
    if not start_date or not end_date:
        return JsonResponse({'error': 'Fechas obligatorias'}, status=400)
 
    try:
        start = date.fromisoformat(start_date)
        end   = date.fromisoformat(end_date)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
 
    if end < start:
        return JsonResponse({'error': 'La fecha fin no puede ser anterior a la fecha inicio'}, status=400)
 
    if leave_type not in LeaveRequest.LeaveType.values:
        return JsonResponse({'error': 'Tipo de ausencia no válido'}, status=400)
 
    leave = LeaveRequest.objects.create(
        user=request.user,
        company=company,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        reason=reason,
        status=LeaveRequest.LeaveStatus.PENDING,
    )
 
    return JsonResponse({
        'ok':      True,
        'id':      str(leave.id),
        'message': 'Solicitud enviada correctamente',
    }, status=201)
 
 
# ── API: cancelar solicitud (empleado) ────────────────────────────────────────
 
@login_required
@require_POST
def api_leave_request_cancel(request, leave_id):
    """El empleado puede cancelar sus propias solicitudes pendientes."""
    company = _get_company(request)
    leave = get_object_or_404(LeaveRequest, id=leave_id, user=request.user, company=company)
 
    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Solo se pueden cancelar solicitudes pendientes'}, status=400)
 
    leave.status = LeaveRequest.LeaveStatus.CANCELED
    leave.save(update_fields=['status', 'updated_at'])
 
    return JsonResponse({'ok': True})
 
 
# ── API: solicitudes pendientes (manager) ─────────────────────────────────────
 
@login_required
@manager_or_admin_required
def api_leave_pending(request):
    """Lista de solicitudes pendientes para el manager."""
    company = _get_company(request)
    leaves = (
        LeaveRequest.objects
        .filter(company=company, status=LeaveRequest.LeaveStatus.PENDING)
        .select_related('user')
        .order_by('start_date')
    )
    data = [
        {
            'id':         str(l.id),
            'user':       l.user.get_full_name() or l.user.email,
            'leave_type': l.get_leave_type_display(),
            'start_date': str(l.start_date),
            'end_date':   str(l.end_date),
            'reason':     l.reason or '',
            'created_at': l.created_at.strftime('%d/%m/%Y'),
        }
        for l in leaves
    ]
    return JsonResponse(data, safe=False)
 
 
# ── API: aprobar / rechazar (manager) ────────────────────────────────────────
 
@login_required
@manager_or_admin_required
@require_POST
def api_leave_review(request, leave_id):
    """Manager aprueba o rechaza una solicitud."""
    company = _get_company(request)
    leave   = get_object_or_404(LeaveRequest, id=leave_id, company=company)
 
    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Esta solicitud ya fue revisada'}, status=400)
 
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
 
    action = data.get('action')  # 'approve' | 'reject'
    note   = data.get('note', '')
 
    if action == 'approve':
        leave.status = LeaveRequest.LeaveStatus.APPROVED
    elif action == 'reject':
        leave.status = LeaveRequest.LeaveStatus.REJECTED
    else:
        return JsonResponse({'error': 'Acción no válida. Usa "approve" o "reject"'}, status=400)
 
    leave.reviewed_by = request.user
    leave.reviewed_at = timezone.now()
    leave.review_note = note
    leave.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])
 
    return JsonResponse({'ok': True, 'new_status': leave.status})
 
 
# ── API: crear horario individual (manager) ───────────────────────────────────
 
@login_required
@manager_or_admin_required
@require_POST
def api_schedule_create(request):
    """Manager crea / actualiza horario individual para un empleado."""
    company = _get_company(request)
 
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
 
    user_id    = data.get('user_id')
    work_days  = data.get('work_days', [1, 2, 3, 4, 5])
    start_time = data.get('start_time')
    end_time   = data.get('end_time')
    valid_from = data.get('valid_from', str(date.today()))
    valid_to   = data.get('valid_to')
 
    if not all([user_id, start_time, end_time]):
        return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)
 
    employee = get_object_or_404(Users, id=user_id)
 
    # Verificar que el empleado pertenece a la empresa
    if not UserCompany.objects.filter(user=employee, company=company).exists():
        return JsonResponse({'error': 'Empleado no pertenece a esta empresa'}, status=403)
 
    schedule = WorkSchedule.objects.create(
        user=employee,
        company=company,
        work_days=work_days,
        start_time=start_time,
        end_time=end_time,
        valid_from=valid_from,
        valid_to=valid_to or None,
        created_by=request.user,
    )
 
    return JsonResponse({'ok': True, 'id': str(schedule.id)}, status=201)
 
 
# ── Vistas de equipo ───────────────────────────────────────────────────────────
 
@login_required
def staff(request):
    return render(request, 'team/staff.html')
 
 
@login_required
def notes(request):
    company_id = request.session.get('company_id')
    company = Companies.objects.filter(id=company_id).first()
 
    notes_qs = Note.objects.filter(company=company).select_related('author')
 
    return render(request, 'team/notes.html', {
        'notes':      notes_qs,
        'note_types': Note.NoteType.choices,
        'company':    company,
    })