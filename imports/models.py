from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class PurchaseOrder(models.Model):
    """Orden de Compra Internacional a Proveedor"""
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente de Envío'),
        ('IN_TRANSIT', 'En Tránsito (Asignada a DUCA)'),
        ('RECEIVED', 'Recibida en Bodega'),
        ('CANCELLED', 'Cancelada'),
    ]

    po_number = models.CharField(max_length=50, unique=True, verbose_name="No. Orden de Compra")
    supplier_name = models.CharField(max_length=150, verbose_name="Proveedor")
    issue_date = models.DateField(auto_now_add=True, verbose_name="Fecha de Emisión")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Monto Total ($)")

    class Meta:
        verbose_name = "Orden de Compra"
        verbose_name_plural = "Órdenes de Compra"

    def __str__(self):
        return f"{self.po_number} - {self.supplier_name} (${self.total_amount_usd})"

class Duca(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', '1. Borrador / En Tránsito'),
        ('CUSTOMS', '2. En Aduana (Gestión)'),
        ('LIQUIDATED', '3. Liquidada (Costo calculado)'),
        ('RECEIVED', '4. Recibida en Bodega'),
        ('CANCELED', 'Anulada'),
    ]

    company = models.CharField(max_length=100, blank=True, null=True)
    
    # DATOS GENERALES
    duca_number = models.CharField(max_length=50, verbose_name="Número de DUCA / Póliza", unique=True)
    purchase_orders = models.ManyToManyField(PurchaseOrder, blank=True, related_name='ducas', verbose_name="Órdenes de Compra Vinculadas")
    date_acceptance = models.DateField(default=timezone.now, verbose_name="Fecha de Aceptación SAT")
    customs_agent = models.CharField(max_length=150, verbose_name="Agente Aduanero", blank=True, null=True)
    supplier_name = models.CharField(max_length=200, verbose_name="Proveedor (Extranjero)")
    
    # FACTORES MACRO (Lo que dicta la SAT y Banguat)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=5, default=7.80000, verbose_name="Tipo de Cambio (GTQ/USD)")
    
    # GASTOS GLOBALES EN DÓLARES (Para el CIF)
    freight_usd = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Flete Total (USD)")
    insurance_usd = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Seguro Total (USD)")
    
    # IMPUESTOS Y GASTOS LOCALES EN QUETZALES
    iva_gtq = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="IVA de Importación (Crédito SAT en Q)")
    other_expenses_gtq = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Otros Gastos (Almacenaje, Tramitador, etc. en Q)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "DUCA / Póliza"
        verbose_name_plural = "DUCAs / Pólizas"
        ordering = ['-date_acceptance']

    def __str__(self):
        return f"{self.duca_number} | {self.supplier_name}"

    @property
    def total_fob_usd(self):
        """Suma el FOB de todos los productos dentro de esta DUCA"""
        return sum(item.fob_total_usd for item in self.items.all())

    @property
    def total_cif_usd(self):
        """FOB + Flete + Seguro"""
        return self.total_fob_usd + self.freight_usd + self.insurance_usd

    @property
    def total_dai_gtq(self):
        """Suma de los aranceles individuales de cada producto"""
        return sum(item.calculated_dai_gtq for item in self.items.all())

    @property
    def total_import_cost_gtq(self):
        """Costo total de la importación puesto en bodega (Sin IVA)"""
        cif_gtq = self.total_cif_usd * self.exchange_rate
        return cif_gtq + self.total_dai_gtq + self.other_expenses_gtq


