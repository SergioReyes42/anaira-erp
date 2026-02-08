from django.urls import path
from . import views

urlpatterns = [
    # --- RUTA PRINCIPAL ---
    path('', views.product_list, name='product_list'),
    
    # --- RUTAS NUEVAS ---
    path('smart-hub/', views.smart_hub, name='smart_hub'),
    path('nuevo/', views.product_create, name='product_create'),
    
    # --- PUENTES (Alias para que el Menú viejo funcione) ---
    # Esto "engaña" al sistema para que los botones viejos lleven a las pantallas nuevas
    
    # 1. El error actual (inventory_kardex) lo mandamos a movimientos
    path('kardex/', views.movement_list, name='inventory_kardex'),
    path('movimientos/', views.movement_list, name='movement_list'),

    # 2. Monitor de existencias (inventory_dashboard) lo mandamos a existencias
    path('monitor/', views.stock_list, name='inventory_dashboard'),
    path('existencias/', views.stock_list, name='stock_list'),

    # 3. Traslados (create_transfer) lo mandamos a crear movimiento
    path('traslados/', views.create_movement, name='create_transfer'),
    path('traslado/', views.make_transfer, name='make_transfer'),
    path('kardex/<int:product_id>/', views.product_kardex, name='product_kardex'),
]