from django.urls import path
from . import views

app_name = 'imports'

urlpatterns = [
    path('', views.duca_list, name='duca_list'),
    path('nueva/', views.duca_create, name='duca_create'),
    path('<int:pk>/', views.duca_detail, name='duca_detail'),
    path('<int:pk>/tracking/nuevo/', views.tracking_add, name='tracking_add'),

    # Rutas para las Órdenes de Compra:
    path('ordenes-compra/', views.po_list, name='po_list'),
    path('ordenes-compra/nueva/', views.po_create, name='po_create'),
]