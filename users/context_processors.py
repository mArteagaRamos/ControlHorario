# Context processor to add current company and breadcrumbs to templates

from datetime import date, timedelta
from users.models import UserCompany
from admin.models import CompanySettings
from .models import UserCompany
from core.context_processors import _translate_role

# URL names to exclude from breadcrumb generation
BREADCRUMB_EXCLUDE = {
    'api_leave_resolved',
    'calendar_events',
    'aeptic_report_data',
    'select_delegated_worker',
}

# Labels for URL names - maps route names to display labels
BREADCRUMB_LABELS = {
    'home_timetracking': 'Inicio',
    'workday': 'Jornadas',
    'calendar': 'Calendario',
    'profile': 'Perfil',
    'team_staff': 'Personal',
    'manager_entity_info': 'Información de la Empresa',
    'notes': 'Notas',
    'manager_logs': 'Correción de jornadas',
    'control': 'Panel de Control',
    'register_unified': 'Registro',
    'security': 'Seguridad',
    'admin_dashboard': 'Panel de Administración',
    'aeptic_summary': 'Control Incurrido',
    'aeptic_report_detail': 'Detalle del Informe',
    'aeptic_history': 'Histórico de Reportes',
}

AEPTIC_TAX_ID = 'B90143645'


def get_breadcrumbs(request):
    """Generate breadcrumbs from navigation history"""
    if not request.user.is_authenticated:
        return []

    history = request.session.get('nav_history', [])

    if not history:
        return []

    breadcrumbs = []

    for page in history:
        page_name = page.get('name') or 'Página'

        if page_name in BREADCRUMB_EXCLUDE:
            continue

        label = BREADCRUMB_LABELS.get(page_name, page_name.replace('_', ' ').title())
        breadcrumbs.append({
            'label': label,
            'url': page['path'],
        })

    if breadcrumbs:
        breadcrumbs[-1]['url'] = None

    return breadcrumbs


def _show_excel_reminder(user):
    """
    Devuelve True si hoy es uno de los últimos 5 días laborables del mes
    para un usuario de AEPTIC (ni admin ni auditor).
    """
    if not user.is_authenticated:
        return False
    if getattr(user, 'is_admin', False) or getattr(user, 'is_auditor', False):
        return False

    membership = UserCompany.objects.filter(
        user=user,
        company__tax_id=AEPTIC_TAX_ID,
        deleted_at__isnull=True
    ).select_related('company').first()

    if not membership:
        return False

    company = membership.company
    today = date.today()

    # Obtener festivos y días de fin de semana de la empresa
    settings_obj = CompanySettings.objects.filter(company=company).first()
    weekend_days = list(settings_obj.weekend_days) if settings_obj and settings_obj.weekend_days else [5, 6]
    holidays = list(settings_obj.holidays) if settings_obj and settings_obj.holidays else []

    # Calcular todos los días laborables del mes
    # Primer día del mes siguiente - 1 = último día del mes actual
    if today.month == 12:
        first_next = date(today.year + 1, 1, 1)
    else:
        first_next = date(today.year, today.month + 1, 1)
    last_day = first_next - timedelta(days=1)

    # Recorrer desde el último día hacia atrás hasta encontrar 5 laborables
    working_days_end = []
    current = last_day
    while len(working_days_end) < 5 and current.month == today.month:
        if current.weekday() not in weekend_days and current not in holidays:
            working_days_end.append(current)
        current -= timedelta(days=1)

    return today in working_days_end


def user_company(request):

    memberships = UserCompany.objects.none()
    is_admin = False

    if request.user.is_authenticated:
        memberships = UserCompany.objects.filter(user=request.user).select_related('company')
        is_admin = getattr(request.user, 'is_admin', False)

    current_role = getattr(request, 'role', None)
    return {
        'current_company': getattr(request, 'company', None),
        'current_role': _translate_role(current_role),
        'current_role_original': current_role,
        'memberships': memberships,
        'company_count': memberships.count(),
        'is_admin': is_admin,
        'breadcrumbs': get_breadcrumbs(request),
        'show_excel_reminder': _show_excel_reminder(request.user),
    }