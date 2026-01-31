from django.db import models
from django.conf import settings
from django.utils import timezone

# ==========================================
# 1. ESTRUCTURA EMPRESARIAL Y SEGURIDAD
# ==========================================

class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre de la Empresa")
    nit = models.CharField(max_length=20, verbose_name="NIT", default="CF")
    tax_id = models.CharField(max_length=20, unique=True, verbose_name="Identificación Fiscal")
    address = models.TextField(verbose_name="Dirección Legal", blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name="Teléfono", blank=True, null=True)
    email = models.EmailField(verbose_name="Correo Electrónico", blank=True, null=True)
    
    # Logo
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_companies')
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        through='UserRoleCompany', 
        related_name='companies_assigned'
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self): 
        return self.name

class Role(models.Model):
    name = models.CharField(max_length=80, unique=True)
    def __str__(self): return self.name

class UserRoleCompany(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    class Meta: 
        unique_together = ("user", "role", "company")

class Branch(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255, verbose_name="Sucursal")
    code = models.CharField(max_length=10, verbose_name="Código")
    location = models.CharField(max_length=255, verbose_name="Ubicación")

    def __str__(self): return f"{self.name} ({self.company.name})"

class Warehouse(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='warehouses')
    name = models.CharField(max_length=255, verbose_name="Bodega")
    is_main = models.BooleanField(default=False, verbose_name="¿Principal?")

    def __str__(self): return f"{self.name} - {self.branch.name}"


# ==========================================
# 2. CONTABILIDAD (NÚCLEO FINANCIERO)
# ==========================================

class Account(models.Model):
    TYPES = (('A', 'Activo'), ('P', 'Pasivo'), ('C', 'Capital'), ('I', 'Ingresos'), ('G', 'Gastos'), ('K', 'Costos'))
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=1, choices=TYPES)
    level = models.IntegerField(default=1)
    is_selectable = models.BooleanField(default=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def __str__(self):
        return f"{self.code} - {self.name}"

class JournalEntry(models.Model):
    date = models.DateField(verbose_name="Fecha")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Partida {self.id} - {self.date}"

class JournalItem(models.Model):
    entry = models.ForeignKey(JournalEntry, related_name='items', on_delete=models.CASCADE)
    account_name = models.CharField(max_length=100, verbose_name="Nombre Cuenta") # Ej: Caja, IVA
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Debe")
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Haber")

    def __str__(self):
        return f"{self.account_name} | D:{self.debit} H:{self.credit}"

# ==========================================
# 3. TESORERÍA (BANCOS Y SOCIOS)
# ==========================================
class BankAccount(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100, verbose_name="Nombre del Banco")
    account_number = models.CharField(max_length=50, verbose_name="Número de Cuenta")
    currency = models.CharField(max_length=3, default='GTQ', verbose_name="Moneda")
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Actual")
    accounting_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cuenta Contable")
    
    def __str__(self): return f"{self.bank_name} - {self.account_number}"

class BankTransaction(models.Model):
    MOVEMENT_CHOICES = (
        ('IN', 'Entrada / Depósito'),
        ('OUT', 'Salida / Retiro'),
    )
    
    # Aquí usamos 'BankAccount' que acabamos de definir arriba
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    
    date = models.DateField(verbose_name="Fecha")
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_CHOICES, default='OUT')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia")
    evidence = models.ImageField(upload_to='bank_evidence/', blank=True, null=True, verbose_name="Comprobante")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} - Q{self.amount}"

class BankMovement(models.Model):
    """El historial real de la libreta"""
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
            if self.movement_type == 'IN': self.account.current_balance += self.amount
            else: self.account.current_balance -= self.amount
            self.account.save()
        super().save(*args, **kwargs)

class BusinessPartner(models.Model):
    """Socios de Negocio: Clientes y Proveedores"""
    TYPES = (('C', 'Cliente'), ('P', 'Proveedor'), ('A', 'Ambos'))
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, verbose_name="Razón Social / Nombre")
    tax_id = models.CharField(max_length=20, verbose_name="NIT") 
    nit = models.CharField(max_length=20, blank=True, null=True, verbose_name="NIT (Opcional)")
    
    # Tipo de Socio
    type = models.CharField(max_length=10, choices=TYPES, default='CLIENTE', verbose_name="Tipo Texto")
    partner_type = models.CharField(max_length=1, choices=TYPES, default='P', verbose_name="Tipo Código")

    # Datos Bancarios
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Banco del Proveedor")
    bank_account = models.CharField(max_length=50, blank=True, null=True, verbose_name="No. Cuenta Proveedor")
    account_type = models.CharField(max_length=50, blank=True, null=True, default="Monetaria", verbose_name="Tipo Cuenta")
    
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.name} ({self.get_partner_type_display()})"


# ==========================================
# 4. OPERACIONES (INGRESOS Y GASTOS)
# ==========================================

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

class Fleet(models.Model):
    plate = models.CharField(max_length=20, unique=True, verbose_name="Placa")
    brand = models.CharField(max_length=50, verbose_name="Marca")
    model = models.CharField(max_length=50, verbose_name="Modelo")
    year = models.IntegerField(verbose_name="Año", null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name="Empresa")
    
    def __str__(self):
        return f"{self.plate} - {self.brand} {self.model}"

