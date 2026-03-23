# ---------- Backend Views: users/views.py ----------

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.utils import timezone
from uuid import uuid4
from .forms import FormRegister, LoginForm, CompanyForm, ManagerSelectForm, ManagerCreateForm
from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompanyMembership, CompanySettings, CorrectionRequests

# Authentication / registration views

def compute_worked_seconds(entry):
    if not entry.clock_in or not entry.clock_out:
        return 0
    elapsed = entry.clock_out - entry.clock_in
    total = int(elapsed.total_seconds())
    # subtract pauses from events
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
        user = Users.objects.create(id=uuid4(), username='demo', email='demo@example.com', surname='Demo', password='demo')
    return user


def ensure_membership(user):
    membership = UserCompanyMembership.objects.filter(user=user).order_by('-joined_at').first()
    if not membership:
        company = Companies.objects.first()
        if not company:
            company = Companies.objects.create(id=uuid4(), name='DemoCorp', legal_name='Demo Corporation')
        membership = UserCompanyMembership.objects.create(id=uuid4(), user=user, company=company, role=UserCompanyMembership.RoleChoices.EMPLOYEE)
    return membership


def register(request):

    """
    if not request.user.is_authenticated or not request.user.is_admin:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('register')
        """

    """Handle user registration via sign-up form."""

    # If request is POST, process submitted registration form data
    if request.method == 'POST':
        form = FormRegister(request.POST)
        if form.is_valid():
            # Save user record to database
            form.save()
            messages.success(request, 'User registered successfully.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the highlighted fields and try again.')
    else:
        # GET request: display an empty registration form
        form = FormRegister()
    return render(request, 'login/sign_up.html', {'form': form})


def create_company(request):
    if request.method == 'POST':
        company_form = CompanyForm(request.POST)
        manager_action = request.POST.get('manager_action', 'select')
        select_form = ManagerSelectForm(request.POST)
        create_form = ManagerCreateForm(request.POST)

        if company_form.is_valid():
            company = company_form.save(commit=False)
            company.id = uuid4()
            company.created_at = timezone.now()
            company.updated_at = timezone.now()
            company.save()
            CompanySettings.objects.create(company=company)

            if manager_action == 'select':
                if select_form.is_valid():
                    manager_email = select_form.cleaned_data['manager_email']
                    manager = Users.objects.filter(email=manager_email).first()
                    if manager:
                        UserCompanyMembership.objects.create(
                            id=uuid4(),
                            user=manager,
                            company=company,
                            role=UserCompanyMembership.RoleChoices.MANAGER
                        )
            elif manager_action == 'create' and create_form.is_valid():
                manager_user = create_form.save(commit=False)
                manager_user.id = uuid4()
                manager_user.is_admin = False
                manager_user.set_password(create_form.cleaned_data['password'])
                manager_user.save()
                UserCompanyMembership.objects.create(
                    id=uuid4(),
                    user=manager_user,
                    company=company,
                    role=UserCompanyMembership.RoleChoices.MANAGER
                )

            messages.success(request, 'Empresa guardada correctamente.')
            return redirect('home')

        # Build errors for all forms
        if not company_form.is_valid():
            messages.error(request, 'Por favor corrige los datos de la empresa.')
        if manager_action == 'select' and not select_form.is_valid():
            messages.error(request, 'Por favor corrige el correo del manager seleccionado.')
        if manager_action == 'create' and not create_form.is_valid():
            messages.error(request, 'Por favor corrige los datos del manager a crear.')
    else:
        company_form = CompanyForm()
        select_form = ManagerSelectForm()
        create_form = ManagerCreateForm()
        manager_action = 'select'

    return render(request, 'login/create_company.html', {
        'company_form': company_form,
        'select_form': select_form,
        'create_form': create_form,
        'manager_action': manager_action,
    })


def login_view(request):
    """Authenticate user credentials and log in admin users."""

    if request.method == 'POST':
        # Bind submitted credentials to authentication form
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            # Extract cleaned data from the form
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Authenticate against Django auth backend
            user = authenticate(request, username=email, password=password)
            if user is not None:
                # Only allow admin users to log in here
                if user.is_admin:
                    auth_login(request, user)
                    messages.success(request, 'Logged in successfully as admin.')
                    return redirect('home')
                else:
                    messages.error(request, 'You do not have permission to access this page.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please check the form for errors.')
    else:
        # GET request: show login form
        form = LoginForm(request)
    return render(request, 'login/login.html', {'form': form})


# User panel section

