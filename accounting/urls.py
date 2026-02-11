from django.urls import path
from . import views

urlpatterns = [
    # Gastos
    path('subir-foto/', views.upload_expense_photo, name='upload_expense_photo'),
    path('gasto-manual/', views.gasto_manual, name='gasto_manual'),

    # Bancos (Aquí están las que faltaban)
    path('bancos/', views.bank_list, name='bank_list'),
    path('bancos/nueva-cuenta/', views.bank_create, name='bank_create'),
    path('bancos/transaccion/', views.bank_transaction_create, name='bank_transaction_create'),
]