from django.db import models
from django.conf import settings
from core.models import Company, Warehouse

# ==========================================
# 1. CATALOGOS
# ==========================================
class Category(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Brand(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Supplier(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, verbose_name="Razón Social")
    nit = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    
    def __str__(self): return self.name

# ==========================================
# 2. PRODUCTO
# ==========================================
class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, verbose_name="SKU")
    name = models.CharField(max_length=255, verbose_name="Nombre")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Precios
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Stock Global (Referencia rápida)
    stock_quantity = models.IntegerField(default=0)
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    def __str__(self): return f"[{self.sku}] {self.name}"

# ==========================================
# 3. STOCK POR BODEGA
# ==========================================
class Stock(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self): return f"{self.product} en {self.warehouse}: {self.quantity}"

# ==========================================
# 4. MOVIMIENTOS (Kardex)
# ==========================================
class StockMovement(models.Model):
    TYPE_CHOICES = [('IN', 'Entrada'), ('OUT', 'Salida')]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    reference = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar o Crear Stock en Bodega
        stock_record, created = Stock.objects.get_or_create(
            product=self.product,
            warehouse=self.warehouse,
            defaults={'quantity': 0}
        )
        
        if self.movement_type == 'IN':
            stock_record.quantity += self.quantity
            self.product.stock_quantity += self.quantity # Global
        else:
            stock_record.quantity -= self.quantity
            self.product.stock_quantity -= self.quantity # Global
   
            
        stock_record.save()
        self.product.save()