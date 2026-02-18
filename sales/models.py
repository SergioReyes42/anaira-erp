from django.db import models
from django.conf import settings
from django.utils import timezone

# 1. IMPORTAMOS LO NECESARIO DE CORE (Solo la base de la empresa)
# ¡OJO! Aquí quitamos 'Client' y 'Product' porque ya no están en Core.
from core.models import Company, CompanyAwareModel

# 2. IMPORTAMOS PRODUCTOS Y BODEGAS DESDE INVENTARIO
from inventory.models import Product, Warehouse

# ==========================================
# 3. CLIENTES (Definido aquí mismo en Ventas)
# ==========================================
class Client(CompanyAwareModel):
    name = models.CharField(max_length=200, verbose_name="Nombre / Razón Social")
    nit = models.CharField(max_length=20, verbose_name="NIT", null=True, blank=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", null=True, blank=True)
    email = models.EmailField(verbose_name="Correo Electrónico", null=True, blank=True)
    address = models.TextField(verbose_name="Dirección", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.nit or 'C/F'})"

# ==========================================
# 4. COTIZACIONES
# ==========================================
class Quotation(CompanyAwareModel):
    # Relaciones
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Cliente")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Vendedor")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Bodega de Salida")
    
    # Datos de la Cotización
    date = models.DateField(default=timezone.now, verbose_name="Fecha de Emisión")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Válida hasta")
    notes = models.TextField(blank=True, verbose_name="Notas Internas")
    
    # Totales Financieros
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # IVA
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Estado del Flujo
    status = models.CharField(max_length=20, default='DRAFT', choices=[
        ('DRAFT', 'Borrador'),
        ('SENT', 'Enviada'),
        ('INVOICED', 'Facturada/Cerrada'),
        ('CANCELED', 'Anulada')
    ])

    def __str__(self):
        return f"Cotización #{self.id} - {self.client}"

# ==========================================
# 5. DETALLE DE PRODUCTOS (ITEMS)
# ==========================================
class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2) 
    total_line = models.DecimalField(max_digits=12, decimal_places=2) 

    def save(self, *args, **kwargs):
        self.total_line = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"