from django.contrib import admin
from .models import (
    CompanyProfile, 
    Client, 
    Product, 
    Quotation, 
    QuotationDetail, 
    Sale, 
    SaleDetail,
    Provider,       # <--- NUEVO
    Purchase,       # <--- NUEVO
    PurchaseDetail  # <--- NUEVO
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
    list_display = ('name', 'price', 'stock', 'product_type')
    search_fields = ('name',)
    list_filter = ('product_type',)

# --- 4. VENTAS Y COTIZACIONES ---
class QuotationDetailInline(admin.TabularInline):
    model = QuotationDetail
    extra = 0

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total')
    inlines = [QuotationDetailInline]

class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total')
    inlines = [SaleDetailInline]

# --- 5. COMPRAS (NUEVO MÓDULO) ---
class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 1

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'provider', 'date', 'reference', 'total')
    list_filter = ('date', 'provider')
    inlines = [PurchaseDetailInline]
    
    # Esto ayuda a que, al guardar en el admin, calcule el total automáticamente
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Recalcular el total de la compra sumando los detalles
        obj = form.instance
        total = sum(item.subtotal for item in obj.details.all())
        obj.total = total
        obj.save()