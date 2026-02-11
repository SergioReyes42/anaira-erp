from django import forms
from core.models import Product, Warehouse
from .models import StockMovement, Purchase

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

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

# --- NUEVO: FORMULARIO DE TRASLADO ENTRE BODEGAS ---
class TransferForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(), # Se llena en la vista
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Producto"
    )
    from_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Bodega Origen"
    )
    to_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Bodega Destino"
    )
    quantity = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Cantidad a Mover"
    )
    reason = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False,
        label="Motivo (Opcional)"
    )