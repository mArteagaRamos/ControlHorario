# ---------- Backend Views: audit/views.py ----------

import csv
from functools import wraps
from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from users.models import CorrectionRequests, UserCompanyMembership, Users
from timetracking.models import TimeEntries
from django.db.models import OuterRef, Subquery
import uuid
from django.utils import timezone
from datetime import datetime
from django.http import HttpResponseForbidden

# Decorador para verificar que el usuario es manager o admin antes de acceder a ciertas vistas
def manager_or_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Si ni siquiera está logueado, fuera
        if not request.user.is_authenticated:
            return render(request, 'error/sin_loguear.html', status=401)

        is_admin = request.user.is_admin
        is_manager = UserCompanyMembership.objects.filter(
            user=request.user, 
            role=UserCompanyMembership.RoleChoices.MANAGER
        ).exists()

        if is_admin or is_manager:
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'error/sin_permisos.html', status=403)
            
    return _wrapped_view

@manager_or_admin_required
def manager_logs(request):
    # 1. Obtener la empresa del manager
    membership = UserCompanyMembership.objects.filter(
        user=request.user, 
        role=UserCompanyMembership.RoleChoices.MANAGER
    ).first()

    if not membership:
        return HttpResponse("No tienes permisos de manager o no estás asignado a una empresa.")

    company = membership.company

    # 2. Obtener los empleados de esta empresa
    empleados_ids = UserCompanyMembership.objects.filter(company=company).values_list('user_id', flat=True)
    empleados = Users.objects.filter(id__in=empleados_ids)

    # 3. Preparamos una subconsulta para sacar el rol exacto de cada usuario en ESTA empresa
    rol_subquery = UserCompanyMembership.objects.filter(
        user=OuterRef('user'),
        company=company
    ).values('role')[:1]

    # --- CAMBIO: Subimos las incidencias aquí arriba para poder usar sus IDs como filtro ---
    incidencias = CorrectionRequests.objects.filter(
        time_entry__company=company, 
        status='pending'
    ).select_related('time_entry', 'requester').order_by('-request_date')

    # Para poner el puntito rojo en la tabla y para filtrar, sacamos las IDs
    fichajes_con_incidencia = incidencias.values_list('time_entry_id', flat=True)
    fichajes_con_incidencia_str = [str(uid) for uid in fichajes_con_incidencia]

    # 4. Obtener los fichajes (TimeEntries) e inyectarles el rol
    registros = TimeEntries.objects.filter(
        company=company
    ).exclude(
        status=TimeEntries.EntryStatus.CORRECTED 
    ).annotate(
        rol_empleado=Subquery(rol_subquery)
    ).select_related('user').order_by('-date', '-clock_in')

    # 5. Aplicar Filtros si existen en el GET
    empleado_id = request.GET.get('empleado')
    fecha = request.GET.get('fecha')
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    solo_incidencias = request.GET.get('solo_incidencias')  # Capturamos el nuevo checkbox

    if empleado_id:
        registros = registros.filter(user_id=empleado_id)
    if fecha:
        registros = registros.filter(date=fecha)
    if desde:
        registros = registros.filter(clock_in__time__gte=desde)
    if hasta:
        registros = registros.filter(clock_out__time__lte=hasta) 
    
    # NUEVO FILTRO: Solo nos quedamos con los que su ID esté en la lista de incidencias
    if solo_incidencias == 'true' or solo_incidencias == 'on':
        registros = registros.filter(id__in=fichajes_con_incidencia)

    # 6. Formatear los segundos a "Xh Ym" para que quede bonito en la tabla
    for r in registros:
        horas = r.total_seconds // 3600
        minutos = (r.total_seconds % 3600) // 60
        r.horas_formateadas = f"{horas}h {minutos}m" if r.total_seconds > 0 else "--"

    context = {
        'registros': registros,
        'empleados': empleados,
        'incidencias': incidencias,
        'fichajes_con_incidencia': fichajes_con_incidencia_str,
    }
    return render(request, 'audit/manager_logs.html', context)  

