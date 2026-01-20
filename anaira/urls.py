from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from anaira_erp.core.models import Company
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.apps import apps 

# --- FUNCIÓN 1: CREAR ADMIN ---
def crear_admin_express(request):
    try:
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@anaira.com', 'admin123')
            return HttpResponse("<h1>✅ ADMIN CREADO</h1><p>User: admin / Pass: admin123</p>")
        return HttpResponse("<h1>⚠️ ADMIN YA EXISTE</h1>")
    except Exception as e:
        return HttpResponse(f"<h1>❌ ERROR</h1><p>{e}</p>")

# --- FUNCIÓN 2: CREAR EMPRESA + ROL (CORREGIDA) ---
def crear_empresa_force(request):
    try:
        # 1. CARGAR MODELOS DINÁMICAMENTE
        Company = apps.get_model('core', 'Company')
        # Intentamos adivinar el nombre del modelo de Rol (generalmente es Role)
        try:
            Role = apps.get_model('core', 'Role')
        except LookupError:
            return HttpResponse("<h1>❌ Error:</h1> No encuentro el modelo 'Role' en la app 'core'.")
            
        User = get_user_model()

        # 2. CREAR OBTENER LA EMPRESA
        empresa, created_comp = Company.objects.get_or_create(
            name="Anaira ERP Principal",
            defaults={
                'nit': 'CF', 'phone': '12345678', 'email': 'admin@anaira.com', 'address': 'Central'
            }
        )

        # 3. CREAR OBTENER EL ROL "ADMINISTRADOR" (¡ESTO FALTABA!)
        # Asumimos que el modelo Role tiene un campo 'name'. 
        # Si tiene otros campos obligatorios, el try/except nos avisará.
        rol_admin, created_rol = Role.objects.get_or_create(
            name="Administrador",
            defaults={'is_active': True} # Ajuste esto si su modelo Role pide más cosas
        )

        # 4. OBTENER EL USUARIO
        if not User.objects.filter(username='admin').exists():
             return HttpResponse("<h1>❌ ERROR:</h1> <p>Primero cree el admin en /crear-emergencia/</p>")
        admin_user = User.objects.get(username='admin')

        # 5. ASIGNACIÓN MANUAL (LA SOLUCIÓN AL ERROR role_id)
        # En lugar de usar .add(), vamos a crear la fila en la tabla intermedia directamente
        # para poder pasarle el role_id.
        
        # Buscamos la tabla intermedia (UserRoleCompany)
        ThroughModel = Company.users.through 
        
        # Verificamos si ya existe la relación para no duplicar
        if not ThroughModel.objects.filter(user=admin_user, company=empresa).exists():
            ThroughModel.objects.create(
                user=admin_user,
                company=empresa,
                role=rol_admin  # <--- ¡AQUÍ ESTÁ LA CLAVE DEL ÉXITO!
            )
            mensaje_final = "✅ Asignación creada con Rol ADMINISTRADOR."
        else:
            mensaje_final = "⚠️ El usuario ya estaba asignado a esta empresa."

        return HttpResponse(f"""
            <div style='font-family: sans-serif; padding: 20px; text-align: center;'>
                <h1 style='color: green;'>🚀 ¡ÉXITO TOTAL!</h1>
                <p><strong>Empresa:</strong> {empresa.name}</p>
                <p><strong>Rol Creado:</strong> {rol_admin.name}</p>
                <p><strong>Resultado:</strong> {mensaje_final}</p>
                <br>
                <a href='/' style='background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 20px;'>
                    👉 ENTRAR AL DASHBOARD
                </a>
            </div>
        """)

    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>❌ ERROR CRÍTICO</h1><pre>{traceback.format_exc()}</pre>")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('crear-emergencia/', crear_admin_express),
    path('crear-empresa/', crear_empresa_force), 
]
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