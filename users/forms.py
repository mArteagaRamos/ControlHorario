from django import forms
from users.models import Users, Companies
from django.contrib.auth.forms import AuthenticationForm

class FormRegister(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['username', 'surname', 'email', 'status', 'is_admin', 'password']
        labels = {
            'username': 'Nombre',
            'surname': 'Apellidos',
            'email': 'Correo electrónico',
            'status': 'Estado',
            'is_admin': '',
            'password': 'Contraseña',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_admin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_admin = False
        if commit:
            user.save()
        return user

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Companies
        fields = ['name', 'legal_name', 'tax_id',]
        labels = {
            'name': 'Nombre de la empresa',
            'legal_name': 'Razón social',
            'tax_id': 'CIF/NIF',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'legal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ManagerSelectForm(forms.Form):
    manager_email = forms.EmailField(
        label='Email del manager existente',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'manager@ejemplo.com'})
    )

class ManagerCreateForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['username', 'surname', 'email', 'status', 'password']
        labels = {
            'username': 'Nombre',
            'surname': 'Apellidos',
            'email': 'Correo electrónico',
            'status': 'Estado',
            'password': 'Contraseña',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required for HTML5 validation when hidden
        for field in self.fields.values():
            field.required = False

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@email.com'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '********'
        })
    )