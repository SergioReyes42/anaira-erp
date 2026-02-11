from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserForm, UserProfileForm, CompanySelectForm
from .models import UserProfile, Company

def home(request):
    """Vista principal (Landing page o Dashboard general)"""
    if request.user.is_authenticated:
        # Si ya tiene empresa, mostrar dashboard
        if hasattr(request.user, 'current_company') and request.user.current_company:
            return render(request, 'core/home.html')
        else:
            # Si no tiene empresa seleccionada, pedirle que seleccione una
            return redirect('select_company')
    return render(request, 'core/landing.html') # O redirigir a login

def register(request):
    """Registro de nuevos usuarios"""
    if request.method == 'POST':
        form = CustomUserForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            # Loguear automáticamente
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
    """Vista para cambiar de empresa (Contexto)"""
    if request.method == 'POST':
        form = CompanySelectForm(request.POST)
        if form.is_valid():
            company = form.cleaned_data['company']
            # Guardamos la empresa en la sesión o en el usuario
            request.user.current_company = company
            request.user.save()
            messages.success(request, f"Cambiado a empresa: {company.name}")
            return redirect('home')
    else:
        form = CompanySelectForm()
    
    return render(request, 'core/select_company.html', {'form': form})