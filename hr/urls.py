from django.urls import path
from . import views

urlpatterns = [
    path('empleados/', views.employee_list, name='employee_list'),
    path('empleados/nuevo/', views.employee_create, name='employee_create'),
    # Esta es la que pide el menú:
    path('nomina/generar/', views.nomina_create, name='nomina_create'),
]