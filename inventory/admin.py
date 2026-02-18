from django.contrib import admin
from .models import Category, Brand, Product, StockMovement, Stock

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'stock_quantity', 'sale_price', 'company')
    search_fields = ('sku', 'name')

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('date', 'movement_type', 'product', 'quantity', 'warehouse')
    list_filter = ('movement_type', 'warehouse')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity')

admin.site.register(Category)
admin.site.register(Brand)