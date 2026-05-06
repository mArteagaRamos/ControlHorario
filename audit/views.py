# audit/views.py

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import AuditLog
from core.decorators import auditor_or_admin_required
from users.models import Companies, Users


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT VIEWS (Read-only audit functions)
# ═══════════════════════════════════════════════════════════════════════════════
#
# 1. Audit Dashboard view (menu buttons)
@auditor_or_admin_required
def audit_dashboard(request):
    # Add 'audit/' to the route
    return render(request, 'audit/audit_dashboard.html')

# ---------------------------------------------------------
# SPECIFIC TABLE VIEWS
# ---------------------------------------------------------

@auditor_or_admin_required
def audit_timetracking(request):
    # Tables to monitor
    tablas_fichajes = ['timetracking_registro', 'timetracking_pausa', 'timetracking_timeentries']
    
    # 1. Base QuerySet
    logs_list = AuditLog.objects.filter(table_name__in=tablas_fichajes).order_by('-timestamp')

    # 2. SEARCH FILTER
    search_query = request.GET.get('search')
    if search_query:
        logs_list = logs_list.filter(
            Q(user__username__icontains=search_query) |
            Q(user__surname__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    # 3. DATE FILTER
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    if desde:
        logs_list = logs_list.filter(timestamp__date__gte=desde)
    if hasta:
        logs_list = logs_list.filter(timestamp__date__lte=hasta)

    # 4. PAGINATION
    paginator = Paginator(logs_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # -----------------------------------------------------------------------
    # 5. MAGIC FOR AUDITOR: TRANSLATION AND DATA FORMAT
    # -----------------------------------------------------------------------
    
    # UUID to Names maps
    mapa_usuarios = {str(u.id): u.username for u in Users.objects.all()}
    
    try:
        mapa_empresas = {str(c.id): c.name for c in Companies.objects.all()}
    except NameError:
        mapa_empresas = {}

    # Dictionary for columns
    traducciones_keys = {
        'id': 'ID Registro',
        'date': 'Fecha de Jornada',
        'user': 'Usuario',
        'notes': 'Notas / Justificación',
        'status': 'Estado',
        'company': 'Compañía',
        'clock_in': 'Hora de Entrada',
        'clock_out': 'Hora de Salida',
        'deleted_at': 'Eliminado el',
        'total_seconds': 'Segundos Totales'
    }

    # Dictionary for states
    traducciones_estados = {
        'present': 'Presente',
        'paused': 'Pausado',
        'voided': 'Anulado',
        'completed': 'Completado',
        'active': 'Activo',
        'pending': 'Pendiente',
        'confirmed': 'Confirmado',
    }

    # -----------------------------------------------------------------------
    # 6. PROCESS LOGS FOR CURRENT PAGE
    # -----------------------------------------------------------------------

    for log in page_obj:
        for atributo in ['before', 'after']:
            estado = getattr(log, atributo)
            if isinstance(estado, dict):
                estado_limpio = {}
                for key, value in estado.items():
                    key_lower = key.lower()
                    key_limpia = traducciones_keys.get(key_lower, key.replace('_', ' ').title())
                    
                    # 1. Translate UUIDs
                    if key_lower == 'user' and str(value) in mapa_usuarios:
                        value = mapa_usuarios[str(value)]
                    elif key_lower == 'company' and str(value) in mapa_empresas:
                        value = mapa_empresas[str(value)]
                        
                    # 2. Translate States
                    elif key_lower == 'status' and isinstance(value, str):
                        value = traducciones_estados.get(value.lower(), value.title())
                        
                    # 3. Format Dates and Times correctly
                    elif isinstance(value, str):
                        # ONLY TIME for Clock In and Clock Out
                        if key_lower in ['clock_in', 'clock_out'] and 'T' in value:
                            try:
                                value = value.split('T')[1][:8]
                            except IndexError:
                                pass
                        
                        # FULL DATE AND TIME for Deleted At (or any other datetime with T)
                        elif 'T' in value: 
                            try:
                                fecha_str, resto = value.split('T')
                                hora_str = resto[:8]
                                anio, mes, dia = fecha_str.split('-')
                                value = f"{dia}/{mes}/{anio} - {hora_str}"
                            except ValueError:
                                pass 
                        
                        # ONLY DATE for Day Date
                        elif key_lower == 'date' and '-' in value: 
                            try:
                                anio, mes, dia = value.split('-')
                                value = f"{dia}/{mes}/{anio}"
                            except ValueError:
                                pass

                    estado_limpio[key_limpia] = value
                
                setattr(log, atributo, estado_limpio)
    # -----------------------------------------------------------------------

    context = {
        'titulo': 'Auditoría de Fichajes',
        'icono': 'fas fa-clock', 
        'color_tema': 'success', 
        'logs': page_obj,
        'search_query': search_query,
        'desde': desde,
        'hasta': hasta,
    }

    return render(request, 'audit/audit_timetracking.html', context)

@auditor_or_admin_required
def audit_leave(request):

    logs_list = AuditLog.objects.filter(table_name='leave_requests').order_by('-timestamp')

    # Search filter
    search_query = request.GET.get('search')
    if search_query:
        logs_list = logs_list.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    # Filter by date
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    if desde:
        logs_list = logs_list.filter(timestamp__date__gte=desde)
    if hasta:
        logs_list = logs_list.filter(timestamp__date__lte=hasta)


    paginator = Paginator(logs_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'titulo': 'Auditoría de Vacaciones y Ausencias',
        'icono': 'fas fa-calendar-alt',
        'color_tema': 'warning',
        'logs': page_obj,
        'search_query': search_query,
        'desde': desde,
        'hasta': hasta,
    }
    return render(request, 'audit/audit_leave_requests.html', context)

@auditor_or_admin_required
def audit_users(request):
    tablas_usuarios = ['user_action']  # Standard table for all user events

    # 1. Base QuerySet
    logs_list = AuditLog.objects.filter(table_name__in=tablas_usuarios).order_by('-timestamp')

    # 2. SEARCH FILTER (By username or email)
    search_query = request.GET.get('search')
    if search_query:
        logs_list = logs_list.filter(
            Q(user__username__icontains=search_query) |
            Q(user__surname__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    # 3. DATE FILTER
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    if desde:
        logs_list = logs_list.filter(timestamp__date__gte=desde)
    if hasta:
        logs_list = logs_list.filter(timestamp__date__lte=hasta)

    # 4. PAGINATION (15 records per page)
    paginator = Paginator(logs_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'titulo': 'Auditoría de Usuarios',
        'icono': 'fas fa-users',
        'color_tema': 'info',
        'logs': page_obj,  # Now we pass the paginated object
        'search_query': search_query,
        'desde': desde,
        'hasta': hasta,
    }
    return render(request, 'audit/audit_users.html', context)

@auditor_or_admin_required
def audit_corrections(request):
    tablas_incidencias = ['timetracking_correctionrequest']
    
    logs_list = AuditLog.objects.filter(table_name__in=tablas_incidencias).order_by('-timestamp')
    
    search_query = request.GET.get('search')
    if search_query:
        logs_list = logs_list.filter(
            Q(user__username__icontains=search_query) |
            Q(user__surname__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(reason__icontains=search_query)
        )

    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    if desde:
        logs_list = logs_list.filter(timestamp__date__gte=desde)
    if hasta:
        logs_list = logs_list.filter(timestamp__date__lte=hasta)

    paginator = Paginator(logs_list, 12) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # -----------------------------------------------------------------------
    # TRANSLATION MAGIC (EXTENDED FOR CORRECTIONS)
    # -----------------------------------------------------------------------
    
    mapa_usuarios = {str(u.id): u.username for u in Users.objects.all()}
    try:
        mapa_empresas = {str(c.id): c.name for c in Companies.objects.all()}
    except NameError:
        mapa_empresas = {}

    traducciones_keys = {
        'id': 'ID Incidencia',
        'date': 'Fecha Afectada',
        'user': 'Usuario',
        'status': 'Estado',
        'reason': 'Motivo / Justificación',
        'company': 'Compañía',
        'clock_in': 'Hora de Entrada',
        'clock_out': 'Hora de Salida',
        'created_at': 'Creado el',
        'updated_at': 'Actualizado el',
        'deleted_at': 'Eliminado el',
        # --- NEW CAPTURE FIELDS ---
        'approver': 'Aprobador',
        'requester': 'Solicitante',
        'time_entry': 'ID Fichaje Original',
        'new_clock_in': 'Nueva Hora de Entrada',
        'new_clock_out': 'Nueva Hora de Salida',
        'request_date': 'Fecha de Solicitud',
        'approval_date': 'Fecha de Aprobación',
        'correction_note': 'Nota de Corrección'
    }

    traducciones_estados = {
        'pending': 'Pendiente',
        'approved': 'Aprobada',
        'rejected': 'Rechazada',
        'voided': 'Anulada',
    }

    for log in page_obj:
        for atributo in ['before', 'after']:
            estado = getattr(log, atributo)
            if isinstance(estado, dict):
                estado_limpio = {}
                for key, value in estado.items():
                    key_lower = key.lower()
                    key_limpia = traducciones_keys.get(key_lower, key.replace('_', ' ').title())
                    
                    # 1. Translate UUIDs of ANY user (requester, approver, etc)
                    if key_lower in ['user', 'approver', 'requester'] and str(value) in mapa_usuarios:
                        value = mapa_usuarios[str(value)]
                    elif key_lower == 'company' and str(value) in mapa_empresas:
                        value = mapa_empresas[str(value)]
                        
                    # 2. Translate States
                    elif key_lower == 'status' and isinstance(value, str):
                        value = traducciones_estados.get(value.lower(), value.title())
                        
                    # 3. Dates and Times
                    elif isinstance(value, str):
                        # ONLY TIME (Added new_clock fields)
                        if key_lower in ['clock_in', 'clock_out', 'new_clock_in', 'new_clock_out'] and 'T' in value:
                            try:
                                value = value.split('T')[1][:8]
                            except IndexError:
                                pass
                        
                        # FULL DATE AND TIME
                        elif 'T' in value: 
                            try:
                                fecha_str, resto = value.split('T')
                                hora_str = resto[:8]
                                anio, mes, dia = fecha_str.split('-')
                                value = f"{dia}/{mes}/{anio} - {hora_str}"
                            except ValueError:
                                pass 
                        
                        # ONLY DATE
                        elif key_lower == 'date' and '-' in value: 
                            try:
                                anio, mes, dia = value.split('-')
                                value = f"{dia}/{mes}/{anio}"
                            except ValueError:
                                pass

                    estado_limpio[key_limpia] = value
                
                setattr(log, atributo, estado_limpio)
    # -----------------------------------------------------------------------

    context = {
        'titulo': 'Auditoría de Incidencias',
        'icono': 'fas fa-exclamation-triangle',
        'color_tema': 'danger', 
        'logs': page_obj,
        'search_query': search_query,
        'desde': desde,
        'hasta': hasta,
    }
    return render(request, 'audit/audit_corrections_requests.html', context)


JORNADA_FIELDS = {'work_start', 'work_end', 'max_tolerance', 'weekend_days', 'holidays'}
CIERRE_FIELDS  = {'auto_close_hours'}
PAUSA_FIELDS   = set()  # CompanySettings has no pause fields

def _infer_categoria(log):
    keys = set((log.after or {}).keys()) | set((log.before or {}).keys())
    if keys & CIERRE_FIELDS:
        return 'cierre'
    if keys & JORNADA_FIELDS:
        return 'jornada'
    return 'otros'


@auditor_or_admin_required
def audit_company(request):

    # ── Filters ────────────────────────────────────────────────────────────────
    search_query = request.GET.get('search', '').strip()
    tipo_cambio  = request.GET.get('tipo_cambio', '').strip()
    desde        = request.GET.get('desde', '').strip()
    hasta        = request.GET.get('hasta', '').strip()

    qs = (
        AuditLog.objects
        .filter(table_name='company_settings')
        .select_related('user')
        .order_by('-timestamp')
    )

    # Free search: actor (username) or reason
    if search_query:
        qs = qs.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)    |
            Q(reason__icontains=search_query)
        )

    # Date filter
    if desde:
        qs = qs.filter(timestamp__date__gte=desde)
    if hasta:
        qs = qs.filter(timestamp__date__lte=hasta)


    if tipo_cambio in ('jornada', 'cierre', 'pausas'):
        field_map = {
            'jornada': JORNADA_FIELDS,
            'cierre':  CIERRE_FIELDS,
            'pausas':  PAUSA_FIELDS,
        }
        target_fields = field_map[tipo_cambio]
        # Filtramos en memoria; primero traemos solo los candidatos del QS
        ids_match = [
            log.id for log in qs
            if (set((log.after or {}).keys()) | set((log.before or {}).keys())) & target_fields
        ]
        qs = AuditLog.objects.filter(id__in=ids_match).select_related('user').order_by('-timestamp')

    # Anotamos la categoría en cada log para usarla en el template sin lógica extra
    log_list = list(qs)
    for log in log_list:
        log.categoria = _infer_categoria(log)

    # ── Paginación ────────────────────────────────────────────────────────────
    paginator = Paginator(log_list, 12)
    page_number = request.GET.get('page', 1)
    logs = paginator.get_page(page_number)

    # Handle AJAX load more
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('load_more'):
        offset = int(request.GET.get('offset', 20))
        limit = 10
        logs_to_add = log_list[offset:offset+limit]
        for log in logs_to_add:
            log.categoria = _infer_categoria(log)
        return render(request, 'audit/audit_company_rows.html', {'logs': logs_to_add})

    return render(request, 'audit/audit_company.html', {
        'logs':         logs,
        'search_query': search_query,
        'tipo_cambio':  tipo_cambio,
        'desde':        desde,
        'hasta':        hasta,
        'has_more':     len(log_list) > 12,
    })