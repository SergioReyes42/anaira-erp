from django.urls import path
from . import views

urlpatterns = [
    # --- 1. HOME / DASHBOARD (LA ENTRADA PRINCIPAL) ---
    path('', views.home, name='home'), # <--- Aquí estaba el detalle, debe apuntar a 'home'

    # --- 2. RUTAS DE CLIENTES ---
    path('clientes/', views.client_list, name='client_list'),
    path('admin/core/client/add/', views.client_list, name='add_client_shortcut'), # Atajo
    path('clientes/nuevo/', views.create_client, name='client_create'),

    # --- 3. VENTAS Y COTIZACIONES ---
    path('ventas/cotizaciones/', views.quotation_list, name='quotation_list'),
    path('ventas/cotizaciones/nueva/', views.create_quotation, name='create_quotation'),
    path('ventas/cotizaciones/<int:pk>/pdf/', views.quotation_pdf, name='quotation_pdf'),
    path('ventas/convertir/<int:pk>/', views.convertir_a_venta, name='convertir_a_venta'),
    path('ventas/factura/<int:pk>/', views.invoice_pdf, name='invoice_pdf'),

    # --- 4. COMPRAS (NUEVO) ---
    path('compras/', views.purchase_list, name='purchase_list'),
    path('compras/nueva/', views.create_purchase, name='create_purchase'),

    # --- 5. INVENTARIO Y LOGÍSTICA ---
    path('inventario/', views.inventory_list, name='inventory_list'),
    
    # --- 6. TESORERÍA / BANCOS ---
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/crear/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),

    # --- 7. CONTABILIDAD ---
    path('contabilidad/diario/', views.journal_list, name='journal_list'),
    path('contabilidad/mayor/', views.ledger_list, name='ledger_list'),
    path('contabilidad/balance-saldos/', views.trial_balance, name='trial_balance'),
    path('contabilidad/estado-resultados/', views.income_statement, name='income_statement'),
    path('contabilidad/balance-general/', views.balance_sheet, name='balance_sheet'),

    # --- 8. RRHH ---
    path('rrhh/empleados/', views.employee_list, name='employee_list'),
    
    # --- 9. GASTOS ---
    path('gastos/manual/', views.gasto_manual, name='gasto_manual'),
]