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
class PilotExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['total_amount', 'vehicle', 'description', 'receipt_image', 'pump_image', 'latitude', 'longitude']
        widgets = {
            'total_amount': forms.NumberInput(attrs={'class': 'form-control form-control-lg fw-bold text-success', 'step': '0.01', 'placeholder': 'Ej. 300.00'}),
            'vehicle': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej. Gasolina para viaje a Escuintla...'}),
            
            # El atributo 'capture': 'environment' obliga al celular a usar la cámara trasera
            'receipt_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment', 'id': 'foto_factura'}),
            'pump_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'capture': 'environment', 'id': 'foto_bomba'}),
            
            'latitude': forms.HiddenInput(attrs={'id': 'lat_input'}),
            'longitude': forms.HiddenInput(attrs={'id': 'lng_input'}),
        }