from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 1. Columnas de la tabla principal
    list_display = ('username', 'email', 'get_full_name', 'role', 'current_company', 'is_active', 'is_superuser')
    
    # 2. Filtros laterales
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'current_company', 'groups')
    
    # 3. Barra de búsqueda
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # 4. Ordenamiento
    ordering = ('-date_joined',)

    # 5. Interfaz de EDICIÓN de usuario
    fieldsets = (
        ('Credenciales de Acceso', {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'avatar')
        }),
        ('Estado y Nivel de Sistema', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'description': 'ATENCIÓN: Si desmarcas "Activo", el usuario no podrá entrar al ERP. "Superusuario" da control total de la base de datos.'
        }),
        ('Configuración Anaira ERP (Accesos y Roles)', {
            'fields': ('role', 'groups', 'current_company', 'allowed_companies'),
            'description': 'Asigna el rol (Ej: Contadora), la empresa actual y las empresas permitidas.'
        }),
        ('Permisos Especiales (Avanzado)', {
            'fields': ('user_permissions',),
            'classes': ('collapse',), # Esto lo dejamos colapsado porque rara vez se usa permiso por permiso
        }),
        ('Seguridad y Actividad', {
            'fields': ('totp_secret', 'last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    filter_horizontal = ('groups', 'user_permissions', 'allowed_companies')

    # 6. Interfaz de CREACIÓN de nuevo usuario (Al darle "Añadir usuario")
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Estado y Nivel de Sistema', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
        ('Configuración Anaira ERP', {
            'fields': ('role', 'groups', 'allowed_companies'),
        }),
    )