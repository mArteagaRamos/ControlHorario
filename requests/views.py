# requests/views.py

import csv
import json
from datetime import date, timedelta, datetime
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date
import uuid
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from users.models import Users, UserCompany, Companies
from timetracking.models import TimeEntries
from requests.models import LeaveRequest, CorrectionRequests, VacationPeriodMultiplier
from admin.models import CompanySettings
from audit.models import AuditLog
from audit.utils import safe_dict
from core.decorators import login_required_with_delegation_support
from core.services import get_effective_context, serialize_leave, log_leave, get_company, is_manager
from core.services import is_manager as check_is_manager

# Motivos que permiten horas parciales
TIMED_REASONS = {'medical_appointment', 'legal_duty'}


# =============================================================================
# CORRECTION REQUESTS MANAGEMENT
# =============================================================================

@login_required_with_delegation_support
def resolver_incidencia(request):
    if request.method == 'POST':
        # Get effective context (delegation info if any)
        delegation_context = get_effective_context(request)

        incidencia_id = request.POST.get('incidencia_id')
        accion = request.POST.get('accion')
        # Capture the note coming from the modal form
        nota_resolucion = request.POST.get('nota_resolucion', '')

        incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)

        # --- COMPROBACIÓN DE CONCURRENCIA ---
        if incidencia.status != 'pending':
            messages.warning(request, "Esta incidencia ya ha sido gestionada (aceptada o denegada) por otro administrador.")
            return redirect('manager_logs')
        # ------------------------------------

        # --- INICIO AUDITORÍA: FOTO DEL ANTES ---
        estado_anterior = safe_dict(incidencia)
        # ----------------------------------------

        ficha_original = incidencia.time_entry

        # --- Determine who is approving ─────────────────────────────────────
        if delegation_context['is_delegating'] and delegation_context['delegated_user_role'] == UserCompany.RoleChoices.MANAGER:
            approver_user = Users.objects.get(id=delegation_context['delegated_user_id'])
        else:
            # Get the Users object corresponding to the Django user
            approver_user = Users.objects.filter(email=request.user.email).first()
            if not approver_user:
                # Fallback: try to get by username
                approver_user = Users.objects.filter(username=request.user.username).first()

        # --- AUDIT FIELDS ASSIGNMENT ---
        incidencia.approver = approver_user
        incidencia.approval_date = timezone.now()
        incidencia.correction_note = nota_resolucion

        if accion == 'aceptar':
            # 1. Mark the original as 'corrected'
            ficha_original.status = TimeEntries.EntryStatus.CORRECTED
            ficha_original.save()

            # --- CALCULATION OF SECONDS ---
            segundos = 0
            if incidencia.new_clock_in and incidencia.new_clock_out:
                delta = incidencia.new_clock_out - incidencia.new_clock_in
                segundos = int(delta.total_seconds())

            # 2. Create the new definitive record
            TimeEntries.objects.create(
                id=uuid.uuid4(),
                user=ficha_original.user,
                company=ficha_original.company,
                date=ficha_original.date,
                clock_in=incidencia.new_clock_in,
                clock_out=incidencia.new_clock_out,
                status=TimeEntries.EntryStatus.CONFIRMED,
                notes=f"Aceptado por {approver_user.username.title()}. Motivo: {incidencia.reason}",
                total_seconds=max(0, segundos)
            )
            incidencia.status = 'approved'
            messages.success(request, "Incidencia aceptada y registro actualizado.")

        elif accion == 'denegar':
            incidencia.status = 'rejected'
            messages.success(request, "Incidencia denegada correctamente.")

        # Save all changes (including approver, date and note)
        incidencia.save()

        # --- INICIO AUDITORÍA: FOTO DEL DESPUÉS ---
        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='timetracking_correctionrequest',
            record_id=str(incidencia.id),
            user=request.user,
            action_type='update', # Update
            before=estado_anterior,
            after=safe_dict(incidencia),
            reason=f"Incidencia {accion}da por manager",
            source='web' # Añadido
        )
        # -------------------------------------------

        return redirect('manager_logs')

    return HttpResponse("Método no permitido.")


@login_required_with_delegation_support
@require_POST
def exportar_logs_rechazadas(request):
    """
    Exporta las incidencias rechazadas a CSV.
    POST params: incidencia_id (lista de IDs seleccionadas)
    """
    incidencia_ids = request.POST.getlist('incidencia_id')

    if not incidencia_ids:
        return HttpResponse("No seleccionaste ningún registro para exportar.")

    incidencias = CorrectionRequests.objects.filter(
        id__in=incidencia_ids,
        status='rejected'
    ).select_related('requester', 'time_entry').order_by('-request_date')

    # AUDITORÍA: Exportación de incidencias rechazadas
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {len(incidencia_ids)} incidencias rechazadas',
        after={
            'tipo': 'Incidencias Rechazadas',
            'tabla': 'core_correction_requests',
            'cantidad': len(incidencia_ids),
            'ids': [str(id) for id in incidencia_ids],
        },
        source='web' # Añadido
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y')
    response['Content-Disposition'] = f'attachment; filename="reporte_incidencias_rechazadas_{fecha_reporte}.csv"'

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Empleado',
        'Fecha Solicitud',
        'Entrada Original',
        'Salida Original',
        'Entrada Solicitada',
        'Salida Solicitada',
        'Motivo',
        'Nota de Rechazo'
    ])

    for incidencia in incidencias:
        writer.writerow([
            f"{incidencia.requester.username} {incidencia.requester.surname}",
            incidencia.request_date.strftime('%d/%m/%Y %H:%M') if incidencia.request_date else '--/--/---- --:--',
            incidencia.time_entry.clock_in.strftime('%d/%m/%Y %H:%M') if incidencia.time_entry and incidencia.time_entry.clock_in else '--/--/---- --:--',
            incidencia.time_entry.clock_out.strftime('%H:%M') if incidencia.time_entry and incidencia.time_entry.clock_out else '--:--',
            incidencia.new_clock_in.strftime('%d/%m/%Y %H:%M') if incidencia.new_clock_in else '--/--/---- --:--',
            incidencia.new_clock_out.strftime('%H:%M') if incidencia.new_clock_out else '--:--',
            incidencia.reason or '',
            incidencia.correction_note or ''
        ])

    return response


