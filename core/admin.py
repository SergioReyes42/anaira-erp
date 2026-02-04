from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
# Importamos SOLO lo que estamos seguros que existe para que no falle
from .models import (
    Product, 
    Client, 
    Sale, 
    SaleDetail, 
    CompanyProfile, 
    Quotation, 
    QuotationDetail, 
    BankAccount, 
    BankMovement
)

# --- 1. ADMIN DE TENANTS (Multi-Empresa) ---
# Intentamos registrar Tenant genéricamente por si el nombre varía
try:
    from .models import Tenant
    @admin.register(Tenant)
    class TenantAdmin(admin.ModelAdmin):
        list_display = ('schema_name', 'name', 'created_on')
        search_fields = ('schema_name', 'name')
except ImportError:
    pass  # Si no existe el modelo Tenant en core, no hace nada.
except AlreadyRegistered:
    pass

try:
    from .models import Domain
    @admin.register(Domain)
    class DomainAdmin(admin.ModelAdmin):
        list_display = ('domain', 'tenant', 'is_primary')
except ImportError:
    pass
except AlreadyRegistered:
    pass


# --- 2. PERFIL DE EMPRESA (Ahora Multi-Empresa) ---
try:
    @admin.register(CompanyProfile)
    class CompanyProfileAdmin(admin.ModelAdmin):
        list_display = ('name', 'nit', 'phone')
        # Esto pone un filtro horizontal muy cómodo para seleccionar muchos usuarios
        filter_horizontal = ('allowed_users',) 
        
        def has_add_permission(self, request):
            # Ahora SÍ permitimos agregar (True) porque usted dijo que es Multi-Empresa
            return True 
except AlreadyRegistered:
    pass


# --- 3. REGISTRO AUTOMÁTICO DEL RESTO ---
models_to_register = [
    Product, 
    Client, 
    Sale, 
    SaleDetail, 
    Quotation, 
    QuotationDetail, 
    BankAccount, 
    BankMovement
]

for model in models_to_register:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass
    except Exception:
        pass