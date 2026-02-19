from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # 1. FLUJO DE GASTOS (PILOTO / SCANNER)
    # ==========================================
    path('subir-gasto/rapido/', views.pilot_upload, name='pilot_upload'),
    path('scanner-ia/', views.smart_scanner, name='smart_scanner'),
    
    # Compatibilidad (por si hay links viejos)
    path('subir-foto/', views.upload_expense_photo, name='upload_expense_photo'),

    # ==========================================
    # 2. APROBACIÓN Y REVISIÓN
    # ==========================================
    path('gastos/pendientes/', views.expense_pending_list, name='expense_pending_list'),
    path('gasto/revisar/<int:pk>/', views.review_expense, name='review_expense'),
    path('gasto/aprobar/<int:pk>/', views.approve_expense, name='approve_expense'),
    path('gasto/rechazar/<int:pk>/', views.reject_expense, name='reject_expense'),

    # ==========================================
    # 3. LIBROS Y ESTADOS FINANCIEROS
    # ==========================================
    path('libro-diario/', views.libro_diario, name='libro_diario'),
    path('libro-mayor/', views.libro_mayor, name='libro_mayor'),
    path('balance-saldos/', views.balance_saldos, name='balance_saldos'),
    path('estado-resultados/', views.estado_resultados, name='estado_resultados'),
    path('balance-general/', views.balance_general, name='balance_general'),
    path('plan-cuentas/', views.chart_of_accounts, name='chart_of_accounts'),

    # ==========================================
    # 4. BANCOS Y FLOTILLA
    # ==========================================
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nuevo/', views.bank_create, name='bank_create'),
    path('transaccion/nueva/', views.bank_transaction_create, name='bank_transaction_create'),
    
    path('flotilla/', views.vehicle_list, name='vehicle_list'),
    path('flotilla/nuevo/', views.vehicle_create, name='vehicle_create'),

    path('api/analizar-factura/', views.analyze_receipt_api, name='analyze_receipt_api'),
]