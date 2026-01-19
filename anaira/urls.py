from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from anaira_erp.core.models import Company

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
from django.apps import apps  # <--- ESTA ES LA CLAVE PARA QUE NO FALLE

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
    
    # --- FUNCIÓN 2: CREAR EMPRESA A LA FUERZA (NUEVA) ---
def crear_empresa_force(request):
    try:
        # 1. Crear la empresa con datos genéricos
        # Usamos get_or_create para que no falle si ya existe
        empresa, created = Company.objects.get_or_create(
            name="Anaira ERP Principal", # Nombre de la empresa
            defaults={
                'nit': 'CF',           # Datos obligatorios rellenos con dummy
                'phone': '12345678',
                'email': 'contacto@anaira.com',
                'address': 'Oficina Central'
            }
        )

        # 2. Buscar al usuario Admin
        User = get_user_model()
        admin_user = User.objects.get(username='admin')

        # 3. Asignar la empresa al usuario
        # Intentamos los dos métodos más comunes (Many-to-Many o ForeignKey)
        asignado = "No se pudo asignar (revise modelos)"
        
        # Opción A: Si el usuario tiene un campo "companies" (Muchos a Muchos)
        if hasattr(admin_user, 'companies'):
            admin_user.companies.add(empresa)
            asignado = "Asignada vía 'companies.add()'"
        
        # Opción B: Si el usuario tiene un campo "company" (Uno a Uno/Muchos)
        elif hasattr(admin_user, 'company'):
            admin_user.company = empresa
            admin_user.save()
            asignado = "Asignada vía 'user.company = ...'"
            
        # Opción C: Si la empresa tiene un campo "users" o "owner"
        elif hasattr(empresa, 'users'):
            empresa.users.add(admin_user)
            asignado = "Asignada vía 'empresa.users.add()'"

        status = "CREADA NUEVA" if created else "YA EXISTÍA (Recuperada)"
        
        return HttpResponse(f"""
            <div style='font-family: sans-serif; padding: 20px;'>
                <h1>🚀 EMPRESA CREADA EXITOSAMENTE</h1>
                <ul>
                    <li><strong>Empresa:</strong> {empresa.name}</li>
                    <li><strong>Estado:</strong> {status}</li>
                    <li><strong>Asignación:</strong> {asignado}</li>
                </ul>
                <br>
                <a href='/' style='background: blue; color: white; padding: 10px; text-decoration: none; border-radius: 5px;'>
                    👉 IR AL DASHBOARD AHORA
                </a>
            </div>
        """)

    except Exception as e:
        # Si falla, imprimimos el error completo para verlo
        import traceback
        return HttpResponse(f"<h1>❌ ERROR CRÍTICO</h1><pre>{traceback.format_exc()}</pre>")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('crear-emergencia/', crear_admin_express),
    path('crear-empresa/', crear_empresa_force), # <--- NUEVA RUTA
]
# -----------------------------

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('crear-emergencia/', crear_admin_express), # <--- RUTA SECRETA
]