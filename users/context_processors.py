# Context processor to add current company to templates
from .models import UserCompanyMembership

def user_company(request):
    memberships = UserCompanyMembership.objects.none()  

    if request.user.is_authenticated:
        memberships = UserCompanyMembership.objects.filter(user=request.user).select_related('company')

    return {
        'current_company': getattr(request, 'company', None),
        'current_role': getattr(request, 'role', None),
        'memberships': memberships,
        'company_count': memberships.count(),
    }

