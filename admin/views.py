# admin/views.py

import csv
import json
from uuid import uuid4

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from audit.models import AuditLog
from core.decorators import admin_only_required
from requests.models import CorrectionRequests
from timetracking.models import TimeEntries, TimeEntryEvent
from users.models import Users, Companies, UserCompany

# Constants
WEEKDAY = [
    (0, 'Domingo'),
    (1, 'Lunes'),
    (2, 'Martes'),
    (3, 'Miércoles'),
    (4, 'Jueves'),
    (5, 'Viernes'),
    (6, 'Sábado'),
]


@admin_only_required
@never_cache
def admin_dashboard(request):
    """Admin dashboard to manage companies and workers globally"""

    # AUDIT: Access to the admin dashboard
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason='Acceso al panel de administración',
        after={
            'tipo': 'Acceso Admin',
            'accion': 'Acceso al panel de control global',
            'rol': 'administrador',
        }
    )

    # Get all companies and workers for listing tables
    companies_list = Companies.objects.all().order_by('name')
    workers_list = Users.objects.exclude(status='suspended').order_by('username')

    # Pagination for companies
    paginator_companies = Paginator(companies_list, 10)
    page_companies = request.GET.get('page_companies', 1)
    companies_page_obj = paginator_companies.get_page(page_companies)

    # Pagination for workers
    paginator_workers = Paginator(workers_list, 10)
    page_workers = request.GET.get('page_workers', 1)
    workers_page_obj = paginator_workers.get_page(page_workers)

    # Serialize companies data (add created_at formatting)
    companies_data = []
    for company in companies_page_obj:
        companies_data.append({
            'id': str(company.id),
            'name': company.name,
            'tax_id': company.tax_id,
            'legal_name': company.legal_name,
            'created_at': company.created_at.strftime('%d/%m/%Y') if company.created_at else '--'
        })

    # Serialize workers data (add companies and formatted info)
    workers_data = []
    for worker in workers_page_obj:
        companies = list(Companies.objects.filter(
            usercompany__user=worker,
            usercompany__deleted_at__isnull=True
        ).values('id', 'name', 'tax_id').distinct())

        # Convert UUID to string for JSON serialization
        for company in companies:
            company['id'] = str(company['id'])

        workers_data.append({
            'id': str(worker.id),
            'username': worker.username,
            'surname': worker.surname,
            'email': worker.email,
            'dni': worker.dni or '--',
            'status': worker.status,
            'companies': companies,
            'companies_json': json.dumps(companies)
        })

    context = {
        'all_companies': companies_data,
        'all_workers': workers_data,
        'companies_page_obj': companies_page_obj,
        'workers_page_obj': workers_page_obj,
        'total_companies': paginator_companies.count,
        'total_workers': paginator_workers.count,
    }

    return render(request, 'admin/admin_dashboard.html', context)

