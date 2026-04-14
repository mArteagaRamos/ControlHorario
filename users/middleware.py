from django.urls import resolve
from .models import UserCompany, Companies, Users
from datetime import date
from django.utils import timezone

class CompanyMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.company = None
        request.role = None

        if request.user.is_authenticated:

            company_id = request.session.get('company_id')

            membership = None

            # 1. If there is a company in session
            if company_id:
                membership = UserCompany.objects.filter(
                    user=request.user,
                    company_id=company_id
                ).select_related('company').first()

            # 2. Fallback -> first valid company
            if not membership:
                membership = UserCompany.objects.filter(
                    user=request.user
                ).select_related('company').first()

                if membership:
                    request.session['company_id'] = str(membership.company.id)

            # 3. Assign to request
            if membership:
                request.company = membership.company
                request.role = membership.role

        return self.get_response(request)


class NavigationHistoryMiddleware:
    """Middleware to track user's navigation history for breadcrumbs"""

    def __init__(self, get_response):
        self.get_response = get_response
        # Pages that should not be added to history (modals, API calls, etc)
        self.excluded_names = {
            'login', 'lookup_company', 'lookup_user', 'switch_company', 'logout',
            'exportar_logs', 'resolver_incidencia', 'editar_registro',
            'anular_registro', 'edit_employee', 'delete_employee'
        }

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Manually resolve the URL to get the url name
                from django.urls import resolve
                match = resolve(request.path)
                url_name = match.url_name

                # Skip excluded pages
                if url_name not in self.excluded_names:
                    # Initialize history if not exists
                    if 'nav_history' not in request.session:
                        request.session['nav_history'] = []

                    history = request.session['nav_history']

                    # Get current page info
                    current_page = {
                        'name': url_name,
                        'path': request.path,
                    }

                    # Remove pages after current if we're going back in history
                    new_history = []
                    found_current = False
                    for page in history:
                        new_history.append(page)
                        if page['path'] == current_page['path']:
                            found_current = True
                            break

                    if found_current:
                        # Going back to a previous page
                        history[:] = new_history
                    else:
                        # New page being visited
                        history.append(current_page)

                    # Limit history to prevent session bloat (max 20 pages)
                    if len(history) > 20:
                        history.pop(0)

                    request.session.modified = True
            except Exception:
                # If resolution fails, just continue without adding to history
                pass

        return self.get_response(request)


class InactiveUserVerificationMiddleware:
    """
    Middleware para verificar y revertir automáticamente el status de usuarios inactivos
    cuyas vacaciones/ausencias han expirado (verificación Lazy).

    Se ejecuta en cada request si el usuario está autenticado e inactivo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Obtener el usuario Django y verificar si está inactivo
                django_user = request.user
                user = Users.objects.filter(email=django_user.email).first()

                if user and user.status == Users.StatusChoices.INACTIVE:
                    # Verificar si hay leaves aprobadas activas (end_date >= hoy)
                    from dashboard.models import LeaveRequest
                    today = date.today()

                    # Buscar si tiene alguna leave aprobada vigente
                    active_leave = LeaveRequest.objects.filter(
                        user=user,
                        status=LeaveRequest.LeaveStatus.APPROVED,
                        end_date__gte=today
                    ).exists()

                    # Si NO hay leaves aprobadas activas, revertir a 'active'
                    if not active_leave:
                        Users.objects.filter(id=user.id).update(
                            status=Users.StatusChoices.ACTIVE
                        )

            except Exception:
                # Si algo falla, simplemente continuar sin romper el request
                pass

        return self.get_response(request)
