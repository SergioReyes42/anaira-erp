from django import template
from django.utils import timezone
from accounts.models import User
import datetime

register = template.Library()

@register.simple_tag
def get_active_users():
    # Definimos "Online" como alguien que dio click en los últimos 30 mins
    now = timezone.now()
    threshold = now - datetime.timedelta(minutes=30)
    
    # Traemos a los usuarios que cumplan la condición
    users = User.objects.filter(last_login__gte=threshold).exclude(current_company__isnull=True)
    
    return users