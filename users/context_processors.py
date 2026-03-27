# Context processor to add current company and breadcrumbs to templates
from django.urls import reverse, NoReverseMatch
from .models import UserCompany


# Breadcrumbs configuration: maps URL names to breadcrumb hierarchy
BREADCRUMBS_CONFIG = {
    # Mi Área section
    'workday': {
        'label': 'Jornadas',
        'parent': 'Mi Área',
    },
    'calendar': {
        'label': 'Calendario',
        'parent': 'Mi Área',
    },
    'profile': {
        'label': 'Perfil',
        'parent': 'Mi Área',
    },
    'absence': {
        'label': 'Ausencias',
        'parent': 'Mi Área',
    },
    'request_correction': {
        'label': 'Solicitar Corrección',
        'parent': 'Mi Área',
    },
    # Equipo section
    'manager_employee': {
        'label': 'Gestión de Empleados',
        'parent': 'Equipo',
    },
    'entity_info': {
        'label': 'Información de la Empresa',
        'parent': 'Equipo',
    },
    'notes': {
        'label': 'Notas',
        'parent': 'Equipo',
    },
    # Manager/Admin section
    'manager_logs': {
        'label': 'Log de Actividades',
        'parent': 'Panel de Control',
    },
    'control': {
        'label': 'Panel de Control',
    },
    # Other
    'home_timetracking': {
        'label': 'Registrar Actividad',
    },
    'register_unified': {
        'label': 'Registro',
    },
}


def get_breadcrumbs(request):
    """Generate breadcrumbs for the current page"""
    if not request.resolver_match or not request.resolver_match.url_name:
        return []

    url_name = request.resolver_match.url_name
    config = BREADCRUMBS_CONFIG.get(url_name)

    if not config:
        return []

    breadcrumbs = [
        {'label': 'Inicio', 'url': reverse('home_timetracking')}
    ]

    if 'parent' in config:
        breadcrumbs.append({
            'label': config['parent'],
            'url': None,  # Parent section has no direct URL
        })

    breadcrumbs.append({
        'label': config['label'],
        'url': None,  # Current page is not clickable
    })

    return breadcrumbs


def user_company(request):
    memberships = UserCompany.objects.none()
    is_admin = False

    if request.user.is_authenticated:
        memberships = UserCompany.objects.filter(user=request.user).select_related('company')

        is_admin = getattr(request.user, 'is_admin', False)

    return {
        'current_company': getattr(request, 'company', None),
        'current_role': getattr(request, 'role', None),
        'memberships': memberships,
        'company_count': memberships.count(),
        'is_admin': is_admin,
        'breadcrumbs': get_breadcrumbs(request),
    }

