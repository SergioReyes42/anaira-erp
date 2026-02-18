from django.shortcuts import render, redirect
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
    """Selección de empresa al iniciar sesión"""
    companies = Company.objects.filter(active=True)
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