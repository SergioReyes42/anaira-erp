from django.urls import path
from . import views

urlpatterns = [
    # Productos
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    
    # Existencias
    path('stock/', views.stock_list, name='stock_list'),
    
    # Movimientos (Kardex)
    path('movements/', views.movement_list, name='movement_list'),
    path('movements/create/', views.create_movement, name='create_movement'),
]