from django.contrib import admin
from .models import Expense, BankAccount, BankTransaction

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'description', 'total_amount', 'status', 'company']
    list_filter = ['status', 'date', 'company']
    search_fields = ['description', 'user__username']
    date_hierarchy = 'date'
    
    # Hacemos readonly la foto para que no la cambien por error desde el admin
    readonly_fields = ['date']

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_number', 'currency', 'balance', 'company']
    list_filter = ['currency', 'company']
    search_fields = ['bank_name', 'account_number']

@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'transaction_type', 'amount', 'bank_account', 'reference', 'company']
    list_filter = ['transaction_type', 'date', 'bank_account']
    search_fields = ['reference', 'description']
    date_hierarchy = 'date'