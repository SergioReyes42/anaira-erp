from django.urls import path
from . import views

urlpatterns = [
    # --- ACCESO Y CONFIGURACIÓN ---
    # CORRECCIÓN AQUÍ: Agregamos ambas rutas para evitar el error 404
    path('', views.login_view, name='root'),         # Ruta raíz (http://127.0.0.1:8000/)
    path('login/', views.login_view, name='login'),  # Ruta explícita (http://127.0.0.1:8000/login/)
    
    path('logout/', views.logout_view, name='logout'),
    path('select_company/', views.select_company, name='select_company'),
    path('home/', views.home, name='home'),
    
    # Esta línea arregla el error específico que tenía:
    # Redirigimos 'workspace' al dashboard de gastos
    path('workspace/', views.dashboard_gastos, name='workspace'), 

    # --- GASTOS ---
    path('dashboard/', views.dashboard_gastos, name='dashboard_gastos'),
    path('gastos/lista/', views.expense_list, name='expense_list'),
    path('gastos/nuevo/manual/', views.gasto_manual, name='gasto_manual'),
    path('gastos/nuevo/rapido/', views.mobile_expense, name='mobile_expense'),
    path('api/ocr/', views.api_ocr_process, name='api_ocr'),
    
    # --- TESORERÍA (BANCOS) ---
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/<int:bank_id>/', views.bank_detail, name='bank_detail'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction'),
    path('bancos/transferencia/', views.transfer_create, name='transfer_create'),
    
    # --- INGRESOS Y PROVEEDORES ---
    path('ingresos/', views.income_list, name='income_list'),
    path('ingresos/nuevo/', views.income_create, name='income_create'),
    path('proveedores/', views.supplier_list, name='supplier_list'),
    path('proveedores/pagar/', views.pay_supplier, name='pay_supplier'),

    # --- INVENTARIO (SMART SCANNER) ---
    path('inventario/scanner/', views.smart_hub, name='smart_hub'), # El cerebro
    path('inventario/catalogo/', views.product_list, name='product_list'),
    path('inventario/producto/nuevo/', views.product_create, name='product_create'),
    path('inventario/producto/<int:pk>/', views.product_detail, name='product_detail'),
    path('inventario/movimiento/', views.create_movement, name='create_movement'),

    # --- RECURSOS HUMANOS ---
    path('rrhh/empleados/', views.employee_list, name='employee_list'),
    path('rrhh/nomina/generar/', views.nomina_create, name='nomina_create'),
    path('rrhh/isr/proyeccion/', views.gestion_isr, name='gestion_isr'),
    path('rrhh/libro-salarios/', views.libro_salarios, name='libro_salarios'),
    path('rrhh/prestamos/', views.prestamo_list, name='prestamo_list'),

    # --- CONTABILIDAD Y REPORTES ---
    path('contabilidad/libro-diario/', views.libro_diario, name='libro_diario'),
    path('contabilidad/libro-mayor/', views.libro_mayor, name='libro_mayor'),
    path('contabilidad/balance-saldos/', views.balance_saldos, name='balance_saldos'),
    path('reportes/estados-resultados/', views.estado_resultados, name='estado_resultados'),
    path('reportes/balance-general/', views.balance_general, name='balance_general'),
    
    path('reportes/dashboard/', views.reports_dashboard, name='reports_dashboard'),
    path('reportes/flota/', views.fleet_report, name='fleet_report'),
    path('reportes/bancos/', views.report_bank_statement, name='report_bank_statement'),
    path('reportes/inventario/', views.report_inventory, name='report_inventory'),

    path('sistema/panel-control/', views.admin_control_panel, name='control_panel'),

    path('gastos/exportar-csv/', views.export_expenses_csv, name='export_expenses_csv'),

    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
    
    path('bancos/transferencia/', views.transfer_create, name='transfer_create'),

    path('crear-super-admin/', views.crear_admin_express),
]