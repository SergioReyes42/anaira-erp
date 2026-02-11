from django.db import models
from django.utils import timezone
from core.models import CompanyAwareModel, Product, Warehouse

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
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Tipo de Movimiento")
    date = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora")
    
    # --- AQUÍ AGREGAMOS EL CAMPO QUE FALTABA ---
    reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="Motivo/Referencia")

    def save(self, *args, **kwargs):
        # Lógica simple: Si es salida, restamos. Si es entrada, sumamos.
        # (Opcional: puedes dejar esto a la vista si prefieres manejarlo allá)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"