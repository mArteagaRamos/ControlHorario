from uuid import uuid4


from datetime import timedelta
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
#from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompanyMembership, CompanySettings


# CALCULATE WORKED SECONDS 

def compute_worked_seconds(entry):
    if not entry.clock_in or not entry.clock_out:
        return 0

    clock_in = entry.clock_in
    clock_out = entry.clock_out
    if timezone.is_naive(clock_in):
        clock_in = timezone.make_aware(clock_in, timezone.get_current_timezone())
    if timezone.is_naive(clock_out):
        clock_out = timezone.make_aware(clock_out, timezone.get_current_timezone())

    if clock_out <= clock_in:
        return 0

    elapsed = clock_out - clock_in
    total = int(elapsed.total_seconds())

    # CALCULATE PAUSES IN SECONDS

    pause_seconds = 0
    pause_start = None
    for ev in TimeEntryEvent.objects.filter(time_entry=entry).order_by('timestamp'):
        if ev.event_type == TimeEntryEvent.EventType.PAUSE_START:
            pause_start = ev.timestamp
        elif ev.event_type == TimeEntryEvent.EventType.PAUSE_END and pause_start is not None:
            pause_end = ev.timestamp
            if timezone.is_naive(pause_start):
                pause_start = timezone.make_aware(pause_start, timezone.get_current_timezone())
            if timezone.is_naive(pause_end):
                pause_end = timezone.make_aware(pause_end, timezone.get_current_timezone())
            if pause_end > pause_start:
                pause_seconds += int((pause_end - pause_start).total_seconds())
            pause_start = None

    return max(0, total - pause_seconds)



def auto_close_entry_if_expired(entry, company):
    settings = CompanySettings.objects.filter(company=company).first()
    max_hours = settings.auto_close_hours if settings and settings.auto_close_hours else 12
    max_duration = timedelta(hours=max_hours)
    now = timezone.now()

    clock_in = entry.clock_in
    if timezone.is_naive(clock_in):
        clock_in = timezone.make_aware(clock_in, timezone.get_current_timezone())

    if entry and entry.clock_out is None and now - clock_in >= max_duration:
        auto_close_time = entry.clock_in + max_duration
        entry.clock_out = auto_close_time
        entry.status = TimeEntries.EntryStatus.AUTO_CLOSED

        # Calc duration and save
        elapsed = entry.clock_out - entry.clock_in
        pause_seconds = compute_worked_seconds(entry)
        work_seconds = max(0, int(elapsed.total_seconds()) - pause_seconds)
        entry.total_seconds = work_seconds

        entry.save(update_fields=['clock_out', 'status', 'total_seconds'])

        TimeEntryEvent.objects.create(
            id=uuid4(),
            time_entry=entry,
            event_type=TimeEntryEvent.EventType.AUTO_CLOSE,
            timestamp=auto_close_time,
            actor=None,
            note=f'Auto-closed after exceeding {max_hours} hours.',
        )
        return True

    return False


# save clock-in, clock-out, pause start/end and calculate total hours worked

#@login_required

