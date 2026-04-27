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


class PayrollRun(CompanyAwareModel):
    period_label = models.CharField(max_length=40, verbose_name="Período (ej. Abril 2026)")
    payment_date = models.DateField(default=timezone.now, verbose_name="Fecha de Pago")
    description = models.CharField(max_length=255, blank=True, default="")
    total_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_net = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_posted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-payment_date", "-id"]

    def __str__(self):
        return f"Planilla {self.period_label} ({self.payment_date})"


class EmployeeLoanAdvance(CompanyAwareModel):
    TYPE_CHOICES = (
        ("ANTICIPO", "Anticipo"),
        ("PRESTAMO", "Préstamo"),
    )

    STATUS_CHOICES = (
        ("ACTIVO", "Activo"),
        ("CANCELADO", "Cancelado"),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="loan_advances")
    request_date = models.DateField(default=timezone.now, verbose_name="Fecha de Solicitud")
    loan_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Tipo")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Saldo")
    installments = models.PositiveIntegerField(default=1, verbose_name="Cuotas")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVO", verbose_name="Estado")
    notes = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Anticipo/Préstamo a Empleado"
        verbose_name_plural = "Anticipos y Préstamos a Empleados"
        ordering = ["-request_date", "-id"]

    def save(self, *args, **kwargs):
        if self.balance in (None, 0):
            self.balance = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.loan_type} - {self.employee} - {self.amount}"


class EmployeePayrollLine(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_lines")
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    loan_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["employee__first_name", "employee__last_name"]

    def __str__(self):
        return f"{self.employee} - Neto Q{self.net_pay}"
