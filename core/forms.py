from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Company

# --- FORMULARIO DE USUARIO (REGISTRO) ---
class CustomUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

# --- PERFIL DE USUARIO ---
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'phone', 'position']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
        }

# --- SELECCIÓN DE EMPRESA ---
class CompanySelectForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label="Seleccionar Empresa",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

# --- NUEVO: GESTIÓN DE EMPRESAS ---
class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'tax_id', 'address', 'logo', 'website', 'email', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Anaira S.A.'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT o RUC'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }