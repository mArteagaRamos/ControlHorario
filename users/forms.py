from django import forms
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