from django.urls import path
from . import views

app_name = 'sales' # 🔥 EL CANDADO DE SEGURIDAD 🔥

urlpatterns = [
    # CRM y Clientes
    path('clientes/', views.client_list, name='client_list'),
    
    # Cotizaciones y Pedidos
    path('cotizaciones/', views.quotation_list, name='quotation_list'),
    path('cotizaciones/nueva/', views.quotation_create, name='quotation_create'),
]