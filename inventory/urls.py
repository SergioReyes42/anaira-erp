from django.urls import path
from . import views

urlpatterns = [
    # --- RUTA PRINCIPAL ---
    path('', views.product_list, name='product_list'),
    
    # --- RUTAS NUEVAS ---
    path('smart-hub/', views.smart_hub, name='smart_hub'),
    path('nuevo/', views.product_create, name='product_create'),
    
    # --- PUENTES (Alias para que el Menú viejo funcione) ---
    
    # 1. El error actual (inventory_kardex) lo mandamos a movimientos
    path('kardex/', views.movement_list, name='inventory_kardex'),
    path('movimientos/', views.movement_list, name='movement_list'),

    # 2. Monitor de existencias (inventory_dashboard) lo mandamos a existencias
    path('monitor/', views.stock_list, name='inventory_dashboard'),
    path('existencias/', views.stock_list, name='stock_list'),

    # 3. Traslados (create_transfer) lo mandamos a crear movimiento
    path('traslados/', views.create_movement, name='create_transfer'),
    path('movimientos/nuevo/', views.create_movement, name='create_movement'),
]