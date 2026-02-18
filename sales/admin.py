from django.contrib import admin
from .models import Client, Quotation, QuotationItem

# Configuración para ver los productos DENTRO de la cotización
class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0 
    readonly_fields = ('total_line',)

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total', 'status', 'seller')
    list_filter = ('status', 'date', 'seller')
    inlines = [QuotationItemInline]

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'phone', 'email')
    search_fields = ('name', 'nit')