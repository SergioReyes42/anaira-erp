from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings # <--- Usamos settings
from .models import UserProfile, Company, Role

# Usamos settings.AUTH_USER_MODEL en lugar de User directo
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=Company)
def create_default_company_roles(sender, instance, created, **kwargs):
    if created:
        Role.objects.create(company=instance, name='Administrador', permissions={'all': True})
        Role.objects.create(company=instance, name='Vendedor', permissions={'sales': True})
        Role.objects.create(company=instance, name='Bodeguero', permissions={'inventory': True})