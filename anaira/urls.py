from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.apps import apps

# --- IMPORTS PARA IMÁGENES (LOGOS) ---
from django.conf import settings
from django.conf.urls.static import static

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

# --- FUNCIÓN 2: CREAR EMPRESA + ROL ---
def crear_empresa_force(request):
    try:
        Company = apps.get_model('core', 'Company')
        try:
            Role = apps.get_model('core', 'Role')
        except LookupError:
            return HttpResponse("<h1>❌ Error:</h1> No encuentro el modelo 'Role'.")
            
        User = get_user_model()

        # 1. OBTENER LA EMPRESA
        empresa, created_comp = Company.objects.get_or_create(
            name="Anaira ERP Principal",
            defaults={
                'nit': 'CF', 'phone': '12345678', 'email': 'admin@anaira.com', 'address': 'Central'
            }
        )

        # 2. OBTENER EL ROL "ADMINISTRADOR"
        rol_admin, created_rol = Role.objects.get_or_create(
            name="Administrador",
            defaults={'is_active': True} 
        )

        # 3. OBTENER EL USUARIO
        if not User.objects.filter(username='admin').exists():
             return HttpResponse("<h1>❌ ERROR:</h1> <p>Primero cree el admin en /crear-emergencia/</p>")
        admin_user = User.objects.get(username='admin')

        # 4. ASIGNACIÓN MANUAL
        ThroughModel = Company.users.through 
        if not ThroughModel.objects.filter(user=admin_user, company=empresa).exists():
            ThroughModel.objects.create(
                user=admin_user,
                company=empresa,
                role=rol_admin
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

# --- HABILITAR CARGA DE LOGOS EN MODO DEBUG ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)