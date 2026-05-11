# 🔐 PASSWORD RESET - Plan de Implementación

**Proyecto:** Control Horario  
**Característica:** Password Reset por Email  
**Fecha Plan:** 2026-05-11  
**Opción elegida:** Token Generator Built-in (sin cambios en BD)

---

## 📋 Resumen Ejecutivo

Implementación de funcionalidad "Olvidé mi contraseña" que permite a usuarios recuperar acceso sin intervención de admin. Flujo:
1. Usuario solicita reset en página dedicada (solo email)
2. Recibe email con link temporal (24h)
3. Accede a formulario de nueva contraseña
4. Contraseña actualizada, redirige a login

**Complejidad:** Media | **Tiempo estimado:** 2-3 horas | **Tests:** Recomendado

---

## 📁 Archivos Involucrados

### Crear (nuevos)
- `templates/users/forgot_password.html` - Formulario de email
- `templates/users/reset_password.html` - Formulario de nueva contraseña
- `templates/users/reset_password_done.html` - Confirmación (opcional, bonito)
- `templates/emails/password_reset_email.txt` - Template de email (texto)
- `templates/emails/password_reset_email.html` - Template de email (HTML)
- `context/PASSWORD_RESET_TESTS.md` - Plan de testing (crear después)

### Modificar
- `users/views.py` - Agregar 3 vistas nuevas
- `users/forms.py` - Agregar 2 forms nuevos
- `core/urls.py` - Agregar 2 rutas nuevas
- `templates/users/login.html` - Agregar link "¿Olvidaste contraseña?"
- `settings.py` - Verificar/configurar EMAIL_BACKEND si es necesario

---

## 🎯 Bloques de Tareas

### BLOQUE 1: Configuración Email Backend
**Objetivo:** Verificar que SMTP está configurado correctamente

#### Tarea 1.1: Revisar settings.py
- [ ] Localizar configuración EMAIL en `settings.py`
- [ ] Verificar presencia de:
  - `EMAIL_BACKEND` (ej: 'django.core.mail.backends.smtp.EmailBackend')
  - `EMAIL_HOST` (servidor SMTP)
  - `EMAIL_PORT` (puerto, típicamente 587 o 465)
  - `EMAIL_USE_TLS` o `EMAIL_USE_SSL`
  - `EMAIL_HOST_USER` (credenciales)
  - `EMAIL_HOST_PASSWORD` (credenciales)
  - `DEFAULT_FROM_EMAIL` (dirección remitente)
- [ ] Documentar valores actuales para referencia

#### Tarea 1.2: Test rápido de email (OPCIONAL)
- [ ] Crear script de test para verificar envío
- [ ] Ejecutar: `python manage.py shell`
- [ ] Código test:
  ```python
  from django.core.mail import send_mail
  send_mail(
      'Test Subject',
      'Test message',
      'from@example.com',
      ['to@example.com'],
      fail_silently=False,
  )
  ```

---

### BLOQUE 2: Crear Forms
**Objetivo:** Formularios para capturar datos del usuario

#### Tarea 2.1: Form para solicitar reset (ForgotPasswordForm)
**Archivo:** `users/forms.py`  
**Ubicación:** Al final del archivo

```python
class ForgotPasswordForm(forms.Form):
    """Form para solicitar reset de contraseña"""
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu email registrado'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            # No indicamos que no existe (seguridad)
            pass
        return email
```

#### Tarea 2.2: Form para nueva contraseña (ResetPasswordForm)
**Archivo:** `users/forms.py`  
**Ubicación:** Después de ForgotPasswordForm

```python
class ResetPasswordForm(forms.Form):
    """Form para establecer nueva contraseña"""
    new_password = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña (mínimo 8 caracteres)'
        }),
        min_length=8,
        help_text='Mínimo 8 caracteres'
    )
    confirm_password = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirma tu contraseña'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('Las contraseñas no coinciden')
        return cleaned_data
```

---

### BLOQUE 3: Crear Vistas
**Objetivo:** Lógica backend para password reset

#### Tarea 3.1: Actualizar email_utils.py
**Archivo:** `users/email_utils.py`  
**Ubicación:** Agregar al final del archivo

```python
def send_password_reset_email(user, reset_url):
    """Send password reset email to user."""
    try:
        context = {
            'username': user.username,
            'email': user.email.lower(),
            'reset_url': reset_url,
            'current_year': datetime.now().year,
            'styles': _get_email_styles(),
        }

        html_message = render_to_string('emails/password_reset_email.html', context)
        text_message = render_to_string('emails/password_reset_email.txt', context)

        subject = 'Recupera tu contraseña - Aeptic'
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email.lower()],
        )
        email.attach_alternative(html_message, 'text/html')
        email.send(fail_silently=False)
        logger.info(f'Email de reset de contraseña enviado a {user.email.lower()}')

        return True

    except Exception as e:
        logger.error(f'Error enviando email de reset a {user.email.lower()}: {str(e)}')
        return False
```

