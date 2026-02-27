from django.db import models
from django.conf import settings
from django.utils import timezone

# Importaciones Correctas
from core.models import Company, CompanyAwareModel, Warehouse
from inventory.models import Product

# ==========================================
# 1. CLIENTES (Directorio y Libro Negro)
# ==========================================
class Client(CompanyAwareModel):
    CLIENT_TYPES = [('RETAIL', 'Consumidor Final'), ('WHOLESALE', 'Mayorista / Distribuidor')]
    
    name = models.CharField(max_length=200, verbose_name="Nombre / Razón Social")
    nit = models.CharField(max_length=20, verbose_name="NIT", null=True, blank=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", null=True, blank=True)
    email = models.EmailField(verbose_name="Correo", null=True, blank=True)
    address = models.TextField(verbose_name="Dirección", null=True, blank=True)
    
    # --- Módulo CRM y Libro Negro ---
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPES, default='RETAIL', verbose_name="Tipo de Cliente")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Límite de Crédito (Q)")
    
    # 🔥 EL LIBRO NEGRO 🔥
    is_blacklisted = models.BooleanField(default=False, verbose_name="En Libro Negro (Moroso)")
    blacklist_reason = models.TextField(null=True, blank=True, verbose_name="Motivo de Bloqueo")

    def __str__(self):
        return f"{self.name} ({self.nit})"

# ==========================================
# 1.5 SEGUIMIENTO CRM (Historial de Contacto)
# ==========================================
class CRMInteraction(CompanyAwareModel):
    INTERACTION_TYPES = [('CALL', 'Llamada Telefónica'), ('EMAIL', 'Correo Electrónico'), ('MEETING', 'Reunión Presencial'), ('WHATSAPP', 'Mensaje WhatsApp')]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='interactions')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Vendedor")
    type = models.CharField(max_length=20, choices=INTERACTION_TYPES, verbose_name="Tipo de Contacto")
    date = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora")
    notes = models.TextField(verbose_name="Minuta / Notas de la reunión")
    
    def __str__(self):
        return f"{self.get_type_display()} con {self.client.name}"

# ==========================================
# 2. COTIZACIONES Y PEDIDOS
# ==========================================
class Quotation(CompanyAwareModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Cliente")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Vendedor")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Bodega Origen")
    
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Válida hasta")
    notes = models.TextField(blank=True, verbose_name="Condiciones / Notas")
    
    # Totales
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, default='DRAFT', choices=[
        ('DRAFT', 'Borrador / Cotización'),
        ('SENT', 'Enviada al Cliente'),
        ('APPROVED', 'Pedido de Venta (Aprobado)'), # <-- Agregamos el estatus de Pedido
        ('INVOICED', 'Facturada y Despachada'),
        ('CANCELED', 'Anulada')
    ])

    def __str__(self):
        return f"Doc #{self.id} - {self.client}"

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio Unitario")
    
    # 🔥 NUEVO: EL CUADRO DE DESCUENTO 🔥
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Descuento (%)")
    
    total_line = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        # La matemática mágica: Calcula subtotal y le resta el porcentaje de descuento
        base_total = self.quantity * self.unit_price
        discount_amount = base_total * (self.discount_percent / 100)
        self.total_line = base_total - discount_amount
        super().save(*args, **kwargs)

# ==========================================
# 3. FACTURACIÓN ELECTRÓNICA (FEL)
# ==========================================
class SaleInvoice(CompanyAwareModel): # <-- Corregido para que coincida con tus signals
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador / Pendiente'),
        ('APPROVED', 'Factura Emitida (FEL)'),
        ('CANCELED', 'Anulada'),
    ]
    
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