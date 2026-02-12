from django.urls import path
from . import views

urlpatterns = [
    # Gastos
    path('subir-foto/', views.upload_expense_photo, name='upload_expense_photo'),
    path('gasto-manual/', views.gasto_manual, name='gasto_manual'),
    path('reporte-gastos/', views.expense_list, name='expense_list'),
    
    # Aprobaciones
    path('gastos/pendientes/', views.expense_pending_list, name='expense_pending_list'),
    path('gastos/aprobar/<int:pk>/', views.approve_expense, name='approve_expense'),
    path('gastos/rechazar/<int:pk>/', views.reject_expense, name='reject_expense'),

    # Libros y Estados Financieros (Aquí estaban los errores)
    path('libros/diario/', views.libro_diario, name='libro_diario'),
    path('libros/mayor/', views.libro_mayor, name='libro_mayor'),
    path('libros/balance-saldos/', views.balance_saldos, name='balance_saldos'),
    path('estados/resultados/', views.estado_resultados, name='estado_resultados'),
    path('estados/balance-general/', views.balance_general, name='balance_general'),

    # Flotilla
    path('vehiculos/', views.vehicle_list, name='vehicle_list'),
    path('vehiculos/nuevo/', views.vehicle_create, name='vehicle_create'),

    # Bancos
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nueva-cuenta/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),

    #Plan de Cuentas
    path('plan-cuentas/', views.chart_of_accounts, name='chart_of_accounts'),
]