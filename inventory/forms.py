from django import forms
from core.models import StockMovement, Product, Warehouse, Company, Branch
from anaira.middleware import get_current_company

# 1. FORMULARIO DE MOVIMIENTOS
class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'warehouse', 'movement_type', 'quantity', 'comments']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select select2'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['product'].queryset = Product.objects.none()
        self.fields['warehouse'].queryset = Warehouse.objects.none()

        company = get_current_company()
        if company:
            self.fields['product'].queryset = Product.objects.filter(company=company)
            self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company)

# 2. FORMULARIO DE PRODUCTOS
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

# 3. FORMULARIO DE BODEGAS (CORREGIDO: SIN ADDRESS)
class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        # Quitamos 'address' de aquí porque no existe en el modelo aún
        fields = ['name', 'branch', 'active'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            # 'address': forms.Textarea(...), <--- LO QUITAMOS
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = get_current_company()
        if company:
            self.fields['branch'].queryset = Branch.objects.filter(company=company)
        else:
            self.fields['branch'].queryset = Branch.objects.none()

# 4. FORMULARIO DE TRASLADOS MANUALES
class TransferForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(), 
        label="Producto", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    warehouse_from = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(), 
        label="Bodega Origen", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    warehouse_to = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(), 
        label="Bodega Destino", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(label="Cantidad", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    comments = forms.CharField(required=False, label="Comentarios", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        company = get_current_company()
        if company:
            self.fields['product'].queryset = Product.objects.filter(company=company)
            qs_warehouses = Warehouse.objects.filter(company=company)
            self.fields['warehouse_from'].queryset = qs_warehouses
            self.fields['warehouse_to'].queryset = qs_warehouses