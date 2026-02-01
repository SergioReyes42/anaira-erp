from django.contrib import admin
from .models import (
    CompanyProfile, 
    Client, 
    Product, 
    Quotation, 
    QuotationDetail,  # <--- ¡IMPORTANTE! Agregamos esto
    Sale, 
    SaleDetail
)

# --- 1. PERFIL DE EMPRESA ---
@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone', 'email')
    search_fields = ('name', 'nit')

# --- 2. CLIENTES ---
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'contact_name', 'phone', 'email')
    search_fields = ('name', 'nit', 'contact_name')
    # Sin list_filter para evitar errores

# --- 3. PRODUCTOS ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'product_type')
    search_fields = ('name', 'code')
    list_filter = ('product_type',)

# --- 4. COTIZACIONES ---
class QuotationDetailInline(admin.TabularInline):
    model = QuotationDetail  # <--- CORREGIDO: Apuntamos directo al modelo
    extra = 0

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total', 'valid_until')
    list_filter = ('date',)
    search_fields = ('client__name',)
    inlines = [QuotationDetailInline]

# --- 5. VENTAS ---
class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice_number', 'client', 'date', 'total', 'payment_method')
    list_filter = ('date', 'payment_method')
    search_fields = ('client__name', 'invoice_number')
    inlines = [SaleDetailInline]