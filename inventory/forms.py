from django import forms
from core.models import StockMovement, Product, Warehouse, Company
from anaira.middleware import get_current_company

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        # Aseguramos que 'comments' esté aquí
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
        
        # 1. Definimos los querysets vacíos por seguridad inicial
        self.fields['product'].queryset = Product.objects.none()
        self.fields['warehouse'].queryset = Warehouse.objects.none()

        # 2. Obtenemos la empresa del hilo actual
        company = get_current_company()
        
        # 3. Si hay empresa, filtramos. Si no, se queda vacío.
        if company:
            # Aquí es donde ocurre la magia segura
            self.fields['product'].queryset = Product.objects.filter(company=company)
            self.fields['warehouse'].queryset = Warehouse.objects.filter(company=company)

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

class TransferForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(), # Iniciamos vacío para evitar error al importar
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