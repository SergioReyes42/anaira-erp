from django.db import models
from django.conf import settings
from core.models import Company

# --- 1. CATÁLOGO DE CUENTAS (PLAN DE CUENTAS) ---
class Account(models.Model):
    TYPE_CHOICES = [
        ('ASSET', 'Activo'),
        ('LIABILITY', 'Pasivo'),
        ('EQUITY', 'Patrimonio/Capital'),
        ('INCOME', 'Ingresos'),
        ('EXPENSE', 'Gastos'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='accounts')
    code = models.CharField(max_length=20, verbose_name="Código Contable") # Ej: 1.1.01
    name = models.CharField(max_length=100, verbose_name="Nombre de la Cuenta") # Ej: Caja General
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Es cuenta padre? (Ej: "Activo Corriente" agrupa a "Caja")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_group = models.BooleanField(default=False, verbose_name="Es cuenta agrupadora")

    class Meta:
        unique_together = ('company', 'code') # No repetir códigos en la misma empresa
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

# --- 2. ENCABEZADO DE PARTIDA (JOURNAL ENTRY) ---
class JournalEntry(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Fecha Contable")
    description = models.TextField(verbose_name="Concepto/Descripción")
    reference = models.CharField(max_length=50, blank=True, null=True) # Ej: "Factura-123"
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Partida #{self.id} - {self.date}"

    @property
    def total_debit(self):
        return sum(item.debit for item in self.items.all())

    @property
    def total_credit(self):
        return sum(item.credit for item in self.items.all())
    
    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

# --- 3. DETALLE DE PARTIDA (DEBE Y HABER) ---
class JournalItem(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey(Account, on_delete=models.PROTECT) # Si borras la cuenta, no borres el historial
    description = models.CharField(max_length=200, blank=True, null=True) # Por si quieres detalle por línea
    
    debit = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Debe")
    credit = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Haber")

    def __str__(self):
        return f"{self.account.code} | D:{self.debit} C:{self.credit}"