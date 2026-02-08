from django import forms
from .models import StockMovement, Product, Warehouse
from core.models import Branch # Asegúrate de importar Branch

# ==========================================
# 1. FORMULARIO DE MOVIMIENTOS (Kardex)
# ==========================================
class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        # AGREGAMOS 'warehouse' AQUÍ:
        fields = ['warehouse', 'product', 'movement_type', 'quantity', 'reference', 'description']
        widgets = {
            # Selector de Bodega
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            
            'product': forms.Select(attrs={'class': 'form-select select2'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Factura #123'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'warehouse': 'Seleccionar Bodega',  # Etiqueta nueva
            'product': 'Producto',
            'movement_type': 'Tipo',
            'quantity': 'Cantidad',
            'reference': 'Ref.',
            'description': 'Notas',
        }

    def __init__(self, *args, **kwargs):
        company_id = kwargs.pop('company_id', None)
        super().__init__(*args, **kwargs)
        
        if company_id:
            self.fields['product'].queryset = Product.objects.filter(company_id=company_id)
            # FILTRO IMPORTANTE: Solo mostrar bodegas de ESTA empresa (vía sucursales)
            from core.models import Warehouse
            self.fields['warehouse'].queryset = Warehouse.objects.filter(branch__company_id=company_id, active=True)


# ==========================================
# 2. FORMULARIO DE PRODUCTOS (Nuevo)
# ==========================================
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'category', 'brand', 'cost_price', 'sale_price', 'product_type', 'image']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. PROD-001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'sku': 'Código / SKU',
            'name': 'Nombre',
            'category': 'Categoría',
            'brand': 'Marca',
            'cost_price': 'Costo',
            'sale_price': 'Precio Venta',
            'product_type': 'Tipo',
            'image': 'Imagen (Opcional)',
        }

class TransferForm(forms.Form):
    # Definimos los campos vacíos primero, los llenaremos en el __init__
    from_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(), # Se llena dinámicamente
        label="🔴 Bodega Origen (Sale)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    to_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(), # Se llena dinámicamente
        label="🟢 Bodega Destino (Entra)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="📦 Producto",
        widget=forms.Select(attrs={'class': 'form-select select2'}) # select2 ayuda a buscar
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Cantidad",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    comments = forms.CharField(
        required=False,
        label="Comentarios",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # === FILTRO INTELIGENTE DE BODEGAS ===
        # Lógica: Excluir cualquier bodega que sea "padre" de otra.
        # Solo queremos las "hojas" del árbol (las que no tienen sub_warehouses).
        
        bodegas_finales = Warehouse.objects.filter(
            active=True, 
            sub_warehouses__isnull=True  # <--- ESTO ES LA CLAVE: Solo las que NO tienen hijos
        )

        self.fields['from_warehouse'].queryset = bodegas_finales
        self.fields['to_warehouse'].queryset = bodegas_finales

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['branch', 'name', 'parent', 'is_main', 'active']
        widgets = {
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'branch': 'Sucursal',
            'name': 'Nombre de la Bodega/Estante',
            'parent': 'Es sub-bodega de... (Opcional)',
            'is_main': '¿Es Bodega Principal?',
            'active': 'Activa',
        }

    def __init__(self, *args, **kwargs):
        company_id = kwargs.pop('company_id', None)
        super().__init__(*args, **kwargs)
        if company_id:
            # Filtramos sucursales de la empresa actual
            self.fields['branch'].queryset = Branch.objects.filter(company_id=company_id)
            # Filtramos padres (bodegas) de la empresa actual
            self.fields['parent'].queryset = Warehouse.objects.filter(branch__company_id=company_id)