from django import forms
from core.models import Warehouse
from .models import Product, StockMovement, Category, Supplier

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['sku', 'name', 'category', 'brand', 'supplier', 'cost_price', 'sale_price', 'image']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'Ej. DS-2CD2021G1-I'}),
            'name': forms.TextInput(attrs={'class': 'form-control fw-bold', 'placeholder': 'Descripción del producto'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control text-success fw-bold', 'step': '0.01'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name', 'address', 'active']

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'nit', 'phone', 'email']

class InventoryMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'warehouse', 'movement_type', 'quantity', 'reference', 'description']