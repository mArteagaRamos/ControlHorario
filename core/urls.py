# ---------- Backend URL Routing: core/urls.py ----------

from django.contrib import admin
from django.urls import path
from users import views as user_views
from dashboard import views as dashboard_views
from timetracking import views as timetracking_views
from audit import views as audit_views

# Project URL patterns
urlpatterns = [
    # Dashboard Home
    path('home/', timetracking_views.time_entries, name='home_timetracking'),

    # Control Panel
    path('control/', dashboard_views.control, name='control'),

    # Auth
    path('', user_views.login_view, name='login'),
    path('register/', user_views.register_unified, name='register_unified'),
    path('api/lookup-company/', user_views.lookup_company, name='lookup_company'),
    path('api/lookup-user/',    user_views.lookup_user,    name='lookup_user'),
    path('switch-company/<uuid:company_id>/', user_views.switch_company, name='switch_company'),

    # Dashboard - Worker
    path('workday/', user_views.workday, name='workday'),
    path('calendar/', dashboard_views.calendar, name='calendar'),
    path('profile/', dashboard_views.profile, name='profile'),
    path('request_correction/', dashboard_views.request_correction, name='request_correction'),
    path('absence/', dashboard_views.absence, name='absence'),

    # Dashboard - Team Management
    path('entity_info/', dashboard_views.entity_info, name='entity_info'),
    path('staff/', dashboard_views.staff, name='staff'),
    path('notes/', dashboard_views.notes, name='notes'),


    # Manager Panel URLs 
    # Manager Logs
    path('manager_logs/', audit_views.manager_logs, name='manager_logs'),  
    path('manager_logs/exportar_logs/', audit_views.exportar_logs, name='exportar_logs'),
    path('manager_logs/resolver/', audit_views.resolver_incidencia, name='resolver_incidencia'),
    path('editar-registro/', audit_views.editar_registro, name='editar_registro'),
    path('anular-registro/', audit_views.anular_registro, name='anular_registro'),
    # Manager Employees
    path('manager_employees/', audit_views.manager_employee, name='manager_employee'),
    path('manager_employees/edit/', audit_views.edit_employee, name='edit_employee'),
    path('manager_employees/delete/', audit_views.delete_employee, name='delete_employee'),
]
