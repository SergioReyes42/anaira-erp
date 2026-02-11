from django.urls import path
from . import views

urlpatterns = [
    # Gastos y Aprobaciones (Aquí estaba el error)
    path('subir-foto/', views.upload_expense_photo, name='upload_expense_photo'),
    path('gasto-manual/', views.gasto_manual, name='gasto_manual'),
    path('reporte-gastos/', views.expense_list, name='expense_list'),
    
    # --- NUEVAS RUTAS DE APROBACIÓN ---
    path('gastos/pendientes/', views.expense_pending_list, name='expense_pending_list'),
    path('gastos/aprobar/<int:pk>/', views.approve_expense, name='approve_expense'),
    path('gastos/rechazar/<int:pk>/', views.reject_expense, name='reject_expense'),

    # --- NUEVAS RUTAS DE LIBROS CONTABLES ---
    path('libros/diario/', views.libro_diario, name='libro_diario'),
    path('libros/mayor/', views.libro_mayor, name='libro_mayor'),

    # Flotilla (Vehículos)
    path('vehiculos/', views.vehicle_list, name='vehicle_list'),
    path('vehiculos/nuevo/', views.vehicle_create, name='vehicle_create'),

    # Bancos
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nueva-cuenta/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
]