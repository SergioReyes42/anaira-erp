from django import forms
from .models import Expense

class ExpensePhotoForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['photo', 'description', 'total_amount']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control', 'capture': 'camera'}), # Activa cámara en móvil
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej: Gasolina, Almuerzo...'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
        }