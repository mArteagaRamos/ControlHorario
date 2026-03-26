# ---------- Backend Forms: users/forms.py ----------

import secrets
import string

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from users.models import Users, Companies, UserCompany


# ── Helper: generador de contraseña temporal ──────────────────────────────────

def generate_temp_password(length=12):
    """Genera una contraseña temporal aleatoria segura."""
    upper     = string.ascii_uppercase
    lower     = string.ascii_lowercase
    digits    = string.digits
    special   = '!@#$%&*?'
    all_chars = upper + lower + digits + special

    # Garantizamos al menos uno de cada tipo
    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]
    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)


# ── Base form de usuario ───────────────────────────────────────────────────────

class _UserBaseForm(forms.ModelForm):
    """
    Base reutilizable para todos los forms de usuario.

    CAMBIO CLAVE: el widget de 'password' es TextInput (no PasswordInput).
    PasswordInput tiene render_value=False por defecto, lo que hace que Django
    descarte el valor en el POST y llegue vacío a cleaned_data. Como la
    contraseña temporal es visible en el formulario de todas formas, usar
    TextInput es correcto y resuelve el problema de validación.

    El campo es readonly en el template; el valor lo genera el JS del frontend.
    """

    role = forms.ChoiceField(
        label='Rol',
        choices=[
            (UserCompany.RoleChoices.EMPLOYEE, 'Empleado'),
            (UserCompany.RoleChoices.MANAGER,  'Manager'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
    )

    class Meta:
        model  = Users
        fields = ['username', 'surname', 'email', 'status', 'password']
        labels = {
            'username': 'Nombre',
            'surname':  'Apellidos',
            'email':    'Correo electrónico',
            'status':   'Estado',
            'password': 'Contraseña temporal',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'surname':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':    forms.EmailInput(attrs={'class': 'form-control'}),
            'status':   forms.Select(attrs={'class': 'form-control'}),
            # TextInput en lugar de PasswordInput: evita que Django descarte
            # el valor del campo al procesar el POST.
            'password': forms.TextInput(attrs={
                'class':    'form-control font-monospace',
                'readonly': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def save(self, commit=True):
        user     = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        user.is_admin = False
        if commit:
            user.save()
        return user


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class':       'form-control',
            'placeholder': 'ejemplo@email.com',
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': '********',
        })
    )


# ── Login con selección de empresa ────────────────────────────────────────────

class CompanySelectLoginForm(forms.Form):
    company_id = forms.ChoiceField(
        label='Selecciona empresa',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    def __init__(self, *args, companies=None, **kwargs):
        super().__init__(*args, **kwargs)
        if companies:
            self.fields['company_id'].choices = [
                (str(m.company.id), m.company.name) for m in companies
            ]


# ── Empresa ───────────────────────────────────────────────────────────────────

class CompanyForm(forms.ModelForm):
    class Meta:
        model  = Companies
        fields = ['name', 'legal_name', 'tax_id']
        labels = {
            'name':       'Nombre de la empresa',
            'legal_name': 'Razón social',
            'tax_id':     'CIF / NIF',
        }
        widgets = {
            'name':       forms.TextInput(attrs={'class': 'form-control'}),
            'legal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id':     forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False


# ── Trabajador ────────────────────────────────────────────────────────────────

class WorkerCreateForm(_UserBaseForm):
    """
    Crea un nuevo usuario.
    La contraseña temporal (generada en el frontend) llega en 'password',
    se hashea con set_password() y se guarda en users.password_hash.
    La vista pone flag=False para forzar el cambio en el primer login.
    """
    pass


class WorkerSelectForm(_UserBaseForm):
    """
    Edita un usuario existente localizado por email.
    El campo 'password' es meramente visual: la vista NO llama a
    set_password ni modifica flag para usuarios ya existentes en la db.
    """
    pass


# ── Primer login: establecer contraseña definitiva ────────────────────────────

class SetPasswordForm(forms.Form):
    """
    Se muestra al usuario en su primer login (flag=False).
    Obliga a establecer una contraseña definitiva con requisitos de complejidad.
    """
    new_password = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class':        'form-control',
            'autocomplete': 'new-password',
            'placeholder':  'Mínimo 8 caracteres',
        }),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class':        'form-control',
            'autocomplete': 'new-password',
        }),
    )

    def clean(self):
        cleaned_data     = super().clean()
        new_password     = cleaned_data.get('new_password', '')
        confirm_password = cleaned_data.get('confirm_password', '')

        if new_password != confirm_password:
            self.add_error('confirm_password', 'Las contraseñas no coinciden.')

        if new_password:
            has_upper = any(c.isupper() for c in new_password)
            has_lower = any(c.islower() for c in new_password)
            has_digit = any(c.isdigit() for c in new_password)
            if not (has_upper and has_lower and has_digit):
                self.add_error(
                    'new_password',
                    'La contraseña debe contener mayúsculas, minúsculas y números.',
                )
        return cleaned_data