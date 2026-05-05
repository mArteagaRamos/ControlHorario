from datetime import timedelta
from django.http import HttpResponse
from django.shortcuts import render, redirect
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
from audit.models import AuditLog
from uuid import uuid4

# Import centralized decorators and services
from core.decorators import auditor_cannot_access, manager_or_admin_with_delegation_check
from core.services import get_company, is_manager as check_is_manager, log_leave

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
                           reason=reason_note or 'Solicitud creada desde calendario',
                           source='web')

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
        company.name.title = request.POST.get('name', company.name.title).strip()
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

            # Auditoría: Jornada laboral
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
                    source='web' # Añadido
                )

            # Auditoría: Cierre automático
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
                    source='web' # Añadido
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