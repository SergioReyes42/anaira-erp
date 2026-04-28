from django.db import models
from django.conf import settings
from django.utils import timezone

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
class UserRoleCompany(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role_name = models.CharField(max_length=50, default='Usuario')

    class Meta:
        unique_together = ('user', 'company')


class AIQueryLog(models.Model):
    STATUS_CHOICES = [
        ('OK', 'OK'),
        ('ERROR', 'ERROR'),
        ('BLOCKED', 'BLOCKED'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_query_logs'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_query_logs'
    )

    question = models.TextField(verbose_name="Pregunta del usuario")
    tool_name = models.CharField(max_length=100, blank=True, default='')
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OK')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AILog #{self.id} - {self.user} - {self.status}"


class UserSessionLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_logs'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_logs'
    )
    session_key = models.CharField(max_length=100, blank=True, default='')
    ip_address = models.CharField(max_length=64, blank=True, default='')
    user_agent = models.TextField(blank=True, default='')

    login_at = models.DateTimeField(default=timezone.now)
    logout_at = models.DateTimeField(null=True, blank=True)
    last_seen = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-login_at']

    def __str__(self):
        return f"{self.user} | login {self.login_at}"

    @property
    def is_online(self):
        if self.logout_at:
            return False
        return (timezone.now() - self.last_seen).total_seconds() <= 300


class AIActionDraft(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
        ('APPLIED', 'Aplicado'),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='ai_action_drafts'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_drafts_created'
    )
    action_type = models.CharField(max_length=100, default='JOURNAL_ENTRY_DRAFT')
    draft_payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_drafts_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_drafts_applied'
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Draft #{self.id} - {self.action_type} - {self.status}"
