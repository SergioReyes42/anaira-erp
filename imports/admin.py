from django.contrib import admin
from .models import Duca, DucaItem

class DucaItemInline(admin.TabularInline):
    model = DucaItem
    extra = 1  # Filas en blanco para agregar productos
    fields = ('product_code', 'description', 'quantity', 'fob_unit_usd', 'dai_rate')
    # Nota: Los campos calculados (cif, costo final, etc.) no se editan, el sistema los calcula solos.

@admin.register(Duca)
class DucaAdmin(admin.ModelAdmin):
    list_display = ('duca_number', 'supplier_name', 'date_acceptance', 'total_fob_usd', 'total_import_cost_gtq', 'status')
    list_filter = ('status', 'date_acceptance')
    search_fields = ('duca_number', 'supplier_name', 'customs_agent')
    readonly_fields = ('created_at',)
    
    # Esto es la magia: mete los productos dentro de la misma pantalla de la DUCA
    inlines = [DucaItemInline]
    
    fieldsets = (
        ('Datos de la Póliza', {
            'fields': ('company', 'duca_number', 'date_acceptance', 'status')
        }),
        ('Proveedores y Agentes', {
            'fields': ('supplier_name', 'customs_agent')
        }),
        ('Valores Globales (Dólares y Quetzales)', {
            'fields': ('exchange_rate', 'freight_usd', 'insurance_usd', 'iva_gtq', 'other_expenses_gtq')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)