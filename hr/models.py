from django.db import models
from core.models import Company  # Importante: Traemos Company del Core

# ==========================================
# 1. DEPARTAMENTOS
# ==========================================
class Department(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="Departamento")
    def __str__(self): return self.name

# ==========================================
# 2. EMPLEADOS
# ==========================================
class Employee(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100, verbose_name="Nombres")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    dpi = models.CharField(max_length=20, blank=True, null=True, verbose_name="DPI")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.CharField(max_length=100, verbose_name="Puesto")
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salario Base")
    incentive_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=250.00)
    date_joined = models.DateField(verbose_name="Fecha Ingreso")
    is_active = models.BooleanField(default=True)

    def __str__(self): return f"{self.first_name} {self.last_name}"

# ==========================================
# 3. PRÉSTAMOS
# ==========================================
class Loan(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="Empleado")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    description = models.CharField(max_length=200, verbose_name="Motivo")
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"Préstamo {self.employee} - {self.amount}"

# ==========================================
# 4. NÓMINA
# ==========================================
class Payroll(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    start_date = models.DateField(verbose_name="Inicio")
    end_date = models.DateField(verbose_name="Fin")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_finalized = models.BooleanField(default=False)

    def __str__(self): return f"Nómina {self.start_date} - {self.end_date}"

class PayrollDetail(models.Model):
    payroll = models.ForeignKey(Payroll, related_name='details', on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    base_salary = models.DecimalField(max_digits=10, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2)
    deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)