from django import forms
from core.models import Product, Warehouse, Company, Branch
from .models import StockMovement  # <--- AHORA LO IMPORTAMOS DE AQUÍ (LOCAL)

from django import forms
from core.models import Product, Warehouse, Supplier
from .models import StockMovement, Purchase

# --- FORMULARIOS DE MOVIMIENTOS ---
class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'warehouse', 'quantity', 'movement_type', 'reason']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'warehouse': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'code', 'description', 'price', 'cost'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# --- NUEVO: FORMULARIO DE COMPRA ---
class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
class TransferForm(forms.Form):
    """
    Formulario especial para mover inventario entre bodegas
    """
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'}), 
        label="Producto"
    )
    from_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'}), 
        label="Bodega Origen"
    )
    to_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.all(), 
        widget=forms.Select(attrs={'class': 'form-select'}), 
        label="Bodega Destino"
    )
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}), 
        label="Cantidad"
    )
    reason = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}), 
        label="Motivo", 
        required=False
    )