from django.db import models
from django.conf import settings
from django.utils import timezone

# Importaciones Correctas
from core.models import Company, CompanyAwareModel, Warehouse
from inventory.models import Product

# ==========================================
# 1. CLIENTES
# ==========================================
class Client(CompanyAwareModel):
    name = models.CharField(max_length=200, verbose_name="Nombre / Razón Social")
    nit = models.CharField(max_length=20, verbose_name="NIT", null=True, blank=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", null=True, blank=True)
    email = models.EmailField(verbose_name="Correo", null=True, blank=True)
    address = models.TextField(verbose_name="Dirección", null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.nit})"

# ==========================================
# 2. COTIZACIONES
# ==========================================
class Quotation(CompanyAwareModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Cliente")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Vendedor")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Bodega")
    
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Totales
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, default='DRAFT', choices=[
        ('DRAFT', 'Borrador'),
        ('SENT', 'Enviada'),
        ('INVOICED', 'Facturada'),
        ('CANCELED', 'Anulada')
    ])

    def __str__(self):
        return f"Cotización #{self.id} - {self.client}"

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_line = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_line = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Sale(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador / Pendiente'),
        ('APPROVED', 'Aprobada / Contabilizada'),
        ('CANCELED', 'Anulada'),
    ]
    
    company = models.CharField(max_length=100, blank=True, null=True) 
    
    date = models.DateField(default=timezone.now, verbose_name="Fecha de Factura")
    serie = models.CharField(max_length=10, default="A", verbose_name="Serie")
    invoice_number = models.CharField(max_length=50, verbose_name="Número de Factura")
    
    client_nit = models.CharField(max_length=15, default="CF", verbose_name="NIT del Cliente")
    client_name = models.CharField(max_length=200, default="Consumidor Final", verbose_name="Nombre del Cliente")
    
    tax_base = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Base Imponible")
    tax_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="IVA (Débito)")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Factura")
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DRAFT')
    
    def __str__(self):
        return f"{self.serie}-{self.invoice_number} | {self.client_name} | Q.{self.total_amount}"