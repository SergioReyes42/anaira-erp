from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('registro/', views.register, name='register'),
    path('perfil/', views.profile_view, name='profile'),
    path('seleccionar-empresa/', views.select_company, name='select_company'),
    
    # Esta es la línea crítica que soluciona tu error actual:
    path('panel-sistema/', views.control_panel, name='control_panel'),

    # Y esta arregla el botón de cerrar sesión que está justo abajo:
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]