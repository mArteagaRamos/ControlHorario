from uuid import uuid4

from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import TimeEntries, TimeEntryEvent
from users.models import Users, UserCompanyMembership, CompanySettings


# save clock-in, clock-out, pause start/end and calculate total hours worked

@login_required
def time_entries(request):
    user = request.user

    membership = UserCompanyMembership.objects.filter(user=user).order_by('-joined_at').first()
    if not membership:
        messages.error(request, 'No company membership found for the user.')
        return render(request, 'timetracking/time_entries.html', {
            'time_entries': [],
            'page_obj': None,
            'events': [],
        })

    company = membership.company

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
                active_entry.clock_out = timezone.now()
                active_entry.status = TimeEntries.EntryStatus.CONFIRMED
                active_entry.save(update_fields=['clock_out', 'status'])
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



@login_required
def total_time_entry(request, entry_id):
    entry = get_object_or_404(TimeEntries, id=entry_id)
    events = TimeEntryEvent.objects.filter(time_entry=entry).order_by('timestamp')

    return render(request, 'timetracking/total_time_entry.html', {
        'entry': entry,
        'events': events,
    })
