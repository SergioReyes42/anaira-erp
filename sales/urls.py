from django.urls import path
from . import views

urlpatterns = [
    # Lista de Cotizaciones
    path('', views.quotation_list, name='quotation_list'),
    
    # Crear Nueva Cotización
    path('nueva/', views.quotation_create, name='quotation_create'),
]