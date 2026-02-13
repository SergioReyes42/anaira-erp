from django.db import models
from django.conf import settings
from core.models import Company  # Asegúrate de importar Company

# --- GASTOS ---
class Expense(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    description = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField()
    
    # --- LOS CAMPOS QUE FALTABAN ---
    receipt_image = models.ImageField(upload_to='expenses_receipts/', null=True, blank=True, verbose_name="Foto del Recibo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Estado")

    def __str__(self):
        return f"{self.description} - Q{self.total_amount}"

# --- FLOTILLA ---
class Vehicle(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    brand = models.CharField(max_length=50)
    line = models.CharField(max_length=50)
    plate = models.CharField(max_length=20)
    driver_name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.brand} {self.line} - {self.plate}"

# --- BANCOS ---
class BankAccount(models.Model):
    CURRENCY_CHOICES = [
        ('GTQ', 'Quetzales'),
        ('USD', 'Dólares'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GTQ')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

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
        # Actualizar saldo de la cuenta automáticamente
        if not self.pk: # Solo si es nueva transacción
            if self.transaction_type == 'IN':
                self.bank_account.balance += self.amount
            else:
                self.bank_account.balance -= self.amount
            self.bank_account.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - Q{self.amount}"