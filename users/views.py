# ---------- Backend Views: users/views.py ----------

import json
import csv
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
    LoginForm, CompanyForm, CompanyCreateForm, CompanySelectLoginForm,
    WorkerCreateForm, WorkerSelectForm, SetPasswordForm,
)
from .email_utils import send_new_user_email, send_new_auditor_email, send_existing_user_email
from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompany
from admin.models import CompanySettings
from corrections.models import CorrectionRequests
from audit.models import AuditLog
from django.views.decorators.cache import never_cache
from audit.models import AuditLog
from audit.utils import safe_dict
from django.core.paginator import Paginator

# Import centralized decorators and services
from core.decorators import admin_only_required
from core.services import (
    validate_manager_role_change,
    compute_worked_seconds,
    parse_local_datetime,
    get_display_date,
    get_or_create_demo_user,
    format_date_spanish,
    ensure_membership,
)



# ── Auth ───────────────────────────────────────────────────────────────────────

def login_view(request):
    form                  = LoginForm()
    company_form          = None
    show_company_selector = False
    set_password_form     = None
    show_set_password     = False

    if request.method == 'POST':
        step = request.POST.get('step', 'credentials')

        # ── Step 1: login ──────────────────────────────────────────────────────
        if step == 'credentials':
            form = LoginForm(data=request.POST)
            if form.is_valid():
                email    = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user     = authenticate(request, username=email, password=password)

                if user is not None:
                    # ── Check if user is suspended ──────────────────────────────
                    if user.status == 'suspended':
                        AuditLog.objects.create(
                            id=uuid4(),
                            table_name='user_action',
                            record_id=user.id,
                            user=user,
                            action_type=AuditLog.AuditAction.CREATE,
                            reason='Intento de login: cuenta suspendida',
                            source='web',
                        )
                        messages.error(request, 'Tu cuenta ha sido suspendida. Puede ponerse en contacto a través de info@aeptic.es.')
                        return render(request, 'login/login.html', {'form': form})

                    # ── Check if user is deleted ────────────────────────────────
                    elif user.deleted_at is not None:
                        AuditLog.objects.create(
                            id=uuid4(),
                            table_name='user_action',
                            record_id=user.id,
                            user=user,
                            action_type=AuditLog.AuditAction.CREATE,
                            reason='Intento de login: cuenta eliminada',
                            source='web',
                        )
                        messages.error(request, 'Tu cuenta ha sido eliminada. Puede ponerse en contacto a través de info@aeptic.es.')
                        return render(request, 'login/login.html', {'form': form})

                    # ── Check if user is auditor ────────────────────────────────
                    elif user.is_auditor:
                        AuditLog.objects.create(
                            id=uuid4(),
                            table_name='user_action',
                            record_id=user.id,
                            user=user,
                            action_type=AuditLog.AuditAction.CREATE,
                            reason='Login exitoso (Auditor)',
                            source='web',
                        )
                        auth_login(request, user)
                        request.session['nav_history'] = []

                        if user.must_change_password:
                            set_password_form = SetPasswordForm()
                            show_set_password = True
                        else:
                            return redirect('audit_dashboard')

                    # ── Regular user (not auditor, not suspended, not deleted) ──
                    else:
                        auth_login(request, user)

                        AuditLog.objects.create(
                            id=uuid4(),
                            table_name='user_action',
                            record_id=user.id,
                            user=user,
                            action_type=AuditLog.AuditAction.CREATE,
                            reason='Login exitoso',
                            source='web',
                        )

                        if user.must_change_password:
                            request.session['nav_history'] = []
                            set_password_form = SetPasswordForm()
                            show_set_password = True
                        else:
                            # ── Get only ACTIVE memberships (not soft-deleted) ───
                            memberships = UserCompany.objects.filter(
                                user=user,
                                deleted_at__isnull=True
                            ).select_related('company')

                            # ── Check if user has at least one active membership ─
                            if memberships.count() == 0:
                                auth_logout(request)
                                messages.error(request, 'No tienes ninguna membresía activa. Puede ponerse en contacto a través de info@aeptic.es.')
                                return render(request, 'login/login.html', {'form': form})
                            else:
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
                    # ── Login fallido ───────────────────────────────────────────
                    email = form.cleaned_data.get('username', 'desconocido')
                    AuditLog.objects.create(
                        id=uuid4(),
                        table_name='user_action',
                        record_id=uuid4(),
                        user=None,
                        action_type=AuditLog.AuditAction.CREATE,
                        reason=f'Intento de login fallido: {email}',
                        source='web',
                    )
                    messages.error(request, 'Email o contraseña incorrectos.')
            else:
                # ── Errores de validación del formulario ────────────────────────
                email_input = request.POST.get('username', 'desconocido')
                error_messages = ', '.join([str(e) for errors in form.errors.values() for e in errors])
                AuditLog.objects.create(
                    id=uuid4(),
                    table_name='user_action',
                    record_id=uuid4(),
                    user=None,
                    action_type=AuditLog.AuditAction.CREATE,
                    reason=f'Intento de login fallido (errores de validación): {email_input}',
                    after={
                        'tipo': 'Login Fallido - Validación',
                        'errores': error_messages,
                    },
                    source='web',
                )

        # ── Step 2: set password ───────────────────────────────────────────────
        elif step == 'set_password':
            if not request.user.is_authenticated:
                return redirect('login')

            set_password_form = SetPasswordForm(request.POST)
            show_set_password = True

            if set_password_form.is_valid():
                new_password = set_password_form.cleaned_data['new_password']
                user         = request.user
                user.set_password(new_password)
                user.must_change_password = False
                user.save(update_fields=['password', 'must_change_password'])

                updated_user = authenticate(
                    request, username=user.email, password=new_password
                )
                if updated_user:
                    auth_login(request, updated_user)

                    if updated_user.deleted_at is not None:
                        messages.error(request, 'Tu cuenta ha sido eliminada. Puede ponerse en contacto a través de info@aeptic.es.')
                        auth_logout(request)
                        return redirect('login')

                    if updated_user.is_auditor:
                        return redirect('audit_dashboard')

                    memberships = UserCompany.objects.filter(
                        user=updated_user,
                        deleted_at__isnull=True
                    ).select_related('company')

                    if memberships.count() == 0:
                        messages.error(request, 'No tienes ninguna membresía activa. Puede ponerse en contacto a través de info@aeptic.es.')
                        auth_logout(request)
                        return redirect('login')

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

        # ── Step 3: select company ─────────────────────────────────────────────
        elif step == 'select_company':
            if not request.user.is_authenticated:
                return redirect('login')

            memberships  = UserCompany.objects.filter(
                user=request.user,
                deleted_at__isnull=True
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
    # 🔐 AUDITORÍA: Registro de logout
    user = request.user
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=user.id,
        user=user,
        action_type=AuditLog.AuditAction.CREATE,
        reason='Logout',
        source='web', 
    )

    auth_logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