@admin_only_required
@require_POST
def export_deleted_records(request):
    """
    Exports deleted records grouped by type to CSV.
    POST params: record_type (users, companies, user_companies, corrections, time_entries, time_events)
    """

    record_type = request.POST.get('record_type', '').strip()

    if not record_type:
        return HttpResponse("Tipo de registro no especificado.")

    # Map record types to models and fields
    models_config = {
        'users': {
            'model': Users,
            'queryset': Users.objects.only_deleted().order_by('-deleted_at'),
            'filename': 'reporte_usuarios_eliminados',
            'headers': ['Email', 'Usuario', 'Nombre', 'Estado', 'Eliminado'],
            'row_func': lambda u: [
                u.email,
                u.username,
                f"{u.username} {u.surname}",
                u.status if hasattr(u, 'status') else '--',
                u.deleted_at.strftime('%d/%m/%Y %H:%M') if u.deleted_at else '--'
            ]
        },
        'companies': {
            'model': Companies,
            'queryset': Companies.objects.only_deleted().order_by('-deleted_at'),
            'filename': 'reporte_empresas_eliminadas',
            'headers': ['Nombre', 'Email', 'Teléfono', 'País', 'Eliminada'],
            'row_func': lambda c: [
                c.name,
                c.email if hasattr(c, 'email') else '--',
                c.phone if hasattr(c, 'phone') else '--',
                c.country if hasattr(c, 'country') else '--',
                c.deleted_at.strftime('%d/%m/%Y %H:%M') if c.deleted_at else '--'
            ]
        },
        'user_companies': {
            'model': UserCompany,
            'queryset': UserCompany.objects.only_deleted().select_related('user', 'company').order_by('-deleted_at'),
            'filename': 'reporte_membresias_eliminadas',
            'headers': ['Usuario', 'Empresa', 'Rol', 'Ingreso', 'Eliminada'],
            'row_func': lambda uc: [
                f"{uc.user.username} {uc.user.surname}" if uc.user else '--',
                uc.company.name if uc.company else '--',
                uc.get_role_display() if hasattr(uc, 'get_role_display') else uc.role,
                uc.joined_at.strftime('%d/%m/%Y') if uc.joined_at else '--/--/----',
                uc.deleted_at.strftime('%d/%m/%Y %H:%M') if uc.deleted_at else '--'
            ]
        },
        'corrections': {
            'model': CorrectionRequests,
            'queryset': CorrectionRequests.objects.only_deleted().select_related('requester', 'time_entry').order_by('-deleted_at'),
            'filename': 'reporte_incidencias_eliminadas',
            'headers': ['Empleado', 'Fecha Solicitud', 'Motivo', 'Estado', 'Eliminada'],
            'row_func': lambda c: [
                f"{c.requester.username} {c.requester.surname}" if c.requester else '--',
                c.request_date.strftime('%d/%m/%Y %H:%M') if c.request_date else '--/--/---- --:--',
                c.reason or '--',
                c.status or '--',
                c.deleted_at.strftime('%d/%m/%Y %H:%M') if c.deleted_at else '--'
            ]
        },
        'time_entries': {
            'model': TimeEntries,
            'queryset': TimeEntries.objects.only_deleted().select_related('user').order_by('-deleted_at'),
            'filename': 'reporte_fichajes_eliminados',
            'headers': ['Empleado', 'Fecha', 'Entrada', 'Salida', 'Estado', 'Eliminado'],
            'row_func': lambda te: [
                f"{te.user.username} {te.user.surname}" if te.user else '--',
                te.date.strftime('%d/%m/%Y') if te.date else '--/--/----',
                te.clock_in.strftime('%H:%M:%S') if te.clock_in else '--:--:--',
                te.clock_out.strftime('%H:%M:%S') if te.clock_out else '--:--:--',
                te.status if hasattr(te, 'status') else '--',
                te.deleted_at.strftime('%d/%m/%Y %H:%M') if te.deleted_at else '--'
            ]
        },
        'time_events': {
            'model': TimeEntryEvent,
            'queryset': TimeEntryEvent.objects.only_deleted().select_related('time_entry').order_by('-deleted_at'),
            'filename': 'reporte_eventos_eliminados',
            'headers': ['Evento', 'Tipo', 'Fecha', 'Descripción', 'Eliminado'],
            'row_func': lambda te: [
                str(te.id) if te.id else '--',
                te.event_type if hasattr(te, 'event_type') else '--',
                te.created_at.strftime('%d/%m/%Y %H:%M') if hasattr(te, 'created_at') and te.created_at else '--/--/---- --:--',
                te.description if hasattr(te, 'description') else '--',
                te.deleted_at.strftime('%d/%m/%Y %H:%M') if te.deleted_at else '--'
            ]
        }
    }

    if record_type not in models_config:
        return HttpResponse("Tipo de registro no válido.")

    config = models_config[record_type]
    records = config['queryset']

    if not records.exists():
        return HttpResponse("No hay registros de este tipo para exportar.")

    # AUDIT: Export of deleted records (admin only)
    record_ids = [str(r.id) for r in records[:50]]
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {records.count()} registros eliminados ({record_type})',
        after={
            'tipo': f'Registros Eliminados ({record_type.upper()})',
            'tabla': f'Registros eliminados',
            'cantidad': records.count(),
            'ids': record_ids,
        }
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y')
    response['Content-Disposition'] = f"attachment; filename=\"{config['filename']}_{fecha_reporte}.csv\""

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(config['headers'])

    for record in records:
        writer.writerow(config['row_func'](record))

    return response


@admin_only_required
@require_POST
def export_all_companies(request):
    """
    Exports all active companies to CSV.
    """
    companies = Companies.objects.filter(deleted_at__isnull=True).order_by('name')

    if not companies.exists():
        return HttpResponse("No hay empresas para exportar.")

    # AUDIT: Export all companies
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {companies.count()} empresas',
        after={
            'tipo': 'Exportación Empresas',
            'tabla': 'Todas las empresas',
            'cantidad': companies.count(),
        }
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y_%H%M%S')
    response['Content-Disposition'] = f"attachment; filename=\"reporte_empresas_{fecha_reporte}.csv\""

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nombre', 'CIF / NIF', 'Razón Social', 'Creada'])

    for company in companies:
        writer.writerow([
            company.name,
            company.tax_id or '--',
            company.legal_name or '--',
            company.created_at.strftime('%d/%m/%Y') if company.created_at else '--'
        ])

    return response


