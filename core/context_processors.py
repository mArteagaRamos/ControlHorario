# core/context_processors.py

from users.models import UserCompany, Companies


def global_context(request):
    """Agregar variables globales a todos los templates"""
    context = {
        'is_admin': request.user.is_admin if request.user.is_authenticated else False,
        'current_role': getattr(request, 'role', None),
        'is_aeptic_user': False,
    }

    # Verificar si el usuario pertenece a AePTIC Y la tiene seleccionada
    if request.user.is_authenticated:
        aeptic_company = Companies.objects.filter(
            tax_id='B90143645'
        ).first()

        if aeptic_company:
            # Verificar que pertenece a la empresa
            membership = UserCompany.objects.filter(
                user=request.user,
                company=aeptic_company,
                deleted_at__isnull=True
            ).exists()

            # Verificar que la empresa está seleccionada en la sesión
            selected_company_id = request.session.get('company_id')
            is_aeptic_selected = selected_company_id and str(aeptic_company.id) == str(selected_company_id)

            context['is_aeptic_user'] = membership and is_aeptic_selected

    return context
