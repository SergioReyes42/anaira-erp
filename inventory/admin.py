from django.contrib import admin
from .models import Category, Brand, Product, Stock, StockMovement, MovementDetail

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'company', 'stock_quantity')
    list_filter = ('company', 'category')
    search_fields = ('name', 'sku')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity')

class MovementDetailInline(admin.TabularInline):
    model = MovementDetail
    extra = 1

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('date', 'product', 'movement_type', 'quantity', 'user')
    list_filter = ('movement_type', 'date')
    inlines = [MovementDetailInline]