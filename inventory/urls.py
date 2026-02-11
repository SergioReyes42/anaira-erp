from django.urls import path
from . import views

urlpatterns = [
    # Inventario General
    path('', views.dashboard, name='inventory_dashboard'),
    path('productos/', views.product_list, name='product_list'),
    path('movimientos/', views.movement_list, name='inventory_list'),
    path('movimientos/nuevo/', views.create_movement, name='create_movement'),

    # Compras (Las que faltaban y daban error)
    path('compras/', views.purchase_list, name='purchase_list'),
    path('compras/nueva/', views.create_purchase, name='create_purchase'),
    path('proveedores/', views.supplier_list, name='supplier_list'),
]