from django.db import models
from django.utils import timezone
from core.models import CompanyAwareModel

class Employee(CompanyAwareModel):
    first_name = models.CharField(max_length=100, verbose_name="Nombres")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    position = models.CharField(max_length=100, verbose_name="Cargo")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salario Base")
    hiring_date = models.DateField(default=timezone.now, verbose_name="Fecha Contratación")
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Payroll(CompanyAwareModel):
    """Nómina/Planilla"""
    date = models.DateField(default=timezone.now, verbose_name="Fecha de Pago")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_closed = models.BooleanField(default=False, verbose_name="Cerrada")
    
    def __str__(self):
        return f"Nómina {self.date}"