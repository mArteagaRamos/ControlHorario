# ---------- Backend Views: audit/views.py ----------

import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from users.models import UserCompanyMembership, Users
from timetracking.models import TimeEntries

@login_required
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

    # 3. Obtener los fichajes (TimeEntries) de esta empresa
    registros = TimeEntries.objects.filter(company=company).select_related('user').order_by('-date', '-clock_in')

    # 4. Aplicar Filtros si existen en el GET
    empleado_id = request.GET.get('empleado')
    fecha = request.GET.get('fecha')
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')

    if empleado_id:
        registros = registros.filter(user_id=empleado_id)
    if fecha:
        registros = registros.filter(date=fecha)
    if desde:
        registros = registros.filter(clock_in__time__gte=desde)
    if hasta:
        # Usamos clock_out o clock_in según prefieras
        registros = registros.filter(clock_out__time__lte=hasta) 

    # 5. Formatear los segundos a "Xh Ym" para que quede bonito en la tabla
    for r in registros:
        horas = r.total_seconds // 3600
        minutos = (r.total_seconds % 3600) // 60
        r.horas_formateadas = f"{horas}h {minutos}m" if r.total_seconds > 0 else "--"

    context = {
        'registros': registros,
        'empleados': empleados,
    }
    return render(request, 'audit/manager_logs.html', context)

def exportar_logs(request):
    # Usamos POST porque vamos a enviar una lista de IDs desde los checkboxes
    if request.method == 'POST':
        registros_ids = request.POST.getlist('registro_id')

        if not registros_ids:
            return HttpResponse("No seleccionaste ningún registro para exportar. Vuelve atrás y marca las casillas.")

        # Obtener solo los seleccionados
        registros = TimeEntries.objects.filter(id__in=registros_ids).select_related('user').order_by('-date')

        # Configurar la respuesta como archivo CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fichajes_exportados.csv"'

        writer = csv.writer(response)
        # Cabeceras del Excel/CSV
        writer.writerow(['Empleado', 'Fecha', 'Entrada', 'Salida', 'Horas Totales (Segundos)'])

        for r in registros:
            writer.writerow([
                f"{r.user.username} {r.user.surname}",
                r.date,
                r.clock_in.strftime('%H:%M:%S') if r.clock_in else '--',
                r.clock_out.strftime('%H:%M:%S') if r.clock_out else '--',
                r.total_seconds
            ])

        return response
        
    return HttpResponse("Método no permitido. Por favor, utiliza el botón de exportar del panel.")

def manager_incidents(request):
    incidents = AuditLog.objects.filter(action__icontains='incidente').order_by('-timestamp')  # Filtrar solo incidentes
    return render(request, 'audit/manager_incidents.html', {'incidents': incidents})

def manager_employee(request):
    employees = Users.objects  # Obtener todos los empleados
    return render(request, 'audit/manager_employee.html', {'employees': employees})



