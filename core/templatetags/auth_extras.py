from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    # Permite verificar si el usuario pertenece a un grupo específico
    # Uso en HTML: {% if request.user|has_group:"Pilotos" %}
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return False
        
    return group in user.groups.all()

@register.filter(name='is_operational')
def is_operational(user):
    # Retorna True si es Vendedor, Piloto, Contador o Admin (Para ver el Scanner)
    groups = ["Vendedores", "Pilotos", "Contadores", "Administradores", "Gerencia"]
    return user.groups.filter(name__in=groups).exists() or user.is_superuser