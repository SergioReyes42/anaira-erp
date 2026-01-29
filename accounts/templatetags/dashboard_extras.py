# anaira_erp/templatetags/dashboard_extras.py
from django import template
from django.contrib.auth.models import User
from django.core.cache import cache
import datetime
from django.utils import timezone

register = template.Library()

@register.simple_tag
def get_online_users():
    # Obtenemos todos los usuarios y verificamos si tienen el 'flag' en caché
    users = User.objects.all().order_by('username')
    online_users = []
    
    for user in users:
        # Verificamos si existe la marca de tiempo creada por el middleware
        last_seen = cache.get(f'seen_{user.username}')
        if last_seen:
            online_users.append(user)
            
    return online_users