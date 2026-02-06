from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # Estos son los campos que el usuario va a llenar.
        # Note que NO incluimos 'company' porque eso se pone automático.
        fields = ['code', 'name', 'category', 'cost_price', 'selling_price', 'min_stock']
        
        # Esto es solo estética para que se vea bien en HTML
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }