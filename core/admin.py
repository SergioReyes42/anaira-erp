from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
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
    Employee,      # Agregado por si acaso
    Supplier       # Agregado por si acaso
)

# --- 1. CONFIGURACIÓN DE LA EMPRESA (Con Logo y NIT) ---
# Usamos un decorador seguro para CompanyProfile
try:
    @admin.register(CompanyProfile)
    class CompanyProfileAdmin(admin.ModelAdmin):
        list_display = ('name', 'nit', 'phone')
        
        # Esto oculta el botón "Agregar" si ya existe una empresa
        # para obligarlo a editar la existente y no crear duplicados.
        def has_add_permission(self, request):
            if self.model.objects.exists():
                return False
            return True
except AlreadyRegistered:
    pass

# --- 2. REGISTRO SEGURO DE OTROS MODELOS ---
# Esta lista incluye todos los modelos clave de su sistema
models_to_register = [
    Product, 
    Client, 
    Sale, 
    SaleDetail, 
    Quotation, 
    QuotationDetail, 
    BankAccount, 
    BankMovement,
    Employee,
    Supplier
]

for model in models_to_register:
    try:
        admin.site.register(model)
    except AlreadyRegistered:
        pass  # Si ya estaba registrado, ignoramos el error y seguimos
    except Exception:
        pass  # Si el modelo no existe o tiene otro problema, no detenemos el servidor