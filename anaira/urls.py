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

from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth import get_user_model

# --- FUNCIÓN DE EMERGENCIA ---
def crear_admin_express(request):
    try:
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@anaira.com', 'admin123')
            return HttpResponse("<h1>✅ ÉXITO TOTAL</h1><p>Usuario creado.<br>User: admin<br>Pass: admin123</p><br><a href='/'>IR AL LOGIN</a>")
        else:
            # Si sale esto, el usuario YA EXISTE y el problema es el "parpadeo" (Paso 2)
            return HttpResponse("<h1>⚠️ YA EXISTE</h1><p>El usuario ya existe. El problema es de configuración (Cookies).</p><br><a href='/'>IR AL LOGIN</a>")
    except Exception as e:
        return HttpResponse(f"<h1>❌ ERROR</h1><p>{e}</p>")
# -----------------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('crear-emergencia/', crear_admin_express), # <--- RUTA SECRETA
]