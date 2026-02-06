from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Company

# --- IMPORTACIÓN DE MODELOS ---
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
    Employee,      
    StockMovement   
)

# ========================================================
# 1. ADMIN DE TENANTS (Multi-Empresa / Multi-Inquilino)
# ========================================================
try:
    from .models import Tenant, Domain
    
    # Usamos un try/except interno por si ya están registrados
    try:
        @admin.register(Tenant)
        class TenantAdmin(admin.ModelAdmin):
            list_display = ('schema_name', 'name', 'created_on')
            search_fields = ('schema_name', 'name')
    except AlreadyRegistered:
        pass

    try:
        @admin.register(Domain)
        class DomainAdmin(admin.ModelAdmin):
            list_display = ('domain', 'tenant', 'is_primary')
    except AlreadyRegistered:
        pass
        
except ImportError:
    pass 


# ========================================================
# 2. PERFIL DE EMPRESA
# ========================================================
try:
    @admin.register(CompanyProfile)
    class CompanyProfileAdmin(admin.ModelAdmin):
        list_display = ('name', 'nit', 'phone')
        filter_horizontal = ('allowed_users',) 
        
        def has_add_permission(self, request):
            return True 
except AlreadyRegistered:
    pass

# Registrar Company si no estaba
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'active')

# 1. Definimos el Inline (el perfil dentro del usuario)
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil Multi-Empresa'
    filter_horizontal = ('allowed_companies',)

# 2. Definimos el nuevo Administrador de Usuarios
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    # Agregamos las columnas extra para ver info rápido en la lista
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_companies')
    
    def get_companies(self, obj):
        # Esto es solo visual para ver las empresas en la lista
        if hasattr(obj, 'profile'):
            return ", ".join([c.name for c in obj.profile.allowed_companies.all()])
        return "-"
    get_companies.short_description = 'Empresas Asignadas'

# 3. EL BLOQUE BLINDADO (Aquí estaba el error)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass  # Si ya estaba des-registrado, ignoramos el error

# Re-registrar User
admin.site.register(User, UserAdmin)

# ========================================================
# 3. MODELOS AVANZADOS (Con Filtros y Buscadores)
# ========================================================

# --- SUCURSALES ---
try:
    @admin.register(Branch)
    class BranchAdmin(admin.ModelAdmin):
        list_display = ('name', 'code', 'company', 'address')
        search_fields = ('name', 'code')
        list_filter = ('company',)
except AlreadyRegistered:
    pass

# --- BODEGAS ---
try:
    @admin.register(Warehouse)
    class WarehouseAdmin(admin.ModelAdmin):
        list_display = ('name', 'branch', 'active')
        list_filter = ('branch', 'active')
        search_fields = ('name',)
except AlreadyRegistered:
    pass

# --- INVENTARIO ---
try:
    @admin.register(Inventory)
    class InventoryAdmin(admin.ModelAdmin):
        list_display = ('product', 'warehouse', 'quantity', 'location')
        list_filter = ('warehouse',)
        search_fields = ('product__name', 'product__code', 'warehouse__name')
except AlreadyRegistered:
    pass

# --- EMPLEADOS (RRHH) ---
try:
    @admin.register(Employee)
    class EmployeeAdmin(admin.ModelAdmin):
        list_display = ('first_name', 'last_name', 'position', 'branch', 'user')
        list_filter = ('branch', 'department')
        search_fields = ('first_name', 'last_name', 'dpi')
        # autocomplete_fields = ['user'] # Descomentar si tiene muchos usuarios
except AlreadyRegistered:
    pass

# --- KARDEX (MOVIMIENTOS) ---
try:
    @admin.register(StockMovement)
    class StockMovementAdmin(admin.ModelAdmin):
        list_display = ('date', 'product', 'warehouse', 'movement_type', 'quantity', 'user')
        list_filter = ('movement_type', 'warehouse', 'date')
        search_fields = ('product__name', 'product__code')
        readonly_fields = ('date',)
except AlreadyRegistered:
    pass


# ========================================================
# 4. REGISTRO AUTOMÁTICO (Modelos Simples)
# ========================================================
# Aquí van SOLO los que NO tienen configuración @admin.register arriba
models_to_register = [
    Product, 
    Client, 
    Sale, 
    SaleDetail, 
    Quotation, 
    QuotationDetail, 
    BankAccount, 
    BankMovement,
    Supplier, 
    Purchase, 
    PurchaseDetail
]

for model in models_to_register:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass