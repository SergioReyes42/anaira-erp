from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Sum
from .forms import CompanySelectionForm, CompanyForm # Asegúrate de que existan o usa los genéricos abajo

# Importamos modelos necesarios
from accounting.models import Expense, BankAccount
from .models import Company

# --- 1. LANDING PAGE (PÚBLICA) ---
def landing(request):
    """Página de bienvenida. Si ya entró, lo manda al Dashboard."""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/landing.html')

# --- 2. DASHBOARD (SISTEMA PRIVADO) ---
@login_required
def home(request):
    """Panel Principal con Totales Reales"""
    company = getattr(request.user, 'current_company', None)
    
    # Si no ha seleccionado empresa, forzar selección
    if not company:
        return redirect('select_company')

    # Calcular Totales Reales
    gastos_query = Expense.objects.filter(company=company, status='APPROVED').aggregate(total=Sum('total_amount'))
    total_gastos = gastos_query['total'] or 0
    
    bancos_query = BankAccount.objects.filter(company=company).aggregate(total=Sum('balance'))
    total_bancos = bancos_query['total'] or 0
    
    # Placeholder ventas
    total_ventas = 0 

    context = {
        'company': company,
        'total_gastos': total_gastos,
        'total_bancos': total_bancos,
        'total_ventas': total_ventas,
    }
    return render(request, 'core/home.html', context)

# --- 3. GESTIÓN DE EMPRESA Y SESIÓN ---

@login_required
def select_company(request):
    # Intentamos importar el form, si falla usamos uno genérico en la vista (por seguridad)
    try:
        from .forms import CompanySelectionForm
    except ImportError:
        # Si no existe el form, redirigimos a crear (parche temporal)
        return redirect('company_create')

    if request.method == 'POST':
        form = CompanySelectionForm(request.POST, user=request.user)
        if form.is_valid():
            company = form.cleaned_data['company']
            request.user.current_company = company
            request.user.save()
            return redirect('home')
    else:
        form = CompanySelectionForm(user=request.user)
        
    return render(request, 'core/select_company.html', {'form': form})

def register(request):
    """Vista de Registro de Usuarios Nuevos"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Aquí podrías loguearlo directamente o mandar al login
            messages.success(request, "Cuenta creada exitosamente. Inicia sesión.")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

# --- 4. VISTAS ADICIONALES (Para evitar errores en urls.py) ---

@login_required
def profile_view(request):
    return render(request, 'core/profile.html', {'user': request.user})

@login_required
def control_panel(request):
    return render(request, 'core/control_panel.html')

@login_required
def company_list(request):
    companies = request.user.companies.all()
    return render(request, 'core/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    # Lógica simple para crear empresa
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            company = Company.objects.create(name=name, active=True)
            company.users.add(request.user)
            request.user.current_company = company
            request.user.save()
            return redirect('home')
    # Renderizamos un template genérico o el específico
    return render(request, 'core/company_form.html')

@login_required
def user_list(request):
    # Placeholder
    return render(request, 'core/user_list.html')

@login_required
def user_create(request):
    # Placeholder
    return redirect('user_list')

from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth.decorators import user_passes_test

# Solo superusuarios pueden tocar este botón de pánico
@user_passes_test(lambda u: u.is_superuser)
def db_fix_view(request):
    try:
        # 1. Crear las migraciones automáticamente (Detectar el campo 'vehicle')
        call_command('makemigrations', 'accounting')
        
        # 2. Aplicar los cambios a la base de datos
        call_command('migrate')
        
        return HttpResponse("<h1>✅ ¡Base de Datos Actualizada! Se agregó la columna Vehículo.</h1>")
    except Exception as e:
        return HttpResponse(f"<h1>❌ Error: {e}</h1>")