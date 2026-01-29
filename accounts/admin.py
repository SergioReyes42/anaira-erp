
# accounts/admin.py
from django.contrib import admin
from django.conf import settings
from .models import User
# Branding del admin usando variables del settings
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Administración")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Panel")

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # Esto activa las cajitas de izquierda a derecha ⬅️➡️
    # 'groups' y 'user_permissions' son los campos por defecto de Django
    # Si su campo de empresas se llama 'companies' o 'empresas', agréguelo a esta lista.
    filter_horizontal = ('groups', 'user_permissions',) 
    
    # Opcional: Para buscar usuarios por email o nombre
    search_fields = ('email', 'first_name', 'last_name')
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')