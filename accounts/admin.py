
# accounts/admin.py
from django.contrib import admin
from django.conf import settings
from .models import User  # O su modelo de usuario personalizado
# Branding del admin usando variables del settings
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Administración")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Panel")

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    # Esto activa las cajas izquierda-derecha para relaciones Muchos-a-Muchos
    filter_horizontal = ('groups', 'user_permissions', 'companies',) 
    
    # Nota: 'companies' debe ser el nombre real de su campo ManyToMany en el modelo
# FIN accounts/admin.py
