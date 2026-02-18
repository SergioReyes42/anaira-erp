from django.contrib import admin
from .models import Company, Warehouse

# Registramos solo lo que realmente existe en core/models.py
admin.site.register(Company)
admin.site.register(Warehouse)