def time_entries(request):
    # pick a user from the system for tests (no auth required)
    user = None

    if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
        django_user = request.user

        # try match by email in your app user table
        user = Users.objects.filter(email=getattr(django_user, 'email', None)).first()

    if not user:
        user = Users.objects.first()

    if not user:
        user = Users.objects.create(
            id=uuid4(),
            username='demo',
            email='demo@example.com',
            surname='Demo',
            password_hash='demo',
        )

    # ensure user has a company and membership for testing

    membership = UserCompanyMembership.objects.filter(user=user).order_by('-joined_at').first()
    if not membership:
        company = Companies.objects.first()
        if not company:
                    company = Companies.objects.create(
                        id=uuid4(),
                        name='DemoCorp',
                        legal_name='Demo Corporation',
                    )
        membership = UserCompanyMembership.objects.create(
                    id=uuid4(),
                    user=user,
                    company=company,
                    role=UserCompanyMembership.RoleChoices.EMPLOYEE,
                )

    company = membership.company

    # eliminar esto cuando hagamos la prueba  


    # Auto-close any ongoing entry that exceeds company auto_close_hours before user actions
    active_entry = TimeEntries.objects.filter(user=user, status=TimeEntries.EntryStatus.ONGOING, clock_out__isnull=True).order_by('-clock_in').first()
    if active_entry and auto_close_entry_if_expired(active_entry, company):
        messages.info(request, 'An overdue active entry was auto-closed based on company policy.')
        active_entry = None

    if request.method == 'POST':
        action = request.POST.get('action')

        active_entry = TimeEntries.objects.filter(user=user, status=TimeEntries.EntryStatus.ONGOING, clock_out__isnull=True).order_by('-clock_in').first()
        #CLOCK IN

        if action == 'clock_in':
            if active_entry:
                messages.warning(request, 'You already have an ongoing clock-in entry.')
            else:
                entry = TimeEntries.objects.create(
                    id=uuid4(),
                    user=user,
                    company=company,
                    date=timezone.localdate(),
                    clock_in=timezone.now(),
                    status=TimeEntries.EntryStatus.ONGOING,
                )
                TimeEntryEvent.objects.create(
                    id=uuid4(),
                    time_entry=entry,
                    event_type=TimeEntryEvent.EventType.CLOCK_IN,
                    timestamp=timezone.now(),
                    actor=user,
                )
                messages.success(request, 'Clock-in registered.')

        #CLOCK OUT

        elif action == 'clock_out':
            if not active_entry:
                messages.error(request, 'No active clock-in entry found to clock out.')
            
        # queda añadir la casuistica de que olvide fichar y se haga el auto close
              
            
            else:
                # Check if this entry should be auto-closed by company policy
                was_auto_closed = auto_close_entry_if_expired(active_entry, company)

                if was_auto_closed:
                        messages.info(request, 'Entry auto-closed because it exceeded maximum open hours.')
            
                else:            
                    active_entry.clock_out = timezone.now()
                    active_entry.status = TimeEntries.EntryStatus.CONFIRMED

                    active_entry.total_seconds = compute_worked_seconds(active_entry)

                    active_entry.save(update_fields=['clock_out', 'status', 'total_seconds'])
                    TimeEntryEvent.objects.create(
                        id=uuid4(),
                        time_entry=active_entry,
                        event_type=TimeEntryEvent.EventType.CLOCK_OUT,
                        timestamp=timezone.now(),
                        actor=user,
                    )
                    messages.success(request, 'Clock-out registered.')
                
        #PAUSE START

        elif action == 'pause_start':
            if not active_entry:
                messages.error(request, 'No active time entry to start pause.')
            else:
                last_event = TimeEntryEvent.objects.filter(time_entry=active_entry).order_by('-timestamp').first()
                if last_event and last_event.event_type == TimeEntryEvent.EventType.PAUSE_START:
                    messages.warning(request, 'Pause already started.')
                else:
                    TimeEntryEvent.objects.create(
                        id=uuid4(),
                        time_entry=active_entry,
                        event_type=TimeEntryEvent.EventType.PAUSE_START,
                        timestamp=timezone.now(),
                        actor=user,
                    )
                    messages.success(request, 'Pause start registered.')

        #PAUSE END

        elif action == 'pause_end':
            if not active_entry:
                messages.error(request, 'No active time entry to end pause.')
            else:
                last_event = TimeEntryEvent.objects.filter(time_entry=active_entry).order_by('-timestamp').first()
                if not last_event or last_event.event_type != TimeEntryEvent.EventType.PAUSE_START:
                    messages.error(request, 'No pause is currently active.')
                else:
                    TimeEntryEvent.objects.create(
                        id=uuid4(),
                        time_entry=active_entry,
                        event_type=TimeEntryEvent.EventType.PAUSE_END,
                        timestamp=timezone.now(),
                        actor=user,
                    )
                    messages.success(request, 'Pause end registered.')

        else:
            messages.error(request, 'Acción desconocida.')

        return redirect('time_entries')

    entries = TimeEntries.objects.filter(user=user).order_by('-date', '-clock_in')
    paginator = Paginator(entries, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    entry_ids = [entry.id for entry in page_obj.object_list]
    events = TimeEntryEvent.objects.filter(time_entry__id__in=entry_ids).order_by('time_entry_id', 'timestamp')

    return render(request, 'timetracking/time_entries.html', {
        'time_entries': page_obj,
        'page_obj': page_obj,
        'events': events,
    })
