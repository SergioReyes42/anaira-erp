from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_names):
    """
    Verifica si el usuario pertenece a alguno de los grupos dados.
    Uso en HTML: {% if request.user|has_group:"Contadora, Gerente" %}
    """
    # El superusuario (Tú) siempre tiene permiso de ver todo
    if user.is_superuser:
        return True
        
    # Limpiamos los nombres de los grupos por si pusiste espacios
    grupos_lista = [nombre.strip() for nombre in group_names.split(',')]
    
    # Comprobamos si el usuario tiene al menos uno de esos roles
    return user.groups.filter(name__in=grupos_lista).exists()