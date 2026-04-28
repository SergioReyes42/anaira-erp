from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Company
from django.db import transaction
from django.contrib.auth.models import Group
from django.urls import reverse
from django.shortcuts import redirect
from django.http import JsonResponse
from .ai_brain import responder_chat_contable

User = get_user_model()

# --- 1. LANDING Y DASHBOARD ---
def landing(request):
    """Página de bienvenida pública"""
    if request.user.is_authenticated:
        return redirect('core:home')
    return render(request, 'core/landing.html')

@login_required
def home(request):
    """Dashboard Principal"""
    return render(request, 'core/home.html')

# --- 2. GESTIÓN DE EMPRESAS ---
@login_required
def select_company(request):
    """Fase 2 del Login: Selector Original (Muestra todas las empresas)"""
    
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        if company_id:
            company = get_object_or_404(Company, id=company_id)
            
            # Asignamos la empresa a la variable de memoria del usuario
            request.user.current_company = company
            
            try:
                request.user.save()
            except Exception:
                pass # Ignoramos si el usuario nativo rechaza el guardado
                
            return redirect('core:home')

    # Versión estable: listamos todas las empresas para que elija
    companies = Company.objects.all() 
    
    return render(request, 'core/select_company.html', {'companies': companies})

@login_required
def company_list(request):
    """Lista de empresas"""
    companies = Company.objects.all()
    return render(request, 'core/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    """Crear nueva empresa"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Company.objects.create(name=name)
            messages.success(request, "Empresa creada.")
            return redirect('company_list')
    return render(request, 'core/company_form.html')

# --- 3. USUARIOS Y PERFIL ---
def register(request):
    """Registro de usuarios"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta creada. Inicia sesión.")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_view(request):
    """Ver perfil del usuario"""
    return render(request, 'core/profile.html', {'user': request.user})

@login_required
def user_list(request):
    """Lista de usuarios"""
    return render(request, 'core/user_list.html')

@login_required
def user_create(request):
    """Crear usuario (Aquí estaba el error, ya la agregamos)"""
    if request.method == 'POST':
        # Aquí iría la lógica de creación
        return redirect('user_list')
    return render(request, 'core/user_form.html')

# --- 4. EXTRAS ---
@login_required
def system_panel(request):
    """VISTA ADMIN: Centro de Mando para gestión de usuarios y sistema"""
    
    es_admin = request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()
    
    if not es_admin:
        messages.error(request, "⛔ Acceso denegado. Esta área es exclusiva para Administradores del Sistema.")
        return redirect('core:home')

    # 🔥 NUEVO: Atrapamos el formulario de creación de usuario
    if request.method == 'POST' and 'create_user' in request.POST:
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        rol_nombre = request.POST.get('rol')

        try:
            with transaction.atomic():
                # 1. Magia de Django: Crea el usuario y ENCRIPTA la contraseña
                nuevo_usuario = User.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    password=password
                )
                
                # 2. Le asignamos la misma empresa que tiene el Administrador que lo está creando
                if hasattr(nuevo_usuario, 'current_company'):
                    nuevo_usuario.current_company = request.user.current_company
                    nuevo_usuario.save()

                # 3. Le asignamos su Puesto/Rol (Piloto, Contadora, etc.)
                if rol_nombre:
                    # Buscamos el grupo, si no existe, lo crea automáticamente
                    grupo, created = Group.objects.get_or_create(name=rol_nombre)
                    nuevo_usuario.groups.add(grupo)

                messages.success(request, f"✅ ¡Usuario '{username}' creado exitosamente como {rol_nombre}!")
                return redirect('core:system_panel')

        except Exception as e:
            messages.error(request, f"❌ Error al crear usuario. Revisa que el nombre de usuario no exista ya. Detalle: {str(e)}")
            return redirect('core:system_panel')

    # Traemos todos los usuarios y todos los grupos disponibles para el formulario
    usuarios = User.objects.all().prefetch_related('groups').order_by('-date_joined')
    grupos_disponibles = Group.objects.all()
    
    return render(request, 'core/system_panel.html', {
        'usuarios': usuarios,
        'grupos_disponibles': grupos_disponibles,
    })

def db_fix_view(request):
    """Vista de reparación de emergencia"""
    return redirect('home')

@login_required
def switch_company(request, company_id):
    """Cambia la sucursal activa del usuario y recarga la página con validación de permisos."""
    company = get_object_or_404(Company, id=company_id)

    user = request.user
    allowed = (
        user.is_superuser
        or user.groups.filter(name__in=['Gerente', 'Administrador']).exists()
        or user.allowed_companies.filter(id=company.id).exists()
    )

    if not allowed:
        messages.error(request, "⛔ No tienes permisos para cambiar a esa empresa.")
        next_url = request.META.get('HTTP_REFERER', '/')
        return redirect(next_url)

    user.current_company = company
    user.save(update_fields=['current_company'])
    request.session['company_id'] = company.id

    messages.success(request, f"🏢 Cambio exitoso: Ahora estás operando en {company.name}")

    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)

@login_required
def reporting_hub(request):
    """Hub central de reportes exportables por módulo"""
    reports_by_module = [
        {
            "module": "Contabilidad",
            "icon": "bi-journal-text",
            "reports": [
                {
                    "name": "Libro Diario General",
                    "view_url": reverse("accounting:general_journal"),
                    "excel_url": reverse("accounting:export_general_journal_excel"),
                    "pdf_url": reverse("accounting:export_general_journal_pdf"),
                    "description": "Movimientos contables con exportación en Excel y PDF.",
                }
            ],
        },
        {
            "module": "Ventas",
            "icon": "bi-cart-check",
            "reports": [],
        },
        {
            "module": "Inventario",
            "icon": "bi-box-seam",
            "reports": [],
        },
        {
            "module": "RRHH",
            "icon": "bi-people",
            "reports": [],
        },
        {
            "module": "Importaciones",
            "icon": "bi-ship",
            "reports": [],
        },
    ]
    return render(request, "core/reporting_hub.html", {"reports_by_module": reports_by_module})


@login_required
def login_router(request):
    """
    Enrutador Inteligente post-login:
    - Si es Superusuario, lo manda al Dashboard (con selector habilitado arriba).
    - Si es usuario normal, le asigna su sucursal fija y lo manda al Dashboard.
    """
    user = request.user
    
    # 1. Si es Administrador/Gerente
    if user.is_superuser or user.groups.filter(name__in=['Gerente', 'Administrador']).exists():
        # Asignamos la Sede Central por defecto si no tiene una activa
        if not user.current_company:
            # Aquí asumo que obtienes la sede central, ajusta a tu modelo real
            # user.current_company = Company.objects.first() 
            # user.save()
            pass
        return redirect('home') # Va al Dashboard (Mi Tablero)
        
    # 2. Si es un usuario normal (Ventas, Bodega, etc.)
    else:
        # Aseguramos que solo tenga activa la empresa a la que fue contratado
        # asumiendo que tu usuario tiene un campo "assigned_company" o similar
        if hasattr(user, 'assigned_company') and user.assigned_company:
            user.current_company = user.assigned_company
            user.save()
            
        return redirect('home') # Va directo al Dashboard de su sucursal

@login_required
def ai_contable_chat_page(request):
    """Página UI del chat IA contable (Fase 1)."""
    return render(request, "core/ai_contable_chat.html")


@login_required
def ai_accounting_chat(request):
    """Endpoint JSON para chat IA contable (solo lectura)."""
    if request.method != 'POST':
        return JsonResponse({"ok": False, "error": "Método no permitido."}, status=405)

    pregunta = (request.POST.get('pregunta') or '').strip()
    if not pregunta:
        return JsonResponse({"ok": False, "error": "La pregunta está vacía."}, status=400)

    company = getattr(request.user, 'current_company', None)
    contexto_empresa = getattr(company, 'name', None) if company else None

    data = responder_chat_contable(pregunta, contexto_empresa=contexto_empresa)
    return JsonResponse(data)


def set_working_period(request):
    """Guarda el mes y año en el que el usuario quiere trabajar"""
    if request.method == 'POST':
        mes = request.POST.get('working_month')
        anio = request.POST.get('working_year')
        
        # Lo guardamos en la memoria de la sesión
        if mes and anio:
            request.session['working_month'] = int(mes)
            request.session['working_year'] = int(anio)
            messages.success(request, f"🗓️ Período de trabajo cambiado a {mes}/{anio}.")
            
    # Lo regresamos a la pantalla donde estaba
    return redirect(request.META.get('HTTP_REFERER', '/'))