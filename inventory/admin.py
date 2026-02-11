from django.contrib import admin
from .models import StockMovement
from core.models import Product, Warehouse # Importamos desde core para poder verlos aquí si es necesario

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['date', 'product', 'movement_type', 'quantity', 'warehouse', 'reason', 'company']
    list_filter = ['movement_type', 'date', 'warehouse', 'company']
    search_fields = ['product__name', 'reason', 'id']
    date_hierarchy = 'date'
    
    # Opcional: Para que sea readonly si no quieres que editen movimientos pasados
    # readonly_fields = ['product', 'quantity', 'movement_type', 'warehouse', 'company']