@login_required_with_delegation_support
@require_POST
def editar_incidencia_rechazada(request):
    """
    Allow managers/admins to edit a rejected correction request (change times and reason)
    """
    from datetime import datetime

    incidencia_id = request.POST.get('incidencia_id')
    new_clock_in_str = request.POST.get('new_clock_in')
    new_clock_out_str = request.POST.get('new_clock_out')
    reason = request.POST.get('reason', '')

    if not incidencia_id:
        return HttpResponse("ID de incidencia no proporcionado.", status=400)

    # 1. Quitamos el filtro estricto de status='rejected' para evitar el error 404 feo
    incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)

    # --- 2. COMPROBACIÓN DE CONCURRENCIA ---
    if incidencia.status != 'rejected' or incidencia.deleted_at is not None:
        messages.warning(request, "⚠️ Esta incidencia ya no puede editarse porque ha sido modificada, reabierta o eliminada por otro administrador.")
        return redirect('manager_logs')
    # ------------------------------------

    # --- INICIO AUDITORÍA: FOTO DEL ANTES ---
    estado_anterior = safe_dict(incidencia)
    # ----------------------------------------

    # Parse datetime inputs
    try:
        if new_clock_in_str:
            new_in = datetime.fromisoformat(new_clock_in_str.replace('T', ' '))
            new_in = timezone.make_aware(new_in, timezone.get_current_timezone())
        else:
            new_in = None

        if new_clock_out_str:
            new_out = datetime.fromisoformat(new_clock_out_str.replace('T', ' '))
            new_out = timezone.make_aware(new_out, timezone.get_current_timezone())
        else:
            new_out = None
    except ValueError:
        return HttpResponse("Formato de fecha/hora inválido.", status=400)

    # Update the correction request
    incidencia.new_clock_in = new_in
    incidencia.new_clock_out = new_out
    incidencia.reason = reason
    # Reset status to pending for re-review
    incidencia.status = 'pending'
    incidencia.save()

    # --- INICIO AUDITORÍA: FOTO DEL DESPUÉS ---
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='timetracking_correctionrequest',
        record_id=str(incidencia.id),
        user=request.user,
        action_type='update',
        before=estado_anterior,
        after=safe_dict(incidencia),
        reason="Edición de incidencia rechazada para volver a revisión",
        source='web' # Añadido
    )
    # -------------------------------------------

    # 3. Añadimos el mensaje de éxito para dar feedback al usuario
    messages.success(request, "Incidencia editada y enviada a revisión correctamente.")
    return redirect('manager_logs')


@login_required_with_delegation_support
@require_POST
def eliminar_incidencia_rechazada(request):
    """
    Soft-delete a rejected correction request
    """
    incidencia_id = request.POST.get('incidencia_id')

    if not incidencia_id:
        return HttpResponse("ID de incidencia no proporcionado.", status=400)

    # La buscamos sin filtro estricto en el get_object para poder mandar el aviso si el estado cambió
    incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)

    # --- COMPROBACIÓN DE CONCURRENCIA ---
    if incidencia.deleted_at is not None or incidencia.status != 'rejected':
        messages.warning(request, "Esta incidencia ya ha sido eliminada o modificada por otro administrador.")
        return redirect('manager_logs')
    # ------------------------------------

    # --- INICIO AUDITORÍA: FOTO DEL ANTES ---
    estado_anterior = safe_dict(incidencia)
    # ----------------------------------------

    # Soft-delete
    incidencia.deleted_at = timezone.now()
    incidencia.save()

    # --- INICIO AUDITORÍA: FOTO DEL DESPUÉS ---
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='timetracking_correctionrequest',
        record_id=str(incidencia.id),
        user=request.user,
        action_type='voided', # Delete (Soft-delete)
        before=estado_anterior,
        after=safe_dict(incidencia),
        reason="Eliminación (soft-delete) de incidencia rechazada",
        source='web' # Añadido
    )
    # -------------------------------------------

    messages.success(request, "Incidencia rechazada eliminada correctamente.")
    return redirect('manager_logs')


# =============================================================================
# LEAVE REQUESTS MANAGEMENT
# =============================================================================

