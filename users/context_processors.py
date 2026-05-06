# Context processor to add current company and breadcrumbs to templates


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
}


def get_breadcrumbs(request):
    """Generate breadcrumbs from navigation history"""
    if not request.user.is_authenticated:
        return []

    history = request.session.get('nav_history', [])

    if not history:
        return []

    breadcrumbs = []

    # Add all pages from history
    for page in history:
        label = BREADCRUMB_LABELS.get(page['name'], page['name'].replace('_', ' ').title())
        breadcrumbs.append({
            'label': label,
            'url': page['path'],
        })

    # Make the last item (current page) non-clickable
    if breadcrumbs:
        breadcrumbs[-1]['url'] = None

    return breadcrumbs


def user_company(request):
    from .models import UserCompany

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

