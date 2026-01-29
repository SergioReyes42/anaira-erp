
# accounts/admin.py
from django.contrib import admin
from django.conf import settings
from .models import User, Company
# Branding del admin usando variables del settings
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Administración")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Panel")

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # Esto activa las cajitas de izquierda a derecha ⬅️➡️
    # 'groups' y 'user_permissions' son los campos por defecto de Django
    # Si su campo de empresas se llama 'companies' o 'empresas', agréguelo a esta lista.
    filter_horizontal = ('groups', 'user_permissions',) 
    
    # Opcional: Para buscar usuarios por email o nombre
    search_fields = ('email', 'first_name', 'last_name')
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')

# --- PARTE 1: Para ver Usuarios dentro de la Empresa ---
class UserInline(admin.TabularInline):
    # Esto busca la relación "Muchos a Muchos" definida en el Usuario
    # IMPORTANTE: Si su campo en User se llama 'empresas', ponga: User.empresas.through
    model = User.companies.through 
    extra = 1
    verbose_name = "Usuario con acceso"
    verbose_name_plural = "Usuarios que pueden acceder a esta empresa"

# --- PARTE 2: El Admin de la Empresa ---
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    # Aquí inyectamos la tabla de usuarios
    inlines = [UserInline]
    
    # Ajuste 'name' si su empresa tiene 'razon_social' o 'nombre'
    list_display = ('name', 'is_active') 
    search_fields = ('name',)

# --- PARTE 3: El Admin del Usuario ---
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # Las cajitas de izquierda a derecha
    filter_horizontal = ('groups', 'user_permissions', 'companies') 
    
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name')