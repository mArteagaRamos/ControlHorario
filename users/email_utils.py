# ---------- Email Utilities: users/email_utils.py ----------

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def send_new_user_email(user, password, company):
    """
    Send welcome email to newly created user with temporary password.

    Args:
        user: Users instance
        password: Temporary password string
        company: Companies instance
    """
    try:
        context = {
            'username': user.username,
            'email': user.email,
            'password': password,
            'company_name': company.name,
            'login_url': _get_login_url(),
            'current_year': datetime.now().year,
        }

        # Render HTML email
        html_message = render_to_string('emails/new_user_email.html', context)
        text_message = strip_tags(html_message)

        # Create email
        subject = f'Bienvenido a {company.name} - Credenciales de acceso'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_message, 'text/html')

        # Send email
        email.send(fail_silently=False)
        logger.info(f'Nuevo usuario email enviado a {user.email}')

    except Exception as e:
        logger.error(f'Error enviando email a {user.email}: {str(e)}')
        # Decide if you want to re-raise or silently fail
        # For now, we'll log but not raise to allow registration to complete
        return False

    return True


def send_existing_user_email(user, company, role):
    """
    Send notification email to existing user who was added to a new company.

    Args:
        user: Users instance
        company: Companies instance
        role: Role string (e.g., 'EMPLOYEE', 'MANAGER')
    """
    try:
        role_display = _get_role_display(role)

        context = {
            'username': user.username,
            'email': user.email,
            'company_name': company.name,
            'role': role_display,
            'login_url': _get_login_url(),
            'current_year': datetime.now().year,
        }

        # Render HTML email
        html_message = render_to_string('emails/existing_user_email.html', context)
        text_message = strip_tags(html_message)

        # Create email
        subject = f'Se te ha añadido acceso a {company.name}'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_message, 'text/html')

        # Send email
        email.send(fail_silently=False)
        logger.info(f'Email de usuario existente enviado a {user.email}')

    except Exception as e:
        logger.error(f'Error enviando email a {user.email}: {str(e)}')
        return False

    return True


def _get_login_url():
    """Get the login URL for the application."""
    # Modify this based on your actual domain/URL configuration
    return 'https://yourapp.com/login/'


def _get_role_display(role):
    """Convert role code to display name."""
    role_map = {
        'EMPLOYEE': 'Empleado',
        'MANAGER': 'Manager',
        'ADMIN': 'Administrador',
    }
    return role_map.get(role, role)