@admin_only_required
@require_POST
def export_all_workers(request):
    """
    Exports all active workers to CSV.
    """
    workers = Users.objects.filter(deleted_at__isnull=True).exclude(status='suspended').order_by('username')

    if not workers.exists():
        return HttpResponse("No hay trabajadores para exportar.")

    # AUDIT: Export all workers
    AuditLog.objects.create(
        id=uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {workers.count()} trabajadores',
        after={
            'tipo': 'Exportación Trabajadores',
            'tabla': 'Todos los trabajadores',
            'cantidad': workers.count(),
        }
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y_%H%M%S')
    response['Content-Disposition'] = f"attachment; filename=\"reporte_trabajadores_{fecha_reporte}.csv\""

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Nombre', 'Apellidos', 'Email', 'DNI', 'Estado', 'Empresas', 'Creado'])

    for worker in workers:
        # Get companies for this worker
        companies = Companies.objects.filter(
            usercompany__user=worker,
            usercompany__deleted_at__isnull=True
        ).values_list('name', flat=True).distinct()

        companies_str = ' | '.join(companies) if companies else '--'

        writer.writerow([
            worker.username,
            worker.surname or '--',
            worker.email,
            worker.dni or '--',
            worker.get_status_display() if hasattr(worker, 'get_status_display') else worker.status,
            companies_str,
            worker.date_joined.strftime('%d/%m/%Y') if worker.date_joined else '--'
        ])

    return response


# ── DELEGATED WORKER SYSTEM ────────────────────────────────────────────────

@admin_only_required
@require_POST
def select_delegated_worker(request):
    """
    Admin selects a worker to delegate actions.
    Stores user_id, name, and company_id in the session.

    POST params:
        worker_id: UUID of the user to delegate to
        company_id: UUID of the company where actions are performed
    """
    worker_id = request.POST.get('worker_id', '').strip()
    company_id = request.POST.get('company_id', '').strip()

    if not worker_id:
        return JsonResponse({'error': 'worker_id es obligatorio'}, status=400)

    if not company_id:
        return JsonResponse({'error': 'company_id es obligatorio'}, status=400)

    # Validate that the user exists
    delegated_user = Users.objects.filter(id=worker_id).first()
    if not delegated_user:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

    # Validate that the company exists
    delegated_company = Companies.objects.filter(id=company_id).first()
    if not delegated_company:
        return JsonResponse({'error': 'Empresa no encontrada'}, status=404)

    # Validate that the user belongs to that company
    membership = UserCompany.objects.filter(
        user=delegated_user,
        company=delegated_company
    ).first()
    if not membership:
        return JsonResponse({'error': 'El usuario no pertenece a esa empresa'}, status=403)

    # Save in session
    request.session['delegated_user_id'] = str(worker_id)
    request.session['delegated_user_name'] = delegated_user.username.title()
    request.session['delegated_company_id'] = str(company_id)
    request.session['delegated_company_name'] = delegated_company.name
    request.session['delegated_user_role'] = membership.role

    return JsonResponse({'success': True})


@admin_only_required
@require_POST
def clear_delegated_worker(request):
    """
    Admin cancels user delegation.
    Clears the associated session variables.
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
    View to show all deleted (soft-deleted) records grouped by type.
    Accessible only to administrators.
    """
    # Get all deleted records by type
    deleted_users = Users.objects.only_deleted().order_by('-deleted_at')
    deleted_companies = Companies.objects.only_deleted().order_by('-deleted_at')
    deleted_user_companies = UserCompany.objects.only_deleted().order_by('-deleted_at')
    deleted_corrections = CorrectionRequests.objects.only_deleted().order_by('-deleted_at')
    deleted_time_entries = TimeEntries.objects.only_deleted().order_by('-deleted_at')
    deleted_time_events = TimeEntryEvent.objects.only_deleted().order_by('-deleted_at')

    # For each deleted user, fetch their associated companies (including deleted memberships)
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
        'deleted_corrections': deleted_corrections,
        'deleted_time_entries': deleted_time_entries,
        'deleted_time_events': deleted_time_events,
        'total_deleted': (
            deleted_users.count() +
            deleted_companies.count() +
            deleted_user_companies.count() +
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
    Restores a deleted (soft-deleted) record.
    Accessible only to administrators.

    POST params:
        record_type: Type of record (users, companies, user_companies, company_settings, corrections, time_entries, time_events)
        record_id: UUID of the record to restore
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

        # If restoring a UserCompany membership, verify the company is not deleted
        if record_type == 'user_companies':
            if record.company.deleted_at is not None:
                messages.error(
                    request,
                    f"No se puede restaurar esta membresía: la empresa '{record.company.name.title}' está eliminada. "
                    f"Restaura primero la empresa desde la lista de registros eliminados."
                )
                return redirect('deleted_records')

        # Restore the record using the manager's restore method
        # This will automatically revert user status to 'active' if it's a user
        model.objects.restore(record)

        # If restoring a UserCompany membership, also restore the associated user if needed
        if record_type == 'user_companies':
            user = record.user

            # If user was deleted, restore it
            if user.deleted_at is not None:
                Users.objects.restore(user)

            # If user is suspended, check if they have other active memberships
            # If they do, mark them as active
            if user.status == 'suspended':
                active_memberships = UserCompany.objects.filter(
                    user=user,
                    deleted_at__isnull=True
                ).count()

                # If user has at least one active membership now, reactivate them
                if active_memberships > 0:
                    user.status = 'active'
                    user.save(update_fields=['status'])

        messages.success(request, "Registro restaurado correctamente.")
    except Exception as e:
        messages.error(request, f"Error al restaurar el registro: {str(e)}")

    return redirect('deleted_records')


@admin_only_required
@require_POST
def permanently_delete_record(request):
    """
    Permanently deletes a deleted record (hard-delete).
    Accessible only to administrators.

    POST params:
        record_type: Type of record
        record_id: UUID of the record to permanently delete
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

        # Store record data before hard-delete for audit
        from audit.utils import safe_dict
        record_data = safe_dict(record)

        # Map record types to appropriate table names for audit
        table_name_map = {
            'users': 'user_action',
            'companies': 'company_settings',
            'user_companies': 'user_company',
            'corrections': 'requests_correctionrequests',
            'time_entries': 'timetracking_timeentries',
            'time_events': 'audit_timeentryevent',
        }
        audit_table_name = table_name_map.get(record_type, record_type)

        # Permanently delete the record
        model.objects.hard_delete(record)

        # AUDIT: Permanent record deletion
        AuditLog.objects.create(
            id=uuid4(),
            table_name=audit_table_name,
            record_id=record_id,
            user=request.user,
            action_type=AuditLog.AuditAction.DELETE,
            before=record_data,
            reason=f'Eliminación permanente de {record_type}: {record_id}',
            source='web'
        )

        messages.success(request, f"Registro de tipo '{record_type}' eliminado permanentemente.")

    except Exception as e:
        messages.error(request, f"Error al eliminar permanentemente el registro: {str(e)}")

    return redirect('deleted_records')


@admin_only_required
@require_POST
def delete_company(request):
    """
    Deletes a company (soft-delete) and all its associated memberships.
    Accessible only to administrators.

    POST params:
        company_id: UUID of the company to delete
    """
    company_id = request.POST.get('company_id', '').strip()

    if not company_id:
        messages.error(request, "ID de empresa es obligatorio.")
        return redirect('admin_dashboard')

    try:
        # Get the company
        company = Companies.objects.filter(id=company_id).first()

        if not company:
            messages.error(request, "Empresa no encontrada.")
            return redirect('admin_dashboard')

        if company.deleted_at is not None:
            messages.warning(request, "Esta empresa ya ha sido eliminada.")
            return redirect('admin_dashboard')

        # Store company info before deletion for audit
        company_info_before = {
            'name': company.name,
            'tax_id': company.tax_id,
            'legal_name': company.legal_name,
            'email': company.email if hasattr(company, 'email') else None,
            'phone': company.phone if hasattr(company, 'phone') else None,
        }

        # Mark the company as deleted
        company.deleted_at = timezone.now()
        company.save(update_fields=['deleted_at'])

        # AUDIT: Company deletion
        AuditLog.objects.create(
            id=uuid4(),
            table_name='company_settings',
            record_id=company.id,
            user=request.user,
            action_type=AuditLog.AuditAction.DELETE,
            before=company_info_before,
            reason=f'Eliminación de empresa {company.name}',
            source='web'
        )

        # Mark all associated memberships as deleted
        memberships = UserCompany.objects.filter(company=company, deleted_at__isnull=True)
        member_count = memberships.count()
        suspended_users_count = 0

        for membership in memberships:
            # Count how many ACTIVE memberships this user has
            active_memberships = UserCompany.objects.filter(
                user=membership.user,
                deleted_at__isnull=True
            ).count()

            # If this is the only active membership, mark the user as suspended
            if active_memberships == 1:
                user = membership.user
                user.status = 'suspended'
                user.save(update_fields=['status'])
                suspended_users_count += 1

            # Mark the membership as deleted
            membership.deleted_at = timezone.now()
            membership.save(update_fields=['deleted_at'])

        # Build success message
        suspended_msg = f" {suspended_users_count} usuario(s) fue(ron) suspendido(s)." if suspended_users_count > 0 else ""
        messages.success(
            request,
            f"Empresa eliminada correctamente. Se desvincularon {member_count} trabajador(es).{suspended_msg}"
        )

    except Exception as e:
        messages.error(request, f"Error al eliminar la empresa: {str(e)}")

    return redirect('admin_dashboard')
