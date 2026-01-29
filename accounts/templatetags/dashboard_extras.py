from django import template
from django.contrib.auth import get_user_model  # <--- ESTA ES LA LÍNEA QUE FALTABA
from django.core.cache import cache

register = template.Library()

@register.simple_tag
def get_online_users():
    # 1. Obtenemos el modelo de usuario correcto (accounts.User)
    User = get_user_model()
    
    # 2. Filtramos solo usuarios activos para evitar errores
    try:
        users = User.objects.filter(is_active=True)
    except:
        return [] # Si falla la DB, devolvemos lista vacía para no romper el sitio
    
    online_users = []
    
    # 3. Verificamos quién tiene la marca de tiempo en caché
    for user in users:
        # Usamos el campo que sirve como username (usualmente 'username' o 'email')
        # get_username() es el método seguro de Django
        username = user.get_username()
        
        if username:
            last_seen = cache.get(f'seen_{username}')
            if last_seen:
                online_users.append(user)
            
    return online_users