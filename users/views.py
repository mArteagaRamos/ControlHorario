# ---------- Backend Views: users/views.py ----------

import json
from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login ,logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from uuid import uuid4
from .forms import (
    LoginForm, CompanyForm, CompanySelectLoginForm,
    WorkerCreateForm, WorkerSelectForm, SetPasswordForm,
)
from .email_utils import send_new_user_email, send_existing_user_email
from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompany, CompanySettings, CorrectionRequests
from django.views.decorators.cache import never_cache



# ── Helpers ────────────────────────────────────────────────────────────────────

def validate_manager_role_change(user, company, new_role):
    """
    Validates that changing a user's role won't leave the company without managers.

    Args:
        user: Users instance being edited
        company: Companies instance context
        new_role: The new role being assigned (RoleChoices value)

    Returns:
        Tuple: (is_valid: bool, message: str or None)
        If valid, returns (True, None)
        If invalid, returns (False, error_message)
    """
    try:
        with transaction.atomic():
            # Only validate if changing TO something other than manager
            if new_role == UserCompany.RoleChoices.MANAGER:
                return (True, None)

            # Get current membership (lock the row to avoid race conditions)
            current_membership = (
                UserCompany.objects
                .select_for_update()
                .filter(user=user, company=company)
                .first()
            )

            # If no membership or not currently a manager, no restriction
            if not current_membership or current_membership.role == UserCompany.RoleChoices.EMPLOYEE:
                return (True, None)

            # User IS a manager and wants to change to employee
            # Count other managers in the company (excluding this user)
            other_managers_count = (
                UserCompany.objects
                .filter(
                    company=company,
                    role=UserCompany.RoleChoices.MANAGER
                )
                .exclude(user=user)
                .count()
            )

            if other_managers_count == 0:
                return (False, 'No se puede cambiar el rol: es el único Manager de la empresa.')

            return (True, None)
    except Exception as e:
        # If transaction fails, fail safely and log
        return (False, f'Error al validar el rol: {str(e)}')


def compute_worked_seconds(entry):
    if not entry.clock_in or not entry.clock_out:
        return 0
    elapsed = entry.clock_out - entry.clock_in
    total = int(elapsed.total_seconds())
    pause_seconds = 0
    pause_start = None
    events = TimeEntryEvent.objects.filter(time_entry=entry).order_by('timestamp')
    for ev in events:
        if ev.event_type == TimeEntryEvent.EventType.PAUSE_START:
            pause_start = ev.timestamp
        elif ev.event_type == TimeEntryEvent.EventType.PAUSE_END and pause_start:
            pause_end = ev.timestamp
            if pause_end > pause_start:
                pause_seconds += int((pause_end - pause_start).total_seconds())
            pause_start = None
    return max(0, total - pause_seconds)


def parse_local_datetime(value):
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def get_display_date(value):
    if not value:
        return None
    if timezone.is_naive(value):
        return value.date()
    return timezone.localtime(value).date()


def get_or_create_demo_user():
    user = Users.objects.first()
    if not user:
        user = Users.objects.create(
            id=uuid4(), username='demo', email='demo@example.com',
            surname='Demo', password='demo'
        )
    return user


def format_date_spanish(date_obj):
    """Format date as '1 ENERO, 2026' format"""
    if not date_obj:
        return None
    months = {
        1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
        5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
        9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
    }
    return f"{date_obj.day} {months[date_obj.month]}, {date_obj.year}"


def ensure_membership(user):
    membership = UserCompany.objects.filter(user=user).order_by('-joined_at').first()
    if not membership:
        company = Companies.objects.first()
        if not company:
            company = Companies.objects.create(
                id=uuid4(), name='DemoCorp', legal_name='Demo Corporation'
            )
        membership = UserCompany.objects.create(
            id=uuid4(), user=user, company=company,
            role=UserCompany.RoleChoices.EMPLOYEE
        )
    return membership


# ── Auth ───────────────────────────────────────────────────────────────────────