def workday(request):
    # Determine current user from auth, fallback to demo user for quick tests
    if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
        user = Users.objects.filter(email=getattr(request.user, 'email', None)).first()
    else:
        user = None

    if not user:
        user = get_or_create_demo_user()

    membership = ensure_membership(user)
    company = membership.company

    # Handle timetracking actions from panel
    if request.method == 'POST':
        action = request.POST.get('action')
        active_entry = TimeEntries.objects.filter(user=user, status=TimeEntries.EntryStatus.ONGOING, clock_out__isnull=True).order_by('-clock_in').first()

        if action == 'clock_in':
            if active_entry:
                messages.warning(request, 'Ya tienes una entrada activa.')
            else:
                entry = TimeEntries.objects.create(id=uuid4(), user=user, company=company, date=timezone.localdate(), clock_in=timezone.now(), status=TimeEntries.EntryStatus.ONGOING)
                TimeEntryEvent.objects.create(id=uuid4(), time_entry=entry, event_type=TimeEntryEvent.EventType.CLOCK_IN, timestamp=timezone.now(), actor=user)
                messages.success(request, 'Clock-in registrado.')

        elif action == 'clock_out':
            if not active_entry:
                messages.error(request, 'No hay entrada activa para hacer clock-out.')
            else:
                active_entry.clock_out = timezone.now()
                active_entry.status = TimeEntries.EntryStatus.CONFIRMED
                active_entry.save(update_fields=['clock_out', 'status'])
                TimeEntryEvent.objects.create(id=uuid4(), time_entry=active_entry, event_type=TimeEntryEvent.EventType.CLOCK_OUT, timestamp=timezone.now(), actor=user)
                messages.success(request, 'Clock-out registrado.')

        elif action == 'pause_start':
            if not active_entry:
                messages.error(request, 'No hay entrada activa para pausar.')
            else:
                TimeEntryEvent.objects.create(id=uuid4(), time_entry=active_entry, event_type=TimeEntryEvent.EventType.PAUSE_START, timestamp=timezone.now(), actor=user)
                messages.success(request, 'Pausa iniciada.')

        elif action == 'pause_end':
            if not active_entry:
                messages.error(request, 'No hay pausa activa para terminar.')
            else:
                TimeEntryEvent.objects.create(id=uuid4(), time_entry=active_entry, event_type=TimeEntryEvent.EventType.PAUSE_END, timestamp=timezone.now(), actor=user)
                messages.success(request, 'Pausa finalizada.')

        elif action == 'request_correction':
            entry_id = request.POST.get('entry_id')
            new_clock_in = request.POST.get('new_clock_in')
            new_clock_out = request.POST.get('new_clock_out')
            reason = request.POST.get('reason', '').strip()
            entry = TimeEntries.objects.filter(id=entry_id, user=user).first()
            if entry and reason:
                CorrectionRequests.objects.create(id=uuid4(), time_entry=entry, requester=user, reason=reason, status='pending')
                messages.success(request, 'Solicitud de corrección enviada.')
            else:
                messages.error(request, 'Datos incompletos para la solicitud de corrección.')

        return redirect('workday')

    entries = TimeEntries.objects.filter(user=user).order_by('-date', '-clock_in')[:20]
    requests = CorrectionRequests.objects.filter(requester=user).order_by('-request_date')[:20]

    # Build simple row data with computed duration
    entry_rows = []
    for e in entries:
        worked_seconds = compute_worked_seconds(e)
        hours = worked_seconds // 3600
        minutes = (worked_seconds % 3600) // 60
        entry_rows.append({
            'id': e.id,
            'date': e.date,
            'clock_in': e.clock_in,
            'clock_out': e.clock_out,
            'status': e.status,
            'worked': f"{hours}:{minutes:02d}",
        })

    request_rows = []
    for r in requests:
        request_rows.append({
            'date': r.request_date.date() if r.request_date else None,
            'new_clock_in': r.time_entry.clock_in if r.time_entry else None,
            'new_clock_out': r.time_entry.clock_out if r.time_entry else None,
            'reason': r.reason,
            'status': r.status,
        })

    return render(request, 'user_panel/workday.html', {
        'entry_rows': entry_rows,
        'request_rows': request_rows,
    })


def calendar(request):
    return render(request, 'user_panel/calendar.html')

def profile(request):
    return render(request, 'user_panel/profile.html')

def absence(request):
    return render(request, 'user_panel/absence.html')

def request_correction(request):
    return render(request, 'user_panel/requests.html')   


def entity_info(request):
    return render(request, 'team/entity_info.html')

def staff(request):
    return render(request, 'team/staff.html')

def notes(request):
    return render(request, 'team/notes.html')
    