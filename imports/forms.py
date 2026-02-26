from django import forms
from django.forms import inlineformset_factory
from .models import Duca, DucaItem, TrackingEvent, PurchaseOrder, WarehouseReception
from django.db.models import Q

class DucaForm(forms.ModelForm):
    class Meta:
        model = Duca
        fields = ['purchase_orders', 'duca_number', 'date_acceptance', 'supplier_name', 'customs_agent', 
                  'exchange_rate', 'freight_usd', 'insurance_usd', 'iva_gtq', 'other_expenses_gtq', 'status']
        widgets = {
            'date_acceptance': forms.DateInput(attrs={'type': 'date'}),
            'purchase_orders': forms.SelectMultiple(attrs={'size': '4'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🔥 EL FILTRO INTELIGENTE 🔥
        # Si estamos creando una DUCA nueva, solo muestra las órdenes "huérfanas" (que no tienen DUCA)
        if not self.instance.pk:
            self.fields['purchase_orders'].queryset = PurchaseOrder.objects.filter(ducas__isnull=True)
        else:
            # Si estamos editando una DUCA vieja, muestra las huérfanas + las que ya tiene esta DUCA
            self.fields['purchase_orders'].queryset = PurchaseOrder.objects.filter(
                Q(ducas__isnull=True) | Q(ducas=self.instance)
            ).distinct()

        # Aplicamos diseño Bootstrap a todos los campos
        for field_name, field in self.fields.items():
            if field_name == 'purchase_orders':
                field.widget.attrs['class'] = 'form-select'
                field.help_text = "Solo se muestran órdenes pendientes. Mantén presionado 'Ctrl' para seleccionar múltiples."
            else:
                field.widget.attrs['class'] = 'form-control'

# Esto permite agregar múltiples productos a una sola póliza (como una factura)
class DucaItemForm(forms.ModelForm):
    class Meta:
        model = DucaItem
        # Agregamos 'product_catalog' para que puedas vincularlo a Logística
        fields = ['product_catalog', 'product_code', 'description', 'quantity', 'fob_unit_usd', 'dai_rate']
        widgets = {
            'product_catalog': forms.Select(attrs={'class': 'form-select border-primary'}),
            'product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Proveedor'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción en Factura'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'fob_unit_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dai_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class TrackingEventForm(forms.ModelForm):
    class Meta:
        model = TrackingEvent
        fields = ['event_type', 'event_date', 'location', 'notes']
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Puerto Quetzal, Miami...'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Novedades del viaje...'}),
        }

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['po_number', 'supplier_name', 'status', 'total_amount_usd']
        widgets = {
            'po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: OC-2026-001'}),
            'supplier_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Proveedor (Ej: Hikvision)'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'total_amount_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class WarehouseReceptionForm(forms.ModelForm):
    class Meta:
        model = WarehouseReception
        fields = ['warehouse','reception_date', 'seal_intact', 'condition', 'damages_notes']
        widgets = {
            'warehouse': forms.Select(attrs={'class': 'form-select fw-bold border-warning'}),
            'reception_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'condition': forms.TextInput(attrs={'class': 'form-control'}),
            'damages_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalla si hubo cajas mojadas, equipos quebrados, etc...'}),
            'seal_intact': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'transform: scale(1.5); margin-right: 10px;'}),
        }