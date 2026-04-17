import json
from datetime import date,timedelta
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.utils.dateparse import parse_date
from users.forms import ProfilePasswordChangeForm, UserPersonalDataForm
from users.models import Companies, Users, UserCompany
from admin.models import CompanySettings
from dashboard.models import Note
from corrections.models import LeaveRequest
from django.views.decorators.http import require_POST
from django.db.utils import IntegrityError as DBIntegrityError
import uuid
from audit.models import AuditLog
from uuid import uuid4
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

# Import centralized decorators and services
from core.decorators import manager_or_admin_required, auditor_cannot_access, manager_or_admin_with_delegation_check
from core.services import get_effective_context, get_company, is_manager as check_is_manager, serialize_leave, log_leave

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
@auditor_cannot_access
def calendar(request):
    company = get_company(request)
    is_manager = check_is_manager(request, company)

    # ── Lógica de POST (Igual que en workday) ──
    if request.method == 'POST':
        leave_type   = request.POST.get('leave_type')
        leave_reason = request.POST.get('leave_reason')
        start_date_str = request.POST.get('start_date')
        end_date_str   = request.POST.get('end_date')
        reason_note  = request.POST.get('reason_note', '').strip()

        if start_date_str and end_date_str:
            try:
                # Usamos parse_date de Django que es más seguro
                start = parse_date(start_date_str)
                end   = parse_date(end_date_str)

                leave = LeaveRequest.objects.create(
                    user=request.user,
                    company=company,
                    leave_type=leave_type,
                    leave_reason=leave_reason,
                    start_date=start,
                    end_date=end,
                    reason_note=reason_note,
                    status=LeaveRequest.LeaveStatus.PENDING
                )
                log_leave(leave, request.user, AuditLog.AuditAction.CREATE,
                           reason=reason_note or 'Solicitud creada desde calendario')

                if request.headers.get('HX-Request'):
                    return HttpResponse(status=204)
                
                messages.success(request, 'Solicitud enviada correctamente.')
                return redirect('calendar')
            except Exception as e:
                if request.headers.get('HX-Request'):
                    return HttpResponse(f"Error: {str(e)}", status=400)
                messages.error(request, f"Error al procesar: {e}")

    # ── Lógica de GET ──
    team = []
    if is_manager:
        team = UserCompany.objects.filter(company=company).select_related('user')
    
    pending_count = LeaveRequest.objects.filter(
        company=company, status=LeaveRequest.LeaveStatus.PENDING
    ).count() if is_manager else 0
    
    context = {
        'is_manager': is_manager,
        'team': team,
        'pending_count': pending_count if is_manager else 0,
        'vacation_types': [
            (v, l) for v, l in LeaveRequest.LeaveReason.choices
            if v in ('annual', 'personal', 'other')
        ],
        'absence_types': [
            (v, l) for v, l in LeaveRequest.LeaveReason.choices
            if v in ('sick', 'maternity', 'wedding', 'bereavement', 'medical_appointment', 'legal_duty')
        ],
    }
    # Asegúrate de que la ruta al HTML sea la correcta según tu estructura
    return render(request, 'dashboard/calendar.html', context)

