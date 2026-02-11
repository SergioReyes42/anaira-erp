from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('registro/', views.register, name='register'),
    path('perfil/', views.profile_view, name='profile'),
    path('seleccionar-empresa/', views.select_company, name='select_company'),
]