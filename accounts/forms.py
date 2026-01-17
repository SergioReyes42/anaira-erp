
# accounts/forms.py
from django import forms

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Usuario"})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"})
    )
    remember_me = forms.BooleanField(
        label="Recordarme",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )
    # Opcional para TOTP si activas 2FA más adelante
    totp_code = forms.CharField(
        label="Código 2FA",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "123456"})
    )
    def clean(self):
        cleaned_data = super().clean()
        # Aquí puedes agregar validaciones adicionales si es necesario
        return cleaned_data
# FIN accounts/forms.py
