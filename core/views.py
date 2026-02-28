from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import Company

# --- 1. LANDING Y DASHBOARD ---
def landing(request):
    """Página de bienvenida pública"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/landing.html')

@login_required
def home(request):
    """Dashboard Principal"""
    return render(request, 'core/home.html')

# --- 2. GESTIÓN DE EMPRESAS ---
@login_required
def select_company(request):
    """Fase 2 del Login: Obliga al usuario a elegir su entorno de trabajo"""
    
    # Si manda el formulario eligiendo la empresa
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        if company_id:
            company = get_object_or_404(Company, id=company_id)
            request.user.current_company = company
            request.user.save()
            
            # ¡Ahora sí, lo dejamos entrar al Dashboard principal!
            return redirect('core:home') 

    # Si acaba de loguearse, le mostramos la pantalla para elegir
    # (Aquí asumimos que el admin ve todas, ajusta si tus usuarios tienen empresas específicas)
    companies = Company.objects.all() 
    
    # IMPORTANTE: Usamos un HTML especial sin el menú lateral para que no pueda navegar aún
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
def control_panel(request):
    """Panel de Control"""
    return render(request, 'core/control_panel.html')

def db_fix_view(request):
    """Vista de reparación de emergencia"""
    return redirect('home')

@login_required
def switch_company(request, company_id):
    """Cambia la sucursal activa del usuario y recarga la página"""
    # Buscamos la empresa que seleccionó
    company = get_object_or_404(Company, id=company_id)
    
    # Se la asignamos al usuario actual
    request.user.current_company = company
    request.user.save()
    
    messages.success(request, f"🏢 Cambio exitoso: Ahora estás operando en {company.name}")
    
    # Lo devolvemos a la página donde estaba (o al inicio si no hay historial)
    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)

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