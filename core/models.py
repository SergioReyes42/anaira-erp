from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

# ==============================================================================
# 1. NÚCLEO: EMPRESAS, USUARIOS Y PERFILES
# ==============================================================================

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre de la Empresa")
    nit = models.CharField(max_length=20, verbose_name="NIT", default="CF")
    tax_id = models.CharField(max_length=20, unique=True, verbose_name="Identificación Fiscal")
    address = models.TextField(verbose_name="Dirección Legal", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", blank=True, null=True)
    email = models.EmailField(verbose_name="Correo Electrónico", blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_companies')
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        through='UserRoleCompany', 
        related_name='companies_assigned'
    )
    active = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self): return self.name

class CompanyProfile(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre Empresa")
    nit = models.CharField(max_length=20, blank=True, null=True, verbose_name="NIT")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True, verbose_name="Logo")
    
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    currency_symbol = models.CharField(max_length=5, default="Q", verbose_name="Símbolo Moneda")

    def __str__(self): return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    allowed_companies = models.ManyToManyField(Company, verbose_name="Empresas Permitidas")
    active_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_users')

    def __str__(self): return f"Perfil de {self.user.username}"

class Role(models.Model):
    name = models.CharField(max_length=80, unique=True)
    def __str__(self): return self.name

class UserRoleCompany(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    class Meta: unique_together = ("user", "role", "company")

# ==============================================================================
# 2. MODELOS BASE (Vehículos, Tarjetas y Cuentas Contables)
# ==============================================================================

class CreditCard(models.Model):
    bank_name = models.CharField(max_length=100, verbose_name="Banco Emisor")
    alias = models.CharField(max_length=100, verbose_name="Alias (Ej: Visa Gerencia)")
    last_4_digits = models.CharField(max_length=4, verbose_name="Últimos 4 dígitos")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Límite de Crédito")
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Saldo Deuda Actual")
    cutoff_day = models.IntegerField(verbose_name="Día de Corte", help_text="Día del mes")
    
    def __str__(self):
        return f"{self.alias} (Termina en {self.last_4_digits})"

class Vehicle(models.Model):
    brand = models.CharField(max_length=50, verbose_name="Marca")
    model = models.CharField(max_length=50, verbose_name="Modelo")
    plate = models.CharField(max_length=20, unique=True, verbose_name="Placa")
    year = models.IntegerField(verbose_name="Año")
    color = models.CharField(max_length=30, blank=True, null=True)
    assigned_driver = models.CharField(max_length=100, verbose_name="Piloto Asignado", blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('ACTIVO', 'Activo'), ('TALLER', 'En Mantenimiento'), ('BAJA', 'De Baja')], default='ACTIVO')
    
    def __str__(self):
        return f"{self.plate} - {self.brand} {self.model}"

# IMPORTANTE: Account debe ir ANTES de Expense
class Account(models.Model):
    """
    CATÁLOGO DE CUENTAS (NOMENCLATURA NIIF)
    """
    code = models.CharField(max_length=20, unique=True, verbose_name="Código Cuenta")
    name = models.CharField(max_length=200, verbose_name="Nombre de la Cuenta")
    
    TYPE_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PASIVO', 'Pasivo'),
        ('PATRIMONIO', 'Patrimonio/Capital'),
        ('INGRESO', 'Ingresos'),
        ('GASTO', 'Gastos'),
        ('COSTO', 'Costos de Venta'),
    ]
    account_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Tipo de Cuenta")
    
    # Jerarquía (Padre/Hijo)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="Cuenta Padre")
    is_group = models.BooleanField(default=False, verbose_name="¿Es Grupo?", help_text="Marcar si es título de grupo")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Saldo Actual")

    class Meta:
        ordering = ['code']
        verbose_name = "Cuenta Contable"
        verbose_name_plural = "Nomenclatura Contable"

    def __str__(self):
        return f"{self.code} - {self.name}"

# ==============================================================================
# 3. ESTRUCTURA FÍSICA Y LOGÍSTICA
# ==============================================================================

