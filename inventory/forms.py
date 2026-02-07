from django import forms
from .models import StockMovement, Product

class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'reference', 'description']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
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