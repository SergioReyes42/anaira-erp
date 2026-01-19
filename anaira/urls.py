from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.apps import apps  # <--- ESTA ES LA CLAVE PARA QUE NO FALLE

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

# --- FUNCIÓN 2: CREAR EMPRESA A LA FUERZA (CORREGIDA) ---
def crear_empresa_force(request):
    try:
        # 1. Buscamos el modelo 'Company' dentro de la app 'core' dinámicamente
        # Esto evita el error "'Company' no está definido"
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
             return HttpResponse("<h1>❌ ERROR:</h1> <p>Primero debe crear el usuario admin usando /crear-emergencia/</p>")
        
        admin_user = User.objects.get(username='admin')

        # 4. Asignar la empresa al usuario (Prueba varios métodos por si acaso)
        log_asignacion = []
        asignado_exito = False

        # Intento A: Relación Many-to-Many (la más común en ERPs)
        if hasattr(admin_user, 'companies'):
            admin_user.companies.add(empresa)
            log_asignacion.append("✅ Asignado vía admin_user.companies.add()")
            asignado_exito = True
        
        # Intento B: Relación ForeignKey directa
        elif hasattr(admin_user, 'company'):
            admin_user.company = empresa
            admin_user.save()
            log_asignacion.append("✅ Asignado vía admin_user.company = ...")
            asignado_exito = True

        # Intento C: Desde la empresa hacia el usuario
        elif hasattr(empresa, 'users'):
            empresa.users.add(admin_user)
            log_asignacion.append("✅ Asignado vía empresa.users.add()")
            asignado_exito = True
            
        # Intento D: Buscar tabla intermedia manualmente (tenant users)
        else:
            log_asignacion.append("⚠️ No se encontró relación directa. Verifique sus modelos.")

        status = "CREADA NUEVA" if created else "YA EXISTÍA (Recuperada)"
        
        return HttpResponse(f"""
            <div style='font-family: sans-serif; padding: 20px; line-height: 1.6;'>
                <h1 style='color: green;'>🚀 OPERACIÓN EXITOSA</h1>
                <ul>
                    <li><strong>Empresa:</strong> {empresa.name} (ID: {empresa.id})</li>
                    <li><strong>Estado:</strong> {status}</li>
                    <li><strong>Usuario:</strong> {admin_user.username}</li>
                </ul>
                <hr>
                <h3>Intentos de Asignación:</h3>
                <ul>
                    {''.join([f'<li>{log}</li>' for log in log_asignacion])}
                </ul>
                <br>
                <a href='/' style='background: #007bff; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 18px;'>
                    👉 ENTRAR AL SISTEMA AHORA
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