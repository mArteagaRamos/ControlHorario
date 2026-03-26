from datetime import timedelta
from urllib import request

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.dateparse import parse_date
from users.models import Companies, Users, UserCompanyMembership, CompanySettings


WEEKDAY = [
    (0, 'Domingo'),
    (1, 'Lunes'),
    (2, 'Martes'),
    (3, 'Miércoles'),
    (4, 'Jueves'),
    (5, 'Viernes'),
    (6, 'Sábado'),
]

@login_required
def control(request):
    return render(request, 'dashboard/control.html')

# User management views

@login_required
def calendar(request):
    return render(request, 'user_panel/calendar.html')

@login_required
def profile(request):
    return render(request, 'user_panel/profile.html')

@login_required
def absence(request):
    return render(request, 'user_panel/absence.html')

@login_required
def request_correction(request):
    return render(request, 'user_panel/requests.html')   


# Team management views

@login_required
def entity_info(request):
    company_id = request.session.get('company_id')
    if not company_id:
        messages.error(request, 'No tienes empresa asignada.')
        return redirect('home_timetracking')

    company = Companies.objects.filter(id=company_id).first()
    if not company:
        messages.error(request, 'Empresa no encontrada.')
        return redirect('home_timetracking')
    
    membership = UserCompanyMembership.objects.filter(
    user=request.user, 
    company=company
    ).first()

    user_role = membership.role if membership else None

    settings_obj = CompanySettings.objects.filter(company=company).first()

    if request.method == 'POST' and user_role == UserCompanyMembership.RoleChoices.MANAGER:
 
        # Update company info
        company.name       = request.POST.get('name', company.name).strip()
        company.legal_name = request.POST.get('legal_name', company.legal_name).strip()
        company.tax_id     = request.POST.get('tax_id', '').strip() or None
        company.updated_at = timezone.now()
        company.save(update_fields=['name', 'legal_name', 'tax_id', 'updated_at'])

        # Workday settings
        
        if settings_obj:
            workday_start = request.POST.get('workday_start')
            if workday_start:
                settings_obj.workday_start = workday_start

            workday_end = request.POST.get('workday_end')
            if workday_end:
                settings_obj.workday_end = workday_end

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

            for raw in request.POST.get('holidays', '').split(','):
                raw = raw.strip()
                if raw:
                    parsed = parse_date(raw)
                    if parsed:
                        holidays.append(parsed)
            settings_obj.holidays = holidays
            settings_obj.updated_at = timezone.now()
            settings_obj.save()

        messages.success(request, "Información de la empresa actualizada correctamente.")
        return redirect('entity_info')
             
    return render(request, 'team/entity_info.html',{

        'company': company,
        'user_role': user_role,
        'settings': settings_obj,
        'weekdays': WEEKDAY,

                  })

@login_required
def staff(request):
    return render(request, 'team/staff.html')

@login_required
def notes(request):
    return render(request, 'team/notes.html')