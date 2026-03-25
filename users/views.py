# ---------- Backend Views: users/views.py ----------

import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from uuid import uuid4
from .forms import (
    LoginForm, CompanyForm, CompanySelectLoginForm,
    WorkerCreateForm, WorkerSelectForm, SetPasswordForm
)
from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompanyMembership, CompanySettings, CorrectionRequests


# ── Helpers ────────────────────────────────────────────────────────────────────

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


def get_or_create_demo_user():
    user = Users.objects.first()
    if not user:
        user = Users.objects.create(
            id=uuid4(), username='demo', email='demo@example.com',
            surname='Demo', password='demo'
        )
    return user


def ensure_membership(user):
    membership = UserCompanyMembership.objects.filter(user=user).order_by('-joined_at').first()
    if not membership:
        company = Companies.objects.first()
        if not company:
            company = Companies.objects.create(
                id=uuid4(), name='DemoCorp', legal_name='Demo Corporation'
            )
        membership = UserCompanyMembership.objects.create(
            id=uuid4(), user=user, company=company,
            role=UserCompanyMembership.RoleChoices.EMPLOYEE
        )
    return membership


# ── Auth ───────────────────────────────────────────────────────────────────────

def login_view(request):
    form = LoginForm(request)
    company_form = None
    show_company_selector = False
    set_password_form = None
    show_set_password = False

    if request.method == 'POST':
        step = request.POST.get('step', 'credentials')

        # ── Paso 1: credenciales ───────────────────────────────────────────────
        if step == 'credentials':
            form = LoginForm(request, data=request.POST)
            if form.is_valid():
                email    = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user     = authenticate(request, username=email, password=password)

                if user is not None:
                    # ── Primer login: flag=False → forzar cambio de contraseña ──
                    if not user.flag:
                        auth_login(request, user)
                        set_password_form  = SetPasswordForm()
                        show_set_password  = True
                    else:
                        memberships = UserCompanyMembership.objects.filter(
                            user=user
                        ).select_related('company')

                        if memberships.count() > 1:
                            auth_login(request, user)
                            company_form = CompanySelectLoginForm(companies=memberships)
                            show_company_selector = True
                            request.session['pending_company_selection'] = True
                        else:
                            auth_login(request, user)
                            if memberships.first():
                                request.session['company_id'] = str(
                                    memberships.first().company.id
                                )
                            messages.success(request, 'Sesión iniciada correctamente.')
                            return redirect('home')
                else:
                    messages.error(request, 'Email o contraseña incorrectos.')
            else:
                messages.error(request, 'Revisa los campos del formulario.')

        # ── Paso 1b: establecer contraseña definitiva ──────────────────────────
        elif step == 'set_password':
            if not request.user.is_authenticated:
                return redirect('login')

            set_password_form = SetPasswordForm(request.POST)
            show_set_password = True

            if set_password_form.is_valid():
                new_password = set_password_form.cleaned_data['new_password']
                user = request.user
                user.set_password(new_password)
                user.flag = True
                user.save(update_fields=['password', 'flag'])

                # Re-autenticar con la nueva contraseña
                updated_user = authenticate(
                    request, username=user.email, password=new_password
                )
                if updated_user:
                    auth_login(request, updated_user)

                memberships = UserCompanyMembership.objects.filter(
                    user=user
                ).select_related('company')

                if memberships.count() > 1:
                    company_form = CompanySelectLoginForm(companies=memberships)
                    show_company_selector = True
                    show_set_password = False
                    set_password_form = None
                    request.session['pending_company_selection'] = True
                else:
                    if memberships.first():
                        request.session['company_id'] = str(
                            memberships.first().company.id
                        )
                    messages.success(request, 'Contraseña actualizada. ¡Bienvenido!')
                    return redirect('home')
            else:
                messages.error(
                    request, 'Revisa los requisitos de la contraseña.'
                )

        # ── Paso 2: seleccionar empresa ────────────────────────────────────────
        elif step == 'select_company':
            if not request.user.is_authenticated:
                return redirect('login')

            memberships  = UserCompanyMembership.objects.filter(
                user=request.user
            ).select_related('company')
            company_form = CompanySelectLoginForm(request.POST, companies=memberships)

            if company_form.is_valid():
                company_id = company_form.cleaned_data['company_id']
                membership = memberships.filter(company_id=company_id).first()
                if membership:
                    request.session['company_id'] = str(company_id)
                    request.session.pop('pending_company_selection', None)
                    messages.success(request, 'Sesión iniciada correctamente.')
                    return redirect('home')
                else:
                    messages.error(request, 'Empresa no válida.')
                    show_company_selector = True
            else:
                show_company_selector = True

    return render(request, 'login/login.html', {
        'form':                  form,
        'company_form':          company_form,
        'show_company_selector': show_company_selector,
        'set_password_form':     set_password_form,
        'show_set_password':     show_set_password,
    })


