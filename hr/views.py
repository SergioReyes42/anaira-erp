from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from core.models import Company
# Importamos SOLO los modelos que existen en hr/models.py
from .models import Employee, Department, Loan, Payroll, PayrollDetail

# ==========================================
# 1. GESTIÓN DE EMPLEADOS
# ==========================================

@login_required
def employee_list(request):
    """Lista de empleados activos"""
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    company = Company.objects.using('default').get(id=company_id)
    employees = Employee.objects.filter(company=company, is_active=True).order_by('last_name')
    
    return render(request, 'hr/employee_list.html', {
        'company': company,
        'employees': employees
    })

@login_required
def employee_create(request):
    """Crear nuevo empleado"""
    company_id = request.session.get('company_id')
    company = Company.objects.using('default').get(id=company_id)
    departments = Department.objects.filter(company=company)

    if request.method == 'POST':
        try:
            dept_id = request.POST.get('department')
            department_obj = Department.objects.get(id=dept_id) if dept_id else None

            Employee.objects.create(
                company=company,
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                dpi=request.POST.get('dpi'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email'),
                address=request.POST.get('address'),
                department=department_obj,
                position=request.POST.get('position'),
                date_joined=request.POST.get('date_joined') or timezone.now().date(),
                base_salary=request.POST.get('base_salary') or 0,
                incentive_bonus=request.POST.get('incentive_bonus') or 250.00,
                is_active=True
            )
            messages.success(request, "Empleado creado exitosamente.")
            return redirect('employee_list')
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'hr/employee_form.html', {
        'company': company, 
        'departments': departments
    })

# ==========================================
# 2. PRÉSTAMOS (LOANS) - RENOMBRADO DE prestamo_list A loan_list
# ==========================================

# --- VISTA PARA PRÉSTAMOS (Conecta con prestamo_list.html) ---
@login_required
def loan_list(request):
    # 1. Validación de seguridad (Esto arregla el error de "te redirigió demasiadas veces")
    company_id = request.session.get('company_id')
    if not company_id:
        return redirect('select_company')

    # 2. Filtrar datos
    prestamos = Loan.objects.filter(employee__company_id=company_id)

    # 3. ¡AQUÍ ESTÁ LA CLAVE! Usamos TU nombre de archivo:
    return render(request, 'hr/prestamo_list.html', {'prestamos': prestamos})

# --- VISTA PARA NÓMINA (Conecta con nomina_create.html) ---
@login_required
def payroll_create(request): # O payroll_list, como lo tengas en urls.py
    # 1. Validación de seguridad
    company_id = request.session.get('company_id')
    if not company_id:
        return redirect('select_company')

    # 2. Filtrar datos (Si necesitas listar nóminas anteriores)
    nominas = Payroll.objects.filter(employee__company_id=company_id)

    # 3. ¡AQUÍ ESTÁ LA CLAVE! Usamos TU nombre de archivo:
    return render(request, 'hr/nomina_create.html', {'nominas': nominas})
@login_required
def loan_create(request):
    """Crear Préstamo"""
    company_id = request.session.get('company_id')
    company = Company.objects.using('default').get(id=company_id)
    employees = Employee.objects.filter(company=company, is_active=True)

    if request.method == 'POST':
        emp_id = request.POST.get('employee')
        amount = Decimal(request.POST.get('amount', 0))
        description = request.POST.get('description')

        Loan.objects.create(
            company=company,
            employee_id=emp_id,
            amount=amount,
            description=description,
            is_paid=False
        )
        messages.success(request, "Préstamo registrado.")
        return redirect('loan_list')

    return render(request, 'hr/loan_form.html', {'company': company, 'employees': employees})


# ==========================================
# 3. NÓMINA (PAYROLL)
# ==========================================

@login_required
def generate_payroll(request):
    """Generar Nómina (Simulada por ahora para evitar errores complejos)"""
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    company = Company.objects.using('default').get(id=company_id)

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # 1. Crear Cabecera
        payroll = Payroll.objects.create(
            company=company,
            start_date=start_date or timezone.now().date(),
            end_date=end_date or timezone.now().date(),
            total_amount=0
        )

        # 2. Calcular detalle por empleado (Simplificado)
        employees = Employee.objects.filter(company=company, is_active=True)
        total_nomina = 0

        for emp in employees:
            # Cálculo simple: Salario Base + Boni - IGSS (4.83%)
            base = emp.base_salary
            boni = emp.incentive_bonus
            igss = base * Decimal(0.0483)
            liquido = base + boni - igss

            PayrollDetail.objects.create(
                payroll=payroll,
                employee=emp,
                base_salary=base,
                bonus=boni,
                deductions=igss,
                net_salary=liquido
            )
            total_nomina += liquido

        payroll.total_amount = total_nomina
        payroll.save()

        messages.success(request, "Nómina generada exitosamente.")
        # Redirigimos a la lista o al detalle, según prefieras
        return redirect('detalle_nomina', nomina_id=payroll.id)

    # --- AQUÍ ESTABA EL ERROR ---
    # Cambiamos 'hr/payroll_form.html' por TU archivo real:
    return render(request, 'hr/nomina_create.html', {'company': company})

@login_required
def generar_nomina(request):
    """Redirección por compatibilidad"""
    return redirect('generate_payroll')

@login_required
def detalle_nomina(request, nomina_id):
    """Ver detalle de una nómina"""
    company_id = request.session.get('company_id')
    payroll = get_object_or_404(Payroll, id=nomina_id, company_id=company_id)
    return render(request, 'hr/payroll_detail.html', {'payroll': payroll})


# ==========================================
# 4. MÓDULOS EN ESPERA (ISR, Impresiones)
# ==========================================
# Mantenemos estas funciones vacías para que no den error las URLs
# que aún apuntan a ellas.

@login_required
def gestion_isr(request):
    messages.info(request, "Módulo ISR en mantenimiento.")
    return redirect('employee_list')

@login_required
def imprimir_proyeccion_isr(request):
    return redirect('employee_list')

@login_required
def boletas_print(request, nomina_id):
    messages.info(request, "Impresión de boletas en mantenimiento.")
    return redirect('detalle_nomina', nomina_id=nomina_id)

@login_required
def libro_salarios_print(request, nomina_id):
    return redirect('detalle_nomina', nomina_id=nomina_id)
