from django.contrib import admin
from .models import CustomerAccount, Invoice, Payment

@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ('customer', 'company', 'balance')
    search_fields = ('customer__name',)

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'customer', 'date', 'total', 'pending_amount', 'status')
    list_filter = ('status', 'company')
    search_fields = ('number', 'customer__name')
    inlines = [PaymentInline]

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'date', 'amount', 'method')