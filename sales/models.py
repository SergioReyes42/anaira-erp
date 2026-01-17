from django.db.models.signals import post_save
from django.db import models
from core.models import BusinessPartner, Company


class CustomerAccount(models.Model):
    """Estado de cuenta general del cliente"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.OneToOneField(BusinessPartner, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.customer.name} - Saldo: {self.balance}"

class Invoice(models.Model):
    """Factura de Venta"""
    STATUS_CHOICES = [('DRAFT', 'Borrador'), ('OPEN', 'Abierta'), ('PAID', 'Pagada')]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    customer = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE)
    number = models.CharField(max_length=20, unique=True) # <-- CORREGIDO: max_length
    date = models.DateField()
    due_date = models.DateField() 
    total = models.DecimalField(max_digits=12, decimal_places=2)
    pending_amount = models.DecimalField(max_digits=12, decimal_places=2) 
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')

    def __str__(self):
        return f"Factura {self.number} - {self.customer.name}"

class Payment(models.Model):
    """Recibo de Caja / Abono de Cliente"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50) 

    def __str__(self):
        return f"Abono a {self.invoice.number} - Q{self.amount}"