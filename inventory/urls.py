from django.urls import path
from . import views

urlpatterns = [
    # Dashboard Principal de Inventario
    # CORRECCIÓN: Usamos 'dashboard', no 'home'
    path('', views.dashboard, name='inventory_dashboard'),
    
    # Productos
    path('productos/', views.product_list, name='product_list'),
    path('productos/nuevo/', views.product_create, name='product_create'),
    
    # Bodegas
    path('bodegas/', views.warehouse_management, name='warehouse_management'), 

    # Movimientos
    path('movimientos/', views.movement_list, name='inventory_list'),
    path('movimientos/nuevo/', views.create_movement, name='create_movement'),
    path('kardex/', views.inventory_kardex, name='inventory_kardex'),
    path('transferencia/', views.make_transfer, name='make_transfer'),

    # Compras
    path('compras/', views.purchase_list, name='purchase_list'),
    path('compras/nueva/', views.create_purchase, name='create_purchase'),
    path('proveedores/', views.supplier_list, name='supplier_list'),
]