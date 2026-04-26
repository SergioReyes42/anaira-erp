from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, Payroll, EmployeeLoanAdvance
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


class EmployeeLoanAdvanceForm(forms.ModelForm):
    class Meta:
        model = EmployeeLoanAdvance
        fields = ['employee', 'loan_type', 'request_date', 'amount', 'installments', 'status', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-select'}),
            'loan_type': forms.Select(attrs={'class': 'form-select'}),
            'request_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installments': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['employee'].queryset = Employee.objects.filter(company=company)

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
    payrolls = Payroll.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'hr/nomina_create.html', {'payrolls': payrolls})


@login_required
def vacaciones_permisos(request):
    employees = Employee.objects.filter(company=request.user.current_company).order_by('first_name', 'last_name')
    return render(request, 'hr/vacaciones_permisos.html', {'employees': employees})


@login_required
def prestamo_list(request):
    prestamos = EmployeeLoanAdvance.objects.filter(
        company=request.user.current_company
    ).select_related('employee').order_by('-request_date', '-id')
    return render(request, 'hr/prestamo_list.html', {'prestamos': prestamos})


@login_required
def prestamo_create(request):
    if request.method == 'POST':
        form = EmployeeLoanAdvanceForm(request.POST, company=request.user.current_company)
        if form.is_valid():
            prestamo = form.save(commit=False)
            prestamo.company = request.user.current_company
            if not prestamo.balance:
                prestamo.balance = prestamo.amount
            prestamo.save()
            messages.success(request, "Anticipo/Préstamo registrado correctamente.")
            return redirect('prestamo_list')
    else:
        form = EmployeeLoanAdvanceForm(company=request.user.current_company)

    return render(request, 'hr/prestamo_form.html', {'form': form})
