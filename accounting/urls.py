from django.urls import path
from . import views

urlpatterns = [
    # Gastos y Reportes
    path('subir-foto/', views.upload_expense_photo, name='upload_expense_photo'),
    path('gasto-manual/', views.gasto_manual, name='gasto_manual'),
    path('reporte-gastos/', views.expense_list, name='expense_list'), # <--- ESTA FALTABA

    # Flotilla (Vehículos)
    path('vehiculos/', views.vehicle_list, name='vehicle_list'), # <--- ESTA FALTABA
    path('vehiculos/nuevo/', views.vehicle_create, name='vehicle_create'),

    # Bancos
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nueva-cuenta/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
]