#### Tarea 3.2: Vista para solicitar reset (forgot_password)
**Archivo:** `users/views.py`  
**Ubicación:** Agregar al final, antes del `return` de otras vistas

```python
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from users.email_utils import send_password_reset_email

def forgot_password(request):
    """
    Vista para solicitar reset de contraseña
    GET: muestra formulario
    POST: envía email con link de reset
    """
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generar token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Construir URL del reset
                reset_url = request.build_absolute_uri(
                    reverse('reset_password', kwargs={'uidb64': uid, 'token': token})
                )
                
                # Enviar email
                send_password_reset_email(user, reset_url)
            except User.DoesNotExist:
                pass  # Por seguridad, no indicamos si existe o no
            
            # Siempre mostrar mensaje de confirmación (aunque no exista)
            messages.success(request, 'Si la cuenta existe, recibirás un email con instrucciones.')
            return redirect('forgot_password')
    else:
        form = ForgotPasswordForm()
    
    return render(request, 'users/forgot_password.html', {'form': form})
```

#### Tarea 3.3: Vista para validar y mostrar formulario de reset
**Archivo:** `users/views.py`

```python
def reset_password(request, uidb64, token):
    """
    Vista para resetear contraseña
    GET: valida token y muestra formulario
    POST: actualiza contraseña
    """
    try:
        # Decodificar UID
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    # Validar token
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data['new_password']
                user.set_password(new_password)
                user.save()
                
                messages.success(request, 'Contraseña actualizada correctamente. Por favor inicia sesión.')
                return redirect('login')
        else:
            form = ResetPasswordForm()
        
        return render(request, 'users/reset_password.html', {'form': form, 'valid_link': True})
    else:
        # Token inválido o expirado
        messages.error(request, 'El link de reset ha expirado o es inválido. Solicita uno nuevo.')
        return redirect('forgot_password')
```

---

### BLOQUE 4: Crear URLs
**Objetivo:** Mapear vistas a rutas

#### Tarea 4.1: Agregar rutas en core/urls.py
**Archivo:** `core/urls.py`  
**Ubicación:** En la sección de URLs de usuarios (buscar donde están login, register, etc.)

```python
# Password Reset
path('forgot-password/', user_views.forgot_password, name='forgot_password'),
path('reset-password/<uidb64>/<token>/', user_views.reset_password, name='reset_password'),
```

---

### BLOQUE 5: Crear Templates HTML
**Objetivo:** Interfaces para el usuario (con estilos consistentes de la app)

#### Tarea 5.1: Template - Página de solicitud (forgot_password.html)
**Archivo:** `templates/users/forgot_password.html`

```html
{% extends 'base.html' %}
{% load django_bootstrap5 static %}

{% block title %}Recuperar Contraseña - Aeptic{% endblock %}

{% block content %}
<div class="container">
    <div class="row justify-content-center mt-5">
        <div class="col-md-5">
            <div class="card shadow-sm">
                <div class="card-header text-center text-white" style="background-color: #1a1f2e;">
                    <h4 class="mb-0">Recuperar Contraseña</h4>
                </div>
                <div class="card-body p-4">
                    
                    {% if messages %}
                        {% for message in messages %}
                            <div class="alert alert-{{ message.tags|default:'info' }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close">×</button>
                            </div>
                        {% endfor %}
                    {% endif %}
                    
                    <p class="text-muted mb-4">
                        Ingresa el email asociado a tu cuenta y recibirás un enlace para resetear tu contraseña.
                    </p>
                    
                    <form method="post">
                        {% csrf_token %}
                        {% bootstrap_form form %}
                        <button type="submit" class="btn w-100" style="background-color: #1a1f2e; color: white;">
                            <i class="fas fa-paper-plane"></i> Enviar Email de Recuperación
                        </button>
                    </form>
                    
                    <div class="text-center mt-3">
                        <small>
                            <a href="{% url 'login' %}" class="text-decoration-none">Volver a Login</a>
                        </small>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### Tarea 5.2: Template - Formulario de nueva contraseña (reset_password.html)
**Archivo:** `templates/users/reset_password.html`

```html
{% extends 'base.html' %}
{% load django_bootstrap5 static %}

{% block title %}Resetear Contraseña - Aeptic{% endblock %}

