
# accounts/admin.py
from django.contrib import admin
from django.conf import settings
from .models import User

# Branding del admin usando variables del settings
admin.site.site_header = getattr(settings, "ADMIN_SITE_HEADER", "Administración")
admin.site.site_title = getattr(settings, "ADMIN_SITE_TITLE", "Admin")
admin.site.index_title = getattr(settings, "ADMIN_INDEX_TITLE", "Panel")

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "role", "is_active", "is_staff", "is_superuser")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)
# FIN accounts/admin.py
