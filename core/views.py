from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, get_user_model # <--- IMPORTANTE: Importamos get_user_model
from django.contrib import messages
# Nota: Ya no importamos 'User' directamente de models
from .forms import CustomUserForm, UserProfileForm, CompanySelectForm
from .models import UserProfile, Company
from .forms import CompanyForm
from sales.models import Sale
from django.db.models import Sum
from accounting.models import Expense, BankAccount

@login_required
def home(request):
    company = getattr(request.user, 'current_company', None)
    
    # 1. Si no hay empresa seleccionada, mandar a seleccionarla
    if not company:
        return redirect('select_company')

    # 2. Calcular Totales Reales
    # Gastos del Mes
    total_gastos = Expense.objects.filter(company=company, status='APPROVED').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Bancos (Disponible)
    total_bancos = BankAccount.objects.filter(company=company).aggregate(Sum('balance'))['balance__sum'] or 0
    
    # Ventas (Placeholder hasta que activemos ventas)
    total_ventas = 0 
    # total_ventas = Sale.objects.filter(company=company).aggregate(Sum('total'))['total__sum'] or 0

    context = {
        'company': company,
        'total_gastos': total_gastos,
        'total_bancos': total_bancos,
        'total_ventas': total_ventas,
    }
    return render(request, 'core/home.html', context)

def register(request):
    """Registro de nuevos usuarios"""
    if request.method == 'POST':
        form = CustomUserForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "¡Registro exitoso! Bienvenido.")
            return redirect('home')
    else:
        form = CustomUserForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile_view(request):
    """Ver y editar perfil"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'core/profile.html', {'form': form})

@login_required
def select_company(request):
    """Vista para cambiar de empresa"""
    if request.method == 'POST':
        form = CompanySelectForm(request.POST)
        if form.is_valid():
            company = form.cleaned_data['company']
            request.user.current_company = company
            request.user.save()
            messages.success(request, f"Cambiado a empresa: {company.name}")
            return redirect('home')
    else:
        form = CompanySelectForm()
    return render(request, 'core/select_company.html', {'form': form})

@login_required
def control_panel(request):
    """Panel de Administración del Sistema"""
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para acceder al panel.")
        return redirect('home')
        
    # --- CORRECCIÓN AQUÍ ---
    # Obtenemos el modelo de usuario dinámicamente
    User = get_user_model() 
    users = User.objects.all()
    # -----------------------

    companies = Company.objects.all()
    
    return render(request, 'core/control_panel.html', {
        'companies': companies, 
        'users': users
    })

@login_required
def company_list(request):
    """Listado de Empresas"""
    # Si no es staff, lo sacamos (opcional, depende de tu regla de negocio)
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido a administración.")
        return redirect('home')
        
    companies = Company.objects.all()
    # Contamos cuántas hay para mostrar en el dashboard si es necesario
    return render(request, 'core/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    """Crear Nueva Empresa"""
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            company = form.save()
            # Si el usuario no tiene empresa, le asignamos esta
            if not request.user.current_company:
                request.user.current_company = company
                request.user.save()
            messages.success(request, f"Empresa {company.name} creada.")
            return redirect('company_list')
    else:
        form = CompanyForm()
    return render(request, 'core/company_form.html', {'form': form})

@login_required
def user_list(request):
    """Listado de Usuarios del Sistema"""
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido.")
        return redirect('home')
    
    User = get_user_model()
    users = User.objects.all()
    return render(request, 'core/user_list.html', {'users': users})

@login_required
def user_create(request):
    """Crear Nuevo Usuario"""
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Opcional: Asignar empresa actual al nuevo usuario si se requiere
            if hasattr(request.user, 'current_company') and request.user.current_company:
                user.current_company = request.user.current_company
                user.save()
            
            messages.success(request, f"Usuario {user.username} creado exitosamente.")
            return redirect('user_list')
    else:
        form = CustomUserForm()
    return render(request, 'core/user_form.html', {'form': form})