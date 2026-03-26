# ---------- Backend Views: users/views.py ----------

import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from uuid import uuid4
from .forms import (
    LoginForm, CompanyForm, CompanySelectLoginForm,
    WorkerCreateForm, WorkerSelectForm, SetPasswordForm,
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

def parse_local_datetime(value):
    if not value:
        return None

    parsed = parse_datetime(value)
    if parsed is None:
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


# ── Auth ───────────────────────────────────────────────────────────────────────

def login_view(request):
    form = LoginForm(request)
    company_form = None
    show_company_selector = False
    set_password_form = None
    show_set_password = False

    if request.method == 'POST':
        step = request.POST.get('step', 'credentials')

        # ── Paso 1: login ─────────────────────────────────────
        if step == 'credentials':
            form = LoginForm(request, data=request.POST)

            if form.is_valid():
                email = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = authenticate(request, username=email, password=password)

                if user is not None:
                    if not user.flag:
                        auth_login(request, user)
                        set_password_form = SetPasswordForm()
                        show_set_password = True
                    else:
                        memberships = UserCompanyMembership.objects.filter(
                            user=user
                        ).select_related('company')

                        auth_login(request, user)

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

        # ── Paso 2: set password ───────────────────────────────
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
                    return redirect('home_timetracking')

        # ── Paso 3: seleccionar empresa ────────────────────────
        elif step == 'select_company':
            if not request.user.is_authenticated:
                return redirect('login')

            memberships = UserCompanyMembership.objects.filter(
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
        'form': form,
        'company_form': company_form,
        'show_company_selector': show_company_selector,
        'set_password_form': set_password_form,
        'show_set_password': show_set_password,
    })


# ── AJAX lookup endpoints ──────────────────────────────────────────────────────

@login_required
def lookup_company(request):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    tax_id = request.GET.get('tax_id', '').strip()
    if not tax_id:
        return JsonResponse({'error': 'CIF requerido'}, status=400)

    company = Companies.objects.filter(tax_id__iexact=tax_id).first()

    if not company:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'id': str(company.id),
        'name': company.name,
        'legal_name': company.legal_name,
        'tax_id': company.tax_id,
    })


@login_required
def lookup_user(request):
    email = request.GET.get('email', '').strip()
    company_id = request.GET.get('company_id', '').strip()

    if not email:
        return JsonResponse({'error': 'Email requerido'}, status=400)

    if company_id:
        membership = UserCompanyMembership.objects.filter(
            user__email__iexact=email,
            company_id=company_id
        ).select_related('user').first()

        if not membership:
            return JsonResponse({'found': False})

        user = membership.user
    else:
        company = getattr(request, 'company', None)

        if not company:
            return JsonResponse({'error': 'Sin empresa asignada'}, status=400)

        membership = UserCompanyMembership.objects.filter(
            user__email__iexact=email,
            company=company
        ).select_related('user').first()

        if not membership:
            return JsonResponse({'found': False})

        user = membership.user

    return JsonResponse({
        'found': True,
        'username': user.username,
        'surname': user.surname,
        'email': user.email,
        'status': user.status,
    })


# ── Registro ───────────────────────────────────────────────────────────────────

@login_required
def register_unified(request):
    is_admin = request.user.is_admin
    current_role = request.role

    if not is_admin and current_role != UserCompanyMembership.RoleChoices.MANAGER:
        messages.error(request, 'No tienes permisos para acceder a esta página.')
        return redirect('home_timetracking')

    company_form = CompanyForm()
    worker_create = WorkerCreateForm()
    worker_select = WorkerSelectForm()

    if request.method == 'POST':
        company_form = CompanyForm(request.POST)
        worker_create = WorkerCreateForm(request.POST)

        company_obj = None
        worker_user = None

        # Empresa
        if is_admin:
            if company_form.is_valid():
                company_obj = company_form.save(commit=False)
                if not company_obj.id:
                    company_obj.id = uuid4()
                company_obj.updated_at = timezone.now()
                company_obj.save()
            else:
                return render(request, 'login/register_unified.html', {
                    'company_form': company_form,
                    'worker_create': worker_create,
                })
        else:
            company_obj = request.company

        # Usuario
        if worker_create.is_valid():
            worker_user = worker_create.save(commit=False)
            if not worker_user.id:
                worker_user.id = uuid4()

            temp_password = worker_create.cleaned_data.get('password')
            if temp_password:
                worker_user.set_password(temp_password)

            worker_user.save()
        else:
            return render(request, 'login/register_unified.html', {
                'company_form': company_form,
                'worker_create': worker_create,
            })

        # Membership
        UserCompanyMembership.objects.get_or_create(
            user=worker_user,
            company=company_obj,
            defaults={'role': UserCompanyMembership.RoleChoices.EMPLOYEE}
        )

        return redirect('home_timetracking')

    return render(request, 'login/register_unified.html', {
        'is_admin': is_admin,
        'current_role': current_role,
        'company_form': company_form,
        'worker_create': worker_create,
        'worker_select': worker_select,
    })


# ── Cambio de empresa ──────────────────────────────────────────────────────────

@login_required
def switch_company(request, company_id):
    membership = UserCompanyMembership.objects.filter(
        user=request.user,
        company_id=company_id
    ).first()

    if not membership:
        messages.error(request, 'No tienes acceso a esta empresa.')

    else:
        request.session['company_id'] = str(company_id)

    return redirect('workday')



# ── Panel de usuario ───────────────────────────────────────────────────────────
"""
@login_required
def workday(request):
    user = Users.objects.filter(email=request.user.email).first()

    if not user:
        messages.error(request, 'Usuario no encontrado en el sistema.')
        return redirect('home_timetracking')

    company = request.company

    if not company:
        messages.error(request, 'No tienes empresa asignada.')
        return redirect('home_timetracking')

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
                active_entry.status    = TimeEntries.EntryStatus.CONFIRMED
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

        # Petición de corrección CORREGIDA
        elif action == 'request_correction':
            entry_id = request.POST.get('entry_id')
            reason = request.POST.get('reason', '').strip()
            new_clock_in_str = request.POST.get('new_clock_in')
            new_clock_out_str = request.POST.get('new_clock_out')
            
            entry = TimeEntries.objects.filter(id=entry_id, user=user).first()
            
            if entry and reason:
                new_in = parse_local_datetime(new_clock_in_str)
                new_out = parse_local_datetime(new_clock_out_str)

                if (new_clock_in_str and new_in is None) or (new_clock_out_str and new_out is None):
                    messages.error(request, 'El formato de fecha y hora no es válido.')
                    return redirect('workday')
                
                CorrectionRequests.objects.create(
                    id=uuid4(), 
                    time_entry=entry, 
                    requester=user, 
                    reason=reason, 
                    new_clock_in=new_in,  
                    new_clock_out=new_out,
                    status='pending'
                )
                messages.success(request, 'Solicitud de corrección enviada.')

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
        hours          = worked_seconds // 3600
        minutes        = (worked_seconds % 3600) // 60
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
        request_date = get_display_date(r.request_date)
        if r.new_clock_in:
            request_date = get_display_date(r.new_clock_in)
        elif r.new_clock_out:
            request_date = get_display_date(r.new_clock_out)

        request_rows.append({
            'date':          r.request_date.date() if r.request_date else None,
            'new_clock_in':  r.time_entry.clock_in  if r.time_entry else None,
            'new_clock_out': r.time_entry.clock_out if r.time_entry else None,
            'reason':        r.reason,
            'status':        r.status,
        })

    return render(request, 'user_panel/workday.html', {
        'entry_rows':   entry_rows,
        'request_rows': request_rows,
    }) """
