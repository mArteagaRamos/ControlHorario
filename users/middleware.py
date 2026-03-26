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

            # 1. Si hay empresa en sesión
            if company_id:
                membership = UserCompany.objects.filter(
                    user=request.user,
                    company_id=company_id
                ).select_related('company').first()

            # 2. Fallback → primera empresa válida
            if not membership:
                membership = UserCompany.objects.filter(
                    user=request.user
                ).select_related('company').first()

                if membership:
                    request.session['company_id'] = str(membership.company.id)

            # 3. Asignar al request
            if membership:
                request.company = membership.company
                request.role = membership.role

        return self.get_response(request)
