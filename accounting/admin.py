from django.contrib import admin
# AQUÍ ESTABA EL ERROR: Cambiamos JournalLine por JournalItem
from .models import Account, JournalEntry, JournalItem 

class JournalItemInline(admin.TabularInline):
    model = JournalItem # AQUÍ TAMBIÉN CORREGIDO
    extra = 2 

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'company')
    list_filter = ('company', 'account_type')
    search_fields = ('code', 'name')

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'total_debit', 'total_credit', 'is_balanced', 'company')
    list_filter = ('company', 'date')
    inlines = [JournalItemInline]