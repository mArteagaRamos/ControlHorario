from django import template

register = template.Library()

ROLE_TRANSLATIONS = {
    'manager': 'Gerente',
    'employee': 'Empleado',
}


@register.filter
def translate_role(role):
    """Translate role to Spanish"""
    if not role:
        return ''
    return ROLE_TRANSLATIONS.get(role, role)