def login_view(request):
    form                  = LoginForm(request)
    company_form          = None
    show_company_selector = False
    set_password_form     = None
    show_set_password     = False

    if request.method == 'POST':
        step = request.POST.get('step', 'credentials')

        # ── Step 1: login ──────────────────────────────────────────────────────
        if step == 'credentials':
            form = LoginForm(request, data=request.POST)
            if form.is_valid():
                email    = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user     = authenticate(request, username=email, password=password)

                if user is not None:
                    if not user.must_change_password:
                        auth_login(request, user)
                        # Clear navigation history on login
                        request.session['nav_history'] = []
                        set_password_form = SetPasswordForm()
                        show_set_password = True
                    else:
                        memberships = UserCompany.objects.filter(
                            user=user
                        ).select_related('company')
                        auth_login(request, user)
                        # Clear navigation history on login
                        request.session['nav_history'] = []
                        if memberships.count() > 1:
                            company_form = CompanySelectLoginForm(companies=memberships)
                            show_company_selector = True
                            request.session['pending_company_selection'] = True
                        else:
                            if memberships.first():
                                request.session['company_id'] = str(
                                    memberships.first().company.id
                                )
                            return redirect('home_timetracking')
                else:
                    messages.error(request, 'Email o contraseña incorrectos.')

        # ── Step 2: set password ───────────────────────────────────────────────
        elif step == 'set_password':
            if not request.user.must_change_password:
                return redirect('login')

            set_password_form = SetPasswordForm(request.POST)
            show_set_password = True

            if set_password_form.is_valid():
                new_password = set_password_form.cleaned_data['new_password']
                user         = request.user
                user.set_password(new_password)
                user.must_change_password = True
                user.save(update_fields=['password', 'must_change_password'])

                updated_user = authenticate(
                    request, username=user.email, password=new_password
                )
                if updated_user:
                    auth_login(request, updated_user)

                memberships = UserCompany.objects.filter(
                    user=user
                ).select_related('company')

                if memberships.count() > 1:
                    company_form          = CompanySelectLoginForm(companies=memberships)
                    show_company_selector = True
                    show_set_password     = False
                    set_password_form     = None
                    request.session['pending_company_selection'] = True
                else:
                    if memberships.first():
                        request.session['company_id'] = str(
                            memberships.first().company.id
                        )
                    return redirect('home_timetracking')

        # ── Step 3: select company ────────────────────────────────────────
        elif step == 'select_company':
            if not request.user.must_change_password:
                return redirect('login')

            memberships  = UserCompany.objects.filter(
                user=request.user
            ).select_related('company')
            company_form = CompanySelectLoginForm(request.POST, companies=memberships)

            if company_form.is_valid():
                company_id = company_form.cleaned_data['company_id']
                membership = memberships.filter(company_id=company_id).first()
                if membership:
                    request.session['company_id'] = str(company_id)
                    request.session.pop('pending_company_selection', None)
                    return redirect('home_timetracking')

            show_company_selector = True

    return render(request, 'login/login.html', {
        'form':                  form,
        'company_form':          company_form,
        'show_company_selector': show_company_selector,
        'set_password_form':     set_password_form,
        'show_set_password':     show_set_password,
    })

#── Logout ─────────────────────────────────────────────────────────────────────

@login_required
def logout_view(request):
    """Cierra la sesión del usuario y redirige al login."""
    auth_logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


# ── AJAX lookup endpoints ──────────────────────────────────────────────────────
def _company_to_dict(company, include_created=False):
    result = {
        'id':         str(company.id),
        'name':       company.name,
        'legal_name': company.legal_name,
        'tax_id':     company.tax_id,
    }
    if include_created and hasattr(company, 'created_at'):
        result['created_at'] = company.created_at.strftime('%d/%m/%Y') if company.created_at else '--'
    return result

@login_required
def lookup_company(request):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    tax_id = request.GET.get('tax_id', '').strip()
    name  = request.GET.get('name', '').strip()
    include_created = request.GET.get('include_created', 'true').lower() == 'true'

    # ── Búsqueda por nombre (autocompletado) → múltiples resultados ───────────
    if name:
        if len(name) < 2:
            return JsonResponse({'results': []})
        companies = (
            Companies.objects
            .filter(
                Q(name__icontains=name) | Q(legal_name__icontains=name)
                )
                [:10]
        )
        results = [_company_to_dict(c, include_created=include_created) for c in companies]
        return JsonResponse({'results': results})

    # ── Búsqueda por CIF → resultado único ────────────────────────────────────
    if not tax_id:
        return JsonResponse({'error': 'Proporciona tax_id o name'}, status=400)

    company = Companies.objects.filter(tax_id__iexact=tax_id).first()
    if not company:
        return JsonResponse({'found': False})

    return JsonResponse({'found': True, **_company_to_dict(company, include_created=include_created)})


