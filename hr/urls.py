from django.urls import path
from . import views

urlpatterns = [
    # 1. EMPLEADOS
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),

    # 2. PRÉSTAMOS
    path('loans/', views.loan_list, name='loan_list'), 
    path('loans/create/', views.loan_create, name='loan_create'),

    # 3. NÓMINAS (CORREGIDO: name='nomina_create')
    path('payroll/create/', views.generate_payroll, name='nomina_create'),
    
    path('payroll/detail/<int:nomina_id>/', views.detalle_nomina, name='detalle_nomina'),

    # 4. EXTRAS
    path('isr/', views.gestion_isr, name='gestion_isr'),
    path('isr/print/', views.imprimir_proyeccion_isr, name='imprimir_proyeccion_isr'),
    path('payroll/print/boleta/<int:nomina_id>/', views.boletas_print, name='boletas_print'),
    path('payroll/print/libro/<int:nomina_id>/', views.libro_salarios_print, name='libro_salarios_print'),
]