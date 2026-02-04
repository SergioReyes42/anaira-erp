from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

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
    # En vez de 'user', ponemos nuestra función 'get_role'
     list_display = ('first_name', 'last_name', 'branch', 'get_role') 
    
    list_filter = ('branch', 'department')
    search_fields = ('first_name', 'last_name', 'dpi')
    
    # 2. Esta es la función mágica que busca el Rol
    @admin.display(description='Rol de Sistema') # Título de la columna
    def get_role(self, obj):
        # Verificamos si el empleado tiene un usuario vinculado
        if obj.user:
            # Si es Superusuario (usted), le ponemos una corona
            if obj.user.is_superuser:
                return "👑 SUPER ADMINISTRADOR"
            
            # Si tiene grupos asignados (ej: Ventas, Bodega), los mostramos
            groups = obj.user.groups.values_list('name', flat=True)
            if groups:
                return ", ".join(groups) # Muestra: "Ventas, Facturación"
            
            return "Usuario Básico (Sin Rol)"
            
        return "❌ Sin Usuario Vinculado"
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