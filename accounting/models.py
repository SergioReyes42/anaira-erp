from django.db import models
from django.conf import settings
from core.models import Company 
from django.utils import timezone

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

    # NUEVO CAMPO: Relación real con los usuarios del sistema
    conductores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='vehiculos_asignados',
        blank=True,
        verbose_name="Pilotos Asignados",
        help_text="Selecciona los usuarios que manejan este vehículo."
    )
    
    def __str__(self):
        return f"{self.plate} - {self.brand} {self.line}"

# ==========================================
# 2. GASTOS E INTELIGENCIA ARTIFICIAL
# ==========================================
class Expense(models.Model):
    STATUS_CHOICES = [
        ('PRE_REVIEW', 'Filtro de Supervisores'), 
        ('PENDING', 'Pendiente de Revisión'),
        ('APPROVED', 'Contabilizado'),
        ('REJECTED', 'Rechazado'),
    ]
    
    ORIGIN_CHOICES = [
        ('PILOT', 'App Piloto'),
        ('SCANNER', 'Smart Scanner IA'),
        ('MANUAL', 'Ingreso Manual'),
    ]

    METODOS_PAGO = [
        ('EFECTIVO', '💵 Efectivo'),
        ('TARJETA', '💳 Tarjeta de Crédito / Débito'),
    ]
    payment_method = models.CharField(
        max_length=20, 
        choices=METODOS_PAGO, 
        default='EFECTIVO', 
        verbose_name="¿Cómo se pagó?"
    )
    # --- DATOS GENERALES ---
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default='MANUAL')

    # --- DATOS DEL DOCUMENTO ---
    receipt_image = models.ImageField(upload_to='expenses_receipts/', verbose_name="Foto Factura")
    
    # --- CAMPOS ANTIFRAUDE ---
    pump_image = models.ImageField(upload_to='expenses_pumps/', null=True, blank=True, verbose_name="Foto de la Bomba")
    latitude = models.CharField(max_length=50, null=True, blank=True, verbose_name="Latitud GPS")
    longitude = models.CharField(max_length=50, null=True, blank=True, verbose_name="Longitud GPS")
    
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

    # --- FLUJO DE APROBACIÓN ---
    supervisor_1_ok = models.BooleanField(default=False, verbose_name="VoBo. Supervisor 1")
    supervisor_2_ok = models.BooleanField(default=False, verbose_name="VoBo. Supervisor 2")
    assistant_ok = models.BooleanField(default=False, verbose_name="VoBo. Asistente")

    def check_and_advance_status(self):
        if self.supervisor_1_ok and self.supervisor_2_ok and self.assistant_ok:
            if self.status == 'PRE_REVIEW':
                self.status = 'PENDING'
                self.save()

    def __str__(self):
        return f"{self.provider_name or 'Gasto'} - Q{self.total_amount}"

# ==========================================
# 3. BANCOS Y TRANSACCIONES
# ==========================================
class BankAccount(models.Model):
    """Bóveda principal: Las cuentas bancarias de la empresa"""
    CURRENCY_CHOICES = [
        ('GTQ', 'Quetzales (Q)'),
        ('USD', 'Dólares ($)'),
    ]

    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100, verbose_name="Nombre del Banco (Ej. Banrural, BI)")
    account_name = models.CharField(max_length=100, verbose_name="Nombre de la Cuenta")
    account_number = models.CharField(max_length=50, verbose_name="Número de Cuenta")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GTQ')
    
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Inicial al 1 de Enero")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Actual")
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.currency})"
    
    @property
    def saldo_actual(self):
        from .models import BankTransaction 
        from django.db.models import Sum
        
        depositos = BankTransaction.objects.filter(account=self, transaction_type='IN').aggregate(total=Sum('amount'))['total'] or 0
        retiros = BankTransaction.objects.filter(account=self, transaction_type='OUT').aggregate(total=Sum('amount'))['total'] or 0
        return self.initial_balance + depositos - retiros

class BankTransaction(models.Model):
    """Registro de movimientos: El libro mayor del banco"""
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Depósito / Ingreso'),
        ('WITHDRAWAL', 'Retiro / Cheque / Gasto'),
    ]

    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions')
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    date = models.DateField(verbose_name="Fecha del Movimiento")
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    
    reference = models.CharField(max_length=100, verbose_name="No. de Boleta / Cheque / Transferencia")
    description = models.TextField(verbose_name="Concepto detallado")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - Q{self.amount} - {self.date}"

# ==========================================
# 4. PARTIDAS CONTABLES (LIBRO DIARIO)
# ==========================================
class Account(models.Model):
    """El Catálogo de Cuentas (NIIF)"""
    code = models.CharField(max_length=20, unique=True, verbose_name="Código NIIF")
    name = models.CharField(max_length=100, verbose_name="Nombre de la Cuenta")
    ACCOUNT_TYPES = [
        ('ASSET', 'Activo'),
        ('LIABILITY', 'Pasivo'),
        ('EQUITY', 'Patrimonio'),
        ('REVENUE', 'Ingresos'),
        ('EXPENSE', 'Gastos'),
    ]
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES)
    is_transactional = models.BooleanField(default=True, verbose_name="Acepta Movimientos") 

    def __str__(self):
        return f"{self.code} - {self.name}"