@login_required
def api_calendar_events(request):
    company = get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    user_id = request.GET.get('user_id')

    start_str = request.GET.get('start', '')[:10]
    end_str   = request.GET.get('end', '')[:10]

    try:
        start = date.fromisoformat(start_str)
        end   = date.fromisoformat(end_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': f'Invalid date format: {start_str}'}, status=400)

    events = []
    STATUS_COLOR = {
        'pending':  '#d97706',
        'approved': '#5a8f5a',
        'rejected': '#b94040',
        'canceled': '#6b7280',
    }

    # ── Todos los empleados ───────────────────────────────────────────────
    if user_id == 'all' and check_is_manager(request, company):
        leaves = LeaveRequest.objects.filter(
            company=company,
            start_date__lte=end,
            end_date__gte=start,
        ).select_related('user')

        for leave in leaves:
            events.append({
                'id': f'leave-{leave.id}',
                'title': f'{leave.user.username} · {leave.get_leave_type_display()}',
                'start': leave.start_date.isoformat(),
                'end': (leave.end_date + timedelta(days=1)).isoformat(),
                'color': STATUS_COLOR.get(leave.status, '#6b7280'),
                'allDay': True,
                'extendedProps': {
                    'status': leave.get_status_display(),
                    'reason': leave.reason_note or '',
                },
            })
        return JsonResponse(events, safe=False)

    # ── Empleado concreto (manager) o usuario propio ──────────────────────
    target_user = request.user
    if user_id and check_is_manager(request, company):
        try:
            target_user = get_object_or_404(Users, id=user_id)
        except:
            return JsonResponse({'error': 'Invalid User ID'}, status=400)

    leaves = LeaveRequest.objects.filter(
        user=target_user,
        company=company,
        start_date__lte=end,
        end_date__gte=start,
    )

    for leave in leaves:
        events.append({
            'id': f'leave-{leave.id}',
            'title': f'{leave.get_leave_type_display()}',
            'start': leave.start_date.isoformat(),
            'end': (leave.end_date + timedelta(days=1)).isoformat(),
            'color': STATUS_COLOR.get(leave.status, '#6b7280'),
            'allDay': True,
            'extendedProps': {
                'status': leave.get_status_display(),
                'reason': leave.reason_note or '',
            },
        })

    return JsonResponse(events, safe=False)

@login_required
@auditor_cannot_access
def profile(request):
    """
    User profile page: display and edit personal data, view associated companies.
    """
    from core.services import get_effective_context

    delegation_context = get_effective_context(request)

    # Determine which user to view profile for
    if delegation_context['is_delegating']:
        user = Users.objects.get(id=delegation_context['delegated_user_id'])
    else:
        user = request.user

    personal_form = UserPersonalDataForm(instance=user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'personal_data')

        if form_type == 'personal_data':
            personal_form = UserPersonalDataForm(request.POST, instance=user)
            if personal_form.is_valid():
                personal_form.save()
                messages.success(request, 'Los datos personales se han actualizado correctamente.')
                return redirect('profile')
            else:
                messages.error(request, 'Revisa los errores del formulario y vuelve a intentarlo.')

    # Get all companies user belongs to
    companies = UserCompany.objects.filter(user=user).select_related('company').order_by('-joined_at')

    context = {
        'personal_form': personal_form,
        'companies': companies,
    }
    context.update(delegation_context)

    return render(request, 'dashboard/profile.html', context)


@login_required
def security(request):
    """
    Security settings page: change password.
    """
    from core.services import get_effective_context

    delegation_context = get_effective_context(request)

    # Determine which user to manage password for
    if delegation_context['is_delegating']:
        user = Users.objects.get(id=delegation_context['delegated_user_id'])
    else:
        user = request.user

    password_form = ProfilePasswordChangeForm(user=user)
    show_password_form = False

    if request.method == 'POST':
        password_form = ProfilePasswordChangeForm(user=user, data=request.POST)
        show_password_form = True
        if password_form.is_valid():
            saved_user = password_form.save()
            if not delegation_context['is_delegating']:
                update_session_auth_hash(request, saved_user)
            messages.success(request, 'La contraseña se ha actualizado correctamente.')
            return redirect('security')

        messages.error(request, 'Revisa los errores del formulario y vuelve a intentarlo.')

    context = {
        'password_form': password_form,
        'show_password_form': show_password_form,
    }
    context.update(delegation_context)

    return render(request, 'dashboard/security.html', context)


# Team management views

@login_required
@manager_or_admin_with_delegation_check
def entity_info(request):
    from core.services import get_effective_context

    delegation_context = get_effective_context(request)

    # 1. Determine which company to view
    company_id = delegation_context['delegated_company_id'] if delegation_context['is_delegating'] else None

    if company_id:
        # Using delegated company
        company = Companies.objects.filter(id=company_id).first()
        if not company:
            messages.error(request, 'Empresa delegada no encontrada.')
            return redirect('home_timetracking')
    else:
        # Original logic
        company_id = request.GET.get('company_id') or request.session.get('company_id')

        if company_id:
            # Admin is inspecting a specific company OR manager checking their own
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                messages.error(request, 'Empresa no encontrada.')
                return redirect('home_timetracking')

            # Validate permissions:
            # - Admins can inspect any company
            # - Managers can only access their own company
            if not request.user.is_admin:
                # Manager: verify it's their own company
                user_membership = UserCompany.objects.filter(
                    user=request.user,
                    company=company,
                    deleted_at__isnull=True
                ).first()
                if not user_membership:
                    return HttpResponseForbidden("No tienes acceso a esta empresa.")

            request.session['company_id'] = company_id
        else:
            # Get the user's company membership
            user_membership = UserCompany.objects.filter(user=request.user).first()
            if not user_membership:
                messages.error(request, 'No tienes empresa asignada.')
                return redirect('home_timetracking')
            company = user_membership.company

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
        company.name = request.POST.get('name', company.name).strip()
        company.legal_name = request.POST.get('legal_name', company.legal_name).strip()
        posted_tax_id = request.POST.get('tax_id', '').strip() or None

        if posted_tax_id and Companies.objects.filter(tax_id=posted_tax_id).exclude(id=company.id).exists():
            messages.error(request, 'El CIF/NIF indicado ya existe en otra empresa.')
            context = {
                'company': company,
                'user_role': user_role,
                'settings': settings_obj,
                'weekdays': WEEKDAY,
            }
            context.update(delegation_context)
            return render(request, 'team/entity_info.html', context)

        company.tax_id = posted_tax_id
        company.updated_at = timezone.now()

        try:
            company.save(update_fields=['name', 'legal_name', 'tax_id', 'updated_at'])
        except IntegrityError:
            messages.error(request, 'No se pudo guardar la empresa porque el CIF/NIF ya está en uso.')
            context = {
                'company': company,
                'user_role': user_role,
                'settings': settings_obj,
                'weekdays': WEEKDAY,
            }
            context.update(delegation_context)
            return render(request, 'team/entity_info.html', context)

        # Workday settings

        if settings_obj:

            # Capturar estado ANTES
            before_jornada = {
                'work_start':    str(settings_obj.work_start),
                'work_end':      str(settings_obj.work_end),
                'max_tolerance': str(settings_obj.max_tolerance),
                'weekend_days':  list(settings_obj.weekend_days),
                'holidays':      [str(h) for h in settings_obj.holidays],
            }
            before_cierre = {
                'auto_close_hours': settings_obj.auto_close_hours,
            }

            # Aplicar cambios
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
            settings_obj.holidays  = holidays
            settings_obj.updated_at = timezone.now()
            settings_obj.save()

            # Capturar estado DESPUÉS
            after_jornada = {
                'work_start':    str(settings_obj.work_start),
                'work_end':      str(settings_obj.work_end),
                'max_tolerance': str(settings_obj.max_tolerance),
                'weekend_days':  list(settings_obj.weekend_days),
                'holidays':      [str(h) for h in settings_obj.holidays],
            }
            after_cierre = {
                'auto_close_hours': settings_obj.auto_close_hours,
            }

            # 🔐 Auditoría: Jornada laboral
            if before_jornada != after_jornada:
                AuditLog.objects.create(
                    id=uuid4(),
                    table_name='company_settings',
                    record_id=settings_obj.id,
                    user=request.user,
                    action_type=AuditLog.AuditAction.UPDATE,
                    before=before_jornada,
                    after=after_jornada,
                    reason=f'Modificación de jornada laboral en empresa {company.name}',
                )

            # 🔐 Auditoría: Cierre automático
            if before_cierre != after_cierre:
                AuditLog.objects.create(
                    id=uuid4(),
                    table_name='company_settings',
                    record_id=settings_obj.id,
                    user=request.user,
                    action_type=AuditLog.AuditAction.UPDATE,
                    before=before_cierre,
                    after=after_cierre,
                    reason=f'Modificación de cierre automático en empresa {company.name}',
                )

        return redirect('entity_info')

    context = {
        'company':   company,
        'user_role': user_role,
        'settings':  settings_obj,
        'weekdays':  WEEKDAY,
    }
    context.update(delegation_context)

    return render(request, 'team/entity_info.html', context)

 
# ── API: solicitar ausencia ────────────────────────────────────────────────────
 
@login_required
@require_POST
def api_leave_request_create(request):
    company = get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)
 
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
 
    start_date = data.get('start_date')
    end_date   = data.get('end_date')
    leave_type = data.get('leave_type', 'other')
    leave_reason = data.get('leave_reason', LeaveRequest.LeaveReason.OTHER)
    reason_note  = data.get('reason_note', '')
 
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
        return JsonResponse({'error': 'Tipo de solicitud no válido'}, status=400)
 
    if leave_reason not in LeaveRequest.LeaveReason.values:
        return JsonResponse({'error': 'Motivo no válido'}, status=400)
 
    leave = LeaveRequest.objects.create(
        user         = request.user,
        company      = company,
        leave_type   = leave_type,
        leave_reason = leave_reason,
        reason_note  = reason_note,
        start_date   = start,
        end_date     = end,
        status       = LeaveRequest.LeaveStatus.PENDING,
    )
 
    log_leave(leave, request.user, AuditLog.AuditAction.CREATE,
               reason=reason_note or 'Solicitud creada por el empleado')
    
    return JsonResponse({
        'ok':      True,
        'id':      str(leave.id),
        'message': 'Solicitud enviada correctamente',
    }, status=201)
 