{% block content %}
<div class="container">
    <div class="row justify-content-center mt-5">
        <div class="col-md-5">
            <div class="card shadow-sm">
                <div class="card-header text-center text-white" style="background-color: #1a1f2e;">
                    <h4 class="mb-0">Establecer Nueva Contraseña</h4>
                </div>
                <div class="card-body p-4">
                    
                    {% if messages %}
                        {% for message in messages %}
                            <div class="alert alert-{{ message.tags|default:'info' }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close">×</button>
                            </div>
                        {% endfor %}
                    {% endif %}
                    
                    {% if valid_link %}
                        <form method="post">
                            {% csrf_token %}
                            {% bootstrap_form form %}
                            <button type="submit" class="btn w-100" style="background-color: #1a1f2e; color: white;">
                                <i class="fas fa-lock"></i> Actualizar Contraseña
                            </button>
                        </form>
                    {% else %}
                        <div class="alert alert-danger" role="alert">
                            <i class="fas fa-exclamation-circle"></i> 
                            El enlace de recuperación es inválido o ha expirado.
                        </div>
                        <a href="{% url 'forgot_password' %}" class="btn w-100" style="background-color: #1a1f2e; color: white;">
                            Solicitar nuevo enlace
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### BLOQUE 6: Crear Templates de Email
**Objetivo:** Contenido del email que recibe el usuario (mismo estilo que otros emails)

#### Tarea 6.1: Email en texto plano (password_reset_email.txt)
**Archivo:** `templates/emails/password_reset_email.txt`

```
Recupera tu Contraseña

Hola {{ username|title }},

Hemos recibido una solicitud para resetear tu contraseña.

Si no fuiste tú, ignora este email. No se realizará ningún cambio en tu cuenta.

Para resetear tu contraseña, haz clic en el siguiente enlace:
{{ reset_url }}

Este enlace es válido por 24 horas. Después de ese tiempo, deberás solicitar un nuevo enlace.

Si tienes problemas con el enlace, copia y pega esta URL en tu navegador:
{{ reset_url }}

---

Saludos,
El equipo de Aeptic

Este correo fue generado automáticamente. Por favor, no responda a este mensaje.
```

#### Tarea 6.2: Email en HTML (password_reset_email.html)
**Archivo:** `templates/emails/password_reset_email.html`

