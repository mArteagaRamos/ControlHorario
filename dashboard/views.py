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
from requests.models import LeaveRequest
from audit.models import AuditLog
from uuid import uuid4

# Import centralized decorators and services
from core.decorators import auditor_cannot_access
from core.services import get_company, is_manager as check_is_manager, log_leave, get_effective_context

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

    delegation_context = get_effective_context(request)

    # Determine which user to work with
    if delegation_context['is_delegating']:
        user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
        company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
        if not user or not company:
            messages.error(request, 'Usuario o empresa delegada no encontrada.')
            return redirect('calendar')
    else:
        user = request.user
        company = get_company(request)

    is_manager = check_is_manager(request, company)

    # ── POST logic ──
    if request.method == 'POST':
        leave_type   = request.POST.get('leave_type')
        leave_reason = request.POST.get('leave_reason')
        start_date_str = request.POST.get('start_date')
        end_date_str   = request.POST.get('end_date')
        reason_note  = request.POST.get('reason_note', '').strip()

        if start_date_str and end_date_str:
            try:
                start = parse_date(start_date_str)
                end   = parse_date(end_date_str)

                leave = LeaveRequest.objects.create(
                    user=user,
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

    # ── GET logic ──
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
    context.update(delegation_context)
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