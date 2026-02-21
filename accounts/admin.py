from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 1. Columnas que verás en la tabla principal al entrar a "Usuarios"
    list_display = ('username', 'email', 'get_full_name', 'role', 'current_company', 'is_active', 'is_staff')
    
    # 2. Filtros laterales rápidos
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'current_company', 'groups')
    
    # 3. Barra de búsqueda superior
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    # 4. Ordenamiento
    ordering = ('-date_joined',)

    # 5. Interfaz de edición súper organizada por bloques lógicos
    fieldsets = (
        ('Credenciales de Acceso', {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'avatar')
        }),
        ('Seguridad y 2FA', {
            'fields': ('totp_secret',)
        }),
        ('Configuración Anaira ERP (Accesos y Roles)', {
            'fields': ('role', 'current_company', 'allowed_companies'),
            'description': 'Define el nivel de acceso en el ERP y a qué empresas/sucursales puede entrar este empleado.'
        }),
        ('Permisos Avanzados y Grupos (Roles Específicos)', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',), # Lo ocultamos por defecto para no saturar la pantalla
            'description': 'Asigna los grupos (Ej: Piloto, Contadora). ATENCIÓN: is_staff permite entrar a este panel de administración.'
        }),
        ('Fechas de Actividad', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    # 6. Agrega un widget doble muy elegante para seleccionar múltiples empresas y grupos
    filter_horizontal = ('groups', 'user_permissions', 'allowed_companies')

    # 7. Formulario simplificado para cuando le das a "Añadir Usuario" por primera vez
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Configuración Anaira ERP', {
            'fields': ('role', 'allowed_companies'),
        }),
    )