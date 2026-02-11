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

# 1. EMPRESA (LÓGICA)
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    search_fields = ['name']

# 2. PERFIL DE EMPRESA (VISUAL)
@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit', 'phone', 'email']
    search_fields = ['name', 'nit']

# 3. USUARIOS Y PERFILES
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# Re-registramos el User con el inline
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)

@admin.register(Role)

class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(UserRoleCompany)
class UserRoleCompanyAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company']

# 4. LOGÍSTICA
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

# 5. VENTAS Y COMPRAS
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

# 6. GASTOS Y CONTABILIDAD
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

# 7. TESORERÍA
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

# 8. RECURSOS HUMANOS
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'position', 'department']

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'balance', 'is_active']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'total_amount', 'is_closed']