**IMPORTANTE:** Este template usa `{{ styles }}` que se carga automáticamente desde `static/css/email_styles.css`.

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        {{ styles }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header password-reset">
            <h1>Recupera tu Contraseña</h1>
            <p class="header-subtitle">Recibimos una solicitud para resetear tu contraseña</p>
        </div>

        <div class="content">
            <p>Hola <strong>{{ username|title }}</strong>,</p>

            <p>Hemos recibido una solicitud para resetear tu contraseña en tu cuenta.</p>

            <p><strong>Si no fuiste tú, ignora este email.</strong> No se realizará ningún cambio sin tu acción.</p>

            <p>Para continuar, haz clic en el siguiente botón:</p>

            <div class="text-center">
                <a href="{{ reset_url }}" class="action-link password-reset">Resetear Contraseña</a>
            </div>

            <p style="color: var(--email-muted); font-size: 12px; margin-top: 20px;">
                <strong>Este enlace es válido por 24 horas.</strong> Si el botón no funciona, copia este enlace en tu navegador:
            </p>
            <p style="word-break: break-all; background-color: var(--email-primary-soft-2); padding: 10px; border-radius: 4px; font-size: 11px; color: var(--email-text);">
                {{ reset_url }}
            </p>

            <p style="margin-top: 20px; color: var(--email-text);">
                Si tienes problemas o no solicitaste este cambio, contacta con tu administrador.
            </p>
        </div>

        <div class="footer">
            <p>Este correo fue generado automáticamente. Por favor, no responda a este mensaje.</p>
            <p>&copy; {{ current_year }} Aeptic. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>
```

#### Tarea 6.3: Agregar CSS para Password Reset en email_styles.css
**Archivo:** `static/css/email_styles.css`  
**Ubicación:** Al final del archivo, después de `.header-subtitle`

```css
/* Password Reset Email styles */
.header.password-reset {
    border-bottom: 2px solid var(--email-primary);
}

.header.password-reset h1 {
    color: var(--email-primary);
}

.action-link.password-reset {
    display: inline-block;
    background-color: var(--email-primary);
    color: white;
    padding: 12px 30px;
    text-decoration: none;
    border-radius: 4px;
    margin: 20px 0;
    box-shadow: 0 8px 18px rgba(26, 31, 46, 0.16);
}

.action-link.password-reset:hover {
    background-color: var(--email-primary-strong);
}
```

---

### BLOQUE 7: Actualizar Login Template
**Objetivo:** Agregar link "Olvidé mi contraseña" en la página de login

#### Tarea 7.1: Modificar login.html
**Archivo:** `templates/login/login.html`  
**Ubicación:** Buscar el botón de submit/login (búscar línea con `class="std-btn"`) y agregar después

```html
<!-- Buscar línea parecida a: -->
<button type="submit" class="std-btn" style="width: 100%;">
    Iniciar Sesión
</button>

<!-- Agregar después: -->
<div class="text-center mt-3">
    <small>
        <a href="{% url 'forgot_password' %}" class="text-decoration-none" style="color: #6b7280;">
            ¿Has olvidado tu contraseña?
        </a>
    </small>
</div>
```

---

### BLOQUE 8: Importaciones Necesarias
**Objetivo:** Verificar que todos los imports estén presentes

#### Tarea 8.1: Verificar imports en users/views.py
**Archivo:** `users/views.py`

Agregar al inicio del archivo si no existen:
```python
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from users.email_utils import send_password_reset_email
```

#### Tarea 8.2: Verificar imports en users/email_utils.py
**Archivo:** `users/email_utils.py`

Verificar que existen estos imports al inicio del archivo:
```python
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime
import logging
import os
```

#### Tarea 8.3: Verificar imports en users/forms.py
**Archivo:** `users/forms.py`

Verificar que existen estos imports:
```python
from django import forms
from django.contrib.auth import authenticate
```

---

### BLOQUE 9: Testing
**Objetivo:** Validar que todo funciona correctamente

#### Tarea 9.1: Test manual - Flujo completo
- [ ] Ir a `/forgot-password/`
- [ ] Ingresar email de usuario existente
- [ ] Verificar que llega email
- [ ] Hacer click en link del email
- [ ] Verificar que abre formulario de nueva contraseña
- [ ] Ingresar nueva contraseña
- [ ] Verificar que se actualiza en BD
- [ ] Intentar login con nueva contraseña → debe funcionar

#### Tarea 9.2: Test manual - Casos de error
- [ ] Ingresar email NO existente → debe mostrar mensaje genérico
- [ ] Usar link expirado (esperar 24h o modificar token) → debe mostrar error
- [ ] Usar link dos veces → segundo intento debe fallar
- [ ] Contraseñas no coinciden en reset → debe mostrar error
- [ ] Contraseña muy corta (< 8 caracteres) → debe mostrar error

#### Tarea 9.3: Test de email (OPCIONAL)
- [ ] Verificar que email llega a bandeja
- [ ] Verificar que link en email funciona
- [ ] Verificar que formato HTML se ve bien
- [ ] Verificar que remitente es correcto (DEFAULT_FROM_EMAIL)

---

## 🔒 Consideraciones de Seguridad

✅ **Implementado por Django:**
- Tokens únicos y criptográficos
- Tokens con expiración de 24 horas
- Un solo uso por token
- Validación en backend antes de permitir cambio

⚠️ **Responsabilidad tuya:**
- Mantener `SECRET_KEY` en settings.py segura
- Configurar email/SMTP con credenciales válidas
- No exponer URLs en logs públicos
- Monitorear intentos de abuso (múltiples requests)

🚨 **Futuras mejoras (no este sprint):**
- Rate limiting en `/forgot-password/` (evitar spam)
- Auditoría de intentos fallidos
- Notificación al usuario cuando contraseña se cambia
- Invalidar todas las sesiones activas después de reset

---

## 📝 Notas Importantes

- **Token Generator:** Django usa `settings.SECRET_KEY` para generar tokens. Si cambia, todos los tokens anteriores se invalidan.
- **Email Sender:** Usar email recomendado en `DEFAULT_FROM_EMAIL`. Algunos servidores rechazan emails de direcciones no registradas.
- **Zona Horaria:** Django usa UTC internamente. Los 24h de expiración se cuentan desde UTC.
- **Template variables:** En templates de email, `{{ reset_url }}` debe ser ABSOLUTA (incluir dominio), no relativa.

---

## ✅ Checklist Final (Al terminar todo)

- [ ] Todos los bloques completados sin errores
- [ ] Tests manuales pasados
- [ ] Email llega correctamente
- [ ] Link del email funciona
- [ ] Nueva contraseña se actualiza en BD
- [ ] Login funciona con nueva contraseña
- [ ] Casos de error manejan correctamente
- [ ] No hay errores en console/logs
- [ ] Link "Olvidé contraseña" visible en login
- [ ] Documentación actualizada (si aplica)

---

## 📚 Referencias Útiles

- [Django: Password Reset (oficial)](https://docs.djangoproject.com/en/stable/contrib/auth/passwords/)
- [Django: Token Generator](https://docs.djangoproject.com/en/stable/contrib/auth/tokens/)
- [Django: Sending Email](https://docs.djangoproject.com/en/stable/topics/email/)
