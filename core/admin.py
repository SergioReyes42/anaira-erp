from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Company, CompanyProfile, UserProfile, Role, UserRoleCompany,
    Branch, Warehouse, Product, Inventory,
    Client, Supplier, Sale, SaleDetail, Purchase, PurchaseDetail,
    Expense, JournalEntry, Account, Vehicle, CreditCard,
    BankAccount, BankMovement, Income, Quotation, Invoice, 
    StockMovement, Employee, Loan, Payroll
)

# ========================================================
# 1. CONFIGURACIÓN DE USUARIOS (¡LO QUE FALTABA!)
# ========================================================

# Esto permite editar el Perfil (teléfono, dirección) dentro del Usuario
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario'
    fk_name = 'user'

# Esto permite asignar EMPRESAS y ROLES dentro del Usuario
class UserRoleCompanyInline(admin.TabularInline):
    model = UserRoleCompany
    extra = 1  # Muestra una línea vacía lista para agregar
    verbose_name = 'Asignación de Empresa'
    verbose_name_plural = 'Empresas a las que tiene acceso'
    autocomplete_fields = ['company', 'role'] # Ayuda si tienes muchas empresas

# Definimos cómo se ve el Administrador de Usuarios
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserRoleCompanyInline) # <--- AQUÍ AGREGAMOS LAS EMPRESAS
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_companies')

    # Truco para ver las empresas en la lista principal de usuarios
    def get_companies(self, obj):
        return ", ".join([str(urc.company) for urc in obj.userrolecompany_set.all()])
    get_companies.short_description = 'Empresas Asignadas'

# Re-registramos el User de forma segura (con try-except)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)

# ========================================================
# 2. RESTO DE MODELOS (Ya estaban bien)
# ========================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    search_fields = ['name']

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit', 'phone', 'email']
    search_fields = ['name', 'nit']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(UserRoleCompany)
class UserRoleCompanyAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company']
    list_filter = ['company', 'role']
    search_fields = ['user__username', 'company__name']

# 3. LOGÍSTICA
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'location']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch', 'active']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'price', 'stock']
    search_fields = ['name', 'code']

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'warehouse', 'quantity']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['date', 'product', 'movement_type', 'quantity', 'warehouse']
    list_filter = ['movement_type', 'date']

# 4. VENTAS Y COMPRAS
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit', 'email']
    search_fields = ['name', 'nit']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit', 'contact_name']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'date', 'total', 'payment_method']
    list_filter = ['date', 'payment_method']

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'supplier', 'date', 'total', 'status']

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'date', 'total', 'status']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['fel_number', 'client', 'date', 'total']

# 5. GASTOS Y CONTABILIDAD
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'provider', 'description', 'total_amount', 'status']
    list_filter = ['status', 'payment_method', 'date']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'parent']
    ordering = ['code']

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'description', 'is_posted']

# 6. TESORERÍA
@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_number', 'balance']

@admin.register(BankMovement)
class BankMovementAdmin(admin.ModelAdmin):
    list_display = ['date', 'account', 'movement_type', 'amount', 'description']

@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ['alias', 'last_4_digits', 'current_balance']

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ['date', 'description', 'amount', 'bank_account']

# 7. RECURSOS HUMANOS
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'position', 'department']

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'balance', 'is_active']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'total_amount', 'is_closed']