@login_required
def api_leave_upload_attachment(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    archivo = request.FILES.get('attachment')

    if archivo:
        # Limpiamos nombre de usuario (ej: "Juan Perez" -> "JuanPerez")
        nombre_usuario = f"{request.user.username}{request.user.surname}".replace(" ", "")
        
        # Creamos el timestamp y sacamos la extensión
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        _, extension = os.path.splitext(archivo.name)
        
        # Nombre final: JuanPerez_20240520_123000.pdf
        nombre_final = f"{nombre_usuario}_{timestamp}{extension.lower()}"
        
        # Ruta relativa: justificantes/ID_SOLICITUD/archivo.pdf
        ruta = f"justificantes/{leave_id}/{nombre_final}"
        
        # Borrar el anterior si existe para no llenar el servidor de basura
        if leave.attachment_path:
            default_storage.delete(leave.attachment_path)
            
        # Guardar físicamente (Django crea las carpetas solo)
        default_storage.save(ruta, ContentFile(archivo.read()))
        
        # Guardar la ruta en la base de datos
        leave.attachment_path = ruta
        leave.save()
        
        return JsonResponse({'ok': True, 'message': 'Subido con éxito'})
    
# ── API: cancelar solicitud (empleado) ────────────────────────────────────────
 
@login_required
@require_POST
def api_leave_request_cancel(request, leave_id):
    """El empleado puede cancelar sus propias solicitudes pendientes."""
    company = get_company(request)
    leave = get_object_or_404(LeaveRequest, id=leave_id, user=request.user, company=company)
 
    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Solo se pueden cancelar solicitudes pendientes'}, status=400)
 
    before = serialize_leave(leave)
    leave.status = LeaveRequest.LeaveStatus.CANCELED
    leave.save(update_fields=['status', 'updated_at'])
    log_leave(leave, request.user, AuditLog.AuditAction.VOIDED,
               before=before, reason='Cancelación por el empleado')

    return JsonResponse({'ok': True})

# ── API: solicitudes resueltas ────────────────────────────────────────────────

@login_required
def api_leave_resolved(request):
    """
    Devuelve solicitudes resueltas (aprobadas, rechazadas, canceladas).
    - Empleados: siempre sus propias solicitudes.
    - Managers: pueden filtrar por ?user_id=<uuid> (empleado concreto)
                o ?user_id=all (todos los empleados de la empresa).
                Sin parámetro → sus propias solicitudes.
    """
    company = get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    is_manager = check_is_manager(request, company)
    user_id    = request.GET.get('user_id', '')

    resolved_statuses = [
        LeaveRequest.LeaveStatus.APPROVED,
        LeaveRequest.LeaveStatus.REJECTED,
        LeaveRequest.LeaveStatus.CANCELED,
    ]

    base_qs = LeaveRequest.objects.filter(
        company=company,
        status__in=resolved_statuses,
    ).select_related('user', 'reviewed_by').order_by('-updated_at')

    if is_manager and user_id == 'all':
        leaves = base_qs[:50]
    elif is_manager and user_id:
        try:
            target = get_object_or_404(Users, id=user_id)
        except Exception:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=400)
        leaves = base_qs.filter(user=target)[:30]
    else:
        leaves = base_qs.filter(user=request.user)[:30]

    show_user_col = is_manager and user_id in ('all', '') is False or (is_manager and user_id == 'all')

    data = []
    for l in leaves:
        data.append({
            'id':               str(l.id),
            'user_name':        f"{l.user.username} {l.user.surname}".strip(),
            'leave_type':       l.get_leave_type_display(),
            'leave_reason':     l.get_leave_reason_display(),
            'start_date':       l.start_date.strftime('%d/%m/%Y'),
            'end_date':         l.end_date.strftime('%d/%m/%Y'),
            'status':           l.status,
            'status_display':   l.get_status_display(),
            'reason_note':      l.reason_note or '',
            'review_note':      l.review_note or '',
            'reviewed_by':      f"{l.reviewed_by.username} {l.reviewed_by.surname}".strip() if l.reviewed_by else '',
            'attachment_path':  l.attachment_path or '',
        })

    return JsonResponse({
        'requests':      data,
        'show_user_col': is_manager and user_id == 'all',
    })

 
# ── Vistas de equipo ───────────────────────────────────────────────────────────

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