def _user_to_dict(user, include_companies=False):
    """Serializes a Users instance to a dict for JSON responses."""
    result = {
        'id': str(user.id),
        'username': user.username,
        'surname':  user.surname,
        'dni':      user.dni,
        'email':    user.email,
        'status':   user.status,
    }
    if include_companies:
        companies = UserCompany.objects.filter(user=user).select_related('company')
        result['companies'] = [
            {'id': str(c.company.id), 'name': c.company.name, 'tax_id': c.company.tax_id or '--'}
            for c in companies
        ]
    return result

@login_required
def lookup_user(request):
    dni      = request.GET.get('dni', '').strip()
    email      = request.GET.get('email', '').strip()
    name     = request.GET.get('name', '').strip()
    company_id = request.GET.get('company_id', '').strip()
    include_companies = request.GET.get('include_companies', 'false').lower() == 'true'

    # Check if user is admin
    is_admin = request.user.is_admin

    # Build company filter
    if company_id:
        # Explicit company_id provided
        company_filter = {'company_id': company_id}
    elif is_admin and name:
        # Admin doing name search: search all users WITHOUT company filter
        company_filter = None
    else:
        # Regular user or non-name search: use their current company
        company = getattr(request, 'company', None)
        if not company:
            return JsonResponse({'error': 'Sin empresa asignada'}, status=400)
        company_filter = {'company': company}

    # ── Name search → multiple results ────────────────────────────────────────
    if name:
        if len(name) < 2:
            return JsonResponse({'results': []})

        if company_filter is None:
            # Admin search: all users matching criteria WITH ACTIVE MEMBERSHIPS
            users = (
                Users.objects
                .filter(Q(username__icontains=name) | Q(surname__icontains=name))
                .filter(usercompany__deleted_at__isnull=True)  # Only users with active memberships
                .distinct()[:10]
            )
            results = [_user_to_dict(u, include_companies=include_companies) for u in users]
        else:
            # Regular search with company filter
            memberships = (
                UserCompany.objects
                .filter(
                    Q(user__username__icontains=name) | Q(user__surname__icontains=name),
                    **company_filter,
                    deleted_at__isnull=True  # Only active memberships
                )
                .select_related('user')[:10]
            )
            results = [_user_to_dict(m.user, include_companies=include_companies) for m in memberships]
        return JsonResponse({'results': results})

    # ── Email search → single result ───────────────────────────────────────────
    if email:
        if company_filter is None:
            user = Users.objects.filter(email__iexact=email).first()
            if not user:
                return JsonResponse({'found': False})
            return JsonResponse({'found': True, **_user_to_dict(user, include_companies=include_companies)})
        else:
            membership = (
                UserCompany.objects
                .filter(user__email__iexact=email, **company_filter)
                .select_related('user')
                .first()
            )
            if not membership:
                return JsonResponse({'found': False})
            return JsonResponse({'found': True, **_user_to_dict(membership.user, include_companies=include_companies)})

    # ── DNI search → single result ─────────────────────────────────────────────
    if dni:
        if company_filter is None:
            user = Users.objects.filter(dni__iexact=dni).first()
            if not user:
                return JsonResponse({'found': False})
            return JsonResponse({'found': True, **_user_to_dict(user, include_companies=include_companies)})
        else:
            membership = (
                UserCompany.objects
                .filter(user__dni__iexact=dni, **company_filter)
                .select_related('user')
                .first()
            )
            if not membership:
                return JsonResponse({'found': False})
            return JsonResponse({'found': True, **_user_to_dict(membership.user, include_companies=include_companies)})

    return JsonResponse({'error': 'Proporciona email, dni o name para buscar'}, status=400)


