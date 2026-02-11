from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

# Importamos TODOS los modelos necesarios (Versión Correcta)
from .models import (
    Company, CompanyProfile, UserProfile, Branch, Warehouse,
    BankAccount, BankTransaction, BankMovement, Income,
    Expense, Vehicle, CreditCard, # Usamos Expense/Vehicle en vez de Gasto/Fleet
    Supplier, Client, Product,
    Employee, Loan,
    Quotation, Sale, Purchase,
    # BusinessPartner, Provider (Legacy - si los usas, descoméntalos en models.py)
)

User = get_user_model()

# ==========================================
# 1. GESTIÓN DE USUARIOS Y EMPRESAS
# ==========================================

class CompanySelectForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(active=True),
        label="Seleccione una Empresa",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CustomUserForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Apellido", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), label="Sucursal", required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'avatar']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # CORREGIDO: Solo ponemos los campos que REALMENTE existen en el modelo
        fields = ['company', 'phone', 'address', 'avatar']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

# ==========================================
# 2. GASTOS (MÓDULO CRÍTICO ACTUALIZADO)
# ==========================================

# A. FORMULARIO COMPLETO (Para Contabilidad/Admin)
class ExpenseForm(forms.ModelForm):
    # Campos adicionales para cálculos visuales
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha Factura"
    )
    
    class Meta:
        model = Expense
        fields = [
            'date', 'provider', 'description', 
            'total_amount', 'idp_amount', 'base_amount', 'vat_amount', 
            'is_fuel', 'vehicle', 'payment_method', 'credit_card', 'invoice_file'
        ]
        widgets = {
            'provider': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Gasolinera Shell'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción del gasto'}),
            
            # Montos
            'total_amount': forms.NumberInput(attrs={'class': 'form-control text-success fw-bold', 'step': '0.01', 'id': 'id_total_amount'}),
            'idp_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'id': 'id_idp_amount'}),
            'base_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly', 'id': 'id_base_amount'}),
            'vat_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly', 'id': 'id_vat_amount'}),
            
            # Selectores
            'is_fuel': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_fuel'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select', 'id': 'id_payment_method'}),
            'credit_card': forms.Select(attrs={'class': 'form-select', 'id': 'id_credit_card'}),
            'invoice_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos solo vehículos activos
        self.fields['vehicle'].queryset = Vehicle.objects.filter(status='ACTIVO')
        self.fields['credit_card'].empty_label = "--- Seleccione Tarjeta ---"


# B. FORMULARIO PILOTO (Simplificado para celular)
class PilotExpenseForm(forms.ModelForm):
    # Este reemplaza al antiguo MobileExpenseForm pero apunta al modelo correcto
    class Meta:
        model = Expense
        fields = ['invoice_file', 'vehicle', 'description']
        widgets = {
            'invoice_file': forms.FileInput(attrs={'class': 'form-control form-control-lg'}),
            'vehicle': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Comentario opcional (Ej: Llantas)'}),
        }

# ==========================================
# 3. TESORERÍA E INGRESOS
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

class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankMovement
        fields = ['account', 'category', 'description', 'amount', 'reference', 'date', 'evidence']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}), # O Select si tienes categorías fijas
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['date', 'description', 'amount', 'bank_account', 'reference_doc', 'evidence']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'bank_account': forms.Select(attrs={'class': 'form-select'}),
            'reference_doc': forms.TextInput(attrs={'class': 'form-control'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }

class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=None, label="Cuenta Origen", widget=forms.Select(attrs={'class': 'form-select'}))
    to_account = forms.ModelChoiceField(queryset=None, label="Cuenta Destino", widget=forms.Select(attrs={'class': 'form-select'}))
    amount = forms.DecimalField(label="Monto", max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    date = forms.DateField(label="Fecha", widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    reference = forms.CharField(required=False, label="Referencia", widget=forms.TextInput(attrs={'class': 'form-control'}))
    evidence = forms.ImageField(required=False, label="Comprobante", widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            qs = BankAccount.objects.filter(company__name=company.name)
            self.fields['from_account'].queryset = qs
            self.fields['to_account'].queryset = qs

# ==========================================
# 4. COMPRAS Y PROVEEDORES
# ==========================================

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = '__all__'
        exclude = ['company', 'created_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'date', 'document_reference', 'payment_method', 'payment_reference', 'warehouse']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select border-success fw-bold'}),
            'document_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Factura #123'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_reference': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'warehouse' in self.fields:
            self.fields['warehouse'].queryset = Warehouse.objects.filter(active=True)

class SupplierPaymentForm(forms.Form):
    # Formulario manual para pagos a proveedores
    provider = forms.ModelChoiceField(queryset=None, label="Proveedor", widget=forms.Select(attrs={'class': 'form-select'}))
    my_account = forms.ModelChoiceField(queryset=None, label="Pagar desde", widget=forms.Select(attrs={'class': 'form-select'}))
    amount = forms.DecimalField(label="Monto a Pagar", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    date = forms.DateField(label="Fecha Pago", widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    evidence = forms.FileField(required=False, label="Comprobante", widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, company, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if company:
            self.fields['provider'].queryset = Supplier.objects.filter(company__name=company.name)
            self.fields['my_account'].queryset = BankAccount.objects.filter(company__name=company.name)

# ==========================================
# 5. INVENTARIO (PRODUCTOS)
# ==========================================

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'cost', 'price', 'stock', 'image']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'code', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'branch', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# ==========================================
# 6. VENTAS Y CLIENTES
# ==========================================

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'nit', 'address', 'phone', 'email', 'contact_name', 'credit_days', 'credit_limit']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ['client', 'valid_until', 'payment_method', 'observation']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select select2'}), 
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['client', 'payment_method']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select select2'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

# ==========================================
# 7. RECURSOS HUMANOS (RRHH)
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
            # Filtramos empleados por la empresa del perfil activo
            self.fields['employee'].queryset = Employee.objects.filter(company__name=company.name)

# ==========================================
# 8. ACTIVOS (VEHÍCULOS)
# ==========================================

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'
        widgets = {
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'plate': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'assigned_driver': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }