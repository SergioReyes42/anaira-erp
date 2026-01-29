# anaira_erp/templatetags/dashboard_extras.py
from django import template
from django.contrib.auth.models import User
from django.core.cache import cache
import datetime
from django.utils import timezone

register = template.Library()

@register.simple_tag
def get_online_users():
    # En lugar de importar User directamente, pedimos el modelo activo
    User = get_user_model()
    
    # Ahora sí podemos hacer consultas sin error
    # Usamos .filter(is_active=True) para ignorar usuarios bloqueados si desea
    users = User.objects.filter(is_active=True)
    
    online_users = []
    
    for user in users:
        # Obtenemos el nombre de usuario de forma segura
        username = user.get_username()
        
        # Verificamos la caché
        if username:
            last_seen = cache.get(f'seen_{username}')
            if last_seen:
                online_users.append(user)
            
    return online_users