# core/urls.py
# ═══════════════════════════════════════════════════════════════════════════

from django.urls import path
from users import views as user_views
from dashboard import views as dashboard_views
from timetracking import views as timetracking_views
from audit import views as audit_views
from admin import views as admin_views   
from management import views as management_views
from requests import views as requests_views

urlpatterns = [
    # ════════════════════════════════════════════════════════════════════════
    # HOME & TIME TRACKING
    # ════════════════════════════════════════════════════════════════════════
    path('home/', timetracking_views.time_entries, name='home_timetracking'),
    path('time-entries/', timetracking_views.time_entries, name='time_entries'),

    # ════════════════════════════════════════════════════════════════════════
    # AUTH & CORE (users/)
    # ════════════════════════════════════════════════════════════════════════
    path('', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    path('register/', user_views.register_unified, name='register_unified'),
    path('switch-company/<uuid:company_id>/', user_views.switch_company, name='switch_company'),

    # API Lookups
    path('api/lookup-company/', user_views.lookup_company, name='lookup_company'),
    path('api/lookup-user/', user_views.lookup_user, name='lookup_user'),
    path('api/user-companies-count/', user_views.user_companies_count, name='user_companies_count'),
    path('api/check-last-manager/', user_views.check_last_manager, name='check_last_manager'),

    # ════════════════════════════════════════════════════════════════════════
    # DASHBOARD - PERSONAL (dashboard/)
    # ════════════════════════════════════════════════════════════════════════

    # Personal Time Tracking
    path('workday/', user_views.workday, name='workday'),
    path('workday/exportar_entries/', user_views.export_workday_entries, name='export_workday_entries'),
    path('workday/exportar_requests/', user_views.export_workday_requests, name='export_workday_requests'),

    # Personal Info
    path('profile/', dashboard_views.profile, name='profile'),
    path('security/', dashboard_views.security, name='security'),

    # Personal Leave & Calendar
    path('calendar/', dashboard_views.calendar, name='calendar'),

    # Team Views (static info)
    path('team/', management_views.staff, name='team_staff'),
    path('notes/', dashboard_views.notes, name='team_notes'),

    # ════════════════════════════════════════════════════════════════════════
    # MANAGEMENT - MANAGER FUNCTIONS (management/)
    # ════════════════════════════════════════════════════════════════════════

    # Time Logs
    path('logs/', management_views.manager_logs, name='manager_logs'),
    path('logs/export/', management_views.exportar_logs, name='exportar_logs'),
    path('logs/edit/', management_views.editar_registro, name='editar_registro'),
    path('logs/void/', management_views.anular_registro, name='anular_registro'),

    # Staff Management
    path('staff/', management_views.staff, name='staff'),
    path('staff/edit/', management_views.edit_employee, name='edit_employee'),
    path('staff/delete/', management_views.delete_employee, name='delete_employee'),
    path('staff/export/', management_views.exportar_staff, name='exportar_staff'),

    # Company Configuration
    path('company-info/', management_views.entity_info, name='manager_entity_info'),

    # ════════════════════════════════════════════════════════════════════════
    # REQUESTS - CORRECTIONS & LEAVE REQUESTS (requests/)
    # ════════════════════════════════════════════════════════════════════════

    # Correction Requests
    path('logs/resolve/', requests_views.resolver_incidencia, name='resolver_incidencia'),
    path('requests/edit/', requests_views.editar_incidencia_rechazada, name='editar_incidencia_rechazada'),
    path('requests/delete/', requests_views.eliminar_incidencia_rechazada, name='eliminar_incidencia_rechazada'),
    path('requests/export/', requests_views.exportar_logs_rechazadas, name='exportar_logs_rechazadas'),

    # Leave Requests (manager review)
    path('leave/pending/', requests_views.api_leave_pending, name='leave_pending'),
    path('leave/<uuid:leave_id>/review/', requests_views.api_leave_review, name='leave_review'),
    path('leave/resolved/', requests_views.api_leave_resolved, name='api_leave_resolved'),
    path('leave/<uuid:leave_id>/upload/', requests_views.api_leave_upload_attachment, name='api_leave_upload_attachment'),
    path('calendar/events/', requests_views.api_calendar_events, name='calendar_events'),
    path('leave/create/', requests_views.api_leave_request_create, name='leave_create'),
    path('api/leave/validate-overlap/', requests_views.api_validate_leave_overlap, name='api_validate_leave_overlap'),
    path('leave/<uuid:leave_id>/cancel/', requests_views.api_leave_request_cancel, name='api_leave_cancel'),

    # ════════════════════════════════════════════════════════════════════════
    # ADMIN - GLOBAL ADMINISTRATION (admin/)
    # ════════════════════════════════════════════════════════════════════════

    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),

    # Soft Delete Management
    path('admin/deleted-records/', admin_views.deleted_records, name='deleted_records'),
    path('admin/deleted-records/export/', admin_views.export_deleted_records, name='export_deleted_records'),
    path('admin/restore/', admin_views.restore_record, name='restore_record'),
    path('admin/delete-permanent/', admin_views.permanently_delete_record, name='permanently_delete_record'),
    path('admin/delete-company/', admin_views.delete_company, name='delete_company'),

    # API - Admin Delegation
    path('api/admin/delegate/', admin_views.select_delegated_worker, name='select_delegated_worker'),
    path('api/admin/clear-delegate/', admin_views.clear_delegated_worker, name='clear_delegated_worker'),

    # ════════════════════════════════════════════════════════════════════════
    # AUDIT - READ-ONLY LOGS (audit/)
    # ════════════════════════════════════════════════════════════════════════
    path('audit/', audit_views.audit_dashboard, name='audit_dashboard'),
    path('audit/logs/', audit_views.audit_timetracking, name='audit_timetracking'),
    path('audit/leave/', audit_views.audit_leave, name='audit_leave'),
    path('audit/users/', audit_views.audit_users, name='audit_users'),
    path('audit/corrections/', audit_views.audit_corrections, name='audit_corrections'),
    path('audit/company/', audit_views.audit_company, name='audit_company'),
]

