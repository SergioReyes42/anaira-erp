from django import forms
from .models import Quotation, Sale
from core.models import Client

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['client', 'valid_until', 'notes']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['client', 'payment_method']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }