from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.apps import apps  # <--- USAMOS ESTO EN LUGAR DE IMPORTAR EL MODELO DIRECTAMENTE

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

# --- FUNCIÓN 2: CREAR EMPRESA (CON IMPORTACIÓN SEGURA) ---
def crear_empresa_force(request):
    try:
        # 1. AQUÍ ESTÁ EL TRUCO: Cargamos el modelo dinámicamente
        # Esto evita el error "ModuleNotFoundError" y "Circular Import"
        Company = apps.get_model('core', 'Company') 
        
        # 2. Creamos la empresa
        empresa, created = Company.objects.get_or_create(
            name="Anaira ERP Principal",
            defaults={
                'nit': 'CF',
                'phone': '12345678',
                'email': 'contacto@anaira.com',
                'address': 'Oficina Central'
            }
        )

        # 3. Buscamos al usuario Admin
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
             return HttpResponse("<h1>❌ ERROR:</h1> <p>Primero cree el admin en /crear-emergencia/</p>")
        
        admin_user = User.objects.get(username='admin')

        # 4. Asignar la empresa (Log de intentos)
        log = []
        
        # Intento A: Many-to-Many
        if hasattr(admin_user, 'companies'):
            admin_user.companies.add(empresa)
            log.append("✅ Asignado a 'companies'")
        
        # Intento B: ForeignKey
        elif hasattr(admin_user, 'company'):
            admin_user.company = empresa
            admin_user.save()
            log.append("✅ Asignado a 'company'")
            
        # Intento C: Inverse
        elif hasattr(empresa, 'users'):
            empresa.users.add(admin_user)
            log.append("✅ Asignado a 'empresa.users'")
        else:
            log.append("⚠️ No se encontró el campo de relación en el modelo User.")

        status = "NUEVA" if created else "RECUPERADA"
        
        return HttpResponse(f"""
            <div style='font-family: sans-serif; padding: 20px; text-align: center;'>
                <h1 style='color: green;'>🚀 ¡LOGRADO!</h1>
                <p>Empresa: <strong>{empresa.name}</strong> ({status})</p>
                <p>Usuario: <strong>{admin_user.username}</strong></p>
                <div style='background: #eee; padding: 10px; margin: 10px 0;'>
                    {' | '.join(log)}
                </div>
                <br>
                <a href='/' style='background: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 20px;'>
                    👉 ENTRAR AL DASHBOARD
                </a>
            </div>
        """)

    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>❌ ERROR</h1><pre>{traceback.format_exc()}</pre>")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('crear-emergencia/', crear_admin_express),
    path('crear-empresa/', crear_empresa_force), 
]