from django import forms
from .models import StockMovement, Product, Warehouse

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
    """Formulario especial para mover mercadería de A a B"""
    from_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(active=True),
        label="🔴 Desde (Origen)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    to_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(active=True),
        label="🟢 Hacia (Destino)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="📦 Producto",
        widget=forms.Select(attrs={'class': 'form-select select2'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Cantidad a Mover",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    comments = forms.CharField(
        required=False,
        label="Comentario / Razón",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
    )

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get("from_warehouse")
        destino = cleaned_data.get("to_warehouse")

        if origen and destino and origen == destino:
            raise forms.ValidationError("¡La bodega de origen y destino no pueden ser la misma!")
        
        return cleaned_data