# ── AJAX lookup endpoints ──────────────────────────────────────────────────────

@login_required
def lookup_company(request):
    """
    GET /api/lookup-company/?tax_id=XXX
    Devuelve los datos de una empresa por CIF para prellenar el formulario.
    Solo accesible por ADMIN.
    """
    if not request.user.is_admin:
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    tax_id = request.GET.get('tax_id', '').strip()
    if not tax_id:
        return JsonResponse({'error': 'CIF requerido'}, status=400)

    company = Companies.objects.filter(tax_id__iexact=tax_id).first()
    if not company:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found':      True,
        'id':         str(company.id),
        'name':       company.name,
        'legal_name': company.legal_name,
        'tax_id':     company.tax_id,
    })


@login_required
def lookup_user(request):
    email      = request.GET.get('email', '').strip()
    company_id = request.GET.get('company_id', '').strip()

    if not email:
        return JsonResponse({'error': 'Email requerido'}, status=400)

    # Filtramos primero por empresa si se proporciona
    if company_id:
        membership = UserCompanyMembership.objects.filter(
            user__email__iexact=email,
            company_id=company_id
        ).select_related('user').first()

        if not membership:
            return JsonResponse({'found': False})

        user = membership.user
    else:
        # Manager: filtramos por su empresa de sesión
        company = getattr(request, 'company', None)
        if company:
            membership = UserCompanyMembership.objects.filter(
                user__email__iexact=email,
                company=company
            ).select_related('user').first()
            if not membership:
                return JsonResponse({'found': False})
            user = membership.user
        else:
            return JsonResponse({'error': 'Sin empresa asignada'}, status=400)

    return JsonResponse({
        'found':    True,
        'username': user.username,
        'surname':  user.surname,
        'email':    user.email,
        'status':   user.status,
    })


# ── Registro unificado ─────────────────────────────────────────────────────────

