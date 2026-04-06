# ---------- Email Utilities: users/email_utils.py ----------

from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


def _get_email_styles():
    """Load email styles from static CSS file."""
    css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'email_styles.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f'Email CSS file not found at {css_path}')
        return ''


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
            'styles': _get_email_styles(),
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
        email.send(fail_silently=True)
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
            'styles': _get_email_styles(),
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
        email.send(fail_silently=True)
        logger.info(f'Email de usuario existente enviado a {user.email}')

    except Exception as e:
        logger.error(f'Error enviando email a {user.email}: {str(e)}')
        return False

    return True


def _get_login_url():
    """Get the login URL for the application."""
    return 'https://127.0.0.1:8000/login/'


def _get_role_display(role):
    """Convert role code to display name."""
    role_map = {
        'EMPLOYEE': 'Empleado',
        'MANAGER': 'Manager',
    }
    return role_map.get(role, role)
