from django.db import models
from django.utils import timezone
from core.models import CompanyAwareModel, Product, Warehouse, Supplier

# --- MODELOS DE MOVIMIENTOS (Ya existían) ---
class StockMovement(CompanyAwareModel):
    MOVEMENT_TYPES = [
        ('IN', 'Entrada'),
        ('OUT', 'Salida'),
        ('ADJ', 'Ajuste'),
        ('TRF', 'Transferencia'),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Bodega")
    quantity = models.IntegerField(verbose_name="Cantidad")
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Tipo")
    date = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="Motivo")

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name}"

# --- NUEVOS: MODELOS DE COMPRA ---
class Purchase(CompanyAwareModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Proveedor")
    date = models.DateTimeField(default=timezone.now, verbose_name="Fecha Compra")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    invoice_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="No. Factura Proveedor")
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('RECEIVED', 'Recibido (Stock Actualizado)'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED')

    def __str__(self):
        return f"Compra #{self.id} - {self.supplier.name}"

class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_cost
        super().save(*args, **kwargs)