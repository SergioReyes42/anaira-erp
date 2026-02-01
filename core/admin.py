from django.contrib import admin
from django.utils.html import mark_safe # Permite mostrar HTML (la imagen) en el admin
from .models import Company, Employee, UserRoleCompany, Income, Gasto, Fleet, Client, Sale

# CONFIGURACIÓN AVANZADA PARA EMPRESAS
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'nit', 'ver_logo_actual', 'address') # Columnas que se verán
    search_fields = ('name', 'nit') # Barra de búsqueda
    
    # Función para mostrar la miniatura en lugar de solo el nombre del archivo
    def ver_logo_actual(self, obj):
        if obj.logo:
            # Muestra una imagen de 50px de alto
            return mark_safe(f'<img src="{obj.logo.url}" style="height: 50px; border-radius: 5px;" />')
        return "Sin Logo"
    
    ver_logo_actual.short_description = 'Logo' # Título de la columna

# REGISTRO DE MODELOS
admin.site.register(Company, CompanyAdmin)
admin.site.register(UserRoleCompany)
# admin.site.register(Employee) # Descomentar si quiere administrar empleados desde aquí también

@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    list_display = ('plate', 'brand', 'model', 'year', 'company') # Lo que se ve en la lista
    search_fields = ('plate', 'brand', 'model') # Barra de búsqueda
    list_filter = ('company', 'brand') # Filtros laterales

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # Quitamos 'company' de list_filter porque dio error
    list_display = ('name', 'nit', 'contact_name', 'phone', 'email')
    search_fields = ('name', 'nit', 'contact_name')
    # list_filter = ('company',)  <--- ESTA LÍNEA LA ELIMINAMOS O COMENTAMOS

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date', 'total', 'payment_method')
    list_filter = ('date', 'payment_method')

# Si no tenía CompanyProfile registrado, agréguelo también:
# admin.site.register(CompanyProfile)