@login_required
def register_unified(request):
    """
    Vista unificada de registro.

    ADMIN — flujo 'Registrar empresa' (company_mode = 'create'):
        Muestra form de empresa + form de trabajador apilados.
        Si el CIF o email ya existen en db, se relacionan silenciosamente
        sin mostrar datos al usuario (política de privacidad).

    ADMIN — flujo 'Seleccionar empresa' (company_mode = 'select'):
        Carga datos de empresa por CIF vía AJAX y permite editarlos.
        Muestra toggles Seleccionar/Añadir trabajador.

    Manager:
        Solo ve el apartado de trabajador de su empresa.
    """
    is_admin = request.user.is_admin
    current_role = request.role

    if not is_admin and current_role != UserCompanyMembership.RoleChoices.MANAGER:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home')

    # Valores de toggle por defecto
    company_mode  = 'create'
    worker_action = 'create'

    # Forms vacíos por defecto
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

        # ── 1. Resolver empresa ────────────────────────────────────────────────
        if is_admin:
            if company_mode == 'create':
                # Intentamos guardar/actualizar por CIF
                tax_id = request.POST.get('tax_id', '').strip()
                existing_company = Companies.objects.filter(tax_id__iexact=tax_id).first() if tax_id else None

                if existing_company:
                    # Ya existe: actualizamos datos silenciosamente
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
                    # Nueva empresa
                    if company_form.is_valid():
                        company_obj = company_form.save(commit=False)
                        company_obj.id = uuid4()
                        company_obj.created_at = timezone.now()
                        company_obj.updated_at = timezone.now()
                        company_obj.save()
                        CompanySettings.objects.create(company=company_obj)
                    else:
                        errors.append('Corrige los datos de la empresa.')

            else:  # select
                company_id = request.POST.get('company_id', '').strip()
                company_obj = Companies.objects.filter(id=company_id).first()

                if company_obj:
                    # Re-bind con instancia para hacer UPDATE limpio
                    company_form = CompanyForm(request.POST, instance=company_obj)
                    if company_form.is_valid():
                        company_obj = company_form.save(commit=False)
                        company_obj.updated_at = timezone.now()
                        company_obj.save()
                    # Si el form no es válido no bloqueamos — los datos originales siguen intactos
                else:
                    errors.append('No se encontró la empresa. Busca de nuevo por CIF.')

        else:
            # Manager: empresa = la suya desde sesión
            company_obj = request.company

        # ── 2. Resolver trabajador ─────────────────────────────────────────────────────
        if not errors:
            email = request.POST.get('email', '').strip()
            existing_user = Users.objects.filter(email__iexact=email).first() if email else None

            if worker_action == 'select' and existing_user:
                # Modo edición: re-bind del form CON la instancia existente
                active_form = WorkerSelectForm(request.POST, instance=existing_user)
            elif worker_action == 'create' and existing_user:
                # El usuario ya existe aunque estemos en modo 'crear': lo actualizamos
                active_form = WorkerCreateForm(request.POST, instance=existing_user)
            else:
                # Usuario nuevo
                active_form = worker_create

            worker_role = request.POST.get('role', UserCompanyMembership.RoleChoices.EMPLOYEE)

            if active_form.is_valid():
                worker_user = active_form.save(commit=False)
                is_new_user = not worker_user.pk

                if is_new_user:
                    worker_user.id = uuid4()

                worker_user.is_admin = False
                password = active_form.cleaned_data.get('password')

                if password:
                    worker_user.set_password(password)
                    if is_new_user:
                        worker_user.flag = False  
                
                worker_user.save()
            else:
                errors.append('Corrige los datos del trabajador.')

        # ── 3. Crear/actualizar membership ─────────────────────────────────────
        if not errors and worker_user and company_obj:
            role = worker_role or UserCompanyMembership.RoleChoices.EMPLOYEE
            membership = UserCompanyMembership.objects.filter(
                user=worker_user,
                company=company_obj,
            ).first()

            if membership:
                # Ya existe la relación: actualizamos el rol si cambió
                if role and membership.role != role:
                    membership.role = role
                    membership.save(update_fields=['role'])
            else:
                UserCompanyMembership.objects.create(
                    id=uuid4(),
                    user=worker_user,
                    company=company_obj,
                    role=role,
                )

            messages.success(request, 'Registro completado correctamente.')
            return redirect('home')

        for error in errors:
            messages.error(request, error)

    return render(request, 'login/register_unified.html', {
        'is_admin':     is_admin,
        'current_role':  current_role,
        'company_form': company_form,
        'worker_create': worker_create,
        'worker_select': worker_select,
        'company_mode': company_mode,
        'worker_action': worker_action,
    })


# ── Panel de usuario ───────────────────────────────────────────────────────────

