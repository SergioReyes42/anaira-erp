from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, Payroll
from django import forms

# --- FORMULARIOS ---
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'position', 'base_salary', 'hiring_date']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'base_salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'hiring_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

# --- VISTAS ---
@login_required
def employee_list(request):
    employees = Employee.objects.filter(company=request.user.current_company)
    return render(request, 'hr/employee_list.html', {'employees': employees})

@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = request.user.current_company
            emp.save()
            messages.success(request, "Empleado creado correctamente.")
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'hr/employee_form.html', {'form': form})

@login_required
def nomina_create(request):
    """Vista placeholder para Generar Nómina"""
    messages.info(request, "El módulo de generación de nómina está en construcción.")
    return redirect('employee_list')