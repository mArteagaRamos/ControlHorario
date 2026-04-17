# corrections/views.py

import csv
import json
from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date
import uuid
from uuid import uuid4

from users.models import Users, Companies, UserCompany
from timetracking.models import TimeEntries
from corrections.models import LeaveRequest, CorrectionRequests
from audit.models import AuditLog
from audit.utils import safe_dict
from core.decorators import manager_or_admin_required, manager_or_admin_with_delegation_check
from core.services import get_effective_context, serialize_leave, log_leave, get_company


# =============================================================================
# CORRECTION REQUESTS MANAGEMENT
# =============================================================================

@manager_or_admin_with_delegation_check
def resolver_incidencia(request):
    if request.method == 'POST':
        # Get effective context (delegation info if any)
        delegation_context = get_effective_context(request)

        incidencia_id = request.POST.get('incidencia_id')
        accion = request.POST.get('accion')
        # Capture the note coming from the modal form
        nota_resolucion = request.POST.get('nota_resolucion', '')

        incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)

        # --- INICIO AUDITORÍA: FOTO DEL ANTES ---
        estado_anterior = safe_dict(incidencia)
        # ----------------------------------------

        ficha_original = incidencia.time_entry

        # --- Determine who is approving ─────────────────────────────────────
        # If delegating and delegated user is manager: use them
        # Otherwise: use request.user
        if delegation_context['is_delegating'] and delegation_context['delegated_user_role'] == UserCompany.RoleChoices.MANAGER:
            approver_user = Users.objects.get(id=delegation_context['delegated_user_id'])
        else:
            approver_user = request.user

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
                notes=f"Aceptado por {approver_user.username}. Motivo: {incidencia.reason}",
                total_seconds=max(0, segundos)
            )
            incidencia.status = 'approved'

        elif accion == 'denegar':
            incidencia.status = 'rejected'

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
            reason=f"Incidencia {accion}da por manager"
        )
        # -------------------------------------------

        return redirect('manager_logs')

    return HttpResponse("Método no permitido.")


@manager_or_admin_with_delegation_check
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

    # 🔐 AUDITORÍA: Exportación de incidencias rechazadas
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
        }
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


@manager_or_admin_with_delegation_check
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

    incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id, status='rejected')

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
        reason="Edición de incidencia rechazada para volver a revisión"
    )
    # -------------------------------------------

    return redirect('manager_logs')


@manager_or_admin_with_delegation_check
@require_POST
def eliminar_incidencia_rechazada(request):
    """
    Soft-delete a rejected correction request
    """
    incidencia_id = request.POST.get('incidencia_id')

    if not incidencia_id:
        return HttpResponse("ID de incidencia no proporcionado.", status=400)

    incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id, status='rejected')

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
        reason="Eliminación (soft-delete) de incidencia rechazada"
    )
    # -------------------------------------------

    return redirect('manager_logs')


# =============================================================================
# LEAVE REQUESTS MANAGEMENT
# =============================================================================

@manager_or_admin_with_delegation_check
def api_leave_pending(request):
    try:
        company = get_company(request)
        leaves = LeaveRequest.objects.filter(
            company=company,
            status=LeaveRequest.LeaveStatus.PENDING
        ).select_related('user')

        data = []
        for l in leaves:
            # Según tu users/models.py, los campos son 'username' y 'surname'
            full_name = f"{l.user.username} {l.user.surname}".strip()

            data.append({
                'id':           str(l.id),
                'user':         full_name or l.user.email,
                'leave_type':   l.get_leave_type_display(),
                # USAMOS 'reason' directamente si get_reason_display falla
                'leave_reason': l.get_leave_reason_display(),
                'start_date':   l.start_date.strftime('%d/%m/%Y'),
                'end_date':     l.end_date.strftime('%d/%m/%Y'),
                'reason_note':  l.reason_note or ""
            })

        # IMPORTANTE: Envolver en un diccionario {'requests': ...} para calendar.html
        return JsonResponse({'requests': data})

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@manager_or_admin_with_delegation_check
@require_POST
def api_leave_review(request, leave_id):
    """Manager aprueba o rechaza una solicitud."""
    company = get_company(request)
    leave   = get_object_or_404(LeaveRequest, id=leave_id, company=company)

    if leave.status != LeaveRequest.LeaveStatus.PENDING:
        return JsonResponse({'error': 'Esta solicitud ya fue revisada'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    action = data.get('action')  # 'approve' | 'reject'
    note   = data.get('note', '')
    note   = note.strip() if note else None

    if action == 'approve':

        new_status  = LeaveRequest.LeaveStatus.APPROVED
        action_type = AuditLog.AuditAction.UPDATE

        # Cambiar status del usuario a 'inactive' cuando se aprueba
        Users.objects.filter(id=leave.user.id).update(status=Users.StatusChoices.INACTIVE)
    elif action == 'reject':
        new_status  = LeaveRequest.LeaveStatus.REJECTED
        action_type = AuditLog.AuditAction.VOIDED
    else:
        return JsonResponse({'error': 'Acción no válida. Usa "approve" o "reject"'}, status=400)

    before = serialize_leave(leave)
    leave.reviewed_by = request.user
    leave.reviewed_at = timezone.now()
    leave.review_note = note
    updated = LeaveRequest.objects.filter(pk=leave.pk).update(
        status      = new_status,
        reviewed_by = leave.reviewed_by,
        reviewed_at = leave.reviewed_at,
        review_note = leave.review_note,
        force_proof = True,
    )

    if not updated:
        return JsonResponse({'error': 'No se pudo actualizar la solicitud.'}, status=500)

    leave.refresh_from_db()
    log_leave(leave, request.user, action_type, before=before,
               reason=note or ('Aprobación' if action == 'approve' else 'Rechazo'))

    return JsonResponse({'ok': True, 'new_status': new_status})
