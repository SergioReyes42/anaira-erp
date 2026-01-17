from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # 1. ADMIN DE DJANGO
    path('gestion-segura-sermaworld/', admin.site.urls),

    # 2. CONECTAR CON LA APP 'CORE' (Aquí está toda la magia)
    # Esto le dice a Django: "Para todo lo demás, ve al archivo urls.py de la carpeta core"
    path('', include('core.urls')),
    
]

# Configuración para servir imágenes (Facturas/Evidencias)
if settings.DEBUG:
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)