@login_required
def check_last_manager(request):
    """
    Check if a user is the last manager in their company.
    Used for frontend UX: deshabilitar dropdown de rol si es el único manager.

    Params:
        user_id: UUID del usuario a verificar
        company_id: UUID de la empresa (opcional, usa request.company si no se proporciona)
    """
    user_id = request.GET.get('user_id', '').strip()
    company_id = request.GET.get('company_id', '').strip()

    if not user_id:
        return JsonResponse({'error': 'user_id es obligatorio'}, status=400)

    if not company_id:
        company = getattr(request, 'company', None)
        if not company:
            return JsonResponse({'error': 'Sin empresa asignada'}, status=400)
        company_id = str(company.id)

    try:
        # Buscar si el usuario tiene un rol en esa empresa
        membership = UserCompany.objects.filter(
            user_id=user_id,
            company_id=company_id
        ).first()

        if not membership:
            return JsonResponse({
                'is_manager': False,
                'is_last_manager': False,
                'other_managers': 0
            })

        # Si no es manager, no hay restricción
        if membership.role != UserCompany.RoleChoices.MANAGER:
            return JsonResponse({
                'is_manager': False,
                'is_last_manager': False,
                'other_managers': -1  # N/A
            })

        # Contar otros managers en la empresa
        other_managers = UserCompany.objects.filter(
            company_id=company_id,
            role=UserCompany.RoleChoices.MANAGER
        ).exclude(user_id=user_id).count()

        is_last_manager = (other_managers == 0)

        return JsonResponse({
            'is_manager': True,
            'is_last_manager': is_last_manager,
            'other_managers': other_managers
        })

    except Exception as e:
        return JsonResponse({
            'error': f'Error al verificar estado de manager: {str(e)}'
        }, status=500)


# ── Register unified ─────────────────────────────────────────────────────────

