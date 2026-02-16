from django import forms
from .models import Company

# ==========================================
# 1. SELECCIÓN DE EMPRESA (VITAL PARA EL LOGIN)
# ==========================================

class CompanySelectionForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.none(), # Se llena dinámicamente abajo
        label="Empresa",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        empty_label="--- Selecciona una opción ---"
    )

    def __init__(self, *args, **kwargs):
        # Extraemos el usuario para mostrar solo SUS empresas
        user = kwargs.pop('user', None)
        super(CompanySelectionForm, self).__init__(*args, **kwargs)
        
        if user:
            # Filtramos: Solo empresas activas donde el usuario es miembro
            # Si da error 'User object has no attribute companies', usa Company.objects.filter(users=user)
            self.fields['company'].queryset = Company.objects.filter(users=user, active=True)

# ==========================================
# 2. CREACIÓN DE EMPRESA (VITAL)
# ==========================================

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'active'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Empresa'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }