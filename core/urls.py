from django.urls import path
from . import views

urlpatterns = [
    # --- ACCESO Y DASHBOARD ---
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('seleccionar-empresa/', views.select_company, name='select_company'),
    path('', views.home, name='home'),

    # --- GASTOS Y OCR ---
    path('gastos/dashboard/', views.dashboard_gastos, name='dashboard_gastos'),
    path('gastos/lista/', views.expense_list, name='expense_list'),
    path('gastos/movil/', views.mobile_expense, name='mobile_expense'),
    path('gastos/manual/', views.gasto_manual, name='gasto_manual'),
    path('api/ocr/', views.api_ocr_process, name='api_ocr_process'),

    # --- TESORERÍA / BANCOS ---
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nueva/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
    path('bancos/<int:bank_id>/detalle/', views.bank_detail, name='bank_detail'),
    path('bancos/transferencia/', views.transfer_create, name='transfer_create'),
    path('ventas/cotizacion/<int:quote_id>/imprimir/', views.quotation_print, name='quotation_print'),
    
    # --- INGRESOS ---
    path('ingresos/', views.income_list, name='income_list'),
    path('ingresos/nuevo/', views.income_create, name='income_create'),

    # --- PROVEEDORES Y COMPRAS ---
    path('proveedores/', views.supplier_list, name='supplier_list'),
    path('proveedores/pagar/', views.pay_supplier, name='pay_supplier'),
    path('compras/', views.purchase_list, name='purchase_list'),
    path('compras/nueva/', views.create_purchase, name='create_purchase'),

    # --- INVENTARIO (Aquí estaba el error) ---
    # path('inventario/smart-hub/', views.smart_hub, name='smart_hub'), # <--- ESTA FALTABA
    # path('inventario/', views.product_list, name='product_list'), # Antes 'inventory_list'
    # path('inventario/nuevo/', views.product_create, name='product_create'),
    # path('inventario/kardex/', views.inventory_kardex, name='inventory_kardex'),
    # path('inventario/movimiento/', views.create_movement, name='create_movement'),
    # path('inventario/traslado/', views.create_transfer, name='create_transfer'),
    # path('inventario/kardex/', views.kardex_list, name='kardex_list'),

    # --- VENTAS Y CLIENTES ---
    path('clientes/', views.client_list, name='client_list'),
    path('clientes/nuevo/', views.client_create, name='client_create'),
    path('ventas/cotizaciones/', views.quotation_list, name='quotation_list'),
    path('ventas/cotizaciones/nueva/', views.create_quotation, name='create_quotation'),
    path('ventas/cotizacion/<int:quote_id>/facturar/', views.convert_quote_to_sale, name='convert_quote_to_sale'),
    path('ventas/cotizacion/<int:pk>/pdf/', views.quotation_pdf, name='quotation_pdf'),
    path('ventas/factura/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),

    # --- RRHH ---
    path('rrhh/empleados/', views.employee_list, name='employee_list'),
    path('rrhh/nomina/generar/', views.nomina_create, name='nomina_create'),
    path('rrhh/isr/', views.gestion_isr, name='gestion_isr'),
    path('rrhh/libro-salarios/', views.libro_salarios, name='libro_salarios'),
    path('rrhh/prestamos/', views.prestamo_list, name='prestamo_list'),

    # --- REPORTES Y ADMIN ---
    path('reportes/dashboard/', views.reports_dashboard, name='reports_dashboard'),
    path('reportes/flota/', views.fleet_report, name='fleet_report'),
    path('reportes/bancos/', views.report_bank_statement, name='report_bank_statement'),
    path('reportes/inventario/', views.report_inventory, name='report_inventory'),
    path('admin-panel/', views.admin_control_panel, name='control_panel'),
    path('export/csv/', views.export_expenses_csv, name='export_expenses_csv'),

    # --- CONTABILIDAD ---
    path('contabilidad/diario/', views.libro_diario, name='libro_diario'),
    path('contabilidad/mayor/', views.libro_mayor, name='libro_mayor'),
    path('contabilidad/balance/', views.balance_saldos, name='balance_saldos'),
    path('contabilidad/estado-resultados/', views.income_statement, name='estado_resultados'),
    path('contabilidad/balance-general/', views.balance_sheet, name='balance_general'),

    path('api/validate-unlock/', views.validate_price_unlock, name='validate_price_unlock'),

    path('inventario/monitor/', views.dashboard_inventario, name='inventory_dashboard'),

    path('fix-users-emergency/', views.fix_profiles_view, name='fix_users'),

    path('reset-password-emergency/', views.force_password_reset, name='reset_password'), # <--- LA NUEVA

    # COTIZACIONES
    path('cotizaciones/', views.quotation_list, name='quotation_list'),
    path('cotizaciones/nueva/', views.quotation_create, name='quotation_create'),
    path('cotizaciones/<int:id>/ver/', views.quotation_print, name='quotation_view'), # Ojo: Asegúrate que esta se llame 'quotation_view' o ajusta el HTML    
    path('cotizaciones/<int:id>/convertir/', views.quotation_convert, name='quotation_convert'),

    # VER COTIZACION (El visor nuevo)
    path('cotizaciones/<int:id>/ver/', views.quotation_print, name='quotation_view'), # Actualiza el nombre de la vista en views.py a quotation_view si cambiaste el nombre
    
    # ACCIÓN: CONVERTIR
    path('cotizaciones/<int:quote_id>/facturar/', views.convert_quote_to_invoice, name='convert_quote_to_invoice'),
    
    # VER FACTURA (Crea el template invoice_view.html copiando el de cotización)
    path('facturas/<int:id>/ver/', views.invoice_view, name='invoice_view'),

    # USUARIOS
    path('config/usuarios/', views.user_list, name='user_list'),
    path('config/usuarios/nuevo/', views.user_create, name='user_create'),
    path('config/panel-sistema/', views.control_panel, name='control_panel'),

    path('config/empresas/', views.company_list, name='company_list'),
    path('config/empresas/nueva/', views.company_create, name='company_create'),

]