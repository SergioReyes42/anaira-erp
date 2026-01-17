from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        STAFF = "STAFF", "Staff"
        MANAGER = "MANAGER", "Gerencia"
        ANALYST = "ANALYST", "Analista"
        VIEWER = "VIEWER", "Consulta"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.VIEWER,
        help_text="Rol dentro de Anaira Systems"
    )

    # Evita el choque de nombres con los modelos internos de Django
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='anaira_user_groups',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='anaira_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    totp_secret = models.CharField(max_length=64, blank=True, null=True)

    def is_admin_or_staff(self):
        return self.role in [self.Roles.ADMIN, self.Roles.STAFF]

    def __str__(self):
        return self.username
    