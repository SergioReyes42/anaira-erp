from django.contrib import admin
# Importamos TODOS los modelos para que no falte ninguno
from .models import CompanyProfile, Client, Product, Quotation, Sale, SaleDetail

# --- 1. PERFIL DE EMPRESA ---
@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone', 'email')
    search_fields = ('name', 'nit')

# --- 2. CLIENTES (Corregido: Sin el filtro que daba error) ---
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # Mostramos las columnas más importantes
    list_display = ('name', 'nit', 'contact_name', 'phone', 'email')
    # Permitimos buscar por nombre o NIT
    search_fields = ('name', 'nit', 'contact_name')
    # OJO: Quitamos 'list_filter' porque la relación con company no estaba lista y daba error.

# --- 3. PRODUCTOS ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'product_type')
    search_fields = ('name', 'code')
    list_filter = ('product_type',)

# --- 4. COTIZACIONES ---
class QuotationDetailInline(admin.TabularInline):
    model = Quotation.details.through # O el modelo intermedio si se usa
    extra = 0

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total', 'valid_until')
    list_filter = ('date',)
    search_fields = ('client__name',)

# --- 5. VENTAS (El nuevo módulo) ---
class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice_number', 'client', 'date', 'total', 'payment_method')
    list_filter = ('date', 'payment_method')
    search_fields = ('client__name', 'invoice_number')
    inlines = [SaleDetailInline]