# ---------- Backend Views: audit/views.py ----------

import csv
from functools import wraps
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from users.models import CorrectionRequests, UserCompany, Users
from timetracking.models import TimeEntries
from django.db.models import OuterRef, Subquery
import uuid
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponseForbidden
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

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

# Main manager view to see the clock-in logs of their company, with filters and incidents
@manager_or_admin_required
def manager_logs(request):
    # 1. Get the manager's company
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
        status=TimeEntries.EntryStatus.CORRECTED 
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

    # 6. PAGINACIÓN: Solo 20 registros por página
    paginator = Paginator(registros, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 7. Formatear segundos SOLO para los 20 registros que se van a mostrar
    for r in page_obj:
        horas = r.total_seconds // 3600
        minutos = (r.total_seconds % 3600) // 60
        r.horas_formateadas = f"{horas}h {minutos}m" if r.total_seconds > 0 else "--"

    context = {
        'page_obj': page_obj, # Enviamos la página en lugar de todos los registros
        'empleados': empleados,
        'incidencias': incidencias,
        'fichajes_con_incidencia': fichajes_con_incidencia_str,
        # Pasamos los filtros actuales para que el HTML los recuerde
        'current_filters': {
            'empleado': empleado_id or '',
            'fecha': fecha or '',
            'desde': desde or '',
            'hasta': hasta or '',
            'solo_incidencias': solo_incidencias or '',
        }
    }
    return render(request, 'audit/manager_logs.html', context)  

# View for the manager to accept or deny an incident, with their resolution note
@manager_or_admin_required
def resolver_incidencia(request):
    if request.method == 'POST':
        incidencia_id = request.POST.get('incidencia_id')
        accion = request.POST.get('accion') 
        # Capture the note coming from the modal form
        nota_resolucion = request.POST.get('nota_resolucion', '') 

        incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)
        ficha_original = incidencia.time_entry 

        # --- AUDIT FIELDS ASSIGNMENT ---
        incidencia.approver = request.user          # Saves who does it
        incidencia.approval_date = timezone.now()    # Saves when it's done
        incidencia.correction_note = nota_resolucion # Saves the reason (the note)

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
                notes=f"Aceptado por {request.user.username}. Motivo: {incidencia.reason}",
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
    if request.method == 'POST':
        registro_id = request.POST.get('registro_id')
        registro_original = get_object_or_404(TimeEntries, id=registro_id)

        hora_entrada = request.POST.get('clock_in') # Ahora recibe algo como "YYYY-MM-DDTHH:MM"
        hora_salida = request.POST.get('clock_out')

        # 1. Void the current one
        registro_original.status = TimeEntries.EntryStatus.CORRECTED
        registro_original.save()

        # 2. Parsear los datetimes que vienen del nuevo input datetime-local
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

        TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=registro_original.user,
            company=registro_original.company,
            date=registro_original.date, # Mantenemos la fecha lógica original del turno
            clock_in=new_in,
            clock_out=new_out,
            status=TimeEntries.EntryStatus.CONFIRMED,
            notes="Editado manualmente por el manager",
            total_seconds=max(0, segundos) # Save the calculated seconds
        )
        return redirect('manager_logs')
    return HttpResponse("Método no permitido.")


@login_required 
def manager_employee(request):
    # 1. Get current user's membership (whether manager or employee)
    user_membership = UserCompany.objects.filter(user=request.user).first()

    if not user_membership:
        return HttpResponseForbidden("No estás asignado a ninguna empresa.")

    company = user_membership.company
    
    # Check if they are a manager or admin to pass it to the template
    is_manager = (user_membership.role == UserCompany.RoleChoices.MANAGER) or request.user.is_admin

    # 2. Get ALL memberships (employees) for that company
    memberships = UserCompany.objects.filter(
        company=company
    ).select_related('user').order_by('-joined_at')

    return render(request, 'audit/manager_employee.html', {
        'memberships': memberships,
        'is_manager': is_manager
    })

@manager_or_admin_required
@require_POST
def edit_employee(request):
    # 1. Get current manager's company
    membership_manager = UserCompany.objects.filter(
        user=request.user, 
        role=UserCompany.RoleChoices.MANAGER
    ).first()
    company = membership_manager.company

    # 2. Collect form data
    user_id = request.POST.get('user_id')
    username = request.POST.get('username')
    surname = request.POST.get('surname')
    role = request.POST.get('role')
    status = request.POST.get('status')

    # 3. Validate that the employee belongs to the manager's company
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
    # 1. Get current manager's company
    membership_manager = UserCompany.objects.filter(
        user=request.user, 
        role=UserCompany.RoleChoices.MANAGER
    ).first()
    company = membership_manager.company

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

