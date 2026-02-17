from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- 1. PÁGINA DE ATERRIZAJE (LANDING) ---
    # Esta es la raíz: Lo que ve el mundo antes de entrar.
    path('', views.landing, name='landing'),

    # --- 2. EL SISTEMA (DASHBOARD) ---
    # Aquí es donde entra el usuario DESPUÉS de loguearse.
    path('dashboard/', views.home, name='home'),

    # --- 3. AUTENTICACIÓN ---
    path('registro/', views.register, name='register'),
    # Al salir, lo mandamos a la Landing Page para que se vea profesional
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    
    # --- 4. UTILIDADES DEL SISTEMA ---
    path('perfil/', views.profile_view, name='profile'),
    path('seleccionar-empresa/', views.select_company, name='select_company'),
    path('panel-sistema/', views.control_panel, name='control_panel'),

    # --- 5. GESTIÓN DE EMPRESAS ---
    path('empresas/', views.company_list, name='company_list'),
    path('empresas/nueva/', views.company_create, name='company_create'),

    # --- 6. GESTIÓN DE USUARIOS ---
    path('usuarios/', views.user_list, name='user_list'),
    path('usuarios/nuevo/', views.user_create, name='user_create'),

    path('fix-db-emergency/', views.db_fix_view, name='db_fix'),
    
]