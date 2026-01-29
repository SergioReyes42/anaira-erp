
# accounts/admin.py
from django.contrib import admin
from django.conf import settings
from .models import User, SuModeloDeUsuario, Empresa  # O su modelo de usuario personalizado
# Branding del admin usando variables del settings
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Administración")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Panel")

@admin.register(SuModeloDeUsuario)
class UsuarioAdmin(admin.ModelAdmin):
    # Esto activa las dos cajitas con flechas
    filter_horizontal = ('empresas', 'groups', 'user_permissions') 
    
    # 'empresas' debe ser el nombre exacto de su campo ManyToMany