class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    company_profile = models.ForeignKey(CompanyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='branches_profile')
    name = models.CharField(max_length=255, verbose_name="Sucursal")
    code = models.CharField(max_length=20, verbose_name="Código")
    location = models.CharField(max_length=255, verbose_name="Ubicación/Dirección", null=True, blank=True)
    address = models.CharField(max_length=200, verbose_name="Dirección", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", blank=True, null=True)

    def __str__(self): return f"{self.name} ({self.code})"
    class Meta: verbose_name = "Sucursal"; verbose_name_plural = "Sucursales"

class Warehouse(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='warehouses', verbose_name="Sucursal")
    name = models.CharField(max_length=100, verbose_name="Nombre Bodega")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_warehouses', verbose_name="Bodega Padre")
    is_main = models.BooleanField(default=False, verbose_name="¿Principal?")
    active = models.BooleanField(default=True, verbose_name="Activa")
    
    def __str__(self):
        if self.parent: return f"{self.branch.name} | {self.parent.name} > {self.name}"
        return f"{self.branch.name} | {self.name}"

    class Meta: verbose_name = "Bodega"; verbose_name_plural = "Bodegas"

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre Producto")
    code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código/SKU")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Venta")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    stock = models.IntegerField(default=0, verbose_name="Stock Físico")
    stock_reserved = models.IntegerField(default=0, verbose_name="Apartado en Cotizaciones")
    def __str__(self): return f"{self.name} ({self.code})"
    @property
    def available_stock(self): return self.stock - self.stock_reserved

class Inventory(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Bodega")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    quantity = models.IntegerField(default=0, verbose_name="Existencia Actual")
    min_stock = models.IntegerField(default=5, verbose_name="Stock Mínimo en esta Bodega")
    location = models.CharField(max_length=50, verbose_name="Ubicación/Estante", blank=True, null=True)
    class Meta: unique_together = ('warehouse', 'product'); verbose_name = "Inventario por Bodega"; verbose_name_plural = "Inventarios por Bodega"
    def __str__(self): return f"{self.product.name} en {self.warehouse.name}: {self.quantity}"

# ==============================================================================
# 4. TESORERÍA, INGRESOS Y GASTOS (CORE)
# ==============================================================================

class BankAccount(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, verbose_name="Empresa")
    bank_name = models.CharField(max_length=50, verbose_name="Nombre del Banco")
    account_number = models.CharField(max_length=50, verbose_name="Número de Cuenta")
    currency = models.CharField(max_length=3, default='GTQ', verbose_name="Moneda")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Actual")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.bank_name} - {self.account_number}"
    class Meta: verbose_name = "Cuenta Bancaria"; verbose_name_plural = "Cuentas Bancarias"

class BankTransaction(models.Model):
    MOVEMENT_CHOICES = (('IN', 'Entrada / Depósito'), ('OUT', 'Salida / Retiro'))
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Fecha")
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_CHOICES, default='OUT')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia")
    evidence = models.ImageField(upload_to='bank_evidence/', blank=True, null=True, verbose_name="Comprobante")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.get_movement_type_display()} - Q{self.amount}"

class BankMovement(models.Model):
    TYPES = (('IN', 'Depósito'), ('OUT', 'Retiro/Cheque'))
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='movements')
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    movement_type = models.CharField(max_length=3, choices=TYPES)
    category = models.CharField(max_length=50, default="General")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Monto")
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia / No. Cheque")
    evidence = models.ImageField(upload_to='bank_movements/', null=True, blank=True, verbose_name="Comprobante")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.pk: 
            if self.movement_type == 'IN': self.account.balance += self.amount
            else: self.account.balance -= self.amount
            self.account.save()
        super().save(*args, **kwargs)

class Income(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    description = models.CharField(max_length=200, verbose_name="Descripción / Cliente")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto Total")
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cuenta Destino")
    reference_doc = models.CharField(max_length=50, blank=True, verbose_name="No. Factura/Recibo")
    evidence = models.ImageField(upload_to='incomes/', blank=True, null=True, verbose_name="Comprobante")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.description} - Q{self.amount}"

