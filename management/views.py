# management/views.py

import csv
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from users.models import Companies, UserCompany, Users
from timetracking.models import TimeEntries
from django.db.models import OuterRef, Subquery
import uuid
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from audit.models import AuditLog
from django.core.paginator import Paginator
from audit.utils import safe_dict
from uuid import uuid4
from core.decorators import manager_or_admin_required, auditor_cannot_access, manager_or_admin_with_delegation_check
from core.services import combine_local_date_time, get_effective_context

# Additional imports for entity_info
from corrections.models import LeaveRequest, CorrectionRequests
from admin.models import CompanySettings
from django.template.defaulttags import register
from django.utils.dateparse import parse_date
from datetime import timedelta, date
from django.db import IntegrityError
import json
from django.http import JsonResponse
from audit.models import AuditLog
from core.services import serialize_leave, log_leave
from django.contrib import messages

# Constants
WEEKDAY = [
    (0, 'Lunes'),
    (1, 'Martes'),
    (2, 'Miércoles'),
    (3, 'Jueves'),
    (4, 'Viernes'),
    (5, 'Sábado'),
    (6, 'Domingo'),
]


@manager_or_admin_with_delegation_check
@never_cache
def manager_logs(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    # 1. Determine which company to work with
    if delegation_context['is_delegating']:
        # Admin delegating: use delegated company
        company = Companies.objects.filter(
            id=delegation_context['delegated_company_id']
        ).first()
        if not company:
            return HttpResponseForbidden("Empresa delegada no encontrada.")
    else:
        # Use request.company set by middleware (respects navbar selection)
        company = request.company
        if not company:
            return HttpResponseForbidden("No estás asignado a ninguna empresa.")

    # 2. Get the employees of this company
    empleados_ids = UserCompany.objects.filter(company=company).values_list('user_id', flat=True)
    empleados = Users.objects.filter(id__in=empleados_ids)

    # 3. Prepare a subquery to get the exact role of each user in THIS company
    rol_subquery = UserCompany.objects.filter(
        user=OuterRef('user'),
        company=company
    ).values('role')[:1]

    incidencias = CorrectionRequests.objects.filter(
        time_entry__company=company,
        status='pending'
    ).select_related('time_entry', 'requester').order_by('-request_date')

    # Get rejected incidents for the separate table
    incidencias_rechazadas = CorrectionRequests.objects.filter(
        time_entry__company=company,
        status='rejected'
    ).select_related('time_entry', 'requester', 'approver').order_by('-request_date')

    fichajes_con_incidencia = incidencias.values_list('time_entry_id', flat=True)
    fichajes_con_incidencia_str = [str(uid) for uid in fichajes_con_incidencia]

    # Get TimeEntries with rejected incidents to exclude them from the main table
    fichajes_rechazados = incidencias_rechazadas.values_list('time_entry_id', flat=True)

    # 4. Get the clock-ins
    registros = TimeEntries.objects.filter(
        company=company
    ).exclude(
        status__in=[TimeEntries.EntryStatus.CORRECTED, TimeEntries.EntryStatus.VOIDED]
    ).exclude(
        id__in=fichajes_rechazados
    ).annotate(
        rol_empleado=Subquery(rol_subquery)
    ).select_related('user').order_by('-date', '-clock_in')

    # 5. Apply Filters
    empleado_id = request.GET.get('empleado')
    fecha = request.GET.get('fecha')
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    solo_incidencias = request.GET.get('solo_incidencias')

    if empleado_id:
        registros = registros.filter(user_id=empleado_id)
    if fecha:
        registros = registros.filter(date=fecha)
    if desde:
        registros = registros.filter(clock_in__time__gte=desde)
    if hasta:
        registros = registros.filter(clock_out__time__lte=hasta)
    if solo_incidencias == 'on':
        registros = registros.filter(id__in=fichajes_con_incidencia)

    # 6. Format seconds for all records and convert to list for iteration
    registros_list = list(registros)
    for r in registros_list:
        horas = r.total_seconds // 3600
        minutos = (r.total_seconds % 3600) // 60
        r.horas_formateadas = f"{horas}h {minutos}m" if r.total_seconds > 0 else "--"

    context = {
        'registros_list': registros_list, # Send all records for JS pagination
        'empleados': empleados,
        'incidencias': incidencias,
        'incidencias_rechazadas': incidencias_rechazadas,
        'fichajes_con_incidencia': fichajes_con_incidencia_str,
        # Pass current filters so the HTML can preserve them
        'current_filters': {
            'empleado': empleado_id or '',
            'fecha': fecha or '',
            'desde': desde or '',
            'hasta': hasta or '',
            'solo_incidencias': solo_incidencias or '',
        }
    }
    # Add delegation context
    context.update(delegation_context)

    return render(request, 'team/manager_logs.html', context)


# View for exporting filtered logs to CSV, with format compatible with Excel and formatted seconds
@manager_or_admin_with_delegation_check
def exportar_logs(request):

    if request.method == 'POST':
        registros_ids = request.POST.getlist('registro_id')

        if not registros_ids:
            return HttpResponse("No seleccionaste ningún registro para exportar.")

        registros = TimeEntries.objects.filter(id__in=registros_ids).select_related('user').order_by('-date', '-clock_in')

        # 🔐 AUDITORÍA: Exportación de fichajes (manager/admin)
        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='user_action',
            record_id=request.user.id,
            user=request.user,
            action_type=AuditLog.AuditAction.CREATE,
            reason=f'Exportación de {len(registros_ids)} fichajes (manager/admin)',
            after={
                'tipo': 'Fichajes (Manager/Admin)',
                'tabla': 'timetracking_registro',
                'cantidad': len(registros_ids),
                'ids': [str(id) for id in registros_ids],
            },
            source='web' # Añadido
        )

        response = HttpResponse(content_type='text/csv')
        fecha_reporte = timezone.now().strftime('%d_%m_%Y')
        response['Content-Disposition'] = f'attachment; filename="reporte_fichajes_{fecha_reporte}.csv"'

        # IMPORTANT: This prevents accents from displaying incorrectly in Excel
        response.write(u'\ufeff'.encode('utf8'))

        writer = csv.writer(response, delimiter=';') # Semicolon is standard for Spanish Excel

        # Clear headers
        writer.writerow(['Empleado', 'Fecha', 'Entrada', 'Salida', 'Tiempo Total (HH:MM:SS)', 'Notas'])

        for r in registros:
            # Seconds to HH:MM:SS conversion logic
            total_s = r.total_seconds

            horas = total_s // 3600
            minutos = (total_s % 3600) // 60
            segundos = total_s % 60

            # Format with leading zeros (e.g., 08:05:09)
            tiempo_formateado = f"{horas:02d}:{minutos:02d}:{segundos:02d}" if total_s > 0 else "00:00:00"

            writer.writerow([
                f"{r.user.username} {r.user.surname}",
                r.date.strftime('%d/%m/%Y'),
                r.clock_in.strftime('%H:%M:%S') if r.clock_in else '--:--:--',
                r.clock_out.strftime('%H:%M:%S') if r.clock_out else '--:--:--',
                tiempo_formateado,
                r.notes if r.notes else ''
            ])

        return response


