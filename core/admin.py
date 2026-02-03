from django.contrib import admin
from .models import (
    CompanyProfile, 
    Client, 
    Product, 
    Quotation, 
    QuotationDetail,
    InventoryMovement, 
    Sale, 
    SaleDetail,
    Provider, 
    Purchase, 
    PurchaseDetail
)

# --- 1. EMPRESA ---
@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone')

# --- 2. CLIENTES Y PROVEEDORES ---
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'contact_name', 'phone')
    search_fields = ('name', 'nit')

@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'contact_name', 'phone')
    search_fields = ('name', 'nit')

# --- 3. PRODUCTOS ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Campos seguros que sí existen en el modelo
    list_display = ('name', 'code', 'stock', 'stock_reserved', 'price')
    search_fields = ('name', 'code')
    list_filter = ('stock',) 

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'type', 'quantity', 'date', 'user')
    list_filter = ('type', 'date')

# --- 4. VENTAS Y COTIZACIONES ---
class QuotationDetailInline(admin.TabularInline):
    model = QuotationDetail
    extra = 0

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total', 'status')
    list_filter = ('status', 'date')
    inlines = [QuotationDetailInline] # Agregado para ver detalles dentro de la cotización

# Configuración de Ventas (Sale)
class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total')
    inlines = [SaleDetailInline]

# --- 5. COMPRAS ---
class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 1

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'date', 'reference', 'total')
    list_filter = ('date', 'provider')
    inlines = [PurchaseDetailInline]
    
    # Recálculo automático del total al guardar desde el Admin
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        # Sumamos los subtotales de los detalles
        total = sum(item.subtotal for item in obj.details.all())
        obj.total = total
        obj.save()