@login_required
def register_unified(request):
    is_admin     = request.user.is_admin
    current_role = request.role

    if not is_admin and current_role != UserCompany.RoleChoices.MANAGER:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home_timetracking')

    company_mode  = 'create'
    worker_action = 'create'

    company_form  = CompanyForm()
    worker_create = WorkerCreateForm()
    worker_select = WorkerSelectForm()

    if request.method == 'POST':
        company_mode  = request.POST.get('company_mode',  'create')
        worker_action = request.POST.get('worker_action', 'create')

        company_form  = CompanyForm(request.POST)
        worker_create = WorkerCreateForm(request.POST)
        worker_select = WorkerSelectForm(request.POST)

        errors      = []
        company_obj = None
        worker_user = None
        worker_role = None
        is_new_user = False
        temp_password = None

        # Get effective context (delegation info if any)
        delegation_context = {}
        if request.user.is_admin:
            from audit.views import get_effective_context
            delegation_context = get_effective_context(request)

        # ── 1. Resolve company ────────────────────────────────────────────────
        if is_admin:
            # Check if using delegated company
            if delegation_context.get('is_delegating') and delegation_context.get('delegated_company_id'):
                company_obj = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
                if not company_obj:
                    errors.append('Empresa delegada no encontrada.')
            elif company_mode == 'create':
                tax_id           = request.POST.get('tax_id', '').strip()
                existing_company = (
                    Companies.objects.filter(tax_id__iexact=tax_id).first()
                    if tax_id else None
                )
                if existing_company:
                    if company_form.is_valid():
                        for field in ['name', 'legal_name', 'tax_id']:
                            value = company_form.cleaned_data.get(field)
                            if value:
                                setattr(existing_company, field, value)
                        existing_company.updated_at = timezone.now()
                        existing_company.save()
                        company_obj = existing_company
                    else:
                        errors.append('Corrige los datos de la empresa.')
                else:
                    if company_form.is_valid():
                        company_obj            = company_form.save(commit=False)
                        company_obj.id         = uuid4()
                        company_obj.created_at = timezone.now()
                        company_obj.updated_at = timezone.now()
                        company_obj.save()
                        CompanySettings.objects.create(company=company_obj)
                    else:
                        errors.append('Corrige los datos de la empresa.')

            else:  # company_mode == 'select'
                company_id  = request.POST.get('company_id', '').strip()
                company_obj = Companies.objects.filter(id=company_id).first()
                if company_obj:
                    company_form = CompanyForm(request.POST, instance=company_obj)
                    if company_form.is_valid():
                        company_obj            = company_form.save(commit=False)
                        company_obj.updated_at = timezone.now()
                        company_obj.save()
                else:
                    errors.append('No se encontró la empresa. Busca de nuevo por CIF.')
        else:
            company_obj = request.company

        # ── 2. Resolve worker ─────────────────────────────────────────────
        if not errors:
            email         = request.POST.get('email', '').strip()
            existing_user = None
            worker_role   = request.POST.get('role', UserCompany.RoleChoices.EMPLOYEE)

            if not email:
                errors.append('El email es obligatorio para el trabajador.')
            else:
                existing_user = (
                    Users.objects.filter(email__iexact=email).first()
                    if email else None
                )
                worker_role = request.POST.get(
                    'role', UserCompany.RoleChoices.EMPLOYEE
                )

            if existing_user:
                active_form = (
                    WorkerSelectForm(request.POST, instance=existing_user)
                    if worker_action == 'select'
                    else WorkerCreateForm(request.POST, instance=existing_user)
                )
                if active_form.is_valid():
                    worker_user          = active_form.save(commit=False)
                    worker_user.is_admin = False
                    worker_user.save(update_fields=['username', 'surname','dni', 'status'])
                else:
                    errors.append('Corrige los datos del trabajador.')
            else:
                if worker_create.is_valid():
                    worker_user          = worker_create.save(commit=False)
                    worker_user.id       = uuid4()
                    worker_user.is_admin = False
                    worker_user.must_change_password = False
                    temp_password = worker_create.cleaned_data.get('password', '')
                    if temp_password:
                        worker_user.set_password(temp_password)
                    worker_user.save()
                    is_new_user = True
                else:
                    errors.append('Corrige los datos del trabajador.')

        # ── 3. Create/update membership ─────────────────────────────────────
        if not errors and worker_user and company_obj:
            role       = worker_role or UserCompany.RoleChoices.EMPLOYEE
            membership = UserCompany.objects.filter(
                user=worker_user,
                company=company_obj,
            ).first()
            if membership:
                if role and membership.role != role:
                    # Validate that changing roles won't leave company without managers
                    is_valid, error_message = validate_manager_role_change(worker_user, company_obj, role)
                    if not is_valid:
                        errors.append(error_message)
                    else:
                        membership.role = role
                        membership.save(update_fields=['role'])
                        # Send email to existing user registering in new company
                        send_existing_user_email(worker_user, company_obj, role)
                else:
                    # Send email to existing user registering in new company
                    send_existing_user_email(worker_user, company_obj, role)
            else:
                UserCompany.objects.create(
                    id=uuid4(),
                    user=worker_user,
                    company=company_obj,
                    role=role,
                )
                # Send appropriate email based on user type
                if is_new_user and temp_password:
                    send_new_user_email(worker_user, temp_password, company_obj)
                else:
                    send_existing_user_email(worker_user, company_obj, role)

            # Only show success if no validation errors occurred
            if not errors:
                messages.success(request, 'Trabajador registrado correctamente.')
                return redirect('home_timetracking')

        for error in errors:
            messages.error(request, error)

    return render(request, 'login/register_unified.html', {
        'is_admin':      is_admin,
        'current_role':  current_role,
        'company_form':  company_form,
        'worker_create': worker_create,
        'worker_select': worker_select,
        'company_mode':  company_mode,
        'worker_action': worker_action,
        'manager_company_id': str(request.company.id) if not is_admin and request.company else '',
    })


# ── Company switch ──────────────────────────────────────────────────────────

@login_required
def switch_company(request, company_id):
    membership = UserCompany.objects.filter(
        user=request.user,
        company_id=company_id
    ).first()
    if not membership:
        messages.error(request, 'No tienes acceso a esta empresa.')
    else:
        request.session['company_id'] = str(company_id)
    return redirect('home_timetracking')


# ── User panel ───────────────────────────────────────────────────────────

