from django.urls import path
from . import views

urlpatterns = [
    # === DASHBOARD PRINCIPAL ===
    path('', views.bank_list, name='home'), # Por ahora el inicio es bancos

    # === TESORERÍA Y BANCOS (Lo que ya funciona) ===
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/crear/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
    path('bancos/estado-de-cuenta/<int:bank_id>/', views.bank_statement, name='bank_statement'),
    path('bancos/recalcular/<int:bank_id>/', views.recalcular_saldo, name='recalcular_saldo'),
    path('transaccion/eliminar/<int:pk>/', views.delete_transaction, name='delete_transaction'),

    # === GASTOS (Lo que ya funciona) ===
    path('gastos/nuevo/', views.gasto_manual, name='gasto_manual'),
    path('gastos/lista/', views.expense_list, name='expense_list'), # Asegúrese de tener esta vista o cambie el nombre

    # === CONTABILIDAD (NUEVO - Para que el menú no falle) ===
    path('contabilidad/libro-diario/', views.journal_list, name='journal_list'),
    path('contabilidad/libro-mayor/', views.ledger_list, name='ledger_list'),
    path('contabilidad/balance-saldos/', views.trial_balance, name='trial_balance'),
    
    # === ESTADOS FINANCIEROS (NUEVO) ===
    path('financiero/estado-resultados/', views.income_statement, name='income_statement'),
    path('financiero/balance-general/', views.balance_sheet, name='balance_sheet'),
    
    # === RRHH (NUEVO) ===
    path('rrhh/empleados/', views.employee_list, name='employee_list'),

    # === LOGÍSTICA / INVENTARIO (Aquí estaba el error) ===
    path('inventario/kardex/', views.inventory_list, name='inventory_list'),

  # === RUTAS DE CLIENTES ===
    path('clientes/', views.client_list, name='client_list'),
    path('clientes/nuevo/', views.client_create, name='client_create'),

  # === COTIZACIONES ===
    path('ventas/cotizaciones/', views.quotation_list, name='quotation_list'),
    path('ventas/cotizacion/nueva/', views.quotation_create, name='quotation_create'),

    path('ventas/cotizacion/<int:pk>/pdf/', views.quotation_pdf, name='quotation_pdf'),
]