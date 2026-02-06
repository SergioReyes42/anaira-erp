from django.db import models
from django.conf import settings
from core.models import Company, Warehouse # Importamos del Core para no duplicar

# ==========================================
# 1. CLASIFICACIÓN Y MARCAS
# ==========================================
class Category(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE) 
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self): return self.name

class Brand(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')    
    name = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    code = models.CharField(max_length=50, verbose_name="Código Interno")
    
    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        
    def __str__(self):
        return f"{self.code} - {self.name}"

# ==========================================
# 2. MAESTRO DE PRODUCTOS
# ==========================================
class Product(models.Model):
    TYPE_CHOICES = [('PRODUCT', 'Producto Almacenable'), ('SERVICE', 'Servicio'), ('CONSUMABLE', 'Consumible')]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    
    sku = models.CharField(max_length=50, verbose_name="Código Interno / SKU")
    barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código de Barras")
    name = models.CharField(max_length=255, verbose_name="Nombre del Producto")
    description = models.TextField(blank=True, null=True)
    
    product_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='PRODUCT')
    
    # Precios y Costos
    cost_price = models.DecimalField(max_digits=12, decimal_places=4, default=0.00, verbose_name="Costo Promedio")
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Precio de Venta")
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Precio Mayorista")
    
    # Control de Stock Global (Referencial)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Stock Mínimo")
    max_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Stock Máximo")
    
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'sku')
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self): return f"[{self.sku}] {self.name}"

# ==========================================
# 3. EXISTENCIAS (STOCK) POR BODEGA
# ==========================================
class Stock(models.Model):
    """Controla cuánto hay de cada producto en cada bodega específica"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Cantidad Disponible")
    location_in_warehouse = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ubicación (Pasillo/Estante)")

    class Meta:
        unique_together = ('product', 'warehouse')
        verbose_name = "Existencia en Bodega"
        verbose_name_plural = "Existencias"

    def __str__(self):
        return f"{self.product.name} en {self.warehouse.name}: {self.quantity}"

# ==========================================
# 4. MOVIMIENTOS DE INVENTARIO (KARDEX)
# ==========================================
class InventoryMovement(models.Model):
    TYPE_CHOICES = [
        ('IN_PURCHASE', 'Entrada por Compra'),
        ('IN_ADJUSTMENT', 'Entrada por Ajuste'),
        ('IN_RETURN', 'Devolución de Cliente'),
        ('OUT_SALE', 'Salida por Venta'),
        ('OUT_ADJUSTMENT', 'Salida por Ajuste/Pérdida'),
        ('OUT_CONSUMPTION', 'Salida por Consumo Interno'),
        ('TRANSFER', 'Traslado entre Bodegas'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Tipo de Movimiento")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    reference = models.CharField(max_length=100, help_text="No. Factura, Orden, etc.", verbose_name="Referencia")
    description = models.CharField(max_length=255, blank=True, verbose_name="Comentario")
    
    # Auditoría
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Kardex / Movimientos"

    def __str__(self): return f"{self.get_movement_type_display()} - {self.reference}"

class MovementDetail(models.Model):
    movement = models.ForeignKey(InventoryMovement, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    
    quantity = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Cantidad")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0, verbose_name="Costo Unitario")
    
    def __str__(self): return f"{self.product.sku} - {self.quantity}"