class DucaItem(models.Model):
    """Los productos que vienen dentro del contenedor/paquete"""
    duca = models.ForeignKey(Duca, on_delete=models.CASCADE, related_name='items')
    
    # Aquí en el futuro puedes enlazarlo con tu modelo de Inventario:
    # product = models.ForeignKey('inventory.Product', on_delete=models.SET_NULL, null=True)
    product_code = models.CharField(max_length=50, verbose_name="SKU / Código")
    description = models.CharField(max_length=200, verbose_name="Descripción del Producto")
    
    quantity = models.IntegerField(verbose_name="Cantidad")
    fob_unit_usd = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Costo Unitario FOB (USD)")
    
    # SAT: Cada producto tiene su propio arancel (Ej: Laptops 0%, Ropa 15%)
    dai_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="Tasa DAI (%)")

    class Meta:
        verbose_name = "Producto Importado"
        verbose_name_plural = "Productos Importados"

    @property
    def fob_total_usd(self):
        return Decimal(self.quantity) * self.fob_unit_usd

    @property
    def factor_prorrateo(self):
        """¿Qué porcentaje del contenedor ocupa este producto en valor?"""
        total_fob_duca = self.duca.total_fob_usd
        if total_fob_duca == 0:
            return Decimal('0.00')
        return self.fob_total_usd / total_fob_duca

    @property
    def calculated_cif_usd(self):
        """Le inyecta su porción exacta de flete y seguro a este producto"""
        flete_asignado = self.duca.freight_usd * self.factor_prorrateo
        seguro_asignado = self.duca.insurance_usd * self.factor_prorrateo
        return self.fob_total_usd + flete_asignado + seguro_asignado

    @property
    def calculated_dai_gtq(self):
        """Calcula el arancel en Quetzales sobre el valor CIF de este producto"""
        cif_gtq = self.calculated_cif_usd * self.duca.exchange_rate
        return cif_gtq * (self.dai_rate / Decimal('100.00'))

    @property
    def final_unit_cost_gtq(self):
        """EL DATO MÁS IMPORTANTE: El costo real unitario para tu inventario en Quetzales"""
        # 1. CIF en Quetzales
        cif_gtq = self.calculated_cif_usd * self.duca.exchange_rate
        
        # 2. Le sumamos su DAI
        dai_gtq = self.calculated_dai_gtq
        
        # 3. Le inyectamos su porción de los "Otros Gastos" (Almacenaje aduanal)
        otros_gastos_asignados = self.duca.other_expenses_gtq * self.factor_prorrateo
        
        # Costo Total del lote de este producto
        costo_total_lote = cif_gtq + dai_gtq + otros_gastos_asignados
        
        # Costo Unitario
        if self.quantity == 0:
            return Decimal('0.00')
        return costo_total_lote / Decimal(self.quantity)

    def __str__(self):
        return f"{self.quantity}x {self.description} | Costo Final: Q.{self.final_unit_cost_gtq:.2f}"

class TrackingEvent(models.Model):
    """Línea de tiempo para saber dónde viene el contenedor"""
    EVENT_CHOICES = [
        ('FACTORY', '1. En Planta del Proveedor (Extranjero)'),
        ('DEPARTURE', '2. Salida de Puerto/Aeropuerto Origen'),
        ('TRANSIT', '3. En Tránsito (Marítimo/Aéreo)'),
        ('ARRIVAL', '4. Llegada a Puerto en Guatemala (Santo Tomás/Quetzal)'),
        ('CUSTOMS', '5. En Trámite Aduanal (Retenido/Revisión)'),
        ('DISPATCHED', '6. Liberado y en Ruta a Bodega Sermaworld'),
    ]

    duca = models.ForeignKey(Duca, on_delete=models.CASCADE, related_name='tracking_events')
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES, verbose_name="Tipo de Evento")
    event_date = models.DateField(default=timezone.now, verbose_name="Fecha del Evento")
    location = models.CharField(max_length=150, verbose_name="Ubicación / Puerto", help_text="Ej: Puerto Shenzen, Miami, Puerto Quetzal")
    notes = models.TextField(blank=True, null=True, verbose_name="Observaciones / Novedades")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de Tracking"
        verbose_name_plural = "Tracking de Contenedores"
        ordering = ['-event_date', '-created_at'] # Ordena del más reciente al más antiguo

    def __str__(self):
        return f"{self.get_event_type_display()} - {self.location}"


class WarehouseReception(models.Model):
    """Acta de Recepción: El documento que firma el bodeguero al recibir el contenedor"""
    duca = models.OneToOneField(Duca, on_delete=models.CASCADE, related_name='reception', verbose_name="Póliza DUCA")
    
    reception_date = models.DateTimeField(default=timezone.now, verbose_name="Fecha y Hora de Recepción")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Recibido por (Bodeguero)")
    
    # Checklists de seguridad al abrir el contenedor
    seal_intact = models.BooleanField(default=True, verbose_name="¿Marchamo de seguridad intacto?")
    condition = models.CharField(max_length=100, default='Excelente - Mercadería en buen estado', verbose_name="Condición de la Carga")
    damages_notes = models.TextField(blank=True, null=True, verbose_name="Notas de Daños o Faltantes")
    
    # Estado de la integración con el Kardex
    integrated_to_inventory = models.BooleanField(default=False, verbose_name="¿Integrado al Kardex?")

    class Meta:
        verbose_name = "Recepción de Bodega"
        verbose_name_plural = "Recepciones de Bodegas"

    def __str__(self):
        return f"Recepción de {self.duca.duca_number} el {self.reception_date.strftime('%d/%m/%Y')}"