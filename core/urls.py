# ---------- Backend URL Routing: core/urls.py ----------

from django.contrib import admin
from django.urls import path
from users import views as user_views
from dashboard import views as dashboard_views
from timetracking import views as timetracking_views
from audit import views as audit_views

# Project URL patterns
urlpatterns = [
    path('home/', dashboard_views.home, name='home'),
    path('control/', dashboard_views.control, name='control'),


    path('', user_views.login_view, name='login'),
    path('sign_up/', user_views.register, name='register'),
    path('create_company/', user_views.create_company, name='create_company'),

    path('workday/', user_views.workday, name='workday'),
    path('calendar/', user_views.calendar, name='calendar'),
    path('profile/', user_views.profile, name='profile'),
    path('request_correction/', user_views.request_correction, name='request_correction'),
    path('absence/', user_views.absence, name='absence'),


    path('entity_info/', user_views.entity_info, name='entity_info'),
    path('staff/', user_views.staff, name='staff'),
    path('notes/', user_views.notes, name='notes'),


    path('timetracking/', timetracking_views.time_entries, name='time_entries'),
    path('switch-company/<uuid:company_id>/', user_views.switch_company, name='switch_company'),


    # Manager Panel URLs 
    path('manager_logs/', audit_views.manager_logs, name='manager_logs'),  
    path('manager_logs/exportar_logs/', audit_views.exportar_logs, name='exportar_logs'),
    path('manager_logs/resolver/', audit_views.resolver_incidencia, name='resolver_incidencia'),
    path('editar-registro/', audit_views.editar_registro, name='editar_registro'),
    path('manager_employee/', audit_views.manager_employee, name='manager_employee'),
]
