from django.contrib import admin
from .models import Employee, Payroll

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'position', 'base_salary', 'hiring_date', 'company']
    search_fields = ['first_name', 'last_name', 'position']
    list_filter = ['company', 'hiring_date']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['date', 'total', 'is_closed', 'company']
    list_filter = ['date', 'is_closed', 'company']
    date_hierarchy = 'date'