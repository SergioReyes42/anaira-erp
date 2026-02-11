from django import forms
from .models import Expense, BankAccount, BankTransaction, Vehicle

# --- GASTOS ---
class ExpensePhotoForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['photo', 'vehicle', 'description', 'total_amount'] # Agregamos 'vehicle'
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control', 'capture': 'camera'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej: Gasolina, Almuerzo...'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
        }

# --- NUEVO: VEHÍCULOS ---
class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['brand', 'model', 'plate', 'year', 'driver_name']
        widgets = {
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'plate': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

# --- BANCOS ---
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'currency', 'balance']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankTransaction
        fields = ['bank_account', 'date', 'amount', 'reference', 'description']
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }