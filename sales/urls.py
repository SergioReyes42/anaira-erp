from django.urls import path
from . import views

app_name = 'sales' # 🔥 EL CANDADO DE SEGURIDAD 🔥

urlpatterns = [
    # CRM y Clientes
    path('clientes/', views.client_list, name='client_list'),
    path('clientes/nuevo/', views.client_create, name='client_create'), # <-- AGREGAR ESTA LÍNEA
    
    # Cotizaciones y Pedidos
    path('cotizaciones/', views.quotation_list, name='quotation_list'),
    path('cotizaciones/nueva/', views.quotation_create, name='quotation_create'),
    path('cotizaciones/historial/', views.quotation_history, name='quotation_history'),
    path('pedidos-venta/', views.sales_orders_list, name='sales_orders_list'),
    path('facturacion-electronica/', views.electronic_invoicing_dashboard, name='electronic_invoicing_dashboard'),
    path('seguimiento-crm/', views.crm_tracking_dashboard, name='crm_tracking_dashboard'),
    path('libro-negro/', views.blacklist_dashboard, name='blacklist_dashboard'),
]