@login_required
@never_cache
def workday(request):
    from audit.views import get_effective_context

    delegation_context = get_effective_context(request)

    # Determine which user to work with
    if delegation_context['is_delegating']:
        user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
        company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
        if not user or not company:
            messages.error(request, 'Usuario o empresa delegada no encontrada.')
            return redirect('home_timetracking')
    else:
        user = Users.objects.filter(email=request.user.email).first()
        company = request.company

        if not user:
            messages.error(request, 'Usuario no encontrado en el sistema.')
            return redirect('home_timetracking')

        if not company:
            messages.error(request, 'No tienes empresa asignada.')
            return redirect('home_timetracking')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'request_correction':
            entry_id = request.POST.get('entry_id')
            reason = request.POST.get('reason', '').strip()
            new_clock_in_str = request.POST.get('new_clock_in')
            new_clock_out_str = request.POST.get('new_clock_out')

            entry = TimeEntries.objects.filter(id=entry_id, user=user).first()

            if entry and reason and new_clock_in_str and new_clock_out_str:
                # ── SECURITY CHECK: Avoid duplicates ─────────────────────
                # Verify whether a 'pending' incident already exists for this record
                incidencia_existente = CorrectionRequests.objects.filter(
                    time_entry=entry,
                    status='pending'
                ).exists()

                if incidencia_existente:
                    messages.error(request, 'Ya existe una solicitud de corrección pendiente para este registro.')
                    return redirect('workday')
                # ──────────────────────────────────────────────────────────────────────

                new_in = parse_local_datetime(new_clock_in_str) if new_clock_in_str else None
                new_out = parse_local_datetime(new_clock_out_str) if new_clock_out_str else None

                if (new_clock_in_str and new_in is None) or \
                   (new_clock_out_str and new_out is None):
                    if request.headers.get('HX-Request'):
                        return HttpResponse('Formato de fecha no válido.', status=400)
                    messages.error(request, 'El formato de fecha y hora no es válido.')
                    return redirect('workday')

                CorrectionRequests.objects.create(
                    id=uuid4(),
                    time_entry=entry,
                    requester=user,
                    reason=reason,
                    new_clock_in=new_in,
                    new_clock_out=new_out,
                    status='pending',
                )

                if request.headers.get('HX-Request'):
                    return HttpResponse(status=204)

                messages.success(request, 'Solicitud de corrección enviada.')
                return redirect('workday')

            else:
                if request.headers.get('HX-Request'):
                    return HttpResponse('Datos incompletos o inválidos.', status=400)
                messages.error(request, 'Datos incompletos o inválidos.')
                return redirect('workday')

        elif action == 'edit_correction':
            request_id = request.POST.get('request_id')
            reason = request.POST.get('reason', '').strip()
            new_clock_in_str = request.POST.get('new_clock_in')
            new_clock_out_str = request.POST.get('new_clock_out')

            # Buscamos la solicitud (asegurándonos de que es de este usuario y sigue pendiente)
            correction = CorrectionRequests.objects.filter(id=request_id, requester=user, status='pending').first()

            if correction and reason and new_clock_in_str and new_clock_out_str:
                correction.new_clock_in = parse_local_datetime(new_clock_in_str)
                correction.new_clock_out = parse_local_datetime(new_clock_out_str)
                correction.reason = reason
                correction.save()

                if request.headers.get('HX-Request'):
                    return HttpResponse(status=204)

                messages.success(request, 'Solicitud actualizada correctamente.')
                return redirect('workday')
            else:
                if request.headers.get('HX-Request'):
                    return HttpResponse('Datos inválidos o solicitud no encontrada.', status=400)
                messages.error(request, 'Error al actualizar la solicitud.')
                return redirect('workday')

        return redirect('workday')

    # ── GET: build data for the template ──────────────────────────────────
    entries = TimeEntries.objects.filter(
        user=user,
        company=company,
    ).order_by('-date', '-clock_in')[:20]

    correction_requests = CorrectionRequests.objects.filter(
        requester=user,
        time_entry__company=company,
    ).order_by('-request_date')[:20]

    entry_rows = []
    for e in entries:
        worked_seconds = compute_worked_seconds(e)
        hours = worked_seconds // 3600
        minutes = (worked_seconds % 3600) // 60
        entry_rows.append({
            'id': e.id,
            'date': format_date_spanish(e.date),
            'date_iso': e.date.isoformat() if e.date else None,
            'clock_in': e.clock_in,
            'clock_out': e.clock_out,
            'status': e.status,
            'worked': f"{hours}:{minutes:02d}",
        })

    request_rows = []
    for r in correction_requests:
        entry_date = r.time_entry.date if r.time_entry else None
        request_rows.append({
            'id': r.id,
            'entry_date': format_date_spanish(entry_date),
            'entry_date_iso': entry_date.isoformat() if entry_date else None,
            'request_date': format_date_spanish(r.request_date.date() if r.request_date else None),
            'new_clock_in': r.new_clock_in if hasattr(r, 'new_clock_in') else None,
            'new_clock_out': r.new_clock_out if hasattr(r, 'new_clock_out') else None,
            'reason': r.reason,
            'correction_note': r.correction_note,
            'status': r.status,
        })

    context = {
        'entry_rows': entry_rows,
        'request_rows': request_rows,
    }
    context.update(delegation_context)

    return render(request, 'user_panel/workday.html', context)


