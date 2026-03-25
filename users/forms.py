from django import forms
import secrets
import string
from django.contrib.auth.forms import AuthenticationForm
from users.models import Users, Companies, UserCompanyMembership


# ── Helper: campos comunes de usuario ─────────────────────────────────────────

class _UserBaseForm(forms.ModelForm):
    """
    Base reutilizable para todos los forms de usuario.
    - Centraliza widgets, labels y set_password.
    - required=False en todos los fields para no bloquear
      el submit cuando el bloque está oculto.
    - set_password solo se ejecuta si se ha introducido contraseña,
      lo que permite editar un usuario existente sin resetearla.
    """

    confirm_password = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'autocomplete': 'new-password'},
            render_value=False,
        ),
        required=False,
    )

    role = forms.ChoiceField(
        label='Rol',
        choices=[
            (UserCompanyMembership.RoleChoices.EMPLOYEE, 'Empleado'),
            (UserCompanyMembership.RoleChoices.MANAGER,  'Manager'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
    )

    class Meta:
        model = Users
        fields = ['username', 'surname', 'email', 'status', 'password']
        labels = {
            'username': 'Nombre',
            'surname':  'Apellidos',
            'email':    'Correo electrónico',
            'status':   'Estado',
            'password': 'Contraseña',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'surname':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':    forms.EmailInput(attrs={'class': 'form-control'}),
            'status':   forms.Select(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(
                attrs={'class': 'form-control', 'autocomplete': 'new-password'},
                render_value=False,
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # Solo validamos si se ha introducido alguna contraseña
        if password or confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', 'Las contraseñas no coinciden.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            # Solo actualiza el hash si se introdujo una nueva contraseña
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
        model = Companies
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
    """Crea un nuevo usuario con el rol elegido."""
    pass


class WorkerSelectForm(_UserBaseForm):
    """
    Carga y edita un usuario existente localizado por email.
    La contraseña es opcional: si se deja vacía no se modifica.
    """
    pass

# ── Primer login: establecer contraseña ───────────────────────────────────────
def generate_temp_password(length=12):
    """Genera una contraseña temporal aleatoria segura."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class SetPasswordForm(forms.Form):
    """
    Formulario que aparece en el primer login (flag=False).
    Obliga al usuario a establecer una contraseña definitiva.
    """
    new_password = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Mínimo 8 caracteres',
        }),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password', '')
        p2 = cleaned_data.get('confirm_password', '')

        if p1 != p2:
            self.add_error('confirm_password', 'Las contraseñas no coinciden.')

        # Validación de complejidad
        if p1:
            has_upper  = any(c.isupper() for c in p1)
            has_lower  = any(c.islower() for c in p1)
            has_digit  = any(c.isdigit() for c in p1)
            if not (has_upper and has_lower and has_digit):
                self.add_error(
                    'new_password',
                    'La contraseña debe contener mayúsculas, minúsculas y números.'
                )
        return cleaned_data