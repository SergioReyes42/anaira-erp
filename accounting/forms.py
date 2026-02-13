from django import forms
from .models import Expense, Vehicle, BankAccount, BankTransaction

# --- GASTOS ---
class ExpensePhotoForm(forms.ModelForm):
    """Formulario auxiliar para la vista de gastos (aunque lo manejemos manual en la vista)"""
    class Meta:
        model = Expense
        fields = ['receipt_image', 'description', 'total_amount']

# --- FLOTILLA ---
class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['brand', 'line', 'plate', 'driver_name'] # Ajusta según tus campos exactos del modelo
        widgets = {
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca (Ej: Toyota)'}),
            'line': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Línea (Ej: Hilux)'}),
            'plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Placa (Ej: C-123BBB)'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Piloto Responsable'}),
        }

# --- BANCOS ---
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'currency', 'balance']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Banco'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Cuenta'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Saldo Inicial'}),
        }

class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankTransaction
        fields = ['bank_account', 'amount', 'description', 'reference']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Monto Q/$.'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Concepto'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'No. Boleta / Cheque'}),
        }