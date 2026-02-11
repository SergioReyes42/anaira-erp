from django import forms
from .models import Expense, BankAccount, BankTransaction

# --- GASTOS ---
class ExpensePhotoForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['photo', 'description', 'total_amount']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control', 'capture': 'camera'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej: Gasolina, Almuerzo...'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
        }

# --- NUEVO: BANCOS ---
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'currency', 'balance']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Banco Industrial'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GTQ'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Saldo Inicial'}),
        }

class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankTransaction
        fields = ['bank_account', 'date', 'amount', 'reference', 'description'] # El tipo se maneja en la vista
        widgets = {
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }