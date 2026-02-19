from django.urls import path
from . import views

urlpatterns = [
    # Cotizaciones (Ya las tenías)
    path('', views.quotation_list, name='quotation_list'),
    path('nueva/', views.quotation_create, name='quotation_create'),
    
    # Clientes (ESTA ES LA QUE FALTABA PARA CORREGIR EL ERROR)
    path('clientes/', views.client_list, name='client_list'),
]