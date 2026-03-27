from .models import UserCompany, Companies

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
            'lookup_company', 'lookup_user', 'switch_company', 'logout',
            'exportar_logs', 'resolver_incidencia', 'editar_registro',
            'anular_registro', 'edit_employee', 'delete_employee'
        }

    def __call__(self, request):
        if request.user.is_authenticated and request.resolver_match:
            url_name = request.resolver_match.url_name

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
                    if page['path'] == current_page['path']:
                        found_current = True
                        break
                    new_history.append(page)

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

        return self.get_response(request)
