from django import forms
from .models import (
    Company, CompanyProfile,
    BankAccount, BankTransaction, BankMovement, 
    Income, Gasto, Fleet,
    BusinessPartner, Provider, 
    Product, 
    Employee, Loan, 
    Quotation, Client
)
from .models import Purchase

# ==========================================
# 1. SELECCIÓN DE EMPRESA
# ==========================================
class CompanySelectForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        label="Seleccione una Empresa",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

# ==========================================
# 2. BANCOS Y TESORERÍA
# ==========================================
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'currency', 'balance']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}), # O Select si tiene choices
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'bank_name': 'Nombre del Banco',
            'account_number': 'Número de Cuenta',
            'currency': 'Moneda',
            'balance': 'Saldo Inicial',
        }

class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankMovement
        fields = ['account', 'category', 'description', 'amount', 'reference', 'date']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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
        # Filtramos cuentas solo de la empresa activa
        if company:
            # Nota: Ajustar filtro según cómo relacione BankAccount con Company en models
            self.fields['from_account'].queryset = BankAccount.objects.filter(company__name=company.name) 
            self.fields['to_account'].queryset = BankAccount.objects.filter(company__name=company.name)

# ==========================================
# 3. GASTOS E INGRESOS
# ==========================================
class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['fecha', 'proveedor', 'descripcion', 'total', 'amount_untaxed', 'iva', 'categoria', 'bank_account', 'vehicle', 'imagen']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'inputTotal', 'oninput': 'calcularIVA()'}),
            
            # Campos de solo lectura (cálculo automático JS)
            'amount_untaxed': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'inputBase'}),
            'iva': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'inputIVA'}),
            
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargamos los vehículos disponibles
        self.fields['vehicle'].queryset = Fleet.objects.all()

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

# ==========================================
# 4. PROVEEDORES (COMPRAS)
# ==========================================
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
        if company:
            self.fields['provider'].queryset = BusinessPartner.objects.filter(company=company, partner_type__in=['P', 'A'])
            # Filtro de cuentas bancarias según lógica de negocio
            # self.fields['my_account'].queryset = BankAccount.objects.filter(...) 

# ==========================================
# 5. INVENTARIO (PRODUCTOS)
# ==========================================
class ProductForm(forms.ModelForm):
    # Definimos widgets explícitos para mejor control visual
    name = forms.CharField(label="Nombre del Producto", widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_name'}))
    code = forms.CharField(label="Código / SKU", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_code'}))
    description = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    price = forms.DecimalField(label="Precio Venta (Q)", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    cost = forms.DecimalField(label="Costo (Q)", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    stock = forms.IntegerField(label="Stock Inicial", initial=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    image = forms.ImageField(label="Imagen", required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Product
        fields = ['name', 'code', 'description', 'price', 'cost', 'stock', 'image']

# ==========================================
# 6. RECURSOS HUMANOS
# ==========================================
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

    def __init__(self, company=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['employee'].queryset = Employee.objects.filter(company=company)

# ==========================================
# 7. VENTAS Y CLIENTES
# ==========================================
class QuotationForm(forms.ModelForm):
    # Campo auxiliar para calcular fecha de vencimiento
    validity_days = forms.IntegerField(
        label="Días de Validez", 
        initial=15,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Quotation
        # 1. QUITAMOS 'description' DE AQUÍ:
        fields = ['client', 'date', 'validity_days', 'total'] 
        
        exclude = ['user', 'company', 'created_at', 'status']
        
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            # 2. QUITAMOS EL WIDGET DE DESCRIPTION TAMBIÉN
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nit', 'name', 'address', 'phone', 'email', 'contact_name', 'credit_days', 'credit_limit']
        widgets = {
            'nit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 123456-7'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la empresa'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
        }
class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'date', 'document_reference', 'total'] # Ajuste según sus campos reales
        exclude = ['user', 'company', 'created_at']
        
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'document_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Factura #123'}),
        }