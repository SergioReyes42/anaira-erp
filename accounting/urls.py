from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Configuración de API (Solo incluimos lo que sí existe)
router = DefaultRouter()
router.register(r'accounts', views.AccountViewSet)
router.register(r'journal-entries', views.JournalEntryViewSet)

urlpatterns = [
    # ==========================================
    # 1. REPORTES CONTABLES
    # ==========================================
    path('journal/', views.libro_diario, name='libro_diario'),
    path('balance-sheet/', views.balance_general, name='balance_general'),
    path('income-statement/', views.estado_resultados, name='estado_resultados'),

    # ==========================================
    # 2. GESTIÓN DE CATÁLOGO (LO IMPORTANTE)
    # ==========================================
    path('chart/', views.chart_of_accounts, name='chart_of_accounts'),
    path('chart/add/', views.account_create, name='account_create'),
    path('chart/edit/<int:account_id>/', views.account_edit, name='account_edit'),

    # ==========================================
    # 3. UTILIDADES
    # ==========================================
    path('import/', views.import_accounts_view, name='import_accounts'),
    path('download-template/', views.download_account_template, name='download_account_template'),

    # ==========================================
    # 4. API
    # ==========================================
    path('api/', include(router.urls)),
    path('api/balance/', views.BalanceSheetAPI.as_view(), name='api_balance'),
]