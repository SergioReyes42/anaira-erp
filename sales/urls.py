from django.urls import path
from . import views

urlpatterns = [
    # Esta es la línea que Django no encuentra:
    path('cotizaciones/nueva/', views.quotation_create, name='quotation_create'),
    
    # Estas son las otras que pide el menú:
    path('cotizaciones/', views.quotation_list, name='quotation_list'),
    path('clientes/', views.client_list, name='client_list'),
]