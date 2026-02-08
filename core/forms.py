from django import forms
from .models import (
    Company, CompanyProfile,
    BankAccount, BankTransaction, BankMovement, 
    Income, Gasto, Fleet,
    BusinessPartner, Provider, 
    Product, 
    Employee, Loan, 
    Quotation, Client, Warehouse, Supplier, Sale,
    Purchase # Aseguramos que Purchase esté importado
)

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
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
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
        if company:
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
            'amount_untaxed': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'inputBase'}),
            'iva': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'inputIVA'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
# 4. PROVEEDORES
# ==========================================
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'
        exclude = ['company']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
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

# ==========================================
# 5. INVENTARIO (PRODUCTOS)
# ==========================================
# NOTA IMPORTANTE: Se han comentado los campos 'category', 'brand' y 'min_stock'
# porque causaban error ya que NO existen en el modelo Product actual.
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'cost', 'price', 'stock', 'image'] # Solo campos existentes
        # fields originales (si agrega los campos al modelo, descomente esta línea):
        # fields = ['code', 'name', 'category', 'brand', 'cost', 'price', 'stock', 'min_stock', 'image']
        
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            # 'category': forms.Select(attrs={'class': 'form-select'}),
            # 'brand': forms.Select(attrs={'class': 'form-select'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            # 'min_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

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
    class Meta:
        model = Quotation
        fields = ['client', 'valid_until', 'payment_method', 'observation']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select select2'}), # select2 ayuda a buscar
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'client': 'Cliente',
            'valid_until': 'Válida hasta',
            'payment_method': 'Forma de Pago',
            'observation': 'Notas / Observaciones',
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['client', 'payment_method'] 
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select select2'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'nit', 'address', 'phone', 'email', 'contact_name', 'credit_days', 'credit_limit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razón Social o Nombre Completo'}),
            'nit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIT / CUI'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Persona de contacto'}),
            'credit_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Nombre del Cliente',
            'nit': 'NIT / RUC',
            'address': 'Dirección Fiscal',
            'phone': 'Teléfono',
            'credit_days': 'Días de Crédito',
            'credit_limit': 'Límite de Crédito (Q)',
        }
# ==========================================
# 8. COMPRAS (CORREGIDO)
# ==========================================
class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        # AQUI ESTA LA MAGIA: Incluimos 'warehouse' para que aparezca el select
        fields = [
            'supplier', 
            'date', 
            'document_reference', 
            'payment_method', 
            'payment_reference', 
            'warehouse' 
        ]
        
        exclude = ['user', 'company', 'created_at', 'status', 'total', 'branch']
        
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            # Estilo verde y negrita para destacar el campo de Bodega
            'warehouse': forms.Select(attrs={'class': 'form-select border-success fw-bold'}),
            'document_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Factura #123'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Banco Industrial / Tarjeta'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargamos solo las bodegas activas
        if 'warehouse' in self.fields:
            self.fields['warehouse'].queryset = Warehouse.objects.filter(active=True)
            self.fields['warehouse'].empty_label = "--- Seleccione Bodega ---"