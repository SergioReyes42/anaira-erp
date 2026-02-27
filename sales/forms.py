from django import forms
from .models import Quotation, Client

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['client', 'warehouse', 'valid_until', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'valid_until': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'nit', 'phone', 'email', 'address', 'client_type', 'credit_limit', 'is_blacklisted', 'blacklist_reason']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control fw-bold', 'placeholder': 'Razón Social o Nombre Completo'}),
            'nit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 123456-7'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono principal'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@empresa.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dirección de facturación o entrega'}),
            
            # Campos CRM y Libro Negro
            'client_type': forms.Select(attrs={'class': 'form-select'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control text-success fw-bold', 'step': '0.01'}),
            'is_blacklisted': forms.CheckboxInput(attrs={'class': 'form-check-input bg-danger border-danger', 'style': 'transform: scale(1.5); margin-left: 0;'}),
            'blacklist_reason': forms.Textarea(attrs={'class': 'form-control border-danger', 'rows': 2, 'placeholder': 'Ej: Cliente tiene facturas vencidas de hace 90 días...'}),
        }