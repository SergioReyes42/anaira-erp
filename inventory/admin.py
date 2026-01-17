from django.contrib import admin
from .models import Category, Brand, Product, Stock, InventoryMovement, MovementDetail

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_active')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'product_type', 'sale_price', 'company')
    list_filter = ('company', 'product_type', 'is_active')
    search_fields = ('sku', 'name')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'location_in_warehouse')
    list_filter = ('warehouse',)

class MovementDetailInline(admin.TabularInline):
    model = MovementDetail
    extra = 1

@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ('date', 'movement_type', 'reference', 'company', 'user')
    list_filter = ('movement_type', 'date')
    inlines = [MovementDetailInline]