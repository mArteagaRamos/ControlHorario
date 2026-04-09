# ---------- Backend Views: audit/views.py ----------

import csv
from functools import wraps
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from users.models import Companies, CorrectionRequests, UserCompany, Users
from timetracking.models import TimeEntries
from django.db.models import OuterRef, Subquery
import uuid
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache

def combine_local_date_time(date_value, time_value):
    naive_dt = datetime.strptime(f"{date_value} {time_value}", '%Y-%m-%d %H:%M')
    return timezone.make_aware(naive_dt, timezone.get_current_timezone())


# Decorator to verify that the user is a manager or admin before accessing certain views
def manager_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If not even logged in, get out
        if not request.user.is_authenticated:
            return render(request, 'error/sin_loguear.html', status=401)

        is_admin = request.user.is_admin
        is_manager = UserCompany.objects.filter(
            user=request.user,
            role=UserCompany.RoleChoices.MANAGER
        ).exists()

        if is_admin or is_manager:
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'error/sin_permisos.html', status=403)

    return _wrapped_view


# ── HELPER: Contexto de delegación de usuario ────────────────────────────────

def get_effective_context(request):
    """
    Retorna un diccionario con el contexto unificado de delegación de usuario.

    Usado por las vistas para determinar si hay un usuario delegado activo
    y pasar información al template para mostrar el banner.

    Retorna dict:
    {
        'delegated_user_id': str(UUID) or None,
        'delegated_user_name': str or None,
        'delegated_company_id': str(UUID) or None,
        'delegated_user_role': 'manager' or 'employee' or None,
        'is_delegating': bool,
    }
    """
    context = {
        'delegated_user_id': None,
        'delegated_user_name': None,
        'delegated_company_id': None,
        'delegated_user_role': None,
        'is_delegating': False,
    }

    # Solo si es admin y hay delegado activo en sesión
    if not request.user.is_admin:
        return context

    delegated_user_id = request.session.get('delegated_user_id')
    if not delegated_user_id:
        return context

    context.update({
        'delegated_user_id': delegated_user_id,
        'delegated_user_name': request.session.get('delegated_user_name'),
        'delegated_company_id': request.session.get('delegated_company_id'),
        'delegated_user_role': request.session.get('delegated_user_role'),
        'is_delegating': True,
    })

    return context


