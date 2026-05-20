# ---------- Email Utilities: users/email_utils.py ----------

from django.core.mail import EmailMultiAlternatives
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
    """Send welcome email to newly created user with temporary password."""
    try:
        context = {
            'username': user.username.title(),
            'email': user.email.lower(),
            'password': password,
            'company_name': company.name.title(),
            'login_url': _get_login_url(),
            'current_year': datetime.now().year,
            'styles': _get_email_styles(),
        }

        html_message = render_to_string('emails/new_user_email.html', context)
        text_message = strip_tags(html_message)

        subject = f'Bienvenido a {company.name.title()} - Credenciales de acceso'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email.lower()],
        )
        email.attach_alternative(html_message, 'text/html')
        email.send(fail_silently=True)
        logger.info(f'Nuevo usuario email enviado a {user.email.lower()}')

    except Exception as e:
        logger.error(f'Error enviando email a {user.email.lower()}: {str(e)}')
        return False

    return True


def send_new_auditor_email(user, password):
    """Send welcome email to newly created auditor with temporary password."""
    try:
        context = {
            'username': user.username.title(),
            'email': user.email.lower(),
            'password': password,
            'login_url': _get_login_url(),
            'current_year': datetime.now().year,
            'styles': _get_email_styles(),
        }

        html_message = render_to_string('emails/new_auditor_email.html', context)
        text_message = strip_tags(html_message)

        subject = 'Bienvenido a la plataforma Aeptic - Credenciales de acceso (Auditor)'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email.lower()],
        )
        email.attach_alternative(html_message, 'text/html')
        email.send(fail_silently=True)
        logger.info(f'Email de nuevo auditor enviado a {user.email.lower()}')

    except Exception as e:
        logger.error(f'Error enviando email a auditor {user.email.lower()}: {str(e)}')
        return False

    return True


def send_existing_user_email(user, company, role):
    """Send notification email to existing user who was added to a new company."""
    try:
        role_display = _get_role_display(role)
        user_email = user.email.lower()

        context = {
            'username': user.username,
            'email': user_email,
            'company_name': company.name,
            'role_display': role_display,
            'login_url': _get_login_url(),
            'current_year': datetime.now().year,
            'styles': _get_email_styles(),
        }

        html_message = render_to_string('emails/existing_user_email.html', context)
        text_message = strip_tags(html_message)

        subject = f'Se te ha añadido acceso a {company.name.title()}'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        email.attach_alternative(html_message, 'text/html')
        email.send(fail_silently=True)
        logger.info(f'Email de usuario existente enviado a {user_email}')

        return True

    except Exception as e:
        logger.exception(f'Error enviando email: {str(e)}')
        return False


def _get_login_url():
    """Get the login URL for the application."""
    return 'https://127.0.0.1:8000/login/'


def _get_role_display(role):
    """Convert role code to display name."""
    role_map = {
        'employee': 'empleado',
        'manager': 'manager',
    }
    role_key = str(role).lower()
    return role_map.get(role_key, role)


def send_password_reset_email(user, reset_url):
    """Send password reset email to user."""
    try:
        logger.info(f'=== INICIANDO ENVÍO DE PASSWORD RESET ===')
        logger.info(f'EMAIL_HOST: {settings.EMAIL_HOST}')
        logger.info(f'EMAIL_PORT: {settings.EMAIL_PORT}')
        logger.info(f'EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        logger.info(f'EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}')
        logger.info(f'EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}')
        logger.info(f'Usuario destinatario: {user.email.lower()}')

        context = {
            'username': user.username,
            'email': user.email.lower(),
            'reset_url': reset_url,
            'current_year': datetime.now().year,
            'styles': _get_email_styles(),
        }

        html_message = render_to_string('emails/password_reset_email.html', context)
        text_message = strip_tags(html_message)

        subject = 'Recupera tu contraseña - Aeptic'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email.lower()],
        )
        email.attach_alternative(html_message, 'text/html')
        logger.info(f'Email creado. Intentando enviar...')
        email.send(fail_silently=False)
        logger.info(f'✅ Email de reset de contraseña enviado a {user.email.lower()}')

        return True

    except Exception as e:
        logger.error(f'❌ Error enviando email de reset a {user.email.lower()}: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return False

