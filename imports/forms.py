from django import forms
from django.forms import inlineformset_factory
from .models import Duca, DucaItem

class DucaForm(forms.ModelForm):
    class Meta:
        model = Duca
        fields = ['duca_number', 'date_acceptance', 'supplier_name', 'customs_agent', 
                  'exchange_rate', 'freight_usd', 'insurance_usd', 'iva_gtq', 'other_expenses_gtq', 'status']
        widgets = {
            'date_acceptance': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le aplicamos diseño Bootstrap a todos los campos automáticamente
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

# Esto permite agregar múltiples productos a una sola póliza (como una factura)
DucaItemFormSet = inlineformset_factory(
    Duca, DucaItem,
    fields=['product_code', 'description', 'quantity', 'fob_unit_usd', 'dai_rate'],
    extra=1, # Muestra 1 fila vacía por defecto
    can_delete=True,
    widgets={
        'product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU'}),
        'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        'fob_unit_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        'dai_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    }
)