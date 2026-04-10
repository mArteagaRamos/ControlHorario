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

    # Auth
    path('', user_views.login_view, name='login'),
    path('register/', user_views.register_unified, name='register_unified'),
    path('api/lookup-company/', user_views.lookup_company, name='lookup_company'),
    path('api/lookup-user/',    user_views.lookup_user,    name='lookup_user'),
    path('api/check-last-manager/', user_views.check_last_manager, name='check_last_manager'),
    path('api/select-delegated-worker/', user_views.select_delegated_worker, name='select_delegated_worker'),
    path('api/clear-delegated-worker/', user_views.clear_delegated_worker, name='clear_delegated_worker'),
    path('switch-company/<uuid:company_id>/', user_views.switch_company, name='switch_company'),
    path('logout/', user_views.logout_view, name='logout'),

    # Dashboard - Worker
    path('workday/', user_views.workday, name='workday'),
    path('calendar/', dashboard_views.calendar, name='calendar'),
    path('profile/', dashboard_views.profile, name='profile'),
    path('security/', dashboard_views.security, name='security'),

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

    path('api/leave/create/',        dashboard_views.api_leave_request_create, name='api_leave_create'),
    path('api/leave/<uuid:leave_id>/cancel/', dashboard_views.api_leave_request_cancel, name='api_leave_cancel'),
path('api/leave/<uuid:leave_id>/review/', dashboard_views.api_leave_review, name='api_leave_review'),    path('api/leave/pending/',       dashboard_views.api_leave_pending,         name='api_leave_pending'),
    path('api/calendar/events/',     dashboard_views.api_calendar_events,       name='api_calendar_events'),
    # Admin Dashboard
    path('admin/', user_views.admin_dashboard, name='admin_dashboard'),
]