class JournalEntry(models.Model):
    """La Partida Contable o Asiento de Diario"""
    date = models.DateField(default='2026-01-01', verbose_name="Fecha de Partida")    
    concept = models.CharField(max_length=255, verbose_name="Concepto General")
    company = models.CharField(max_length=100, blank=True, null=True) 
    
    is_opening_balance = models.BooleanField(default=False, verbose_name="Es Asiento de Apertura")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Partida {self.id} - {self.date} - {self.concept}"

class JournalEntryLine(models.Model):
    """Los detalles del Debe y Haber de la partida"""
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name="Cuenta Contable")
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Debe")
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Haber")

    def __str__(self):
        return f"{self.account.name} | Debe: {self.debit} | Haber: {self.credit}"
    
class JournalItem(models.Model):
    entry = models.ForeignKey(JournalEntry, related_name='items', on_delete=models.CASCADE)
    account_name = models.CharField(max_length=100)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.account_name} | D:{self.debit} H:{self.credit}"
    
class AccountingPeriod(models.Model):
    company = models.CharField(max_length=100, blank=True, null=True)
    year = models.IntegerField(verbose_name="Año Fiscal")
    month = models.IntegerField(verbose_name="Mes")
    is_closed = models.BooleanField(default=False, verbose_name="¿Mes Cerrado?")
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('company', 'year', 'month')

    def __str__(self):
        estado = "CERRADO" if self.is_closed else "ABIERTO"
        return f"{self.month}/{self.year} - {estado}"

# ==========================================
# 5. NUEVO MÓDULO DE AUDITORÍA DE GASTOS
# ==========================================
class GastoOperativo(models.Model):
    TIPO_GASTO_CHOICES = [
        ('combustible', 'Combustible'),
        ('repuestos', 'Repuestos'),
        ('mantenimiento', 'Mantenimiento'),
    ]

    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta (Crédito/Débito)'),
    ]

    ESTADO_CHOICES = [
        ('En_Supervision', 'En Supervisión'),
        ('Pendiente_Contabilidad', 'Pendiente Contabilidad'),
        ('Rechazado', 'Rechazado'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gastos')
    
    # 🔥 AQUÍ ESTÁ EL ARREGLO PRINCIPAL: Conectado a 'Vehicle'
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    
    date = models.DateTimeField(auto_now_add=True)
    tipo_gasto = models.CharField(max_length=20, choices=TIPO_GASTO_CHOICES, default='combustible')
    payment_method = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='EFECTIVO')
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    receipt_image = models.ImageField(upload_to='gastos/facturas/')
    pump_image = models.ImageField(upload_to='gastos/bombas/', null=True, blank=True)

    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)

    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES, default='En_Supervision')
    supervisor_1_ok = models.BooleanField(default=False)
    supervisor_2_ok = models.BooleanField(default=False)
    assistant_ok = models.BooleanField(default=False)

    def __str__(self):
        return f"Gasto {self.id} - {self.user.username} - {self.get_tipo_gasto_display()}"

    def verificar_pase_contabilidad(self):
        if self.supervisor_1_ok and self.supervisor_2_ok and self.assistant_ok:
            self.estado = 'Pendiente_Contabilidad'
            self.save()

# ==========================================
# 6. TARJETAS DE CRÉDITO Y CXP
# ==========================================
class CreditCard(models.Model):
    """Bóveda de Pasivo: Control de Tarjetas de Crédito Empresariales"""
    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='credit_cards')
    bank_name = models.CharField(max_length=100, verbose_name="Banco Emisor (Ej. Promerica, BAC)")
    card_name = models.CharField(max_length=100, verbose_name="Nombre en la Tarjeta (Ej. Visa Flotilla 1)")
    last_four_digits = models.CharField(max_length=4, verbose_name="Últimos 4 dígitos")
    
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Límite de Crédito")
    cutoff_day = models.IntegerField(verbose_name="Día de Corte (1-31)")
    payment_day = models.IntegerField(verbose_name="Día de Pago (1-31)")
    
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Deuda Actual (Saldo Consumido)")
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.card_name} termina en {self.last_four_digits} - Deuda: Q.{self.current_debt}"
        
    @property
    def available_credit(self):
        return self.credit_limit - self.current_debt
    
    @property
    def debt_percentage(self):
        if self.credit_limit > 0:
            return (self.current_debt / self.credit_limit) * 100
        return 0

class AccountPayable(models.Model):
    """Módulo CxP: Control de Cuentas por Pagar a Proveedores"""
    
    STATUS_CHOICES = [
        ('PENDIENTE', 'Pendiente de Pago'),
        ('PARCIAL', 'Pago Parcial'),
        ('PAGADO', 'Pagado / Liquidado'),
    ]

    company = models.ForeignKey('core.Company', on_delete=models.CASCADE, related_name='accounts_payable')
    
    supplier_name = models.CharField(max_length=200, verbose_name="Nombre del Proveedor")
    invoice_number = models.CharField(max_length=100, verbose_name="No. de Factura / Recibo")
    description = models.TextField(verbose_name="Concepto de la Deuda")
    
    issue_date = models.DateField(verbose_name="Fecha de Emisión")
    due_date = models.DateField(verbose_name="Fecha de Vencimiento límite")
    
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Total Original")
    balance = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Saldo Pendiente Actual")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDIENTE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.supplier_name} - Fac: {self.invoice_number} (Debe: Q.{self.balance})"
        
    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.balance > 0 and self.due_date < timezone.now().date()