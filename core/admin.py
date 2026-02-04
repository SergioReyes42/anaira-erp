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

# --- 1. CONFIGURACIÓN DE LA EMPRESA (Para subir el Logo) ---
try:
    @admin.register(CompanyProfile)
    class CompanyProfileAdmin(admin.ModelAdmin):
        list_display = ('name', 'nit', 'phone')
        
        # Evita crear duplicados (solo editar)
        def has_add_permission(self, request):
            if self.model.objects.exists():
                return False
            return True
except AlreadyRegistered:
    pass

# --- 2. REGISTRO SEGURO DE LOS DEMÁS MODELOS ---
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
        pass  # Si ya estaba, lo ignora
    except Exception:
        pass  # Si algo sale mal, no detiene el servidor