from django import forms
from .models import Product
from .models import (
    Company, BankAccount, BankMovement, Income, Gasto,
    BusinessPartner, Product, Employee, Loan, Fleet, BankTransaction
)

# --- 1. SELECCIÓN DE EMPRESA ---
class CompanySelectForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label="Seleccione una Empresa",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

# --- 2. BANCOS Y TESORERÍA ---
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'currency', 'balance']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'balance': forms.NumberInput(attrs={'class': 'form-select', 'step': '0.01'}), # Corregí un pequeño typo en widget
        }
        labels = {
            'bank_name': 'Nombre del Banco',
            'account_number': 'Número de Cuenta',
            'currency': 'Moneda',
            'balance': 'Saldo Inicial',
        }

class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankTransaction
        # 1. CAMBIAMOS EL NOMBRE EN LA LISTA:
        fields = ['account', 'date', 'reference', 'description', 'amount', 'movement_type']
        
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            # 2. CAMBIAMOS EL NOMBRE AQUÍ TAMBIÉN:
            'movement_type': forms.HiddenInput(),
        }

class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=None, label="Cuenta Origen", widget=forms.Select(attrs={'class': 'form-select'}))
    to_account = forms.ModelChoiceField(queryset=None, label="Cuenta Destino", widget=forms.Select(attrs={'class': 'form-select'}))
    amount = forms.DecimalField(label="Monto a Transferir", max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    date = forms.DateField(label="Fecha", widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    reference = forms.CharField(required=False, label="Referencia", widget=forms.TextInput(attrs={'class': 'form-control'}))
    evidence = forms.ImageField(required=False, label="Comprobante", widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['from_account'].queryset = BankAccount.objects.filter(company=company)
        self.fields['to_account'].queryset = BankAccount.objects.filter(company=company)

# --- 3. GASTOS E INGRESOS ---
class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        # Agregamos 'amount_untaxed', 'iva' y 'vehicle'
        fields = ['fecha', 'proveedor', 'descripcion', 'total', 'amount_untaxed', 'iva', 'categoria', 'bank_account', 'vehicle', 'imagen']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'inputTotal', 'oninput': 'calcularIVA()'}), # OJO AL ID
            
            # Estos serán de solo lectura (readonly) porque se calculan solos
            'amount_untaxed': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'inputBase'}),
            'iva': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'inputIVA'}),
            
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}), # Lista de vehículos
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    # Agregamos esto para filtrar solo vehículos de la empresa
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Verificamos si existe el modelo Fleet antes de filtrar
        try:
            from .models import Fleet
            self.fields['vehicle'].queryset = Fleet.objects.all()
        except ImportError:
            pass

class MobileExpenseForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['total', 'imagen', 'descripcion'] 
        widgets = {
            'total': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Q 0.00'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '¿Qué compraste?'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['date', 'description', 'amount', 'bank_account', 'reference_doc', 'evidence']
        labels = {
            'date': 'Fecha', 'description': 'Descripción / Cliente', 'amount': 'Monto',
            'bank_account': 'Cuenta Destino', 'reference_doc': 'No. Documento', 'evidence': 'Comprobante'
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'reference_doc': forms.TextInput(attrs={'class': 'form-control'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }

# --- 4. PROVEEDORES ---
class SupplierForm(forms.ModelForm):
    class Meta:
        model = BusinessPartner
        fields = ['name', 'tax_id', 'email', 'phone', 'bank_name', 'bank_account']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.TextInput(attrs={'class': 'form-control'}),
        }

class SupplierPaymentForm(forms.Form):
    provider = forms.ModelChoiceField(queryset=None, label="Proveedor", widget=forms.Select(attrs={'class': 'form-select'}))
    my_account = forms.ModelChoiceField(queryset=None, label="Pagar desde", widget=forms.Select(attrs={'class': 'form-select'}))
    amount = forms.DecimalField(label="Monto a Pagar", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    date = forms.DateField(label="Fecha Pago", widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    evidence = forms.FileField(required=False, label="Comprobante", widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['provider'].queryset = BusinessPartner.objects.filter(company=company, partner_type__in=['P', 'A'])
        self.fields['my_account'].queryset = BankAccount.objects.filter(company=company)

# --- 5. INVENTARIO ---
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # Estos son los campos EXACTOS que definimos en models.py
        fields = ['code', 'name', 'product_type', 'price', 'cost', 'stock']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SERV-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# --- 6. RRHH ---
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'dpi', 'nit', 'address', 'phone', 'position', 'department', 'date_hired', 'base_salary', 'bonus', 'igss_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'dpi': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'date_hired': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bonus': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'igss_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['employee', 'amount', 'monthly_fee', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(company=company)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_name'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'id': 'id_code'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'id': 'id_description', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }