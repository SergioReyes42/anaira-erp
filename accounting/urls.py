from django.urls import path
from . import views

app_name = 'accounting'

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
    # Rutas legacy (sin colisión con rutas NIIF nuevas)
    path('libro-diario-legacy/', views.libro_diario, name='libro_diario'),
    path('libro-mayor-legacy/', views.libro_mayor, name='libro_mayor'),
    path('balance-saldos/', views.balance_saldos, name='balance_saldos'),
    path('estado-resultados-legacy/', views.estado_resultados, name='estado_resultados'),
    path('balance-general-legacy/', views.balance_general, name='balance_general'),
    path('plan-cuentas/', views.chart_of_accounts, name='chart_of_accounts'),

    # ==========================================
    # 4. BANCOS Y FLOTILLA
    # ==========================================
    # path('bancos/', views.bank_list, name='bank_list'),
    # path('bancos/nuevo/', views.bank_create, name='bank_create'),
    path('transaccion/nueva/', views.bank_transaction_create, name='bank_transaction_create'),
    path('bancos/', views.bank_dashboard, name='bank_dashboard'),
    path('bancos/nueva-cuenta/', views.bank_create, name='bank_create'),
    path('flotilla/', views.vehicle_list, name='vehicle_list'),
    path('flotilla/nuevo/', views.vehicle_create, name='vehicle_create'),
    path('bancos/deposito/', views.register_deposit, name='register_deposit'),
    path('api/analizar-factura/', views.analyze_receipt_api, name='analyze_receipt_api'),
    path('bancos/retiro/', views.registrar_retiro, name='registrar_retiro'),
    path('reporte-flotilla/', views.fleet_expense_report, name='fleet_report'),
    path('reporte-flotilla/pdf/', views.fleet_expense_report_pdf, name='fleet_report_pdf'),
    path('bancos/nueva-cuenta/', views.nueva_cuenta_bancaria, name='nueva_cuenta'),

    path('migracion-saldos/', views.opening_balance_migration, name='opening_balance'),

    path('aprobar-gasto/<int:expense_id>/', views.approve_expense, name='approve_expense'),

    path('libro-diario/', views.general_journal, name='general_journal'),

    path('plan-de-cuentas/', views.chart_of_accounts, name='chart_of_accounts'),

    path('libro-mayor/', views.general_ledger, name='general_ledger'),

    path('balance-general/', views.balance_sheet, name='balance_sheet'),

    path('estado-resultados/', views.income_statement, name='income_statement'),

    path('balance-comprobacion/', views.trial_balance, name='trial_balance'),

    path('libro-compras/', views.purchase_ledger, name='purchase_ledger'),

    path('libro-ventas/', views.sales_ledger, name='sales_ledger'),

    path('cierre-fiscal/', views.fiscal_close, name='fiscal_close'),

    path('reportes/libro-diario/excel/', views.export_general_journal_excel, name='export_general_journal_excel'),
    path('reportes/libro-diario/pdf/', views.export_general_journal_pdf, name='export_general_journal_pdf'),
    path('manual-partida/', views.manual_journal_entry_create, name='manual_journal_entry_create'),

    path('supervision-gastos/', views.expense_pre_review_list, name='expense_pre_review_list'),

    path('tarjetas-credito/', views.panel_tarjetas, name='panel_tarjetas'),

    path('tarjetas-credito/nueva/', views.nueva_tarjeta, name='nueva_tarjeta'),

    path('bancos/transferencia-interna/', views.transferencia_interna, name='transferencia_interna'),

    path('tarjetas-credito/consumo/', views.registrar_consumo_tarjeta, name='registrar_consumo_tarjeta'),
    path('tarjetas-credito/pagar/', views.pagar_tarjeta_credito, name='pagar_tarjeta_credito'),

    # ==========================================
    # 5. COMPRAS
    # ==========================================
    path('compras/historial/', views.purchase_history, name='purchase_history'),
    path('compras/nueva/', views.purchase_create, name='purchase_create'),
    path('compras/proveedores/', views.suppliers_list, name='suppliers_list'),
    path('compras/registrar-gasto-ia/', views.ai_expense_register, name='ai_expense_register'),
    path('compras/gastos-operativos/', views.operating_expenses, name='operating_expenses'),
    path('compras/ordenes/', views.purchase_orders, name='purchase_orders'),

    # ==========================================
    # 6. CUENTAS POR PAGAR (CXP)
    # ==========================================
    path('cxp/', views.cxp_dashboard, name='cxp_dashboard'),
    path('cxp/nueva/', views.registrar_factura_cxp, name='registrar_factura_cxp'),

    # ==========================================
    # 7. TESORERÍA / BANCOS (NUEVAS PÁGINAS MENÚ)
    # ==========================================
    path('cxc/', views.cxc_dashboard_view, name='cxc_dashboard'),
    path('programacion-pagos/', views.payment_schedule_view, name='payment_schedule'),
    path('notas-credito-debito/', views.credit_debit_notes_view, name='credit_debit_notes'),

]
