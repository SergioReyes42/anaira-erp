from django.contrib import admin
from .models import Employee, Loan, Payroll, PayrollDetail, Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'position', 'company', 'is_active')
    list_filter = ('company', 'is_active')
    search_fields = ('first_name', 'last_name')

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('employee', 'amount', 'is_paid', 'company')
    list_filter = ('is_paid',)

class PayrollDetailInline(admin.TabularInline):
    model = PayrollDetail
    extra = 0

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('start_date', 'end_date', 'total_amount', 'is_finalized', 'company')
    inlines = [PayrollDetailInline]