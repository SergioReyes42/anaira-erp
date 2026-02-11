from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Company, CompanyProfile, UserProfile, Role, UserRoleCompany,
    Branch, Warehouse, Product, Client, Supplier
)

# ========================================================
# 1. CONFIGURACIÓN DE USUARIOS
# ========================================================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario'
    fk_name = 'user'

class UserRoleCompanyInline(admin.TabularInline):
    model = UserRoleCompany
    extra = 1
    verbose_name = 'Asignación de Empresa'
    verbose_name_plural = '🏢 Empresas y Roles Asignados'
    autocomplete_fields = ['company', 'role']

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserRoleCompanyInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_companies')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'groups', 'userrolecompany__company')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    def get_companies(self, obj):
        companies = [str(urc.company) for urc in obj.userrolecompany_set.all()]
        return ", ".join(companies) if companies else "-"
    get_companies.short_description = 'Empresas Acceso'

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, CustomUserAdmin)


# ========================================================
# 2. CONFIGURACIÓN DE MODELOS DEL SISTEMA
# ========================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'active'] # Ahora sí funcionará porque agregamos 'active' al modelo
    search_fields = ['name']

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(UserRoleCompany)
class UserRoleCompanyAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'company']
    list_filter = ['company', 'role']

# 3. LOGÍSTICA
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'location']
    search_fields = ['name', 'code']

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'branch', 'active']
    list_filter = ['branch', 'active']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'price', 'stock']
    search_fields = ['name', 'code']
    list_filter = ['company']

# 4. TERCEROS
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit', 'email']
    search_fields = ['name', 'nit']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'nit', 'contact_name']
    search_fields = ['name', 'nit']