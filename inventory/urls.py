from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='inventory_dashboard'),
    
    # Productos
    path('productos/', views.product_list, name='product_list'),
    path('productos/nuevo/', views.product_create, name='product_create'),
    
    # Bodegas (CORREGIDO: Ahora hay dos rutas)
    # 1. La lista (que antes se llamaba management, ahora warehouse_list)
    # Nota: Mantenemos el nombre 'warehouse_management' apuntando a la lista por si el menú lo usa.
    path('bodegas/', views.warehouse_list, name='warehouse_management'), 
    # 2. La creación (que es la que daba el error)
    path('bodegas/nueva/', views.warehouse_create, name='warehouse_create'),

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