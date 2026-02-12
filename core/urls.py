from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # --- RUTAS GENERALES ---
    path('', views.home, name='home'),
    path('registro/', views.register, name='register'),
    path('perfil/', views.profile_view, name='profile'),
    path('seleccionar-empresa/', views.select_company, name='select_company'),
    path('panel-sistema/', views.control_panel, name='control_panel'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- EMPRESAS ---
    path('empresas/', views.company_list, name='company_list'),
    path('empresas/nueva/', views.company_create, name='company_create'),

    # --- USUARIOS (¡ESTO ES LO QUE FALTABA!) ---
    path('usuarios/', views.user_list, name='user_list'),
    path('usuarios/nuevo/', views.user_create, name='user_create'),
]