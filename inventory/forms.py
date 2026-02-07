from django import forms
from .models import StockMovement, Product

# ==========================================
# 1. FORMULARIO DE MOVIMIENTOS (Kardex)
# ==========================================
class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'reference', 'description']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select select2'}), # select2 para búsqueda rápida
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Factura #123'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Comentarios opcionales...'}),
        }
        labels = {
            'product': 'Seleccione Producto',
            'movement_type': 'Tipo de Movimiento',
            'quantity': 'Cantidad',
            'reference': 'Referencia (Opcional)',
            'description': 'Notas',
        }

    def __init__(self, *args, **kwargs):
        # Capturamos el ID de la empresa para filtrar los productos
        company_id = kwargs.pop('company_id', None)
        super().__init__(*args, **kwargs)
        
        if company_id:
            # FILTRO DE SEGURIDAD: Solo mostrar productos de esta empresa
            self.fields['product'].queryset = Product.objects.filter(company_id=company_id)


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