@manager_or_admin_with_delegation_check
@require_POST
def exportar_staff(request):
    """
    Exporta la lista de empleados de una empresa a CSV.
    POST params: employee_id (lista de IDs seleccionadas)
    """
    employee_ids = request.POST.getlist('employee_id')

    if not employee_ids:
        return HttpResponse("No seleccionaste ningún registro para exportar.")

    memberships = UserCompany.objects.filter(
        id__in=employee_ids
    ).select_related('user', 'company').order_by('user__username')

    # 🔐 AUDITORÍA: Exportación de lista de empleados
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='user_action',
        record_id=request.user.id,
        user=request.user,
        action_type=AuditLog.AuditAction.CREATE,
        reason=f'Exportación de {len(employee_ids)} empleados',
        after={
            'tipo': 'Lista de Empleados',
            'tabla': 'user_company',
            'cantidad': len(employee_ids),
            'ids': [str(id) for id in employee_ids],
        },
        source='web' # Añadido
    )

    response = HttpResponse(content_type='text/csv')
    fecha_reporte = timezone.now().strftime('%d_%m_%Y')
    response['Content-Disposition'] = f'attachment; filename="reporte_empleados_{fecha_reporte}.csv"'

    # Byte order mark for Excel with accents
    response.write(u'\ufeff'.encode('utf8'))

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Usuario',
        'Email',
        'Nombre Completo',
        'Rol',
        'Estado',
        'Empresa',
        'Fecha de Ingreso'
    ])

    for membership in memberships:
        user = membership.user
        writer.writerow([
            user.username,
            user.email,
            f"{user.username} {user.surname}",
            membership.get_role_display() if hasattr(membership, 'get_role_display') else membership.role,
            user.status if hasattr(user, 'status') else '--',
            membership.company.name,
            membership.joined_at.strftime('%d/%m/%Y') if membership.joined_at else '--/--/----'
        ])

    return response


