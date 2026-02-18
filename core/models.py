from django.db import models
from django.conf import settings

# ==========================================
# 1. BASE DEL SISTEMA
# ==========================================
class Company(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre de la Empresa")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CompanyAwareModel(models.Model):
    """
    Clase abstracta para que otros modelos (Clientes, Ventas)
    hereden automáticamente el campo 'company'.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    class Meta:
        abstract = True

class Warehouse(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="Nombre de Bodega")
    address = models.CharField(max_length=200, null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.company}"

# ==========================================
# 2. USUARIOS
# ==========================================
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.user}"

class UserRoleCompany(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role_name = models.CharField(max_length=50, default='Usuario')

    class Meta:
        unique_together = ('user', 'company')