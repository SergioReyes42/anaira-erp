from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import CompanyAwareModel

# --- NUEVO: VEHÍCULOS (FLOTILLA) ---
class Vehicle(CompanyAwareModel):
    brand = models.CharField(max_length=50, verbose_name="Marca")
    model = models.CharField(max_length=50, verbose_name="Modelo")
    plate = models.CharField(max_length=20, verbose_name="Placa/Matrícula")
    year = models.IntegerField(verbose_name="Año", null=True, blank=True)
    color = models.CharField(max_length=30, null=True, blank=True, verbose_name="Color")
    driver_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Piloto Asignado")
    
    def __str__(self):
        return f"{self.brand} {self.model} - {self.plate}"

# --- GASTOS ---
class Expense(CompanyAwareModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Usuario")
    # Agregamos relación opcional con Vehículo
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vehículo (Opcional)")
    
    photo = models.ImageField(upload_to='expenses/', verbose_name="Foto del Recibo")
    description = models.TextField(verbose_name="Descripción", null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total", null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")

    def __str__(self):
        return f"Gasto {self.id} - {self.user}"

# --- BANCOS Y TRANSACCIONES ---
class BankAccount(CompanyAwareModel):
    bank_name = models.CharField(max_length=100, verbose_name="Nombre del Banco")
    account_number = models.CharField(max_length=50, verbose_name="Número de Cuenta")
    currency = models.CharField(max_length=3, default='GTQ', verbose_name="Moneda")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo Actual")

    def __str__(self):
        return f"{self.bank_name} - {self.account_number} ({self.currency})"

class BankTransaction(CompanyAwareModel):
    TYPE_CHOICES = [
        ('IN', 'Depósito (Entrada)'),
        ('OUT', 'Retiro/Cheque (Salida)'),
    ]
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, verbose_name="Cuenta Bancaria")
    date = models.DateField(default=timezone.now, verbose_name="Fecha")
    transaction_type = models.CharField(max_length=3, choices=TYPE_CHOICES, verbose_name="Tipo")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    reference = models.CharField(max_length=100, verbose_name="Referencia/Boleta")
    description = models.CharField(max_length=255, verbose_name="Descripción")

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.transaction_type == 'IN':
                self.bank_account.balance += self.amount
            elif self.transaction_type == 'OUT':
                self.bank_account.balance -= self.amount
            self.bank_account.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}"