# View for the manager to manually edit a record (in case of incident or error), creating a new corrected record and voiding the original
@manager_or_admin_with_delegation_check
def editar_registro(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    if request.method == 'POST':
        registro_id = request.POST.get('registro_id')
        registro_original = get_object_or_404(TimeEntries, id=registro_id)

        # --- INICIO AUDITORÍA: FOTO DEL ANTES ---
        estado_anterior = safe_dict(registro_original)
        # ----------------------------------------

        hora_entrada = request.POST.get('clock_in')  # Now receives values like "YYYY-MM-DDTHH:MM"
        hora_salida = request.POST.get('clock_out')

        # 1. Void the current one
        registro_original.status = TimeEntries.EntryStatus.CORRECTED
        registro_original.save()

        # 2. Parse datetimes coming from the new datetime-local input
        try:
            naive_in = datetime.strptime(hora_entrada, '%Y-%m-%dT%H:%M')
            new_in = timezone.make_aware(naive_in, timezone.get_current_timezone())
        except ValueError:
            return HttpResponse("Hora de entrada no válida.", status=400)

        new_out = None
        segundos = 0
        if hora_salida:
            try:
                naive_out = datetime.strptime(hora_salida, '%Y-%m-%dT%H:%M')
                new_out = timezone.make_aware(naive_out, timezone.get_current_timezone())
            except ValueError:
                return HttpResponse("Hora de salida no válida.", status=400)

            # Calculate seconds for the new record
            delta = new_out - new_in
            segundos = int(delta.total_seconds())

        # Determine who edited the record
        if delegation_context['is_delegating']:
            editor_user = Users.objects.get(id=delegation_context['delegated_user_id'])
            editor_name = delegation_context['delegated_user_name']
        else:
            editor_user = registro_original.user
            editor_name = request.user.username

        nuevo_registro = TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=editor_user,
            company=delegation_context['delegated_company_id'] if delegation_context['is_delegating'] else registro_original.company,
            date=registro_original.date,  # Keep the original logical date of the shift
            clock_in=new_in,
            clock_out=new_out,
            status=TimeEntries.EntryStatus.CONFIRMED,
            notes=f"Editado manualmente por {editor_name}",
            total_seconds=max(0, segundos)
        )

        # --- INICIO AUDITORÍA ---
        AuditLog.objects.create(
            id=uuid.uuid4(),
            table_name='timetracking_timeentries',
            record_id=str(registro_original.id),
            user=request.user,
            action_type='update', # Se considera actualización porque reemplaza el original
            before=estado_anterior,
            after=safe_dict(nuevo_registro),
            reason="Edición manual de fichaje por el manager/admin",
            source='web' # Añadido
        )
        # -------------------------------------------

        return redirect('manager_logs')
    return HttpResponse("Método no permitido.")


