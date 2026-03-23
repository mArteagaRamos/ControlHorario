# ---------- Backend URL Routing: core/urls.py ----------

from django.contrib import admin
from django.urls import path, include
from users import views as user_views
from dashboard import views as dashboard_views
from timetracking import views as timetracking_views
from audit import views as audit_views

# Project URL patterns
urlpatterns = [
    path('', dashboard_views.home, name='home'),
    path('login/', user_views.login_view, name='login'),
    path('sign_up/', user_views.register, name='register'),
    path('user_panel/', user_views.user_panel, name='user_panel'),
    path('timetracking/', timetracking_views.time_entries, name='time_entries'),


    # Manager Panel URLs 
    path('manager_logs/', audit_views.manager_logs, name='manager_logs'),  
    path('manager_logs/exportar_logs/', audit_views.exportar_logs, name='exportar_logs'),
    path('manager_incidents/', audit_views.manager_incidents, name='manager_incidents'),
    path('manager_employee/', audit_views.manager_employee, name='manager_employee'),
]
