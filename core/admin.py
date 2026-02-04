from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

# --- IMPORTACIÓN MASIVA DE MODELOS ---
from .models import (
    Product, 
    Client, 
    Sale, 
    SaleDetail, 
    CompanyProfile, 
    Quotation, 
    QuotationDetail, 
    BankAccount, 
    BankMovement,
    Supplier, 
    Purchase, 
    PurchaseDetail,
    Branch, 
    Warehouse, 
    Inventory,
    Employee,       # <--- IMPORTANTE
    StockMovement   # <--- IMPORTANTE
)

# --- 1. ADMIN DE TENANTS (Opcional) ---
try:
    from .models import Tenant, Domain
    @admin.register(Tenant)
    class TenantAdmin(admin.ModelAdmin):
        list_display = ('schema_name', 'name', 'created_on')
    @admin.register(Domain)
    class DomainAdmin(admin.ModelAdmin):
        list_display = ('domain', 'tenant', 'is_primary')
except ImportError:
    pass 
except AlreadyRegistered:
    pass

# --- 2. PERFIL DE EMPRESA ---
try:
    @admin.register(CompanyProfile)
    class CompanyProfileAdmin(admin.ModelAdmin):
        list_display = ('name', 'nit', 'phone')
        filter_horizontal = ('allowed_users',) 
        def has_add_permission(self, request):
            return True 
except AlreadyRegistered:
    pass

# --- 3. REGISTRO AUTOMÁTICO (Modelos Simples) ---
models_to_register = [
    Product, Client, Sale, SaleDetail, 
    Quotation, QuotationDetail, 
    BankAccount, BankMovement,
    Supplier, Purchase, PurchaseDetail
]

for model in models_to_register:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass


# --- 4. REGISTRO DE SUCURSALES Y BODEGAS ---

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'company', 'address')
    search_fields = ('name', 'code')
    list_filter = ('company',)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'active')
    list_filter = ('branch', 'active')
    search_fields = ('name',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'location')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'product__code', 'warehouse__name')


# --- 5. REGISTRO DE RRHH Y KARDEX (LO NUEVO) ---

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'position', 'branch', 'user')
    list_filter = ('branch', 'department')
    search_fields = ('first_name', 'last_name', 'dpi')
    # Nota: Si 'autocomplete_fields' da error, comente la siguiente línea
    # autocomplete_fields = ['user'] 

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('date', 'product', 'warehouse', 'movement_type', 'quantity', 'user')
    list_filter = ('movement_type', 'warehouse', 'date')
    search_fields = ('product__name', 'product__code')
    readonly_fields = ('date',)