from django.db import models
from django.conf import settings  # <--- IMPORTANTE: Para usar TU usuario personalizado
from django.utils import timezone

# ==========================================
# 1. MODELOS MAESTROS (Estructurales)
# ==========================================

class Company(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre de la Empresa")
    active = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CompanyProfile(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='profile')
    name = models.CharField(max_length=100)
    nit = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)

    def __str__(self):
        return self.name

class CompanyAwareModel(models.Model):
    """
    Clase Abstracta: Da superpoderes a quien la herede.
    """
    company = models.ForeignKey(
        'core.Company',  # <--- CORRECCIÓN CRÍTICA: Apuntamos explícitamente a core.Company
        on_delete=models.CASCADE,
        verbose_name="Empresa",
        null=True, blank=True
    )

    class Meta:
        abstract = True

# ==========================================
# 2. USUARIOS Y ROLES
# ==========================================

class UserProfile(models.Model):
    # CORRECCIÓN: Usamos settings.AUTH_USER_MODEL en lugar de User directo
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Empresa Principal")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.user}"

class Role(CompanyAwareModel):
    name = models.CharField(max_length=50)
    permissions = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

class UserRoleCompany(models.Model):
    # CORRECCIÓN: Usamos settings.AUTH_USER_MODEL aquí también
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('user', 'company')
        verbose_name = "Asignación de Empresa"
        verbose_name_plural = "Asignaciones de Empresas"

# ==========================================
# 3. LOGÍSTICA BÁSICA (Compartida)
# ==========================================

class Branch(CompanyAwareModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    location = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.name} ({self.company})"

class Warehouse(CompanyAwareModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.branch.name}"

class Product(CompanyAwareModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name

# ==========================================
# 4. TERCEROS
# ==========================================

class Client(CompanyAwareModel):
    name = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Supplier(CompanyAwareModel):
    name = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, null=True, blank=True)
    contact_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return self.name