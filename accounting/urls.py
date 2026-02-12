from django.urls import path
from . import views

urlpatterns = [
    # --- ALIAS PARA EL MENÚ (Solución de errores NoReverseMatch) ---
    path('gastos/dashboard/', views.expense_list, name='dashboard_gastos'),
    path('gastos/ocr/', views.upload_expense_photo, name='mobile_expense'),
    path('flota/reporte/', views.vehicle_list, name='fleet_report'),
    
    # NUEVO ALIAS: El menú pide 'reports_dashboard', lo mandamos al Balance de Saldos
    path('reportes/generales/', views.balance_saldos, name='reports_dashboard'),

    # --- SMART SCANNER ---
    path('smart-scanner/', views.upload_expense_photo, name='smart_hub'),

    # --- GASTOS ---
    path('subir-foto/', views.upload_expense_photo, name='upload_expense_photo'),
    path('gasto-manual/', views.gasto_manual, name='gasto_manual'),
    path('reporte-gastos/', views.expense_list, name='expense_list'),
    
    # --- APROBACIONES ---
    path('gastos/pendientes/', views.expense_pending_list, name='expense_pending_list'),
    path('gastos/aprobar/<int:pk>/', views.approve_expense, name='approve_expense'),
    path('gastos/rechazar/<int:pk>/', views.reject_expense, name='reject_expense'),

    # --- PLAN DE CUENTAS (NIIF) ---
    path('plan-cuentas/', views.chart_of_accounts, name='chart_of_accounts'),

    # --- LIBROS Y ESTADOS FINANCIEROS ---
    path('libros/diario/', views.libro_diario, name='libro_diario'),
    path('libros/mayor/', views.libro_mayor, name='libro_mayor'),
    path('libros/balance-saldos/', views.balance_saldos, name='balance_saldos'),
    path('estados/resultados/', views.estado_resultados, name='estado_resultados'),
    path('estados/balance-general/', views.balance_general, name='balance_general'),

    # --- FLOTILLA ---
    path('vehiculos/', views.vehicle_list, name='vehicle_list'),
    path('vehiculos/nuevo/', views.vehicle_create, name='vehicle_create'),

    # --- BANCOS ---
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nueva-cuenta/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
]