@manager_or_admin_required
def resolver_incidencia(request):
    if request.method == 'POST':
        incidencia_id = request.POST.get('incidencia_id')
        accion = request.POST.get('accion') 
        # Capturamos la nota que viene del formulario del modal
        nota_resolucion = request.POST.get('nota_resolucion', '') 

        incidencia = get_object_or_404(CorrectionRequests, id=incidencia_id)
        ficha_original = incidencia.time_entry 

        # --- ASIGNACIÓN DE CAMPOS DE AUDITORÍA ---
        incidencia.approver = request.user          # Guarda quién lo hace
        incidencia.approval_date = timezone.now()    # Guarda cuándo lo hace
        incidencia.correction_note = nota_resolucion # Guarda el porqué (la nota)

        if accion == 'aceptar':
            # 1. Marcamos el original como 'corrected'
            ficha_original.status = TimeEntries.EntryStatus.CORRECTED
            ficha_original.save()

            # --- CÁLCULO DE SEGUNDOS ---
            segundos = 0
            if incidencia.new_clock_in and incidencia.new_clock_out:
                delta = incidencia.new_clock_out - incidencia.new_clock_in
                segundos = int(delta.total_seconds())

            # 2. Creamos el nuevo registro definitivo
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

        # Guardamos todos los cambios (incluyendo approver, date y note)
        incidencia.save()
        
        return redirect('manager_logs')
        
    return HttpResponse("Método no permitido.")

def exportar_logs(request):
    
    if not request.usercompanymembership.role == UserCompanyMembership.RoleChoices.MANAGER or not request.user.is_admin == 'True':
        return HttpResponse("No tienes permisos para acceder a esta página.")
    
    if request.method == 'POST':
        registros_ids = request.POST.getlist('registro_id')

        if not registros_ids:
            return HttpResponse("No seleccionaste ningún registro para exportar.")

        registros = TimeEntries.objects.filter(id__in=registros_ids).select_related('user').order_by('-date', '-clock_in')

        response = HttpResponse(content_type='text/csv')
        fecha_reporte = timezone.now().strftime('%d_%m_%Y')
        response['Content-Disposition'] = f'attachment; filename="reporte_fichajes_{fecha_reporte}.csv"'

        # IMPORTANTE: Esto evita que los acentos se vean mal en Excel
        response.write(u'\ufeff'.encode('utf8'))
        
        writer = csv.writer(response, delimiter=';') # El punto y coma es el estándar para Excel en español
        
        # Cabeceras claras
        writer.writerow(['Empleado', 'Fecha', 'Entrada', 'Salida', 'Tiempo Total (HH:MM:SS)', 'Notas'])

    for r in registros:
        # Lógica de conversión de segundos a formato HH:MM:SS
        total_s = r.total_seconds
        
        horas = total_s // 3600
        minutos = (total_s % 3600) // 60
        segundos = total_s % 60

        # Formateamos con ceros a la izquierda (ej: 08:05:09)
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
    
    return HttpResponse("Método no permitido.")

@manager_or_admin_required
def editar_registro(request):   
    if request.method == 'POST':
        registro_id = request.POST.get('registro_id')
        registro_original = get_object_or_404(TimeEntries, id=registro_id)

        hora_entrada = request.POST.get('clock_in')
        hora_salida = request.POST.get('clock_out')

        # 1. Anulamos el actual
        registro_original.status = TimeEntries.EntryStatus.CORRECTED
        registro_original.save()

        # 2. Construimos los datetimes para el nuevo registro
        # Usamos la fecha del registro original y le pegamos la nueva hora
        new_in_str = f"{registro_original.date} {hora_entrada}"
        new_in = datetime.strptime(new_in_str, '%Y-%m-%d %H:%M')
        
        new_out = None
        segundos = 0
        if hora_salida:
            new_out_str = f"{registro_original.date} {hora_salida}"
            new_out = datetime.strptime(new_out_str, '%Y-%m-%d %H:%M')
            # Calcular segundos
            delta = new_out - new_in
            segundos = int(delta.total_seconds())

        TimeEntries.objects.create(
            id=uuid.uuid4(),
            user=registro_original.user,
            company=registro_original.company,
            date=registro_original.date,
            clock_in=new_in,
            clock_out=new_out,
            status=TimeEntries.EntryStatus.CONFIRMED,
            notes="Editado manualmente por el manager",
            total_seconds=max(0, segundos) # Guardamos los segundos calculados
        )
        return redirect('manager_logs')
    return HttpResponse("Método no permitido.")

@manager_or_admin_required
def manager_employee(request):
    employees = Users.objects  # Obtener todos los empleados
    return render(request, 'audit/manager_employee.html', {'employees': employees})