@login_required
def workday(request):

    user = Users.objects.filter(email=request.user.email).first()

    if not user:
        messages.error(request, 'Usuario no encontrado en el sistema.')
        return redirect('home')

    company = request.company

    if not company:
        messages.error(request, 'No tienes empresa asignada.')
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')

        active_entry = TimeEntries.objects.filter(
            user=user,
            company=company,
            status=TimeEntries.EntryStatus.ONGOING,
            clock_out__isnull=True
        ).order_by('-clock_in').first()

        if action == 'clock_in':
            if active_entry:
                messages.warning(request, 'Ya tienes una entrada activa.')
            else:
                entry = TimeEntries.objects.create(
                    id=uuid4(),
                    user=user,
                    company=company,
                    date=timezone.localdate(),
                    clock_in=timezone.now(),
                    status=TimeEntries.EntryStatus.ONGOING
                )
                TimeEntryEvent.objects.create(
                    id=uuid4(),
                    time_entry=entry,
                    event_type=TimeEntryEvent.EventType.CLOCK_IN,
                    timestamp=timezone.now(),
                    actor=user
                )
                messages.success(request, 'Clock-in registrado.')

        elif action == 'clock_out':
            if not active_entry:
                messages.error(request, 'No hay entrada activa para hacer clock-out.')
            else:
                active_entry.clock_out = timezone.now()
                active_entry.status = TimeEntries.EntryStatus.CONFIRMED
                active_entry.save(update_fields=['clock_out', 'status'])
                TimeEntryEvent.objects.create(
                    id=uuid4(),
                    time_entry=active_entry,
                    event_type=TimeEntryEvent.EventType.CLOCK_OUT,
                    timestamp=timezone.now(),
                    actor=user
                )
                messages.success(request, 'Clock-out registrado.')

        elif action == 'pause_start':
            if not active_entry:
                messages.error(request, 'No hay entrada activa para pausar.')
            else:
                TimeEntryEvent.objects.create(
                    id=uuid4(),
                    time_entry=active_entry,
                    event_type=TimeEntryEvent.EventType.PAUSE_START,
                    timestamp=timezone.now(),
                    actor=user
                )
                messages.success(request, 'Pausa iniciada.')

        elif action == 'pause_end':
            if not active_entry:
                messages.error(request, 'No hay pausa activa para terminar.')
            else:
                TimeEntryEvent.objects.create(
                    id=uuid4(),
                    time_entry=active_entry,
                    event_type=TimeEntryEvent.EventType.PAUSE_END,
                    timestamp=timezone.now(),
                    actor=user
                )
                messages.success(request, 'Pausa finalizada.')

        elif action == 'request_correction':
            entry_id = request.POST.get('entry_id')
            reason = request.POST.get('reason', '').strip()
            #new_clock_in_str = request.POST.get('new_clock_in')
            #new_clock_out_str = request.POST.get('new_clock_out')
            entry = TimeEntries.objects.filter(id=entry_id, user=user).first()
            
            if entry and reason:
                # Convertimos los strings del formulario a objetos datetime si existen
         #       from django.utils.dateparse import parse_datetime
                # Si el formulario envía solo la hora (HH:MM), deberás combinarlo con la fecha del registro original
                # Suponiendo que el input es datetime-local o que ya envías el string completo:
         #       new_in = parse_datetime(f"{entry.date} {new_clock_in_str}") if new_clock_in_str else None
        #        new_out = parse_datetime(f"{entry.date} {new_clock_out_str}") if new_clock_out_str else None
                # Ahora SÍ guardamos las horas nuevas
                CorrectionRequests.objects.create(
                    id=uuid4(), 
                    time_entry=entry, 
                    requester=user, 
                    reason=reason, 
              #      new_clock_in=new_in,  
             #       new_clock_out=new_out,
                    status='pending'
                )
                messages.success(request, 'Solicitud de corrección enviada.')
            else:
                messages.error(request, 'Datos incompletos o inválidos.')

        return redirect('workday')

    # ── Datos para la plantilla ────────────────────────────────────────────────

    entries = TimeEntries.objects.filter(
        user=user,
        company=company
    ).order_by('-date', '-clock_in')[:20]

    correction_requests = CorrectionRequests.objects.filter(
        requester=user,
        time_entry__company=company
    ).order_by('-request_date')[:20]

    entry_rows = []
    for e in entries:
        worked_seconds = compute_worked_seconds(e)
        hours = worked_seconds // 3600
        minutes = (worked_seconds % 3600) // 60
        entry_rows.append({
            'id':        e.id,
            'date':      e.date,
            'clock_in':  e.clock_in,
            'clock_out': e.clock_out,
            'status':    e.status,
            'worked':    f"{hours}:{minutes:02d}",
        })

    request_rows = []
    for r in correction_requests:
        request_rows.append({
            'date':          r.request_date.date() if r.request_date else None,
            'new_clock_in':  r.time_entry.clock_in if r.time_entry else None,
            'new_clock_out': r.time_entry.clock_out if r.time_entry else None,
            'reason':        r.reason,
            'status':        r.status,
        })

    return render(request, 'user_panel/workday.html', {
        'entry_rows':   entry_rows,
        'request_rows': request_rows,
    })


# ── Cambio de empresa ──────────────────────────────────────────────────────────

@login_required
def switch_company(request, company_id):
    membership = UserCompanyMembership.objects.filter(
        user=request.user,
        company_id=company_id
    ).first()

    if membership:
        request.session['company_id'] = str(company_id)

    return redirect('workday')