@manager_or_admin_required
@never_cache
def manager_logs(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    # 1. Determine which company to work with
    company_id = delegation_context['delegated_company_id'] if delegation_context['is_delegating'] else None

    if company_id:
        # Using delegated company
        company = Companies.objects.filter(id=company_id).first()
        if not company:
            return HttpResponseForbidden("Empresa delegada no encontrada.")
    else:
        # Get the manager's company
        membership = UserCompany.objects.filter(
            user=request.user,
            role=UserCompany.RoleChoices.MANAGER
        ).first()

        if not membership:
            return HttpResponse("No tienes permisos de manager o no estás asignado a una empresa.")

        company = membership.company

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

    fichajes_con_incidencia = incidencias.values_list('time_entry_id', flat=True)
    fichajes_con_incidencia_str = [str(uid) for uid in fichajes_con_incidencia]

    # 4. Get the clock-ins
    registros = TimeEntries.objects.filter(
        company=company
    ).exclude(
        status__in=[TimeEntries.EntryStatus.CORRECTED, TimeEntries.EntryStatus.VOIDED]
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

    # 6. PAGINATION: Only 20 records per page
    paginator = Paginator(registros, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 7. Format seconds ONLY for the 20 records that will be displayed
    for r in page_obj:
        horas = r.total_seconds // 3600
        minutos = (r.total_seconds % 3600) // 60
        r.horas_formateadas = f"{horas}h {minutos}m" if r.total_seconds > 0 else "--"

    context = {
        'page_obj': page_obj, # Send the current page instead of all records
        'empleados': empleados,
        'incidencias': incidencias,
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

    return render(request, 'audit/manager_logs.html', context)  

# View for the manager to accept or deny an incident, with their resolution note
@manager_or_admin_required
def resolver_incidencia(request):
    if request.method == 'POST':
        # Get effective context (delegation info if any)
        delegation_context = get_effective_context(request)

        incidencia_id = request.POST.get('incidencia_id')
        accion = request.POST.get('accion')
        # Capture the note coming from the modal form
        nota_resolucion = request.POST.get('nota_resolucion', '')

        incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)
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

        return redirect('manager_logs')

    return HttpResponse("Método no permitido.")

# View for exporting filtered logs to CSV, with format compatible with Excel and formatted seconds
@manager_or_admin_required
def exportar_logs(request):

    if request.method == 'POST':
        registros_ids = request.POST.getlist('registro_id')

        if not registros_ids:
            return HttpResponse("No seleccionaste ningún registro para exportar.")

        registros = TimeEntries.objects.filter(id__in=registros_ids).select_related('user').order_by('-date', '-clock_in')

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
    
# View for the manager to manually edit a record (in case of incident or error), creating a new corrected record and voiding the original
@manager_or_admin_required
def editar_registro(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    if request.method == 'POST':
        registro_id = request.POST.get('registro_id')
        registro_original = get_object_or_404(TimeEntries, id=registro_id)

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
        else:
            editor_user = registro_original.user

        TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=editor_user,
            company=delegation_context['delegated_company_id'] if delegation_context['is_delegating'] else registro_original.company,
            date=registro_original.date,  # Keep the original logical date of the shift
            clock_in=new_in,
            clock_out=new_out,
            status=TimeEntries.EntryStatus.CONFIRMED,
            notes=f"Editado manualmente por {(request.user.username if not delegation_context['is_delegating'] else delegation_context['delegated_user_name'])}",
            total_seconds=max(0, segundos)
        )
        return redirect('manager_logs')
    return HttpResponse("Método no permitido.")


@login_required
@never_cache
def manager_employee(request):
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
            # Admin is inspecting a specific company
            company = Companies.objects.filter(id=company_id).first()
            if not company:
                return HttpResponseForbidden("Empresa no encontrada.")

            # Validate permissions: must be admin
            if not request.user.is_admin:
                return HttpResponseForbidden("Solo administradores pueden inspeccionar otras empresas.")

            request.session['company_id'] = company_id
            delegation_context['is_inspecting'] = True
        else:
            # Get the user's own company membership
            user_membership = UserCompany.objects.filter(user=request.user).first()
            if not user_membership:
                return HttpResponseForbidden("No estás asignado a ninguna empresa.")
            company = user_membership.company

    # 2. Check if they are a manager or admin to pass it to the template
    user_membership = UserCompany.objects.filter(user=request.user, company=company).first()
    is_manager = (user_membership and user_membership.role == UserCompany.RoleChoices.MANAGER) or request.user.is_admin

    # 3. Get ALL memberships (employees) for that company
    memberships = UserCompany.objects.filter(
        company=company
    ).select_related('user').order_by('-joined_at')

    context = {
        'memberships': memberships,
        'is_manager': is_manager,
        'company': company,
        'is_inspecting': delegation_context.get('is_inspecting', False),
    }
    context.update(delegation_context)

    return render(request, 'audit/manager_employee.html', context)

@manager_or_admin_required
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

    return redirect('manager_employee')

@manager_or_admin_required
@require_POST
def delete_employee(request):
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

    # 2. Collect ID of user to delete
    user_id = request.POST.get('user_id')

    # 3. Find the membership and delete it
    # With this we "unlink" the user from the company without deleting their historical clock-ins or global account
    membership = get_object_or_404(UserCompany, user_id=user_id, company=company)

    # Prevent a manager from accidentally deleting themselves
    if user_id == str(request.user.id):
        return redirect('manager_employee')

    membership.delete()

    return redirect('manager_employee')

@manager_or_admin_required
@require_POST
def anular_registro(request):
    # Get effective context (delegation info if any)
    delegation_context = get_effective_context(request)

    registro_id = request.POST.get('registro_id')

    if not registro_id:
        return HttpResponse("ID de registro no proporcionado.", status=400)

    registro = get_object_or_404(TimeEntries, id=registro_id)

    # Determine who is voiding the record
    if delegation_context['is_delegating']:
        voiding_username = delegation_context['delegated_user_name']
    else:
        voiding_username = request.user.username

    registro.status = 'voided'

    registro.total_seconds = 0
    registro.notes = f"{registro.notes}\n[Anulado por {voiding_username}]"

    registro.save()

    return redirect('manager_logs')
