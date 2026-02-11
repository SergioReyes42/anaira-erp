from django.db import models
from django.utils import timezone
from core.models import CompanyAwareModel, Client, Product

class Sale(CompanyAwareModel):
    """Encabezado de la Venta"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Cliente")
    date = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    PAYMENT_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta de Crédito/Débito'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='EFECTIVO')

    def __str__(self):
        return f"Venta #{self.id} - {self.client.name}"

class SaleDetail(models.Model):
    """Detalle de productos en la venta"""
    sale = models.ForeignKey(Sale, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Invoice(CompanyAwareModel):
    """Factura Electrónica (FEL)"""
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, verbose_name="Venta Original")
    fel_number = models.CharField(max_length=100, verbose_name="Número FEL (UUID)")
    serie = models.CharField(max_length=50, verbose_name="Serie")
    numero = models.CharField(max_length=50, verbose_name="Número DTE")
    authorization_date = models.DateTimeField(verbose_name="Fecha de Autorización")
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    def __str__(self):
        return f"Factura {self.serie}-{self.numero}"

# --- NUEVO: MODELO DE COTIZACIÓN ---
class Quotation(CompanyAwareModel):
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador'),
        ('SENT', 'Enviada'),
        ('ACCEPTED', 'Aceptada'),
        ('REJECTED', 'Rechazada'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Cliente")
    date = models.DateTimeField(default=timezone.now, verbose_name="Fecha Emisión")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Válida hasta")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    notes = models.TextField(null=True, blank=True, verbose_name="Notas")

    def __str__(self):
        return f"Cotización #{self.id} - {self.client.name}"