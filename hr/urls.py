from django.urls import path
from . import views

urlpatterns = [
    # --- GESTIÓN DE EMPLEADOS ---
    path('empleados/', views.employee_list, name='employee_list'),
    path('empleados/nuevo/', views.employee_create, name='employee_create'),
    
    # --- NÓMINA ---
    path('nomina/generar/', views.nomina_create, name='nomina_create'),

    # --- ALIAS PARA EL MENÚ (Solución de errores NoReverseMatch) ---
    # Redirigimos estas funciones avanzadas a la lista de empleados por ahora
    # para que el menú no rompa el sistema.
    
    # 1. Proyección ISR Asalariado
    path('empleados/isr/', views.employee_list, name='gestion_isr'),
    
    # 2. Libro de Salarios (MINTRAB)
    path('empleados/libro-salarios/', views.employee_list, name='libro_salarios'),
    
    # 3. Préstamos y Anticipos
    path('empleados/prestamos/', views.employee_list, name='prestamo_list'),
]