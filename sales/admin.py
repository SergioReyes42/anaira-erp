from django.contrib import admin
from .models import Sale, SaleDetail, Invoice

# Configuración para ver los productos DENTRO de la venta
class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 1  # Muestra una línea vacía para agregar productos rápido
    autocomplete_fields = ['product']  # Buscador de productos (si tienes muchos)
    readonly_fields = ['subtotal']  # El subtotal se calcula solo, mejor no tocarlo

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'date', 'total', 'payment_method', 'company']
    list_filter = ['date', 'payment_method', 'company']
    search_fields = ['client__name', 'id']
    date_hierarchy = 'date'
    
    # Aquí agregamos los detalles
    inlines = [SaleDetailInline]
    
    # Hacemos que el total sea de solo lectura (se debería calcular por los detalles)
    readonly_fields = ['total', 'company']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['fel_number', 'serie', 'numero', 'client', 'authorization_date']
    search_fields = ['fel_number', 'client__name', 'numero']
    list_filter = ['authorization_date', 'company']