# GASTOS: Ahora ya conoce 'Account', 'Vehicle' y 'CreditCard'
class Expense(models.Model):
    # Relación con Usuario
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Datos Factura
    date = models.DateField(verbose_name="Fecha")
    provider = models.CharField(max_length=200, verbose_name="Proveedor")
    description = models.CharField(max_length=255, verbose_name="Concepto")
    invoice_file = models.FileField(upload_to='gastos/', blank=True, null=True, verbose_name="Factura")
    
    # Montos
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Factura")
    idp_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="IDP")
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="IVA Crédito")
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo/Gasto")
    
    # Lógica Combustible
    is_fuel = models.BooleanField(default=False, verbose_name="Es Combustible")
    
    # Relaciones
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vehículo")
    
    # Método de Pago
    PAYMENT_METHODS = [
        ('CASH', 'Efectivo / Caja Chica'),
        ('CARD', 'Tarjeta de Crédito / Débito'),
        ('TRANSFER', 'Transferencia Bancaria'),
        ('CHECK', 'Cheque'),
        ('CREDIT', 'Crédito (Cuenta por Pagar)'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH', verbose_name="Método de Pago")
    
    # Vinculación con Tarjeta
    credit_card = models.ForeignKey(CreditCard, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tarjeta Usada")

    # Estados (Flujo Piloto -> Contador)
    STATUS_CHOICES = [
        ('PENDING', '🟡 Pendiente (Solo Foto)'),
        ('APPROVED', '🟢 Aprobado y Contabilizado'),
        ('REJECTED', '🔴 Rechazado'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='APPROVED')
    
    # ID legado
    accounting_entry_id = models.IntegerField(blank=True, null=True, verbose_name="ID Partida (Legacy)")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.provider} (Q{self.total_amount})"

# ==============================================================================
# 5. CONTABILIDAD (PARTIDAS Y DETALLES)
# ==============================================================================

class JournalEntry(models.Model):
    """
    ENCABEZADO DE PARTIDA (ASIENTO CONTABLE)
    """
    date = models.DateField(verbose_name="Fecha Contable")
    description = models.CharField(max_length=255, verbose_name="Descripción / Glosa")
    reference = models.CharField(max_length=100, blank=True, verbose_name="Referencia (Doc/Fac)")
    
    # Vínculo automático con GASTOS (Si viene de un gasto, se guarda aquí)
    expense = models.OneToOneField(Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entry', verbose_name="Origen Gasto")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_posted = models.BooleanField(default=False, verbose_name="Asentada (Definitiva)")
    
    class Meta:
        ordering = ['-date', '-id']
        verbose_name = "Partida Diario"
        verbose_name_plural = "Libro Diario"

    def __str__(self):
        return f"Partida #{self.id} | {self.date}"

class JournalItem(models.Model):
    """
    DETALLE DE PARTIDA (LÍNEAS)
    """
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name="Cuenta")
    
    description = models.CharField(max_length=255, blank=True, verbose_name="Concepto de Línea")
    
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Debe")
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Haber")
    
    def __str__(self):
        return f"{self.account.code} | D:{self.debit} H:{self.credit}"

# ==============================================================================
# 6. CLIENTES, PROVEEDORES Y TRANSACCIONES COMERCIALES
# ==============================================================================

class Client(models.Model):
    name = models.CharField(max_length=200, verbose_name="Razón Social / Nombre")
    nit = models.CharField(max_length=20, verbose_name="NIT", unique=True)
    address = models.CharField(max_length=255, verbose_name="Dirección Fiscal", blank=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", blank=True)
    email = models.EmailField(verbose_name="Email Facturación", blank=True)
    contact_name = models.CharField(max_length=100, verbose_name="Nombre de Contacto", blank=True)
    credit_days = models.IntegerField(default=0, verbose_name="Días de Crédito")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Límite de Crédito")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    company = models.ForeignKey(CompanyProfile, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self): return f"{self.name} ({self.nit})"

class Supplier(models.Model):
    company = models.ForeignKey('CompanyProfile', on_delete=models.CASCADE, verbose_name="Empresa", null=True, blank=True)
    name = models.CharField(max_length=200, verbose_name="Razón Social / Nombre")
    nit = models.CharField(max_length=20, verbose_name="NIT / RUT", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", blank=True, null=True)
    email = models.EmailField(verbose_name="Correo Electrónico", blank=True, null=True)
    address = models.TextField(verbose_name="Dirección", blank=True, null=True)
    contact_name = models.CharField(max_length=100, verbose_name="Nombre de Contacto", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.name
    class Meta: verbose_name = "Proveedor"; verbose_name_plural = "Proveedores"

class Provider(models.Model): # LEGACY
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, verbose_name="Empresa")
    name = models.CharField(max_length=100, verbose_name="Razón Social / Nombre")
    nit = models.CharField(max_length=20, blank=True, verbose_name="NIT")
    contact_name = models.CharField(max_length=100, blank=True, verbose_name="Contacto")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, verbose_name="Email")
    def __str__(self): return self.name
    class Meta: verbose_name = "Proveedor (Simple)"; verbose_name_plural = "Proveedores (Simple)"

class BusinessPartner(models.Model): # LEGACY
    TYPES = (('C', 'Cliente'), ('P', 'Proveedor'), ('A', 'Ambos'))
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, verbose_name="Razón Social / Nombre")
    tax_id = models.CharField(max_length=20, verbose_name="NIT") 
    nit = models.CharField(max_length=20, blank=True, null=True, verbose_name="NIT (Opcional)")
    type = models.CharField(max_length=10, choices=TYPES, default='CLIENTE', verbose_name="Tipo Texto")
    partner_type = models.CharField(max_length=1, choices=TYPES, default='P', verbose_name="Tipo Código")
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco del Proveedor")
    bank_account = models.CharField(max_length=50, blank=True, null=True, verbose_name="No. Cuenta Proveedor")
    account_type = models.CharField(max_length=50, blank=True, null=True, default="Monetaria", verbose_name="Tipo Cuenta")
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name} ({self.get_partner_type_display()})"

# ==============================================================================
# 7. VENTAS Y COMPRAS (OPERATIVO)
# ==============================================================================

class Quotation(models.Model):
    STATUS_CHOICES = [('DRAFT', 'Borrador (Aparta Stock)'), ('BILLED', 'Facturada (Rebaja Stock)'), ('CANCELED', 'Cancelada (Libera Stock)')]
    PAYMENT_CHOICES = [('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('CHEQUE', 'Cheque'), ('CREDITO', 'Crédito / Por Cobrar')]
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)    
    date = models.DateField(default=timezone.now)
    valid_until = models.DateField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observation = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='EFECTIVO', verbose_name="Método de Pago")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Cotización #{self.id} - {self.client.name}"

class QuotationDetail(models.Model):
    quotation = models.ForeignKey(Quotation, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self): return f"{self.quantity} x {self.product.name}"

class Sale(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, verbose_name="Empresa")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name="Cliente")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Venta")
    quotation_origin = models.OneToOneField(Quotation, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cotización Origen")
    payment_method = models.CharField(max_length=50, choices=[('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('CHEQUE', 'Cheque'), ('CREDITO', 'Crédito / Por Cobrar')], default='EFECTIVO', verbose_name="Método de Pago")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vendedor")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name="No. Factura/Recibo")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, verbose_name="Sucursal de Facturación")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Bodega de Despacho")
    def __str__(self): return f"Venta #{self.id} - {self.client.name}"
    class Meta: verbose_name = "Venta"; verbose_name_plural = "Ventas"

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.quantity} x {self.product.name}"

class Purchase(models.Model):
    STATUS_CHOICES = [('DRAFT', 'Borrador'), ('RECEIVED', 'Recibido / Inventario Cargado'), ('CANCELLED', 'Cancelada')]
    PAYMENT_METHODS = [('CASH', 'Efectivo'), ('TRANSFER', 'Transferencia Bancaria'), ('CARD', 'Tarjeta de Crédito/Débito'), ('CHECK', 'Cheque'), ('CREDIT', 'Crédito (Por Pagar)')]
    company = models.ForeignKey('CompanyProfile', on_delete=models.CASCADE, verbose_name="Empresa")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Comprador")
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name="Proveedor", null=True, blank=True)
    date = models.DateField(default=timezone.now, verbose_name="Fecha de Compra")
    document_reference = models.CharField(max_length=50, verbose_name="No. Factura Proveedor", blank=True, null=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Bodega de Entrada")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH', verbose_name="Método de Pago")
    payment_reference = models.CharField(max_length=100, verbose_name="Cuenta / Referencia / Tarjeta", blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RECEIVED', verbose_name="Estado")
    description = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Compra #{self.id} - {self.supplier.name if self.supplier else 'Desconocido'}"
    class Meta: verbose_name = "Compra"; verbose_name_plural = "Compras"

class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
    def __str__(self): return f"{self.quantity} x {self.product.name}"

@receiver(post_save, sender=PurchaseDetail)
def update_inventory_on_purchase(sender, instance, created, **kwargs):
    if created: 
        producto = instance.product
        producto.stock += instance.quantity
        producto.save()

class Invoice(models.Model):
    client = models.ForeignKey('Client', on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    due_date = models.DateField() # Fecha de vencimiento
    payment_method = models.CharField(max_length=50, choices=[('CONTADO', 'Contado'), ('CREDITO', 'Crédito')])
    
    # Datos Fiscales
    fel_uuid = models.CharField(max_length=100, blank=True, null=True, verbose_name="UUID Fiscal")
    fel_series = models.CharField(max_length=50, blank=True, null=True)
    fel_number = models.CharField(max_length=50, blank=True, null=True)
    
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Relación con la cotización original
    origin_quotation = models.ForeignKey('Quotation', on_delete=models.SET_NULL, null=True, blank=True)
    
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Factura #{self.id} - {self.client.name}"

class InvoiceDetail(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='details', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price

class StockMovement(models.Model):
    MOVEMENT_TYPES = [('IN_PURCHASE', 'Entrada por Compra'), ('OUT_SALE', 'Salida por Venta'), ('TRANSFER_OUT', 'Salida por Traslado'), ('TRANSFER_IN', 'Entrada por Traslado'), ('ADJUST_ADD', 'Ajuste (Entrada)'), ('ADJUST_SUB', 'Ajuste (Salida)')]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, verbose_name="Bodega Afectada")
    quantity = models.IntegerField(verbose_name="Cantidad")
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name="Tipo de Movimiento")
    related_purchase = models.ForeignKey('Purchase', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ref. Compra")
    related_sale = models.ForeignKey('Sale', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ref. Venta")
    related_transfer_id = models.IntegerField(null=True, blank=True, help_text="ID del grupo de traslado")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Responsable")
    comments = models.CharField(max_length=200, blank=True, null=True, verbose_name="Comentario/Razón")
    def __str__(self): return f"{self.get_movement_type_display()}: {self.quantity} de {self.product.code}"
    class Meta: verbose_name = "Movimiento de Kardex"; verbose_name_plural = "Kardex (Historial)"; ordering = ['-date']

class InventoryMovement(models.Model): # LEGACY
    TYPE_CHOICES = [('IN', 'Entrada'), ('OUT', 'Salida')]
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    date = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=200)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='inventory_history_legacy')
    def __str__(self): return f"{self.type} {self.quantity} - {self.product.name}"

# ==============================================================================
# 8. RECURSOS HUMANOS (RRHH)
# ==============================================================================

class Employee(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Nombres")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    dpi = models.CharField(max_length=20, verbose_name="DPI", unique=True)
    nit = models.CharField(max_length=20, verbose_name="NIT", blank=True, null=True)
    address = models.CharField(max_length=200, verbose_name="Dirección")
    phone = models.CharField(max_length=20, verbose_name="Teléfono")
    position = models.CharField(max_length=100, verbose_name="Puesto")
    department = models.CharField(max_length=100, verbose_name="Departamento")
    date_hired = models.DateField(verbose_name="Fecha Contratación")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salario Base")
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Bonificación")
    igss_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="No. IGSS")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario de Sistema")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sucursal Asignada")
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self): return f"{self.first_name} {self.last_name}"
    class Meta: verbose_name = "Empleado"; verbose_name_plural = "Empleados"

class Loan(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Empleado")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Préstamo")
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cuota Mensual")
    balance = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Pendiente")
    reason = models.CharField(max_length=200, verbose_name="Motivo")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    def __str__(self): return f"Préstamo {self.employee.first_name} - Q{self.balance}"

class Payroll(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='core_payrolls')
    month = models.IntegerField(verbose_name="Mes")
    year = models.IntegerField(verbose_name="Año")
    date_generated = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_closed = models.BooleanField(default=False, verbose_name="Cerrada")
    def __str__(self): return f"Nómina {self.month}/{self.year}"

class PayrollDetail(models.Model):
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2)
    igss_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    loan_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    isr_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_income = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self): return f"Detalle {self.employee.first_name} - {self.payroll}"

# ==============================================================================
# 9. SIGNALS (DISPARADORES AUTOMÁTICOS)
# ==============================================================================

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Usa get_or_create para evitar errores de duplicidad
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except:
        pass