# ── ADMIN DASHBOARD ──────────────────────────────────────────────────────────

def admin_only_required(view_func):
    """Decorator to ensure only admin users can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.must_change_password:
            return render(request, 'error/sin_loguear.html', status=401)

        if not request.user.is_admin:
            return render(request, 'error/sin_permisos.html', status=403)

        return view_func(request, *args, **kwargs)
    return _wrapped_view

@admin_only_required
@never_cache
def admin_dashboard(request):
    """Admin dashboard to manage companies and workers globally"""

    return render(request, 'admin/admin_dashboard.html')


# ── DELEGATED WORKER SYSTEM ────────────────────────────────────────────────

@admin_only_required
@require_POST
def select_delegated_worker(request):
    """
    Admin selecciona un trabajador para delegar las acciones.
    Guarda user_id, name y company_id en sesión.

    POST params:
        worker_id: UUID del usuario a delegar
        company_id: UUID de la empresa donde se actúa
    """
    worker_id = request.POST.get('worker_id', '').strip()
    company_id = request.POST.get('company_id', '').strip()

    if not worker_id:
        return JsonResponse({'error': 'worker_id es obligatorio'}, status=400)

    if not company_id:
        return JsonResponse({'error': 'company_id es obligatorio'}, status=400)

    # Validar que el usuario existe
    delegated_user = Users.objects.filter(id=worker_id).first()
    if not delegated_user:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

    # Validar que la empresa existe
    delegated_company = Companies.objects.filter(id=company_id).first()
    if not delegated_company:
        return JsonResponse({'error': 'Empresa no encontrada'}, status=404)

    # Validar que el usuario pertenece a esa empresa
    membership = UserCompany.objects.filter(
        user=delegated_user,
        company=delegated_company
    ).first()
    if not membership:
        return JsonResponse({'error': 'El usuario no pertenece a esa empresa'}, status=403)

    # Guardar en sesión
    request.session['delegated_user_id'] = str(worker_id)
    request.session['delegated_user_name'] = delegated_user.username
    request.session['delegated_company_id'] = str(company_id)
    request.session['delegated_user_role'] = membership.role

    return JsonResponse({'success': True})


@admin_only_required
@require_POST
def clear_delegated_worker(request):
    """
    Admin cancela la delegación de usuario.
    Limpia las variables de sesión asociadas.
    """
    request.session.pop('delegated_user_id', None)
    request.session.pop('delegated_user_name', None)
    request.session.pop('delegated_company_id', None)
    request.session.pop('delegated_user_role', None)

    return JsonResponse({'success': True})


# ────────────────────────────────────────────────────────────────────
# SOFT DELETE MANAGEMENT VIEWS (ADMIN ONLY)
# ────────────────────────────────────────────────────────────────────

@admin_only_required
def deleted_records(request):
    """
    Vista para mostrar todos los registros eliminados (soft-deleted) agrupados por tipo.
    Solo accesible para administradores.
    """
    # Get all deleted records by type
    deleted_users = Users.objects.only_deleted().order_by('-deleted_at')
    deleted_companies = Companies.objects.only_deleted().order_by('-deleted_at')
    deleted_user_companies = UserCompany.objects.only_deleted().order_by('-deleted_at')
    deleted_company_settings = CompanySettings.objects.only_deleted().order_by('-deleted_at')
    deleted_corrections = CorrectionRequests.objects.only_deleted().order_by('-deleted_at')
    deleted_time_entries = TimeEntries.objects.only_deleted().order_by('-deleted_at')
    deleted_time_events = TimeEntryEvent.objects.only_deleted().order_by('-deleted_at')

    # Para cada usuario eliminado, obtener sus empresas asociadas (incluyendo membresías eliminadas)
    users_with_companies = []
    for user in deleted_users:
        companies = Companies.objects.all_with_deleted().filter(
            usercompany__user=user
        ).distinct()
        users_with_companies.append({
            'user': user,
            'companies': companies
        })

    context = {
        'deleted_users': users_with_companies,
        'deleted_companies': deleted_companies,
        'deleted_user_companies': deleted_user_companies,
        'deleted_company_settings': deleted_company_settings,
        'deleted_corrections': deleted_corrections,
        'deleted_time_entries': deleted_time_entries,
        'deleted_time_events': deleted_time_events,
        'total_deleted': (
            deleted_users.count() +
            deleted_companies.count() +
            deleted_user_companies.count() +
            deleted_company_settings.count() +
            deleted_corrections.count() +
            deleted_time_entries.count() +
            deleted_time_events.count()
        ),
    }

    return render(request, 'admin/deleted_records.html', context)


@admin_only_required
@require_POST
def restore_record(request):
    """
    Restaura un registro eliminado (soft-deleted).
    Solo accesible para administradores.

    POST params:
        record_type: Tipo de registro (users, companies, user_companies, company_settings, corrections, time_entries, time_events)
        record_id: UUID del registro a restaurar
    """
    record_type = request.POST.get('record_type', '').strip()
    record_id = request.POST.get('record_id', '').strip()

    if not record_type or not record_id:
        messages.error(request, "Tipo de registro e ID son obligatorios.")
        return redirect('deleted_records')

    try:
        # Map record types to models
        models_map = {
            'users': Users,
            'companies': Companies,
            'user_companies': UserCompany,
            'company_settings': CompanySettings,
            'corrections': CorrectionRequests,
            'time_entries': TimeEntries,
            'time_events': TimeEntryEvent,
        }

        if record_type not in models_map:
            messages.error(request, "Tipo de registro no válido.")
            return redirect('deleted_records')

        model = models_map[record_type]

        # Get the deleted record
        record = model.objects.all_with_deleted().filter(id=record_id).first()

        if not record:
            messages.error(request, f"Registro de tipo '{record_type}' con ID '{record_id}' no encontrado.")
            return redirect('deleted_records')

        if record.deleted_at is None:
            messages.warning(request, "Este registro no está eliminado.")
            return redirect('deleted_records')

        # Restore the record
        model.objects.restore(record)
        messages.success(request, f"Registro de tipo '{record_type}' restaurado correctamente.")

    except Exception as e:
        messages.error(request, f"Error al restaurar el registro: {str(e)}")

    return redirect('deleted_records')


@admin_only_required
@require_POST
def permanently_delete_record(request):
    """
    Elimina permanentemente un registro eliminado (hard-delete).
    Solo accesible para administradores.

    POST params:
        record_type: Tipo de registro
        record_id: UUID del registro a eliminar permanentemente
    """
    record_type = request.POST.get('record_type', '').strip()
    record_id = request.POST.get('record_id', '').strip()

    if not record_type or not record_id:
        messages.error(request, "Tipo de registro e ID son obligatorios.")
        return redirect('deleted_records')

    try:
        # Map record types to models
        models_map = {
            'users': Users,
            'companies': Companies,
            'user_companies': UserCompany,
            'company_settings': CompanySettings,
            'corrections': CorrectionRequests,
            'time_entries': TimeEntries,
            'time_events': TimeEntryEvent,
        }

        if record_type not in models_map:
            messages.error(request, "Tipo de registro no válido.")
            return redirect('deleted_records')

        model = models_map[record_type]

        # Get the deleted record
        record = model.objects.all_with_deleted().filter(id=record_id).first()

        if not record:
            messages.error(request, f"Registro de tipo '{record_type}' con ID '{record_id}' no encontrado.")
            return redirect('deleted_records')

        # Permanently delete the record
        model.objects.hard_delete(record)
        messages.success(request, f"Registro de tipo '{record_type}' eliminado permanentemente.")

    except Exception as e:
        messages.error(request, f"Error al eliminar permanentemente el registro: {str(e)}")

    return redirect('deleted_records')
