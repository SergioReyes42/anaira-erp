from django.urls import path
from . import views

urlpatterns = [
    # Ruta principal (/inventario/)
    path('', views.product_list, name='product_list'),
    
    # 🚨 ESTA ES LA LÍNEA QUE LE FALTA A SU ARCHIVO:
    path('smart-hub/', views.smart_hub, name='smart_hub'),

    # Rutas para evitar errores de enlaces rotos
    path('nuevo/', views.product_create, name='product_create'),
    path('existencias/', views.stock_list, name='stock_list'),
    path('movimientos/', views.movement_list, name='movement_list'),
    path('movimientos/nuevo/', views.create_movement, name='create_movement'),
]