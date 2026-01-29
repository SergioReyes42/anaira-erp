from django.contrib import admin
from django.conf import settings
from .models import User
# Si necesita importar la empresa para inlines, descomente abajo:
# from core.models import Company 

# Branding del admin
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Administración")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Panel")

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    
    # 1. Cajitas de izquierda a derecha (Grupos y Empresas)
    # IMPORTANTE: Si su campo en models.py se llama 'empresas', cambie 'companies' por 'empresas'
    filter_horizontal = ('groups', 'user_permissions') 
    
    # 2. Buscador
    search_fields = ('email', 'first_name', 'last_name')

    # 3. Columnas de la tabla (He comentado current_company para que pase la migración)
    list_display = ('email', 'first_name', 'get_online_status', 'current_company', 'last_login')
    # Cuando ya haya hecho la migración, cambie la linea de arriba por esta:
    # list_display = ('email', 'first_name', 'get_online_status', 'current_company', 'last_login')

    # 4. Filtros laterales
    list_filter = ('current_company', 'is_staff', 'is_active') 
    # Cuando ya haya hecho la migración, agregue 'current_company' aquí también.

    # 5. Función del Semáforo 🟢🔴
    def get_online_status(self, obj):
        from django.utils import timezone
        import datetime
        
        if not obj.last_login:
            return "🔴 Offline"
            
        now = timezone.now()
        # Calculamos la diferencia
        diff = now - obj.last_login
        
        # Si se conectó en los últimos 30 mins
        if diff < datetime.timedelta(minutes=30):
            return "🟢 Online"
        else:
            return "⚫ Ausente"
    
    get_online_status.short_description = "Estado"