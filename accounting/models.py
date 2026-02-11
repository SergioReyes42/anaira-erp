from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import CompanyAwareModel

# --- GASTOS (LO QUE YA TENÍAS) ---
class Expense(CompanyAwareModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Usuario")
    photo = models.ImageField(upload_to='expenses/', verbose_name="Foto del Recibo")
    description = models.TextField(verbose_name="Descripción", null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total", null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")

    def __str__(self):
        return f"Gasto {self.id} - {self.user}"

# --- NUEVO: BANCOS Y TRANSACCIONES ---
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
        # Actualizar saldo de la cuenta al guardar
        if not self.pk: # Solo si es nueva transacción
            if self.transaction_type == 'IN':
                self.bank_account.balance += self.amount
            elif self.transaction_type == 'OUT':
                self.bank_account.balance -= self.amount
            self.bank_account.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount}"