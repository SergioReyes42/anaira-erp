from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User  # Importamos TU usuario personalizado
from core.models import UserRoleCompany, UserProfile

# 1. INLINE DE EMPRESAS (La Joya de la Corona 👑)
# Esto permite asignar empresas y roles directamente en la ficha del usuario
class UserRoleCompanyInline(admin.TabularInline):
    model = UserRoleCompany
    extra = 0  # No mostrar filas vacías extra para limpiar la vista
    verbose_name = "Empresa Asignada"
    verbose_name_plural = "🏢 Acceso a Empresas"
    autocomplete_fields = ['company', 'role'] # Útil si tienes muchas empresas
    classes = ['collapse'] # Permite colapsar la sección si es muy larga

# 2. INLINE DE PERFIL (Datos extra: Avatar, Teléfono)
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = '👤 Perfil Detallado'
    fk_name = 'user'

# 3. EL ADMINISTRADOR PROFESIONAL 👔
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Qué columnas ver en la lista principal
    list_display = ('username', 'email', 'get_full_name', 'is_active', 'get_companies_display', 'is_staff')
    
    # Por qué campos se puede buscar
    search_fields = ('username', 'first_name', 'last_name', 'email', 'userrolecompany__company__name')
    
    # Filtros laterales potentes
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'userrolecompany__company')
    
    # Los Inlines que definimos arriba
    inlines = [UserProfileInline, UserRoleCompanyInline]

    # ORGANIZACIÓN VISUAL (Fieldsets)
    # Esto agrupa los campos para que no sea una lista interminable
    fieldsets = (
        ('🔑 Credenciales de Acceso', {
            'fields': ('username', 'password')
        }),
        ('👤 Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'avatar') # Agregamos avatar si está en tu modelo User
        }),
        ('🏢 Empresa Actual (Contexto)', {
            'fields': ('current_company',),
            'description': 'Empresa en la que el usuario está operando actualmente.'
        }),
        ('🛡️ Permisos y Seguridad', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',), # Oculto por defecto para no estorbar
        }),
        ('📅 Fechas Importantes', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    # Función para mostrar las empresas bonitas en la lista
    def get_companies_display(self, obj):
        companies = [str(urc.company) for urc in obj.userrolecompany_set.all()]
        if not companies:
            return "-"
        return ", ".join(companies)
    get_companies_display.short_description = 'Empresas Asignadas'

    # Corrección para el manejo de avatares en formularios
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)