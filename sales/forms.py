# sales/forms.py
from django import forms
from .models import Invoice
from core.models import BusinessPartner
from .models import Invoice, Payment

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'number', 'date', 'due_date', 'total']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FAC-001'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            # CORRECCIÓN: Filtramos por partner_type='CLIENTE' (o como lo tengas en tu modelo)
            # También filtramos por la empresa activa
            self.fields['customer'].queryset = BusinessPartner.objects.filter(
                company=company, 
                partner_type__icontains='CLIENT' # Busca 'CLIENTE' o 'Customer' de forma flexible
            )

# sales/forms.py
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['invoice', 'date', 'amount', 'method']
        widgets = {
            'invoice': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'method': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Efectivo, Cheque, Transferencia'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            # Solo mostramos facturas abiertas de esta empresa
            self.fields['invoice'].queryset = Invoice.objects.filter(
                company=company, 
                status='OPEN'
            )