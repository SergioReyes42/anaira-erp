from django.db import models
from django.utils import timezone
from django.conf import settings

class Duca(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador / En Tránsito'),
        ('CUSTOMS', 'En Aduana (Gestión)'),
        ('LIQUIDATED', 'Liquidada (Costeada en Inventario)'),
        ('CANCELED', 'Anulada'),
    ]

    company = models.CharField(max_length=100, blank=True, null=True)
    
    # 1. Datos Generales de la Póliza
    duca_number = models.CharField(max_length=50, verbose_name="Número de DUCA / Póliza", unique=True)
    date_acceptance = models.DateField(default=timezone.now, verbose_name="Fecha de Aceptación SAT")
    customs_agent = models.CharField(max_length=150, verbose_name="Agente Aduanero", blank=True, null=True)
    supplier_name = models.CharField(max_length=200, verbose_name="Proveedor en el Extranjero")
    
    # 2. Valores Internacionales (Moneda Extranjera - Usualmente USD)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=5, default=7.80000, verbose_name="Tipo de Cambio (BANGUAT)")
    fob_usd = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Valor FOB (USD)")
    freight_usd = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Flete (USD)")
    insurance_usd = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Seguro (USD)")
    
    # 3. Impuestos Aduanales y Liquidación SAT (En Quetzales - GTQ)
    # El CIF se calcula sumando FOB + Flete + Seguro y multiplicando por el tipo de cambio.
    dai_gtq = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="DAI Pagado (Arancel en Q)")
    iva_gtq = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="IVA de Importación (Crédito SAT en Q)")
    other_expenses_gtq = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Otros Gastos (Almacenaje, Tramitador en Q)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name="Estado de la Importación")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "DUCA / Póliza de Importación"
        verbose_name_plural = "DUCAs / Pólizas de Importación"
        ordering = ['-date_acceptance']

    def __str__(self):
        return f"DUCA: {self.duca_number} | {self.supplier_name} | FOB: ${self.fob_usd}"

    @property
    def cif_usd(self):
        """Calcula el valor CIF en Dólares"""
        return self.fob_usd + self.freight_usd + self.insurance_usd

    @property
    def cif_gtq(self):
        """Calcula el valor CIF convertido a Quetzales"""
        return self.cif_usd * self.exchange_rate

    @property
    def total_cost_gtq(self):
        """
        El costo real que se va al inventario.
        Nota: El IVA de importación NO suma al costo del producto, es Crédito Fiscal.
        Costo = CIF(Q) + DAI(Q) + Otros Gastos(Q)
        """
        return self.cif_gtq + self.dai_gtq + self.other_expenses_gtq