@login_required_with_delegation_support
def api_leave_pending(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    try:
        company = get_company(request)

        # Si hay delegación, mostrar solicitudes de la empresa delegada
        if delegation_context['is_delegating']:
            company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
            if not company:
                return JsonResponse({'error': 'Empresa delegada no encontrada'}, status=400)

        leaves = LeaveRequest.objects.filter(
            company=company,
            status=LeaveRequest.LeaveStatus.PENDING
        ).select_related('user')

        data = []
        for l in leaves:
            full_name = f"{l.user.username.title()} {l.user.surname.title()}".strip()

            data.append({
                'id':           str(l.id),
                'user':         full_name or l.user.email.lower(),
                'leave_type':   l.get_leave_type_display(),
                'leave_type_raw': l.leave_type,
                'leave_reason': l.get_leave_reason_display(),
                'start_date':   l.start_date.strftime('%d/%m/%Y'),
                'end_date':     l.end_date.strftime('%d/%m/%Y'),
                'reason_note':  l.reason_note or ""
            })

        return JsonResponse({'requests': data})

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required_with_delegation_support
def api_get_leave_for_review(request, leave_id):
    """Obtiene detalles de una solicitud para el modal de aprobación,
    incluyendo sugerencias de multiplicador para vacaciones."""
    company = get_company(request)
    leave = get_object_or_404(LeaveRequest, id=leave_id, company=company, status=LeaveRequest.LeaveStatus.PENDING)

    response_data = {
        'id': str(leave.id),
        'user': f"{leave.user.username.title()} {leave.user.surname.title()}".strip(),
        'leave_type': leave.leave_type,
        'leave_type_display': leave.get_leave_type_display(),
        'leave_reason': leave.leave_reason,
        'leave_reason_display': leave.get_leave_reason_display(),
        'start_date': leave.start_date.isoformat(),
        'end_date': leave.end_date.isoformat(),
        'reason_note': leave.reason_note or '',
    }

    # Si es vacaciones, agregar datos sugeridos
    if leave.leave_type == 'vacation':
        # 1. Obtener multiplicador sugerido
        suggested_multiplier = VacationPeriodMultiplier.get_multiplier_for_range(
            company_id=leave.company.id,
            start_date=leave.start_date,
            end_date=leave.end_date
        )

        # 2. Calcular días consumidos en el año
        year = leave.start_date.year
        consumed_days = LeaveRequest.get_consumed_days(
            user_id=leave.user.id,
            company_id=leave.company.id,
            year=year
        )

        # 3. Obtener límite anual
        settings = CompanySettings.objects.filter(company=leave.company, deleted_at__isnull=True).first()
        available_days = settings.default_vacation_days if settings else 23

        # 4. Calcular días de esta solicitud
        request_days = (leave.end_date - leave.start_date).days + 1

        # 5. Determinar si hay aviso
        exceeds_limit = (consumed_days + request_days) > available_days
        remaining_days = available_days - consumed_days
        remaining_days_after = available_days - consumed_days - request_days
        consumed_percentage = min(100, int((consumed_days / available_days) * 100)) if available_days > 0 else 0
        consumed_days_with_request = consumed_days + request_days

        response_data.update({
            'suggested_multiplier': float(suggested_multiplier),
            'consumed_days': float(consumed_days),
            'available_days': available_days,
            'remaining_days': float(remaining_days),
            'request_days': request_days,
            'exceeds_limit': exceeds_limit,
            'remaining_days_after': float(remaining_days_after),
            'consumed_percentage': consumed_percentage,
            'consumed_days_with_request': consumed_days_with_request,
        })

    return JsonResponse(response_data)



@login_required_with_delegation_support
@require_POST
def api_leave_review(request, leave_id):
    """Manager aprueba o rechaza una solicitud."""
    company = get_company(request)
    leave   = get_object_or_404(LeaveRequest, id=leave_id, company=company)
 
    # --- COMPROBACION DE CONCURRENCIA ---
    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Esta solicitud ya fue revisada por otro administrador.'}, status=400)
 
    # ------------------------------------
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
 
    action = data.get('action')  # 'approve' | 'reject'
    note   = data.get('note', '')
    note   = note.strip() if note else None
 
    #todo: Validar estado de la solicitud antes de aprobar/rechazar (ej: no solapamientos aprobados, etc)

    if action == 'approve':
        new_status  = LeaveRequest.LeaveStatus.APPROVED
        action_type = AuditLog.AuditAction.UPDATE

        # Procesar hour_multiplier para vacaciones
        hour_multiplier = 1.0
        if leave.leave_type == 'vacation':
            hour_multiplier = data.get('hour_multiplier', 1.0)
            try:
                hour_multiplier = float(hour_multiplier)
                if not (0.1 <= hour_multiplier <= 2.0):
                    return JsonResponse({'error': 'Multiplicador fuera de rango (0.1 a 2.0)'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Multiplicador inválido'}, status=400)

    elif action == 'reject':
        new_status  = LeaveRequest.LeaveStatus.REJECTED
        action_type = AuditLog.AuditAction.VOIDED
        hour_multiplier = 1.0
    else:
        return JsonResponse({'error': 'Acción no válida. Usa "approve" o "reject"'}, status=400)

    before = serialize_leave(leave)
    leave.reviewed_by = request.user
    leave.reviewed_at = timezone.now()
    leave.review_note = note

    update_fields = {
        'status': new_status,
        'reviewed_by': leave.reviewed_by,
        'reviewed_at': leave.reviewed_at,
        'review_note': leave.review_note,
        'force_proof': True,
    }

    if action == 'approve':
        update_fields['hour_multiplier'] = hour_multiplier

    updated = LeaveRequest.objects.filter(pk=leave.pk).update(**update_fields)

    if not updated:
        return JsonResponse({'error': 'No se pudo actualizar la solicitud.'}, status=500)

    leave.refresh_from_db()
    log_leave(leave, request.user, action_type, before=before,
               reason=note or ('Aprobación' if action == 'approve' else 'Rechazo'),
               source='web')

    return JsonResponse({'ok': True, 'new_status': new_status})
 


# ── API: solicitudes resueltas ────────────────────────────────────────────────

@login_required
def api_leave_resolved(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    company = get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    user_is_manager = is_manager(request, company)
    user_id         = request.GET.get('user_id', '')

    # Determinar si mostrar solicitudes PENDING
    # Mostrar PENDING solo si:
    # 1. El usuario NO es manager, O
    # 2. El usuario es manager PERO está viendo su propio calendario (user_id vacío)
    show_pending = (not user_is_manager) or (user_is_manager and not user_id)

    resolved_statuses = [
        LeaveRequest.LeaveStatus.APPROVED,
        LeaveRequest.LeaveStatus.REJECTED,
        LeaveRequest.LeaveStatus.CANCELED,
    ]
    if show_pending:
        resolved_statuses.append(LeaveRequest.LeaveStatus.PENDING)

    base_qs = LeaveRequest.objects.filter(
        company=company,
        status__in=resolved_statuses,
    ).select_related('user', 'reviewed_by').order_by('-updated_at')

    if user_is_manager and user_id == 'all':
        leaves = base_qs[:50]
    elif user_is_manager and user_id:
        try:
            target = get_object_or_404(Users, id=user_id)
        except Exception:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=400)
        leaves = base_qs.filter(user=target)[:30]
    else:
        # Si hay delegación, mostrar solicitudes del usuario delegado
        if delegation_context['is_delegating']:
            delegated_user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
            if not delegated_user:
                return JsonResponse({'error': 'Usuario delegado no encontrado'}, status=400)
            leaves = base_qs.filter(user=delegated_user)[:30]
        else:
            leaves = base_qs.filter(user=request.user)[:30]

    show_user_col: bool = user_is_manager and user_id == 'all'

    data = []
    for l in leaves:
        data.append({
            'id':               str(l.id),
            'user_name':        f"{l.user.username.title()} {l.user.surname.title()}".strip(),
            'leave_type':       l.get_leave_type_display(),
            'leave_reason':     l.get_leave_reason_display(),
            'start_date':       l.start_date.strftime('%d/%m/%Y'),
            'end_date':         l.end_date.strftime('%d/%m/%Y'),
            'status':           l.status,
            'status_display':   l.get_status_display(),
            'reason_note':      l.reason_note or '',
            'review_note':      l.review_note or '',
            'reviewed_by':      f"{l.reviewed_by.username} {l.reviewed_by.surname}".strip() if l.reviewed_by else '',
            'attachment_path':  l.attachment_path or '',
        })

    return JsonResponse({
        'requests':      data,
        'show_user_col': user_is_manager and user_id == 'all',
    })

@login_required
def api_calendar_events(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    company = get_company(request)
    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    user_id = request.GET.get('user_id')
    statuses_param = request.GET.get('statuses', 'pending,approved')
    statuses = [s.strip() for s in statuses_param.split(',') if s.strip()]

    start_str = request.GET.get('start', '')[:10]
    end_str   = request.GET.get('end', '')[:10]

    try:
        start = date.fromisoformat(start_str)
        end   = date.fromisoformat(end_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': f'Invalid date format: {start_str}'}, status=400)

    events = []
    STATUS_COLOR = {
        'pending':  '#d97706',
        'approved': '#5a8f5a',
        'rejected': '#b94040',
    }

    # Mapeo de status para filtrar
    status_mapping = {
        'pending': LeaveRequest.LeaveStatus.PENDING,
        'approved': LeaveRequest.LeaveStatus.APPROVED,
        'rejected': LeaveRequest.LeaveStatus.REJECTED,
    }

    filtered_statuses = [status_mapping[s] for s in statuses if s in status_mapping]

    if not filtered_statuses:
        filtered_statuses = [LeaveRequest.LeaveStatus.PENDING, LeaveRequest.LeaveStatus.APPROVED]

    # ── Todos los empleados ───────────────────────────────────────────────
    if user_id == 'all' and check_is_manager(request, company):
        leaves = LeaveRequest.objects.filter(
            company=company,
            start_date__lte=end,
            end_date__gte=start,
            status__in=filtered_statuses,
        ).select_related('user')

        # Detectar solapamientos
        conflict_map = {}
        for leave in leaves:
            conflicts = LeaveRequest.objects.filter(
                user=leave.user,
                company=company,
                status__in=[LeaveRequest.LeaveStatus.APPROVED, LeaveRequest.LeaveStatus.PENDING],
            ).exclude(id=leave.id).filter(
                start_date__lte=leave.end_date,
                end_date__gte=leave.start_date
            )
            if conflicts.exists():
                conflict_map[str(leave.id)] = True

        for leave in leaves:
            is_owner = leave.user.email == request.user.email or str(leave.user.id) == str(request.user.id)
            extended_props = {
                'status': leave.get_status_display(),
                'reason': leave.reason_note or '',
                'has_conflict': str(leave.id) in conflict_map,
                'leave_type': leave.leave_type,
                'attachment_path': leave.attachment_path or '',
                'is_owner': is_owner,
            }
            # Añadir horas si existen
            if leave.start_time:
                extended_props['start_time'] = leave.start_time.isoformat()
            if leave.end_time:
                extended_props['end_time'] = leave.end_time.isoformat()
            
            events.append({
                'id': f'leave-{leave.id}',
                'title': f'{leave.user.username.title()} · {leave.get_leave_type_display()}',
                'start': leave.start_date.isoformat(),
                'end': (leave.end_date + timedelta(days=1)).isoformat(),
                'color': STATUS_COLOR.get(leave.status, '#6b7280'),
                'allDay': True,
                'classNames': ['has-conflict'] if str(leave.id) in conflict_map else [],
                'extendedProps': extended_props,
            })
        return JsonResponse(events, safe=False)

    # ── Empleado concreto (manager) o usuario propio ──────────────────────
    # Si hay delegación, usar el usuario delegado
    if delegation_context['is_delegating']:
        target_user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
        if not target_user:
            return JsonResponse({'error': 'Usuario delegado no encontrado'}, status=400)
        real_user = target_user
    else:
        # Obtener el usuario personalizado (Users) correspondiente a request.user
        real_user = Users.objects.filter(email=request.user.email).first()
        if not real_user:
            real_user = Users.objects.filter(username=request.user.username).first()
        if not real_user:
            return JsonResponse({'error': 'Usuario no encontrado en el sistema'}, status=400)

        target_user = real_user

        # Si es manager viendo a otro usuario específico, cambiar target_user
        if user_id and check_is_manager(request, company):
            try:
                target_user = get_object_or_404(Users, id=user_id)
            except:
                return JsonResponse({'error': 'Invalid User ID'}, status=400)

    leaves = LeaveRequest.objects.filter(
        user=target_user,
        company=company,
        start_date__lte=end,
        end_date__gte=start,
        status__in=filtered_statuses,
    )

    # Detectar solapamientos
    conflict_map = {}
    for leave in leaves:
        conflicts = LeaveRequest.objects.filter(
            user=leave.user,
            company=company,
            status__in=[LeaveRequest.LeaveStatus.APPROVED, LeaveRequest.LeaveStatus.PENDING],
        ).exclude(id=leave.id).filter(
            start_date__lte=leave.end_date,
            end_date__gte=leave.start_date
        )
        if conflicts.exists():
            conflict_map[str(leave.id)] = True

    for leave in leaves:
        is_owner = leave.user.id == real_user.id
        extended_props = {
            'status': leave.get_status_display(),
            'reason': leave.reason_note or '',
            'has_conflict': str(leave.id) in conflict_map,
            'leave_type': leave.leave_type,
            'attachment_path': leave.attachment_path or '',
            'is_owner': is_owner,
            'leave_reason': leave.leave_reason,
            'start_time': leave.start_time.isoformat() if leave.start_time else None,
            'end_time': leave.end_time.isoformat() if leave.end_time else None,
        }
        events.append({
            'id': f'leave-{leave.id}',
            'title': f'{leave.get_leave_type_display()}',
            'start': leave.start_date.isoformat(),
            'end': (leave.end_date + timedelta(days=1)).isoformat(),
            'color': STATUS_COLOR.get(leave.status, '#6b7280'),
            'allDay': True,
            'classNames': ['has-conflict'] if str(leave.id) in conflict_map else [],
            'extendedProps': extended_props,
        })

    return JsonResponse(events, safe=False)

# ── API: validar solapamientos ────────────────────────────────────────────────
 
@login_required
@require_POST
def api_validate_leave_overlap(request):
    """Valida si hay solapamientos ANTES de crear solicitud"""
    try:
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Fechas inválidas'}, status=400)
        
        if not start_date or not end_date:
            return JsonResponse({'error': 'Fechas inválidas'}, status=400)
        
        company = get_company(request)
        
        conflicts = LeaveRequest.objects.filter(
            user=request.user,
            company=company,
            status__in=[LeaveRequest.LeaveStatus.PENDING, LeaveRequest.LeaveStatus.APPROVED],
            start_date__lte=end_date,
            end_date__gte=start_date
        ).values('id', 'leave_type', 'start_date', 'end_date', 'status')
        
        conflicts_list = list(conflicts)
        
        if conflicts_list:
            return JsonResponse({
                'ok': False,
                'conflicts': [
                    {
                        'id': str(c['id']),
                        'leave_type': dict(LeaveRequest.LeaveType.choices).get(c['leave_type'], c['leave_type']),
                        'start_date': str(c['start_date']),
                        'end_date': str(c['end_date']),
                    }
                    for c in conflicts_list
                ]
            }, status=200)
        
        return JsonResponse({'ok': True, 'conflicts': []})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ── API: solicitar ausencia ────────────────────────────────────────────────────

@login_required
@require_POST
def api_leave_request_create(request):
    delegation_context = get_effective_context(request)

    if delegation_context['is_delegating']:
        user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
        company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
        if not user or not company:
            return JsonResponse({'error': 'Usuario o empresa delegada no encontrada'}, status=400)
    else:
        user = request.user
        company = get_company(request)

    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
    else:
        data = request.POST.dict()

    start_date   = data.get('start_date')
    end_date     = data.get('end_date')
    leave_reason = data.get('leave_reason', LeaveRequest.LeaveReason.OTHER)
    reason_note  = data.get('reason_note', '')

    # Deducir leave_type automáticamente del leave_reason
    leave_type = LeaveRequest.LeaveType.VACATION if leave_reason == LeaveRequest.LeaveReason.ANNUAL else LeaveRequest.LeaveType.ABSENCE

    if not start_date or not end_date:
        return JsonResponse({'error': 'Fechas obligatorias'}, status=400)

    try:
        start = date.fromisoformat(start_date)
        end   = date.fromisoformat(end_date)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

    if end < start:
        return JsonResponse({'error': 'La fecha fin no puede ser anterior a la fecha inicio'}, status=400)

    if start < date.today():
        return JsonResponse({'error': 'No puedes solicitar días anteriores a hoy'}, status=400)

    if leave_type not in LeaveRequest.LeaveType.values:
        return JsonResponse({'error': 'Tipo de solicitud no válido'}, status=400)

    if leave_reason not in LeaveRequest.LeaveReason.values:
        return JsonResponse({'error': 'Motivo no válido'}, status=400)

    # --- Horas parciales (solo para cita médica / deber legal) ---
    start_time = None
    end_time   = None

    if leave_reason in TIMED_REASONS:
        from django.utils.dateparse import parse_time
        start_time_str = data.get('start_time', '').strip() or None
        end_time_str   = data.get('end_time', '').strip() or None

        if start_time_str:
            start_time = parse_time(start_time_str)
            if start_time is None:
                return JsonResponse({'error': 'Formato de hora de inicio inválido'}, status=400)

        if end_time_str:
            end_time = parse_time(end_time_str)
            if end_time is None:
                return JsonResponse({'error': 'Formato de hora de fin inválido'}, status=400)

        if start_time and end_time and end_time <= start_time:
            return JsonResponse(
                {'error': 'La hora de fin debe ser posterior a la hora de inicio'},
                status=400
            )

    leave = LeaveRequest.objects.create(
        user=user,
        company=company,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        leave_reason=data.get('leave_reason'),
        reason_note=data.get('reason_note'),
        start_time=data.get('start_time') if data.get('start_time') else None,
        end_time=data.get('end_time') if data.get('end_time') else None,
        status=LeaveRequest.LeaveStatus.PENDING
    )

    log_leave(leave, request.user, AuditLog.AuditAction.CREATE,
               reason=reason_note or 'Solicitud creada desde calendario',
               source='web')

    return JsonResponse({
        'ok':      True,
        'id':      str(leave.id),
        'message': 'Solicitud enviada correctamente',
    }, status=201)


@login_required
@require_POST
def api_leave_request_edit(request, leave_id):
    """Permite que el usuario edite su propia solicitud mientras esté en estado PENDIENTE."""
    delegation_context = get_effective_context(request)

    if delegation_context['is_delegating']:
        user = Users.objects.filter(id=delegation_context['delegated_user_id']).first()
        company = Companies.objects.filter(id=delegation_context['delegated_company_id']).first()
        if not user or not company:
            return JsonResponse({'error': 'Usuario o empresa delegada no encontrada'}, status=400)
    else:
        user = request.user
        company = get_company(request)

    if not company:
        return JsonResponse({'error': 'No company'}, status=400)

    leave = get_object_or_404(LeaveRequest, id=leave_id, user=user, company=company)

    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Solo se pueden editar solicitudes pendientes'}, status=403)

    if request.content_type and 'application/json' in request.content_type:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
    else:
        data = request.POST.dict()

    start_date   = data.get('start_date')
    end_date     = data.get('end_date')
    leave_reason = data.get('leave_reason', leave.leave_reason)
    reason_note = data.get('reason_note', '')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    if not start_date or not end_date:
        return JsonResponse({'error': 'Fechas obligatorias'}, status=400)

    try:
        start = date.fromisoformat(start_date)
        end   = date.fromisoformat(end_date)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

    if end < start:
        return JsonResponse({'error': 'La fecha fin no puede ser anterior a la fecha inicio'}, status=400)

    if start < date.today():
        return JsonResponse({'error': 'No puedes solicitar días anteriores a hoy'}, status=400)

    if leave_reason not in LeaveRequest.LeaveReason.values:
        return JsonResponse({'error': 'Motivo no válido'}, status=400)

    # --- Validación de horas si es cita médica o deber público ---
    hourly_reasons = ['medical_appointment', 'legal_duty']
    if leave_reason in hourly_reasons:
        if not start_time or not end_time:
            return JsonResponse({'error': 'Las horas son obligatorias para este tipo de ausencia'}, status=400)
        try:
            start_t = datetime.strptime(start_time, '%H:%M').time()
            end_t = datetime.strptime(end_time, '%H:%M').time()
            if end_t < start_t:
                return JsonResponse({'error': 'La hora fin no puede ser menor a la hora inicio'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Formato de hora inválido'}, status=400)
    else:
        # Limpiar horas si no es cita médica/deber público
        start_time = None
        end_time = None

    # --- Sanitización de reason_note ---
    if reason_note and len(reason_note) > 500:
        return JsonResponse({'error': 'La nota no puede exceder 500 caracteres'}, status=400)

    conflicts = LeaveRequest.objects.filter(
        user=user,
        company=company,
        status__in=[LeaveRequest.LeaveStatus.PENDING, LeaveRequest.LeaveStatus.APPROVED],
        start_date__lte=end,
        end_date__gte=start
    ).exclude(id=leave_id).values('id', 'leave_type', 'start_date', 'end_date', 'status')

    if conflicts:
        return JsonResponse({
            'error': 'Hay un solapamiento con otra solicitud',
            'conflicts': [
                {
                    'id': str(c['id']),
                    'leave_type': dict(LeaveRequest.LeaveType.choices).get(c['leave_type'], c['leave_type']),
                    'start_date': str(c['start_date']),
                    'end_date':   str(c['end_date']),
                }
                for c in conflicts
            ]
        }, status=400)

    # --- Horas parciales (solo para cita médica / deber legal) ---
    start_time = None
    end_time   = None

    if leave_reason in TIMED_REASONS:
        from django.utils.dateparse import parse_time
        start_time_str = data.get('start_time', '').strip() or None
        end_time_str   = data.get('end_time', '').strip() or None

        if start_time_str:
            start_time = parse_time(start_time_str)
            if start_time is None:
                return JsonResponse({'error': 'Formato de hora de inicio inválido'}, status=400)

        if end_time_str:
            end_time = parse_time(end_time_str)
            if end_time is None:
                return JsonResponse({'error': 'Formato de hora de fin inválido'}, status=400)

        if start_time and end_time and end_time <= start_time:
            return JsonResponse(
                {'error': 'La hora de fin debe ser posterior a la hora de inicio'},
                status=400
            )

    before = serialize_leave(leave)

    leave.start_date  = start
    leave.end_date    = end
    leave.leave_reason = leave_reason
    leave.reason_note = reason_note
    leave.start_time = start_time
    leave.end_time = end_time
    # Deducir leave_type automáticamente del leave_reason
    leave.leave_type = LeaveRequest.LeaveType.VACATION if leave_reason == LeaveRequest.LeaveReason.ANNUAL else LeaveRequest.LeaveType.ABSENCE
    leave.save(update_fields=['start_date', 'end_date', 'leave_reason', 'reason_note', 'start_time', 'end_time', 'leave_type', 'updated_at'])

    log_leave(leave, request.user, AuditLog.AuditAction.UPDATE,
              before=before,
              reason='Edición de solicitud por el usuario',
              source='web')

    return JsonResponse({
        'ok':     True,
        'message': 'Solicitud actualizada correctamente'
    }, status=200)

@login_required
@require_POST
def api_leave_upload_attachment(request, leave_id):
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    archivo = request.FILES.get('attachment')

    if archivo:
        # Obtener el objeto Users personalizado
        user_obj = Users.objects.filter(email=request.user.email).first()
        if not user_obj:
            user_obj = Users.objects.filter(username=request.user.username).first()

        # Crear nombre de usuario limpio
        username_clean = request.user.username.title()
        if user_obj and user_obj.surname:
            username_clean = f"{request.user.username.title()}{user_obj.surname.title()}".replace(" ", "")
        else:
            username_clean = request.user.username.title()

        # Creamos el timestamp y sacamos la extensión
        timestamp = timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H.%M.%S')
        _, extension = os.path.splitext(archivo.name)

        # Nombre final: MariaAeptic_2026-05-11_14.43.55.png
        nombre_final = f"{username_clean}_{timestamp}{extension.lower()}"

        # Ruta relativa: justificantes/ID_SOLICITUD/archivo.pdf
        ruta = f"justificantes/{leave_id}/{nombre_final}"

        # Borrar el anterior si existe para no llenar el servidor de basura
        if leave.attachment_path:
            default_storage.delete(leave.attachment_path)

        # Guardar físicamente (Django crea las carpetas solo)
        default_storage.save(ruta, ContentFile(archivo.read()))

        # Guardar la ruta en la base de datos
        leave.attachment_path = ruta
        leave.save()

        return JsonResponse({'ok': True, 'message': 'Subido con éxito'})

    return JsonResponse({'error': 'No file provided'}, status=400)

    
# ── API: cancelar solicitud (empleado) ────────────────────────────────────────
 
@login_required
@require_POST
def api_leave_request_cancel(request, leave_id):
    """El empleado puede cancelar sus propias solicitudes pendientes."""
    company = get_company(request)
    leave = get_object_or_404(LeaveRequest, id=leave_id, user=request.user, company=company)

    # --- COMPROBACION DE CONCURRENCIA ---
    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Solo se pueden cancelar solicitudes pendientes'}, status=400)
    # ------------------------------------

    before = serialize_leave(leave)
    leave.status = LeaveRequest.LeaveStatus.CANCELED
    leave.save(update_fields=['status', 'updated_at'])

    # AUDITORÍA: Cancelación
    log_leave(leave, request.user, AuditLog.AuditAction.VOIDED,
               before=before, reason='Cancelación por el empleado',
               source='web') # Añadido

    return JsonResponse({'ok': True})


# =============================================================================
# VACATION PERIOD MULTIPLIERS MANAGEMENT (BLOQUE 4)
# =============================================================================

@login_required_with_delegation_support
@login_required_with_delegation_support
def list_vacation_periods(request):
    """Lista todos los periodos vacacionales de la empresa del manager."""
    company = get_company(request)

    if not is_manager(request, company):
        return JsonResponse({'error': 'No tienes permiso para esta operación'}, status=403)

    periods = VacationPeriodMultiplier.objects.filter(
        company=company,
        deleted_at__isnull=True
    ).order_by('date_from')

    return JsonResponse({
        'periods': [
            {
                'id': str(p.id),
                'name': p.name,
                'date_from': p.date_from.isoformat(),
                'date_to': p.date_to.isoformat(),
                'multiplier': float(p.multiplier),
                'created_by': p.created_by.username if p.created_by else 'Sistema',
                'created_at': p.created_at.isoformat(),
            }
            for p in periods
        ]
    })


@login_required_with_delegation_support
@require_POST
def create_vacation_period(request):
    """Crea un nuevo periodo de multiplicador."""
    company = get_company(request)

    if not is_manager(request, company):
        return JsonResponse({'error': 'No tienes permiso para esta operación'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    required = ['name', 'date_from', 'date_to', 'multiplier']
    if not all(data.get(f) for f in required):
        return JsonResponse({'error': 'Campos requeridos incompletos'}, status=400)

    try:
        name = data.get('name').strip()
        date_from = datetime.strptime(data.get('date_from'), '%Y-%m-%d').date()
        date_to = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
        multiplier = float(data.get('multiplier'))

        # Validaciones
        if not (0.1 <= multiplier <= 2.0):
            return JsonResponse({'error': 'Multiplicador debe estar entre 0.1 y 2.0'}, status=400)
        if date_from > date_to:
            return JsonResponse({'error': 'Fecha inicio debe ser anterior a fecha fin'}, status=400)
        if len(name) > 100:
            return JsonResponse({'error': 'Nombre muy largo'}, status=400)

        # Crear periodo
        period = VacationPeriodMultiplier.objects.create(
            id=uuid.uuid4(),
            company=company,
            name=name,
            date_from=date_from,
            date_to=date_to,
            multiplier=multiplier,
            created_by=request.user,
        )

        # Auditoría
        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='vacation_period_multipliers',
            record_id=str(period.id),
            user=request.user,
            action_type='create',
            reason=f"Creación de periodo vacacional '{name}'",
            source='web'
        )

        return JsonResponse({'ok': True, 'id': str(period.id)})

    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {str(e)}'}, status=400)


@login_required_with_delegation_support
@require_POST
def edit_vacation_period(request):
    """Edita un periodo existente."""
    company = get_company(request)

    if not is_manager(request, company):
        return JsonResponse({'error': 'No tienes permiso para esta operación'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    period_id = data.get('id')
    if not period_id:
        return JsonResponse({'error': 'ID del periodo requerido'}, status=400)

    period = get_object_or_404(
        VacationPeriodMultiplier,
        id=period_id,
        company=company
    )

    try:
        # Guardamos el estado anterior
        before = {
            'name': period.name,
            'date_from': str(period.date_from),
            'date_to': str(period.date_to),
            'multiplier': float(period.multiplier),
        }

        # Actualizar campos si se proporcionan
        if 'name' in data:
            period.name = data['name'].strip()
        if 'date_from' in data:
            period.date_from = datetime.strptime(data['date_from'], '%Y-%m-%d').date()
        if 'date_to' in data:
            period.date_to = datetime.strptime(data['date_to'], '%Y-%m-%d').date()
        if 'multiplier' in data:
            mult = float(data['multiplier'])
            if not (0.1 <= mult <= 2.0):
                return JsonResponse({'error': 'Multiplicador debe estar entre 0.1 y 2.0'}, status=400)
            period.multiplier = mult

        # Validación de fechas
        if period.date_from > period.date_to:
            return JsonResponse({'error': 'Fecha inicio debe ser anterior a fecha fin'}, status=400)

        period.updated_at = timezone.now()
        period.save()

        # Auditoría
        after = {
            'name': period.name,
            'date_from': str(period.date_from),
            'date_to': str(period.date_to),
            'multiplier': float(period.multiplier),
        }

        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='vacation_period_multipliers',
            record_id=str(period.id),
            user=request.user,
            action_type='update',
            before=before,
            after=after,
            reason=f"Edición de periodo vacacional '{period.name}'",
            source='web'
        )

        return JsonResponse({'ok': True})

    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Datos inválidos: {str(e)}'}, status=400)


@login_required_with_delegation_support
@require_POST
def delete_vacation_period(request):
    """Soft-delete de un periodo vacacional."""
    company = get_company(request)

    if not is_manager(request, company):
        return JsonResponse({'error': 'No tienes permiso para esta operación'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    period_id = data.get('id')
    if not period_id:
        return JsonResponse({'error': 'ID del periodo requerido'}, status=400)

    period = get_object_or_404(
        VacationPeriodMultiplier,
        id=period_id,
        company=company,
        deleted_at__isnull=True
    )

    # Soft-delete
    before = {
        'name': period.name,
        'deleted_at': None,
    }

    period.deleted_at = timezone.now()
    period.save()

    # Auditoría
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='vacation_period_multipliers',
        record_id=str(period.id),
        user=request.user,
        action_type='voided',
        before=before,
        after={'deleted_at': str(period.deleted_at)},
        reason=f"Eliminación (soft-delete) de periodo '{period.name}'",
        source='web'
    )

    return JsonResponse({'ok': True})