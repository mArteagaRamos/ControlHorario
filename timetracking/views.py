import uuid
import datetime
from uuid import uuid4
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.forms.models import model_to_dict
from django.views.decorators.cache import never_cache

from .models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompany
from admin.models import CompanySettings
from audit.models import AuditLog
from core.decorators import auditor_cannot_access
from core.services import safe_dict, compute_worked_seconds, auto_close_entry_if_expired, get_effective_context


# save clock-in, clock-out, pause start/end and calculate total hours worked
@never_cache
@login_required
@auditor_cannot_access
def time_entries(request):
    delegation_context = get_effective_context(request)

    # Get the effective user (delegated or authenticated)
    if delegation_context['is_delegating']:
        user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
        company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
        if not user or not company:
            messages.error(request, 'Usuario o empresa delegada no encontrada.')
            return redirect('home_timetracking')
    else:
        django_user = request.user
        user = Users.objects.filter(email=django_user.email).first()

        if not user:
            messages.error(request, 'Usuario no encontrado en el sistema.')
            return redirect('home_timetracking')

        company = request.company
        if not company and not user.is_auditor:
            messages.error(request, 'No tienes una empresa asignada.')
            return redirect('home_timetracking')

    # Bloquear acciones de fichaje si el usuario está inactivo (vacaciones/ausencia)
    if request.method == 'POST':
        if user.status == Users.StatusChoices.INACTIVE:
            messages.error(request, 'No puedes registrar fichajes. Estás marcado como ausente (vacaciones/ausencia).')
            return redirect('home_timetracking')

    # Auto-close any ongoing entry that exceeds company auto_close_hours before user actions
    active_entry = TimeEntries.objects.filter(user=user, status=TimeEntries.EntryStatus.ONGOING, clock_out__isnull=True).order_by('-clock_in').first()
    if active_entry and auto_close_entry_if_expired(active_entry, company):
        messages.info(request, 'An overdue active entry was auto-closed based on company policy.')
        active_entry = None

    if request.method == 'POST':
        action = request.POST.get('action')

        active_entry = TimeEntries.objects.filter(user=user, status=TimeEntries.EntryStatus.ONGOING, clock_out__isnull=True).order_by('-clock_in').first()

        # ---------------------------------------------------------
        # CLOCK IN
        # ---------------------------------------------------------
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
                
                # REGISTRO DE AUDITORÍA (CREATE)
                # No necesitas pasar los hashes, el modelo los calcula automáticamente.
                AuditLog.objects.create(
                    id=uuid4(),
                    table_name='timetracking_registro',
                    record_id=entry.id,
                    user=user,
                    action_type=AuditLog.AuditAction.CREATE,
                    before=None,
                    after=safe_dict(entry),
                    reason='Fichaje de entrada (Clock-in)',
                    source='web', # Añadido para completitud del payload
                    timestamp=timezone.now()
                )
                
                messages.success(request, 'Clock-in registered.')

        # ---------------------------------------------------------
        # CLOCK OUT
        # ---------------------------------------------------------
        elif action == 'clock_out':
            if not active_entry:
                messages.error(request, 'No active clock-in entry found to clock out.')
            else:
                was_auto_closed = auto_close_entry_if_expired(active_entry, company)

                if was_auto_closed:
                    messages.info(request, 'Entry auto-closed because it exceeded maximum open hours.')
                else:
                    estado_anterior = safe_dict(active_entry) # FOTO ANTES

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
                    
                    # REGISTRO DE AUDITORÍA (UPDATE)
                    AuditLog.objects.create(
                        id=uuid4(),
                        table_name='timetracking_registro',
                        record_id=active_entry.id,
                        user=user,
                        action_type=AuditLog.AuditAction.UPDATE,
                        before=estado_anterior,
                        after=safe_dict(active_entry),
                        reason='Fichaje de salida (Clock-out)',
                        source='web', # Añadido
                        timestamp=timezone.now()
                    )

                    messages.success(request, 'Clock-out registered.')

        # ---------------------------------------------------------
        # PAUSE START
        # ---------------------------------------------------------
        elif action == 'pause_start':
            if not active_entry:
                messages.error(request, 'No active time entry to start pause.')
            else:
                last_event = TimeEntryEvent.objects.filter(time_entry=active_entry).order_by('-timestamp').first()
                if last_event and last_event.event_type == TimeEntryEvent.EventType.PAUSE_START:
                    messages.warning(request, 'Pause already started.')
                else:
                    evento = TimeEntryEvent.objects.create(
                        id=uuid4(),
                        time_entry=active_entry,
                        event_type=TimeEntryEvent.EventType.PAUSE_START,
                        timestamp=timezone.now(),
                        actor=user,
                    )
                    
                    # REGISTRO DE AUDITORÍA (PAUSA INICIO)
                    AuditLog.objects.create(
                        id=uuid4(),
                        table_name='timetracking_pausa',
                        record_id=evento.id,
                        user=user,
                        action_type=AuditLog.AuditAction.CREATE,
                        before=None,
                        after=safe_dict(evento),
                        reason='Inicio de pausa',
                        source='web', # Añadido
                        timestamp=timezone.now()
                    )

                    messages.success(request, 'Pause start registered.')

        # ---------------------------------------------------------
        # PAUSE END
        # ---------------------------------------------------------
        elif action == 'pause_end':
            if not active_entry:
                messages.error(request, 'No active time entry to end pause.')
            else:
                last_event = TimeEntryEvent.objects.filter(time_entry=active_entry).order_by('-timestamp').first()
                if not last_event or last_event.event_type != TimeEntryEvent.EventType.PAUSE_START:
                    messages.error(request, 'No pause is currently active.')
                else:
                    evento = TimeEntryEvent.objects.create(
                        id=uuid4(),
                        time_entry=active_entry,
                        event_type=TimeEntryEvent.EventType.PAUSE_END,
                        timestamp=timezone.now(),
                        actor=user,
                    )
                    
                    # REGISTRO DE AUDITORÍA (PAUSA FIN)
                    AuditLog.objects.create(
                        id=uuid4(),
                        table_name='timetracking_pausa',
                        record_id=evento.id,
                        user=user,
                        action_type=AuditLog.AuditAction.CREATE,
                        before=None,
                        after=safe_dict(evento),
                        reason='Fin de pausa',
                        source='web', # Añadido
                        timestamp=timezone.now()
                    )

                    messages.success(request, 'Pause end registered.')

        else:
            messages.error(request, 'Acción desconocida.')

        return redirect('home_timetracking')

    # ---------------------------------------------------------
    # RENDERIZADO DE LA VISTA (SIN CAMBIOS)
    # ---------------------------------------------------------
    entries = TimeEntries.objects.filter(user=user, company=company).order_by('-date', '-clock_in')
    paginator = Paginator(entries, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    entry_ids = [entry.id for entry in page_obj.object_list]
    events = TimeEntryEvent.objects.filter(time_entry__id__in=entry_ids).order_by('time_entry_id', 'timestamp')

    active_entry = TimeEntries.objects.filter(
        user=user,
        status=TimeEntries.EntryStatus.ONGOING,
        clock_out__isnull=True
    ).order_by('-clock_in').first()

    last_event = None
    if active_entry:
        last_event = TimeEntryEvent.objects.filter(
            time_entry=active_entry
        ).order_by('-timestamp').first()

    is_paused = (
        last_event is not None and
        last_event.event_type == TimeEntryEvent.EventType.PAUSE_START
    )

    pause_seconds = 0
    paused_elapsed = 0

    if active_entry:
        events_list = TimeEntryEvent.objects.filter(time_entry=active_entry).order_by('timestamp')
        pause_start = None
        for ev in events_list:
                if ev.event_type == TimeEntryEvent.EventType.PAUSE_START:
                    pause_start = ev.timestamp
                elif ev.event_type == TimeEntryEvent.EventType.PAUSE_END and pause_start:
                    pause_seconds += int((ev.timestamp - pause_start).total_seconds())
                    pause_start = None

        if is_paused:
            clock_in = active_entry.clock_in
            if timezone.is_naive(clock_in):
                clock_in = timezone.make_aware(clock_in, timezone.get_current_timezone())

            current_pause_start = TimeEntryEvent.objects.filter(
                time_entry=active_entry,
                event_type=TimeEntryEvent.EventType.PAUSE_START
            ).order_by('-timestamp').first()

            # Timer freezes at pause start time for display purposes
            frozen_at = current_pause_start.timestamp
            if timezone.is_naive(frozen_at):
                frozen_at = timezone.make_aware(frozen_at, timezone.get_current_timezone())

            elapsed = int((frozen_at - clock_in).total_seconds())
            paused_elapsed = max(0, elapsed - pause_seconds)

    context = {
        'time_entries': page_obj,
        'page_obj': page_obj,
        'events': events,
        'active_entry': active_entry,
        'is_paused': is_paused,
        'pause_seconds': pause_seconds,
        'paused_elapsed': paused_elapsed,
        'user_status': user.status,
    }
    context.update(delegation_context)

    return render(request, 'dashboard/home_timetracking.html', context)