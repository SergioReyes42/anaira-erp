from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import NotRegistered # Importante para el error

# Importación de TODOS tus modelos
from .models import (
    # Núcleo
    Company, CompanyProfile, UserProfile, Role, UserRoleCompany,
    # Estructura
    Branch, Warehouse, 
    # Inventario y Productos
    Product, Inventory, StockMovement, InventoryMovement,
    # Ventas y Clientes
    Client, Quotation, QuotationDetail, Sale, SaleDetail, Invoice, InvoiceDetail,
    # Compras y Proveedores
    Supplier, Provider, Purchase, PurchaseDetail,
    # Tesorería
    BankAccount, BankTransaction, BankMovement, Income,
    # Gastos y Activos
    Expense, Vehicle, CreditCard,
    # Contabilidad
    Account, JournalEntry, JournalItem,
    # RRHH
    Employee, Loan, Payroll, PayrollDetail
)

# ========================================================
# 1. PERSONALIZACIÓN DEL USUARIO (PERFIL INTEGRADO)
# ========================================================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario ERP'
    filter_horizontal = ('allowed_companies',)

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'is_staff', 'get_active_company')
    
    def get_active_company(self, obj):
        if hasattr(obj, 'profile') and obj.profile.active_company:
            return obj.profile.active_company.name
        return "-"
    get_active_company.short_description = 'Empresa Activa'

# --- CORRECCIÓN DEL ERROR AQUÍ ---
# Intentamos des-registrar el usuario por defecto. 
# Si no estaba registrado, ignoramos el error y seguimos.
try:
    admin.site.unregister(User)
except NotRegistered:
    pass

# Ahora sí lo registramos con nuestra configuración
admin.site.register(User, UserAdmin)


# ========================================================
# 2. CONTABILIDAD Y FINANZAS (Módulo Crítico)
# ========================================================

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_group', 'balance')
    list_filter = ('account_type', 'is_group')
    search_fields = ('code', 'name')
    ordering = ('code',)

class JournalItemInline(admin.TabularInline):
    model = JournalItem
    extra = 2

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'description', 'reference', 'is_posted', 'total_debit', 'total_credit')
    inlines = [JournalItemInline]
    list_filter = ('is_posted', 'date')
    search_fields = ('description', 'reference')
    ordering = ('-date', '-id')

    def total_debit(self, obj):
        return sum(item.debit for item in obj.items.all())
    
    def total_credit(self, obj):
        return sum(item.credit for item in obj.items.all())

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('date', 'provider', 'total_amount', 'status', 'is_fuel', 'payment_method')
    list_filter = ('status', 'is_fuel', 'payment_method', 'date')
    search_fields = ('provider', 'description')
    ordering = ('-date',)


# ========================================================
# 3. INVENTARIO Y LOGÍSTICA
# ========================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'stock', 'price', 'cost')
    search_fields = ('name', 'code')
    list_filter = ('stock',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'location')
    list_filter = ('warehouse',)
    search_fields = ('product__name', 'warehouse__name')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('date', 'product', 'warehouse', 'movement_type', 'quantity', 'user')
    list_filter = ('movement_type', 'warehouse', 'date')
    search_fields = ('product__name', 'product__code')
    readonly_fields = ('date',)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'company')
    search_fields = ('name', 'code')

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'active')
    list_filter = ('branch', 'active')


# ========================================================
# 4. VENTAS, COMPRAS Y TESORERÍA
# ========================================================

class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'client', 'total', 'payment_method')
    inlines = [SaleDetailInline]
    list_filter = ('date', 'payment_method')
    search_fields = ('client__name',)

class PurchaseDetailInline(admin.TabularInline):
    model = PurchaseDetail
    extra = 0

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'supplier', 'total', 'status')
    inlines = [PurchaseDetailInline]
    list_filter = ('status', 'date')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone', 'email')
    search_fields = ('name', 'nit')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone')
    search_fields = ('name', 'nit')


# ========================================================
# 5. REGISTROS SIMPLES (Sin configuración especial)
# ========================================================

# Núcleo
admin.site.register(Company)
admin.site.register(CompanyProfile)
admin.site.register(Role)
admin.site.register(UserRoleCompany)

# Operaciones
admin.site.register(Quotation)
admin.site.register(QuotationDetail)
admin.site.register(Invoice)
admin.site.register(InvoiceDetail)
admin.site.register(InventoryMovement) # Legacy
admin.site.register(Provider) # Legacy

# Tesorería
admin.site.register(BankAccount)
admin.site.register(BankTransaction)
admin.site.register(BankMovement)
admin.site.register(Income)
admin.site.register(CreditCard)

# Activos
admin.site.register(Vehicle)

# RRHH
admin.site.register(Employee)
admin.site.register(Loan)
admin.site.register(Payroll)
admin.site.register(PayrollDetail)