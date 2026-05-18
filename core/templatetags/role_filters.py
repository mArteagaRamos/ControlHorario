from django import template

register = template.Library()

ROLE_TRANSLATIONS = {
    'manager': 'Gerente',
    'employee': 'Empleado',
}

MONTH_TRANSLATIONS = {
    'January': 'enero', 'February': 'febrero', 'March': 'marzo',
    'April': 'abril', 'May': 'mayo', 'June': 'junio',
    'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
    'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
}


@register.filter
def translate_role(role):
    """Translate role to Spanish"""
    if not role:
        return ''
    return ROLE_TRANSLATIONS.get(role, role)


@register.filter
def spanish_date(date_obj, format_str="d M Y"):
    """Format date with Spanish month names"""
    if not date_obj:
        return ''
    from django.template.defaultfilters import date as date_filter
    formatted = date_filter(date_obj, format_str)
    for en, es in MONTH_TRANSLATIONS.items():
        formatted = formatted.replace(en, es)
    return formatted
