from django.urls import path
from . import views

urlpatterns = [
    # --- GESTIÓN DE EMPLEADOS ---
    path('empleados/', views.employee_list, name='employee_list'),
    path('empleados/nuevo/', views.employee_create, name='employee_create'),

    # --- NÓMINA ---
    path('nomina/generar/', views.nomina_create, name='nomina_create'),
    path('nomina/recibo/<int:line_id>/pdf/', views.payroll_receipt_pdf, name='payroll_receipt_pdf'),

    # --- RRHH ---
    path('vacaciones-permisos/', views.vacaciones_permisos, name='vacaciones_permisos'),
    path('empleados/prestamos/', views.prestamo_list, name='prestamo_list'),
    path('empleados/prestamos/nuevo/', views.prestamo_create, name='prestamo_create'),

    # --- ALIAS TEMPORALES ---
    path('empleados/isr/', views.employee_list, name='gestion_isr'),
    path('empleados/libro-salarios/', views.employee_list, name='libro_salarios'),
]