@login_required
@never_cache
@manager_or_admin_with_delegation_check
def staff(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    # 1. Determine which company to view
    company_id = delegation_context['delegated_company_id'] if delegation_context['is_delegating'] else None

    if company_id:
        # Using delegated company
        company = Companies.objects.filter(id=company_id).first()
        if not company:
            return HttpResponseForbidden("Empresa delegada no encontrada.")
    else:
        # Original logic: from URL or session
        company_id = request.GET.get('company_id') or request.session.get('company_id')

        if company_id:
            # Admin is inspecting a specific company OR manager checking their own
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                return HttpResponseForbidden("Empresa no encontrada.")

            # Validate permissions:
            # - Admins can inspect any company
            # - Managers can only access their own company
            if not request.user.is_admin:
                # Manager: verify it's their own company
                user_membership = UserCompany.objects.filter(
                    user=request.user,
                    company=company,
                    deleted_at__isnull=True
                ).first()
                if not user_membership:
                    return HttpResponseForbidden("No tienes acceso a esta empresa.")

            request.session['company_id'] = company_id
            delegation_context['is_inspecting'] = True
        else:
            # Get the user's own company membership
            user_membership = UserCompany.objects.all_with_deleted().filter(
                user=request.user,
                deleted_at__isnull=True
            ).first()
            if not user_membership:
                return HttpResponseForbidden("No estás asignado a ninguna empresa.")
            company = user_membership.company

    # 2. Check if they are a manager or admin to pass it to the template
    user_membership = UserCompany.objects.all_with_deleted().filter(
        user=request.user,
        company=company,
        deleted_at__isnull=True
    ).first()
    is_manager = (user_membership and user_membership.role == UserCompany.RoleChoices.MANAGER) or request.user.is_admin

    # 3. Get ALL memberships (employees) for that company (non-deleted only)
    memberships_list = UserCompany.objects.filter(
        company=company
    ).select_related('user').order_by('-joined_at')

    # 4. For each membership, obtener leaves activas (aprobadas con end_date >= hoy)
    today = date.today()

    # Crear diccionario de leaves activas por user_id
    active_leaves_map = {}
    for membership in memberships_list:
        # Asegúrate de tener LeaveRequest importado si es necesario
        active_leave = LeaveRequest.objects.filter(
            user=membership.user,
            company=company,
            status=LeaveRequest.LeaveStatus.APPROVED,
            end_date__gte=today
        ).first()
        if active_leave:
            active_leaves_map[membership.user.id] = active_leave

    # Agregar la information de leaves al contexto de cada membership
    for membership in memberships_list:
        membership.active_leave = active_leaves_map.get(membership.user.id)

    # 5. Paginación
    paginator = Paginator(memberships_list, 20)
    page_number = request.GET.get('page')
    memberships = paginator.get_page(page_number)

    context = {
        'memberships': memberships,
        'is_manager': is_manager,
        'company': company,
        'is_inspecting': delegation_context.get('is_inspecting', False),
    }
    context.update(delegation_context)

    return render(request, 'team/staff.html', context)

@manager_or_admin_with_delegation_check
@require_POST
def edit_employee(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    # 1. Determine which company to use
    if delegation_context['is_delegating']:
        company_id = delegation_context['delegated_company_id']
        company = Companies.objects.get(id=company_id)
    else:
        # Get current manager's company
        membership_manager = UserCompany.objects.filter(
            user=request.user,
            role=UserCompany.RoleChoices.MANAGER
        ).first()
        company = membership_manager.company if membership_manager else None

    if not company:
        return HttpResponseForbidden("No se pudo determinar la empresa.")

    # 2. Collect form data
    user_id = request.POST.get('user_id')
    username = request.POST.get('username')
    surname = request.POST.get('surname')
    role = request.POST.get('role')
    status = request.POST.get('status')

    # 3. Validate that the employee belongs to the company
    membership = get_object_or_404(UserCompany, user_id=user_id, company=company)
    user = membership.user

    # 4. Update user data
    user.username = username
    user.surname = surname
    user.status = status
    user.save()

    # 5. Update role in the company
    membership.role = role
    membership.save()

    return redirect('staff')


@manager_or_admin_with_delegation_check
@require_POST
def delete_employee(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    # 1. Collect ID of user to delete
    user_id = request.POST.get('user_id')

    if not user_id:
        return HttpResponseForbidden("ID de usuario no proporcionado.")

    # Get the user to mark as deleted
    try:
        user = Users.objects.all_with_deleted().get(id=user_id)
    except Users.DoesNotExist:
        return HttpResponseForbidden("Usuario no encontrado.")

    # 2. Determine which companies to delete from
    company_ids_str = request.POST.get('company_ids', '').strip()
    company_id_single = request.POST.get('company_id', '').strip()

    company_ids = []

    if company_ids_str:
        # Multiple companies from multi-select
        company_ids = [cid.strip() for cid in company_ids_str.split(',') if cid.strip()]
    elif company_id_single:
        # Single company from manager view
        company_ids = [company_id_single]
    elif delegation_context['is_delegating']:
        # Delegated context
        company_ids = [delegation_context['delegated_company_id']]
    else:
        # Get current manager's own company
        membership_manager = UserCompany.objects.all_with_deleted().filter(
            user=request.user,
            role=UserCompany.RoleChoices.MANAGER,
            deleted_at__isnull=True
        ).first()
        if membership_manager:
            company_ids = [str(membership_manager.company.id)]

    if not company_ids:
        return HttpResponseForbidden("No se especificaron empresas.")

    # 3. Validate permissions and get companies
    companies_to_delete = []
    for cid in company_ids:
        try:
            company = Companies.objects.get(id=cid)
            # Validate permission (admin or manager of this company OR delegating)
            if not delegation_context['is_delegating'] and not request.user.is_admin:
                membership_manager = UserCompany.objects.filter(
                    user=request.user,
                    company=company,
                    role=UserCompany.RoleChoices.MANAGER,
                    deleted_at__isnull=True
                ).first()
                if not membership_manager:
                    return HttpResponseForbidden(f"No tienes permiso para eliminar usuarios de {company.name}.")
            companies_to_delete.append(company)
        except Companies.DoesNotExist:
            return HttpResponseForbidden(f"Empresa {cid} no encontrada.")

    # 4. Prevent a manager from accidentally deleting themselves
    for company in companies_to_delete:
        membership = UserCompany.objects.all_with_deleted().filter(
            user=request.user,
            company=company,
            deleted_at__isnull=True
        ).first()
        if membership and str(user_id) == str(request.user.id):
            return redirect('deleted_records')

    # 5. Delete from all specified companies
    now = timezone.now()

    # Mark all memberships for these companies as deleted
    memberships = UserCompany.objects.all_with_deleted().filter(
        user=user,
        company__in=companies_to_delete
    )

    for membership in memberships:
        if membership.deleted_at is None:  # Only soft-delete if not already deleted
            membership.deleted_at = now
            membership.save()

    # 6. Check if user belongs to any active companies after deletion
    active_memberships = UserCompany.objects.filter(
        user=user,
        deleted_at__isnull=True
    )

    # If user has no more active memberships, mark user as suspended and deleted
    if not active_memberships.exists():
        user.status = 'suspended'
        user.deleted_at = now
        user.save(update_fields=['status', 'deleted_at'])

    return redirect('deleted_records')


@manager_or_admin_with_delegation_check
@require_POST
def anular_registro(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    registro_id = request.POST.get('registro_id')

    if not registro_id:
        return HttpResponse("ID de registro no proporcionado.", status=400)

    registro = get_object_or_404(TimeEntries, id=registro_id)

    # --- INICIO AUDITORÍA: FOTO DEL ANTES ---
    estado_anterior = safe_dict(registro)
    # ----------------------------------------

    # Determine who is voiding the record
    if delegation_context['is_delegating']:
        voiding_username = delegation_context['delegated_user_name']
    else:
        voiding_username = request.user.username

    registro.status = 'voided'
    registro.total_seconds = 0
    registro.notes = f"{registro.notes}\n[Anulado por {voiding_username}]"

    # Soft-delete: Mark with deletion timestamp
    registro.deleted_at = timezone.now()

    registro.save()

    # --- INICIO AUDITORÍA ---
    AuditLog.objects.create(
        id=uuid.uuid4(),
        table_name='timetracking_timeentries',
        record_id=str(registro.id),
        user=request.user,
        action_type='voided', # Registramos el tipo de acción
        before=estado_anterior,
        after=safe_dict(registro),
        reason="Anulación directa de registro",
        source='web' # Añadido
    )
    # -------------------------------------------

    return redirect('manager_logs')


@login_required
@manager_or_admin_with_delegation_check
def entity_info(request):
    from core.services import get_effective_context

    delegation_context = get_effective_context(request)

    # 1. Determine which company to view
    company_id = delegation_context['delegated_company_id'] if delegation_context['is_delegating'] else None

    if company_id:
        # Using delegated company
        company = Companies.objects.filter(id=company_id).first()
        if not company:
            messages.error(request, 'Empresa delegada no encontrada.')
            return redirect('home_timetracking')
    else:
        # Original logic
        company_id = request.GET.get('company_id') or request.session.get('company_id')

        if company_id:
            # Admin is inspecting a specific company OR manager checking their own
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                messages.error(request, 'Empresa no encontrada.')
                return redirect('home_timetracking')

            # Validate permissions:
            # - Admins can inspect any company
            # - Managers can only access their own company
            if not request.user.is_admin:
                # Manager: verify it's their own company
                user_membership = UserCompany.objects.filter(
                    user=request.user,
                    company=company,
                    deleted_at__isnull=True
                ).first()
                if not user_membership:
                    return HttpResponseForbidden("No tienes acceso a esta empresa.")

            request.session['company_id'] = company_id
        else:
            # Get the user's company membership
            user_membership = UserCompany.objects.filter(user=request.user).first()
            if not user_membership:
                messages.error(request, 'No tienes empresa asignada.')
                return redirect('home_timetracking')
            company = user_membership.company

    membership = UserCompany.objects.filter(
        user=request.user,
        company=company
    ).first()

    # Global admin can always edit, regardless of their role in the company
    if request.user.is_admin:
        user_role = 'admin'
    elif membership and membership.role == UserCompany.RoleChoices.MANAGER:
        user_role = 'manager'
    else:
        user_role = 'employee'

    can_edit = user_role in ('admin', 'manager')

    settings_obj = CompanySettings.objects.filter(company=company).first()

    if request.method == 'POST' and can_edit:

        # Update company info
        company.name = request.POST.get('name', company.name).strip()
        company.legal_name = request.POST.get('legal_name', company.legal_name).strip()
        posted_tax_id = request.POST.get('tax_id', '').strip() or None

        if posted_tax_id and Companies.objects.filter(tax_id=posted_tax_id).exclude(id=company.id).exists():
            messages.error(request, 'El CIF/NIF indicado ya existe en otra empresa.')
            context = {
                'company': company,
                'user_role': user_role,
                'settings': settings_obj,
                'weekdays': WEEKDAY, # Asegúrate de que WEEKDAY esté definido globalmente o importado
            }
            context.update(delegation_context)
            return render(request, 'team/entity_info.html', context)

        company.tax_id = posted_tax_id
        company.updated_at = timezone.now()

        try:
            company.save(update_fields=['name', 'legal_name', 'tax_id', 'updated_at'])
        except IntegrityError:
            messages.error(request, 'No se pudo guardar la empresa porque el CIF/NIF ya está en uso.')
            context = {
                'company': company,
                'user_role': user_role,
                'settings': settings_obj,
                'weekdays': WEEKDAY, # Asegúrate de que WEEKDAY esté definido globalmente o importado
            }
            context.update(delegation_context)
            return render(request, 'team/entity_info.html', context)

        # Workday settings

        if settings_obj:

            # Capturar estado ANTES
            before_jornada = {
                'work_start':    str(settings_obj.work_start),
                'work_end':      str(settings_obj.work_end),
                'max_tolerance': str(settings_obj.max_tolerance),
                'weekend_days':  list(settings_obj.weekend_days),
                'holidays':      [str(h) for h in settings_obj.holidays],
            }
            before_cierre = {
                'auto_close_hours': settings_obj.auto_close_hours,
            }

            # Aplicar cambios
            work_start = request.POST.get('work_start')
            if work_start:
                settings_obj.work_start = work_start

            work_end = request.POST.get('work_end')
            if work_end:
                settings_obj.work_end = work_end

            tolerance_min = request.POST.get('max_tolerance')
            if tolerance_min is not None and tolerance_min != '':
                settings_obj.max_tolerance = timedelta(minutes=int(tolerance_min))

            auto_close = request.POST.get('auto_close_hours')
            if auto_close is not None and auto_close != '':
                settings_obj.auto_close_hours = int(auto_close)

            settings_obj.weekend_days = [
                int(day) for day in request.POST.getlist('weekend_days')
            ]

            holidays = []
            # Asegúrate de importar parse_date de django.utils.dateparse si no lo tienes
            for raw in request.POST.get('holidays', '').split(','):
                raw = raw.strip()
                if raw:
                    # from django.utils.dateparse import parse_date (importarlo si falta)
                    from django.utils.dateparse import parse_date
                    parsed = parse_date(raw)
                    if parsed:
                        holidays.append(parsed)
            settings_obj.holidays  = holidays
            settings_obj.updated_at = timezone.now()
            settings_obj.save()

            # Capturar estado DESPUÉS
            after_jornada = {
                'work_start':    str(settings_obj.work_start),
                'work_end':      str(settings_obj.work_end),
                'max_tolerance': str(settings_obj.max_tolerance),
                'weekend_days':  list(settings_obj.weekend_days),
                'holidays':      [str(h) for h in settings_obj.holidays],
            }
            after_cierre = {
                'auto_close_hours': settings_obj.auto_close_hours,
            }

            # 🔐 Auditoría: Jornada laboral
            if before_jornada != after_jornada:
                # Usa uuid.uuid4() porque importamos uuid
                AuditLog.objects.create(
                    id=uuid.uuid4(),
                    table_name='company_settings',
                    record_id=settings_obj.id,
                    user=request.user,
                    action_type=AuditLog.AuditAction.UPDATE,
                    before=before_jornada,
                    after=after_jornada,
                    reason=f'Modificación de jornada laboral en empresa {company.name}',
                    source='web' # Añadido
                )

            # 🔐 Auditoría: Cierre automático
            if before_cierre != after_cierre:
                AuditLog.objects.create(
                    id=uuid.uuid4(),
                    table_name='company_settings',
                    record_id=settings_obj.id,
                    user=request.user,
                    action_type=AuditLog.AuditAction.UPDATE,
                    before=before_cierre,
                    after=after_cierre,
                    reason=f'Modificación de cierre automático en empresa {company.name}',
                    source='web' # Añadido
                )

        return redirect('manager_entity_info')

    context = {
        'company':   company,
        'user_role': user_role,
        'settings':  settings_obj,
        'weekdays':  WEEKDAY, # Asegúrate de que WEEKDAY esté definido globalmente
    }
    context.update(delegation_context)

    return render(request, 'team/entity_info.html', context)