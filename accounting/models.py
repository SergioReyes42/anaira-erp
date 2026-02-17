from django.db import models
from django.conf import settings
from core.models import Company 

# ==========================================
# 1. FLOTILLA (VEHÍCULOS)
# ==========================================
class Vehicle(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    brand = models.CharField(max_length=50, verbose_name="Marca")
    line = models.CharField(max_length=50, verbose_name="Línea")
    plate = models.CharField(max_length=20, verbose_name="Placa")
    color = models.CharField(max_length=30, blank=True, verbose_name="Color")
    driver_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Conductor Asignado")
    active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.plate} - {self.brand} {self.line}"

# ==========================================
# 2. GASTOS E INTELIGENCIA ARTIFICIAL
# ==========================================
class Expense(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente de Revisión'),
        ('APPROVED', 'Contabilizado'),
        ('REJECTED', 'Rechazado'),
    ]

    # --- DATOS GENERALES ---
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # --- DATOS DEL DOCUMENTO (IA SCANNER) ---
    receipt_image = models.ImageField(upload_to='expenses_receipts/', verbose_name="Foto Factura")
    description = models.TextField(verbose_name="Descripción del Gasto")
    
    provider_name = models.CharField(max_length=150, verbose_name="Nombre del Proveedor", null=True, blank=True)
    provider_nit = models.CharField(max_length=20, verbose_name="NIT", null=True, blank=True)
    invoice_series = models.CharField(max_length=20, verbose_name="Serie", null=True, blank=True)
    invoice_number = models.CharField(max_length=50, verbose_name="No. Factura", null=True, blank=True)

    # --- RELACIONES ---
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vehículo Asignado")

    # --- CONTABILIDAD ---
    suggested_account = models.CharField(max_length=100, verbose_name="Cuenta Contable Sugerida", default="Gastos Generales")

    # --- DESGLOSE FINANCIERO (MATH) ---
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Factura")
    tax_base = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Base Imponible")
    tax_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="IVA Crédito")
    tax_idp = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Impuesto IDP")

    def __str__(self):
        return f"{self.provider_name or 'Gasto'} - Q{self.total_amount}"

# ==========================================
# 3. BANCOS Y TRANSACCIONES
# ==========================================
class BankAccount(models.Model):
    CURRENCY_CHOICES = [
        ('GTQ', 'Quetzales'),
        ('USD', 'Dólares'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100, verbose_name="Banco")
    account_number = models.CharField(max_length=50, verbose_name="No. Cuenta")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GTQ', verbose_name="Moneda")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Saldo Actual")

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.currency})"

class BankTransaction(models.Model):
    TYPE_CHOICES = [
        ('IN', 'Depósito / Ingreso'),
        ('OUT', 'Retiro / Cheque / Transferencia'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateTimeField(auto_now_add=True)
    transaction_type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=50, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Actualizar saldo de la cuenta automáticamente al crear
        if not self.pk: 
            if self.transaction_type == 'IN':
                self.bank_account.balance += self.amount
            else:
                self.bank_account.balance -= self.amount
            self.bank_account.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - Q{self.amount}"

# ==========================================
# 4. PARTIDAS CONTABLES (LIBRO DIARIO)
# ==========================================

class JournalEntry(models.Model):
    """Encabezado de la Partida Contable"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, verbose_name="Concepto")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    # Vinculamos al gasto original para saber de dónde salió
    expense_ref = models.OneToOneField(Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entry')

    def __str__(self):
        return f"Partida #{self.id} - {self.description}"

class JournalItem(models.Model):
    """Detalle de la Partida (Debe / Haber)"""
    entry = models.ForeignKey(JournalEntry, related_name='items', on_delete=models.CASCADE)
    account_name = models.CharField(max_length=100) # Ej: Combustibles, IVA, IDP, Banco
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  # Debe
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # Haber

    def __str__(self):
        return f"{self.account_name} | D:{self.debit} H:{self.credit}"