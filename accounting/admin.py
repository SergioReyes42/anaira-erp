from django.contrib import admin
from .models import (
    Vehicle, Expense, BankAccount, BankTransaction, 
    JournalEntry, JournalItem, Account, JournalEntryLine
)

# ==========================================
# 1. CONFIGURACIÓN PARA PARTIDAS CONTABLES
# ==========================================

# --- NUEVOS MODELOS CONTABLES ---

class JournalEntryLineInline(admin.TabularInline):
    """Permite ver las líneas del Debe y Haber dentro de la Partida"""
    model = JournalEntryLine
    extra = 1

class JournalItemInline(admin.TabularInline):
    """
    Esto permite editar el DEBE y HABER dentro de la misma Partida.
    """
    model = JournalItem
    extra = 0 # No muestra filas vacías extra
    classes = ('collapse',) # Permite colapsar si es muy largo

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    # Actualizado con los nombres exactos de tu nuevo modelo
    # list_display = ('id', 'date', 'concept', 'company', 'is_opening_balance')
    # list_filter = ('date', 'is_opening_balance', 'company')
    search_fields = ('concept', 'company')
    inlines = [JournalEntryLineInline] # Agrega las líneas adentro

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_transactional')
    search_fields = ('code', 'name')
    list_filter = ('account_type', 'is_transactional')

# ==========================================
# 2. CONFIGURACIÓN PARA GASTOS
# ==========================================

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'description', 'total_amount', 'status', 'vehicle', 'user')
    list_filter = ('status', 'company', 'date', 'vehicle')
    search_fields = ('description', 'provider_name', 'invoice_number')
    readonly_fields = ('date',) # Evita que manipulen la fecha de creación
    
    fieldsets = (
        ('Información General', {
            'fields': ('company', 'user', 'date', 'description', 'receipt_image')
        }),
        ('Detalle Financiero', {
            'fields': ('total_amount', ('tax_base', 'tax_iva', 'tax_idp'), 'status')
        }),
        ('Datos del Proveedor (IA)', {
            'classes': ('collapse',),
            'fields': ('provider_name', 'provider_nit', 'invoice_series', 'invoice_number')
        }),
    )

# ==========================================
# 3. CONFIGURACIÓN PARA BANCOS
# ==========================================

class BankTransactionInline(admin.TabularInline):
    model = BankTransaction
    extra = 0
    readonly_fields = ('date', 'transaction_type', 'amount', 'description')
    can_delete = False # Por seguridad, no borrar transacciones desde aquí

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_number', 'currency', 'initial_balance', 'company')
    list_filter = ('company', 'currency')
    search_fields = ('bank_name', 'account_number')
    inlines = [BankTransactionInline] # Ver movimientos dentro de la cuenta

@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'transaction_type', 'amount', 'description', 'account')
    list_filter = ('transaction_type', 'date', 'account')
    search_fields = ('description', 'reference')
    date_hierarchy = 'date'

# ==========================================
# 4. CONFIGURACIÓN PARA FLOTILLA
# ==========================================

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate', 'brand', 'line', 'driver_name', 'active', 'company')
    list_filter = ('active', 'company', 'brand')
    search_fields = ('plate', 'driver_name')
    list_editable = ('active', 'driver_name') # ¡Editar rápido desde la lista!
    filter_horizontal = ('conductores',)