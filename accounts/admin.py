from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.exceptions import NotRegistered # Importamos la excepción
from core.models import UserProfile, UserRoleCompany

# Configuración del Perfil
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil de Usuario'

# Configuración de Roles
class UserRoleCompanyInline(admin.TabularInline):
    model = UserRoleCompany
    extra = 1

# Extendemos el UserAdmin oficial
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserRoleCompanyInline)

# --- BLOQUE DE SEGURIDAD ---
# Intentamos desregistrar el User original.
# Si falla porque no existe, ignoramos el error y seguimos.
try:
    admin.site.unregister(User)
except NotRegistered:
    pass
# ---------------------------

# Registramos nuestro UserAdmin personalizado
admin.site.register(User, UserAdmin)