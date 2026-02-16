from django import forms
from django.contrib.auth.forms import UserCreationForm
# Usamos get_user_model para evitar errores si cambia la ubicación del modelo User
from django.contrib.auth import get_user_model 
from .models import (
    Company, Branch, Warehouse, Product, 
    Client, Supplier, UserProfile
)

User = get_user_model()

# ==========================================
# 1. SELECCIÓN DE EMPRESA (CORREGIDO)
# ==========================================

class CompanySelectionForm(forms.Form):  # <--- Renombrado para coincidir con views.py
    company = forms.ModelChoiceField(
        queryset=Company.objects.none(), # Se llena dinámicamente abajo
        label="Seleccionar Empresa",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        empty_label="--- Selecciona una opción ---"
    )

    def __init__(self, *args, **kwargs):
        # Extraemos el usuario para mostrar solo SUS empresas
        user = kwargs.pop('user', None)
        super(CompanySelectionForm, self).__init__(*args, **kwargs)
        
        if user:
            # Filtramos: Solo empresas activas donde el usuario es miembro
            self.fields['company'].queryset = user.companies.filter(active=True)

# ==========================================
# 2. USUARIOS Y PERFILES
# ==========================================

class CustomUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email'] # Quitamos avatar si User no lo tiene nativo
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

# ==========================================
# 3. EMPRESAS Y SUCURSALES
# ==========================================

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'active'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Empresa'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'code', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'branch', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# ==========================================
# 4. TERCEROS (CLIENTES Y PROVEEDORES)
# ==========================================

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'nit', 'phone', 'email', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'nit', 'contact_name', 'phone', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms
        }