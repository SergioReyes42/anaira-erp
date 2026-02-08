from django.db import models
from django.conf import settings
from core.models import Company, Warehouse 

# ==========================================
# 1. CLASIFICACIÓN Y MARCAS
# ==========================================
class Category(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="Nombre de Categoría")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self): return self.name
    class Meta: verbose_name_plural = "Categorías"

class Brand(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="Marca")
    
    def __str__(self): return self.name
    class Meta: verbose_name = "Marca"

# ==========================================
# 2. MAESTRO DE PRODUCTOS
# ==========================================
class Product(models.Model):
    TYPE_CHOICES = [('PRODUCT', 'Producto Almacenable'), ('SERVICE', 'Servicio')]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='inventory_products_v2')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    
    sku = models.CharField(max_length=50, verbose_name="Código Interno / SKU")
    name = models.CharField(max_length=255, verbose_name="Nombre del Producto")
    description = models.TextField(blank=True, null=True)
    product_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='PRODUCT')
    
    cost_price = models.DecimalField(max_digits=12, decimal_places=4, default=0.00)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock_quantity = models.IntegerField(default=0, verbose_name="Existencia Total (Ref)")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self): return f"[{self.sku}] {self.name}"
    
    @property
    def total_stock(self):
        return self.stock_quantity

# ==========================================
# 3. STOCK DETALLADO
# ==========================================
class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks_v2')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks_v2')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    location = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name = "Existencia en Bodega"

    def __str__(self): return f"{self.product.name} en {self.warehouse.name}: {self.quantity}"

# ==========================================
# 4. KARDEX (AQUÍ ESTÁ LA CORRECCIÓN)
# ==========================================
class StockMovement(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Entrada'),
        ('OUT', 'Salida'),
        ('TRANSFER', 'Traslado'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements_v2')
    
    # === LA SOLUCIÓN AL ERROR E304 ===
    # Agregamos related_name='inventory_movements' para que no choque con el viejo
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.CASCADE, 
        verbose_name="Bodega", 
        null=True, 
        blank=True,
        related_name='inventory_movements' 
    )
    # =================================

    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.IntegerField(verbose_name="Cantidad")
    date = models.DateTimeField(auto_now_add=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='inventory_updates' 
    )
    
    reference = models.CharField(max_length=100, blank=True, verbose_name="Referencia")
    description = models.CharField(max_length=255, blank=True, verbose_name="Comentario")

    class Meta:
        verbose_name = "Movimiento (Kardex)"
        verbose_name_plural = "Movimientos"
        ordering = ['-date']

    def __str__(self): return f"{self.get_movement_type_display()} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # 1. Guardar el movimiento
        super().save(*args, **kwargs)

        # 2. Actualizar stock en BODEGA ESPECÍFICA (si existe)
        if self.warehouse:
            stock_record, created = Stock.objects.get_or_create(
                product=self.product,
                warehouse=self.warehouse,
                defaults={'quantity': 0}
            )
            if 'IN' in self.movement_type:
                stock_record.quantity += self.quantity
            elif 'OUT' in self.movement_type:
                stock_record.quantity -= self.quantity
            stock_record.save()

        # 3. Actualizar stock GLOBAL del producto
        # (Suma de todas las bodegas para tener el dato rápido)
        total_real = self.product.stocks_v2.aggregate(total=models.Sum('quantity'))['total'] or 0
        self.product.stock_quantity = total_real
        self.product.save()

class MovementDetail(models.Model):
    movement = models.ForeignKey(StockMovement, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)