class Gasto(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha Factura")
    proveedor = models.CharField(max_length=200, blank=True, null=True, verbose_name="Proveedor")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción", blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total")
    imagen = models.ImageField(upload_to='gastos/', null=True, blank=True, verbose_name="Factura")

    # AGREGUE O VERIFIQUE ESTOS CAMPOS:
    amount_untaxed = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Base (Sin IVA)")
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="IVA Crédito")
    
    # Relación con el vehículo (Opcional, solo si es gasto de flota)
    vehicle = models.ForeignKey('Fleet', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vehículo / Placa")
    
    # Vinculaciones
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cuenta de Pago")
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Cuenta Contable (NIC/NIIF)", related_name="gastos")
    usuario_registra = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    # Datos Fiscales
    serie = models.CharField(max_length=50, blank=True, null=True)
    no_factura = models.CharField(max_length=50, blank=True, null=True)
    nit_emisor = models.CharField(max_length=20, blank=True, null=True)
    nombre_emisor = models.CharField(max_length=200, blank=True, null=True)
    concepto = models.TextField(blank=True, null=True)
    base_imponible = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto_iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto_idp = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    tipo_gasto = models.CharField(max_length=20, default='GENERAL')
    categoria = models.CharField(max_length=100, blank=True, null=True)
    placa_vehiculo = models.CharField(max_length=20, blank=True, null=True)
    ocr_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.proveedor} - Q{self.total}"


# ==========================================
# 5. LOGÍSTICA E INVENTARIO
# ==========================================

class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='core_products')
    name = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    description = models.TextField(blank=True, verbose_name="Descripción")
    
    # Identificadores
    sku = models.CharField(max_length=50, verbose_name="SKU / Código Interno") 
    barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código de Barras (Escáner)")
    
    # Valores
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo Promedio")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio Venta")
    
    # Control
    stock = models.IntegerField(default=0, verbose_name="Existencia Actual")
    min_stock = models.IntegerField(default=5, verbose_name="Stock Mínimo")
    
    # Multimedia
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Foto del Producto")
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'sku')

    def __str__(self):
        return f"[{self.sku}] {self.name}"

class InventoryMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Entrada (Compra/Ajuste)'),
        ('OUT', 'Salida (Venta/Consumo)'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='core_movements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Tipo")
    quantity = models.IntegerField(verbose_name="Cantidad")
    
    # Dinero
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario (Q)")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Costo Total")
    
    # Referencias
    reference = models.CharField(max_length=100, verbose_name="Referencia (Fac/Vale)")
    description = models.CharField(max_length=255, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='core_movement_users')

    def save(self, *args, **kwargs):
        self.total_cost = float(self.quantity) * float(self.unit_cost)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movement_type} - {self.product.name} ({self.quantity})"


# ==========================================
# 6. RECURSOS HUMANOS (EMPLEADOS Y NÓMINA)
# ==========================================

class Employee(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='core_employees')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario de Sistema")
    
    first_name = models.CharField(max_length=100, verbose_name="Nombres")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    dpi = models.CharField(max_length=20, blank=True, verbose_name="DPI")
    nit = models.CharField(max_length=20, blank=True, verbose_name="NIT")
    address = models.CharField(max_length=200, blank=True, verbose_name="Dirección")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    
    position = models.CharField(max_length=100, verbose_name="Cargo / Puesto")
    department = models.CharField(max_length=100, blank=True, verbose_name="Departamento")
    date_hired = models.DateField(verbose_name="Fecha de Contratación")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salario Base (Q)")
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=250.00, verbose_name="Bonificación Decreto")
    
    igss_number = models.CharField(max_length=20, blank=True, verbose_name="No. Afiliación IGSS")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def total_income(self):
        return self.base_salary + self.bonus

class Loan(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Empleado")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Préstamo")
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cuota Mensual")
    balance = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Pendiente")
    reason = models.CharField(max_length=200, verbose_name="Motivo")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Préstamo {self.employee.first_name} - Q{self.balance}"

class Payroll(models.Model):
    # Enlazamos con related_name para evitar choque
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='core_payrolls')
    month = models.IntegerField(verbose_name="Mes")
    year = models.IntegerField(verbose_name="Año")
    date_generated = models.DateField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_closed = models.BooleanField(default=False, verbose_name="Cerrada")

    def __str__(self):
        return f"Nómina {self.month}/{self.year}"

class PayrollDetail(models.Model):
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    
    # NOTA: Se eliminó el campo 'company' para evitar el conflicto "Reverse accessor clashes".
    # El detalle ya está ligado a la empresa a través de 'payroll.company'.
    
    # Ingresos
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Deducciones
    igss_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    loan_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    isr_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Totales
    total_income = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Detalle {self.employee.first_name} - {self.payroll}"

# En core/models.py (al final)

class Client(models.Model):
    # Datos Fiscales
    name = models.CharField(max_length=200, verbose_name="Razón Social / Nombre")
    nit = models.CharField(max_length=20, verbose_name="NIT", unique=True)
    address = models.CharField(max_length=255, verbose_name="Dirección Fiscal", blank=True)
    
    # Datos de Contacto
    phone = models.CharField(max_length=20, verbose_name="Teléfono", blank=True)
    email = models.EmailField(verbose_name="Email Facturación", blank=True)
    contact_name = models.CharField(max_length=100, verbose_name="Nombre de Contacto", blank=True)
    
    # Datos Comerciales (Para el Libro Negro y Créditos)
    credit_days = models.IntegerField(default=0, verbose_name="Días de Crédito")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Límite de Crédito")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    def __str__(self):
        return f"{self.name} ({self.nit})"