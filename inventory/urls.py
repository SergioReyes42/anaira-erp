from django.urls import path
from . import views

urlpatterns = [
    # Ruta vacía = Dashboard
    path('', views.dashboard, name='inventory_dashboard'),
    
    # Ruta /productos/ = Lista de productos
    path('productos/', views.product_list, name='product_list'),
    
    # Ruta /movimientos/ = Historial
    path('movimientos/', views.movement_list, name='inventory_list'),
    
    # Ruta /movimientos/nuevo/ = Crear movimiento
    path('movimientos/nuevo/', views.create_movement, name='create_movement'),
]