# ── AJAX lookup endpoints ──────────────────────────────────────────────────────
def _company_to_dict(company, include_created=False):
    result = {
        'id':         str(company.id),
        'name':       company.name.title(),
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
    company_id = request.GET.get('company_id', '').strip()
    include_created = request.GET.get('include_created', 'true').lower() == 'true'

    # ── Búsqueda por company_id → obtener conteo de miembros ─────────────────
    if company_id:
        company = Companies.objects.filter(id=company_id).first()
        if not company:
            return JsonResponse({'found': False})

        member_count = UserCompany.objects.filter(company=company, deleted_at__isnull=True).count()
        result = _company_to_dict(company, include_created=include_created)
        result['member_count'] = member_count
        return JsonResponse({'found': True, **result})

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
        'username': user.username.title(),
        'surname':  user.surname.title(),
        'dni':      user.dni,
        'email':    user.email,
        'status':   user.status,
    }
    if include_companies:
        companies = UserCompany.objects.filter(user=user).select_related('company')
        result['companies'] = [
            {'id': str(c.company.id), 'name': c.company.name.title(), 'tax_id': c.company.tax_id or '--'}
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
    elif is_admin:
        # Admin search: search all users regardless of field
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
            # Admin search: all users matching criteria WITH ACTIVE MEMBERSHIPS and NOT suspended
            users = (
                Users.objects
                .filter(Q(username__icontains=name) | Q(surname__icontains=name))
                .filter(usercompany__deleted_at__isnull=True)
                .exclude(status='suspended')  # Exclude suspended users
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
                    deleted_at__isnull=True,  # Only active memberships
                )
                .exclude(user__status='suspended')  # Exclude suspended users
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
        is_auditor    = request.POST.get('is_auditor') == 'on'

        # For auditors, skip company form validation entirely
        company_form  = CompanyForm(request.POST) if not is_auditor else None
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
            from core.services import get_effective_context
            delegation_context = get_effective_context(request)

        # ── 1. Resolve company ────────────────────────────────────────────────
        if is_auditor:
            # Auditors don't need a company; skip all company validation
            company_obj = None
        elif is_admin:
            # Check if using delegated company
            if delegation_context.get('is_delegating') and delegation_context.get('delegated_company_id'):
                company_obj = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
                if not company_obj:
                    errors.append('Empresa delegada no encontrada.')
            elif company_mode == 'create':
                tax_id           = request.POST.get('tax_id', '').strip()
                company_form     = CompanyCreateForm(request.POST)
                existing_company = (
                    Companies.objects.filter(tax_id__iexact=tax_id).first()
                    if tax_id else None
                )
                if existing_company:
                    if company_form.is_valid():

                        estado_anterior = safe_dict(existing_company)
                        for field in ['name', 'legal_name', 'tax_id']:
                            value = company_form.cleaned_data.get(field)
                            if value:
                                setattr(existing_company, field, value)
                        existing_company.updated_at = timezone.now()
                        existing_company.save()
                        company_obj = existing_company

                        AuditLog.objects.create(
                            id=uuid4(),
                            table_name='company_settings', # Importante: coincide con tu filtro de audit_company
                            record_id=str(company_obj.id),
                            user=request.user,
                            action_type='update',
                            before=estado_anterior,
                            after=safe_dict(company_obj),
                            reason="Actualización de datos de empresa en registro unificado",
                            source='web' # Añadido para el hash
                        )
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
                    worker_user.is_auditor = is_auditor
                    worker_user.must_change_password = True
                    temp_password = worker_create.cleaned_data.get('password', '')
                    if temp_password:
                        worker_user.set_password(temp_password)
                    worker_user.save()
                    is_new_user = True
                else:
                    errors.append('Corrige los datos del trabajador.')

        # ── 3. Create/update membership ─────────────────────────────────────
        if not errors and worker_user:
            # If auditor, skip membership creation
            if is_auditor:
                # Just send welcome email for new auditor
                if is_new_user and temp_password:
                    send_new_auditor_email(worker_user, temp_password)
            elif company_obj:
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
    from core.services import get_effective_context
    from audit.models import AuditLog
    from core.services import safe_dict
    from uuid import uuid4

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

                # Guardamos la creación en una variable para poder auditarla
                nueva_solicitud = CorrectionRequests.objects.create(
                    id=uuid4(),
                    time_entry=entry,
                    requester=user,
                    reason=reason,
                    new_clock_in=new_in,
                    new_clock_out=new_out,
                    status='pending',
                )

                # ---AUDITORÍA (CREACIÓN) ---
                AuditLog.objects.create(
                    id=uuid4(),
                    table_name='timetracking_correctionrequest',
                    record_id=str(nueva_solicitud.id),
                    user=request.user,
                    action_type='create',
                    before=None,
                    after=safe_dict(nueva_solicitud),
                    reason="Nueva incidencia reportada",
                    source='web' # Añadido para el hash
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
                
                # --- INICIO AUDITORÍA (FOTO DEL ANTES) ---
                estado_anterior = safe_dict(correction)
                # ----------------------------------------

                correction.new_clock_in = parse_local_datetime(new_clock_in_str)
                correction.new_clock_out = parse_local_datetime(new_clock_out_str)
                correction.reason = reason
                correction.save()

                # --- INICIO AUDITORÍA (FOTO DEL DESPUÉS) ---
                AuditLog.objects.create(
                    id=uuid4(),
                    table_name='timetracking_correctionrequest',
                    record_id=str(correction.id),
                    user=request.user,
                    action_type='update',
                    before=estado_anterior,
                    after=safe_dict(correction),
                    reason="Edición de datos de la incidencia por el usuario",
                    source='web' # Añadido para el hash
                )
                # -------------------------------------------

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
    entries_list = TimeEntries.objects.filter(
        user=user,
        company=company,
    ).order_by('-date', '-clock_in')

    correction_requests_list = CorrectionRequests.objects.filter(
        requester=user,
        time_entry__company=company,
    ).order_by('-request_date')

    # Pagination for entries
    paginator_entries = Paginator(entries_list, 10)
    page_entries = request.GET.get('page_entries', 1)
    entries_page_obj = paginator_entries.get_page(page_entries)

    # Pagination for requests
    paginator_requests = Paginator(correction_requests_list, 10)
    page_requests = request.GET.get('page_requests', 1)
    requests_page_obj = paginator_requests.get_page(page_requests)

    entry_rows = []
    for e in entries_page_obj:
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
    for r in requests_page_obj:
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
        'entries_page_obj': entries_page_obj,
        'requests_page_obj': requests_page_obj,
    }
    context.update(delegation_context)

    return render(request, 'dashboard/workday.html', context)


@login_required
@require_POST
def exportar_workday_entries(request):
    """
    Exporta los fichajes del usuario a CSV.
    POST params: entry_id (lista de IDs seleccionadas)
    """
    from core.services import get_effective_context

    entry_ids = request.POST.getlist('entry_id')

    if not entry_ids:
        return HttpResponse("No seleccionaste ningún registro para exportar.")

    entries = TimeEntries.objects.filter(id__in=entry_ids).select_related('user').order_by('-date', '-clock_in')

    # 🔐 AUDITORÍA: Exportación de fichajes personales
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {len(entry_ids)} fichajes personales',
        after={
            'tipo': 'Fichajes Personales',
            'tabla': 'timetracking_registro',
            'cantidad': len(entry_ids),
            'ids': [str(id) for id in entry_ids],
        },
        source='web' # Añadido para el hash
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y')
    response['Content-Disposition'] = f'attachment; filename="reporte_fichajes_personales_{fecha_reporte}.csv"'

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Fecha', 'Entrada', 'Salida', 'Tiempo Total (HH:MM:SS)', 'Estado', 'Notas'])

    for entry in entries:
        total_s = entry.total_seconds
        horas = total_s // 3600
        minutos = (total_s % 3600) // 60
        segundos = total_s % 60
        tiempo_formateado = f"{horas:02d}:{minutos:02d}:{segundos:02d}" if total_s > 0 else "00:00:00"

        writer.writerow([
            entry.date.strftime('%d/%m/%Y'),
            entry.clock_in.strftime('%H:%M:%S') if entry.clock_in else '--:--:--',
            entry.clock_out.strftime('%H:%M:%S') if entry.clock_out else '--:--:--',
            tiempo_formateado,
            entry.status if hasattr(entry, 'status') else '',
            entry.notes if entry.notes else ''
        ])

    return response


@login_required
@require_POST
def exportar_workday_requests(request):
    """
    Exporta las solicitudes de corrección del usuario a CSV.
    POST params: request_id (lista de IDs seleccionadas)
    """

    request_ids = request.POST.getlist('request_id')

    if not request_ids:
        return HttpResponse("No seleccionaste ningún registro para exportar.")

    corrections = CorrectionRequests.objects.filter(
        id__in=request_ids
    ).select_related('requester', 'time_entry').order_by('-request_date')

    # 🔐 AUDITORÍA: Exportación de solicitudes de corrección
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {len(request_ids)} solicitudes de corrección',
        after={
            'tipo': 'Solicitudes de Corrección',
            'tabla': 'core_correction_requests',
            'cantidad': len(request_ids),
            'ids': [str(id) for id in request_ids],
        },
        source='web' # Añadido para el hash
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y')
    response['Content-Disposition'] = f'attachment; filename="reporte_solicitudes_{fecha_reporte}.csv"'

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Fecha de Solicitud',
        'Fecha del Evento',
        'Entrada Original',
        'Salida Original',
        'Entrada Solicitada',
        'Salida Solicitada',
        'Motivo',
        'Estado'
    ])

    for correction in corrections:
        writer.writerow([
            correction.request_date.strftime('%d/%m/%Y %H:%M') if correction.request_date else '--/--/---- --:--',
            correction.time_entry.date.strftime('%d/%m/%Y') if correction.time_entry else '--/--/----',
            correction.time_entry.clock_in.strftime('%d/%m/%Y %H:%M') if correction.time_entry and correction.time_entry.clock_in else '--/--/---- --:--',
            correction.time_entry.clock_out.strftime('%H:%M') if correction.time_entry and correction.time_entry.clock_out else '--:--',
            correction.new_clock_in.strftime('%d/%m/%Y %H:%M') if correction.new_clock_in else '--/--/---- --:--',
            correction.new_clock_out.strftime('%H:%M') if correction.new_clock_out else '--:--',
            correction.reason or '',
            correction.status or ''
        ])

    return response