from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Employee, EmployeeLoanAdvance, PayrollRun, EmployeePayrollLine
from django import forms
from accounting.models import JournalEntry, JournalEntryLine, Account, BankAccount
from core.reporting import export_to_pdf, export_to_excel

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
    is_modal = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('modal') == '1'

    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = request.user.current_company
            emp.save()
            messages.success(request, "Empleado creado correctamente.")

            if is_modal:
                return render(request, 'hr/partials/employee_form_response.html', {'success': True})

            return redirect('employee_list')
    else:
        form = EmployeeForm()

    if is_modal:
        html = render_to_string('hr/partials/employee_form_fields.html', {'form': form}, request=request)
        return render(request, 'hr/partials/employee_form_response.html', {'success': False, 'form_html': html})

    return render(request, 'hr/employee_form.html', {'form': form})

@login_required
def vacaciones_permisos(request):
    employees = Employee.objects.filter(company=request.user.current_company).order_by('first_name', 'last_name')
    return render(request, 'hr/vacaciones_permisos.html', {'employees': employees})


@login_required
def prestamo_list(request):
    company = request.user.current_company
    employee_id = request.GET.get('employee')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    prestamos = EmployeeLoanAdvance.objects.filter(
        company=company
    ).select_related('employee').order_by('-request_date', '-id')

    if employee_id:
        prestamos = prestamos.filter(employee_id=employee_id)
    if fecha_inicio:
        prestamos = prestamos.filter(request_date__gte=fecha_inicio)
    if fecha_fin:
        prestamos = prestamos.filter(request_date__lte=fecha_fin)

    total_prestado = sum((p.amount for p in prestamos), Decimal('0.00'))
    total_recuperado = sum(((p.amount - p.balance) for p in prestamos), Decimal('0.00'))

    employees = Employee.objects.filter(company=company).order_by('first_name', 'last_name')

    return render(request, 'hr/prestamo_list.html', {
        'prestamos': prestamos,
        'employees': employees,
        'employee_id': employee_id or '',
        'fecha_inicio': fecha_inicio or '',
        'fecha_fin': fecha_fin or '',
        'total_prestado': total_prestado,
        'total_recuperado': total_recuperado,
    })


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

            # Asiento NIIF/NIC al otorgar préstamo/anticipo:
            # Debe: Cuentas por cobrar a empleados
            # Haber: Banco
            account_receivable_code = request.POST.get('account_receivable_code', '').strip()
            account_bank_code = request.POST.get('account_bank_code', '').strip()

            if account_receivable_code and account_bank_code:
                try:
                    cuenta_cxc = Account.objects.get(code=account_receivable_code)
                    cuenta_banco = Account.objects.get(code=account_bank_code)

                    entry = JournalEntry.objects.create(
                        date=prestamo.request_date,
                        concept=f"{prestamo.get_loan_type_display()} a empleado {prestamo.employee}",
                        company=str(request.user.current_company.id),
                    )
                    JournalEntryLine.objects.create(entry=entry, account=cuenta_cxc, debit=prestamo.amount, credit=Decimal('0.00'))
                    JournalEntryLine.objects.create(entry=entry, account=cuenta_banco, debit=Decimal('0.00'), credit=prestamo.amount)
                except Account.DoesNotExist:
                    messages.warning(request, "Préstamo guardado, pero no se generó asiento: códigos contables inválidos.")

            messages.success(request, "Anticipo/Préstamo registrado correctamente.")
            return redirect('prestamo_list')
    else:
        form = EmployeeLoanAdvanceForm(company=request.user.current_company)

    bank_accounts = BankAccount.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'hr/prestamo_form.html', {'form': form, 'bank_accounts': bank_accounts})


@login_required
def nomina_create(request):
    company = request.user.current_company
    employees = Employee.objects.filter(company=company).order_by('first_name', 'last_name')
    payroll_runs = PayrollRun.objects.filter(company=company).order_by('-payment_date', '-id')

    if request.method == 'POST':
        period_label = request.POST.get('period_label', '').strip()
        payment_date = request.POST.get('payment_date') or timezone.now().date()
        description = request.POST.get('description', '').strip()
        account_salary_code = request.POST.get('account_salary_code', '').strip()
        account_receivable_code = request.POST.get('account_receivable_code', '').strip()
        account_bank_code = request.POST.get('account_bank_code', '').strip()

        if not period_label:
            messages.error(request, "Debes indicar el período de nómina.")
            return redirect('nomina_create')

        run = PayrollRun.objects.create(
            company=company,
            period_label=period_label,
            payment_date=payment_date,
            description=description,
        )

        total_gross = Decimal('0.00')
        total_deductions = Decimal('0.00')
        total_net = Decimal('0.00')

        for employee in employees:
            gross = Decimal(str(employee.base_salary or 0))
            loan_active = EmployeeLoanAdvance.objects.filter(
                company=company, employee=employee, status='ACTIVO', balance__gt=0
            ).order_by('request_date', 'id')

            loan_deduction = Decimal('0.00')
            for loan in loan_active:
                if loan.installments and loan.installments > 0:
                    quota = (loan.amount / Decimal(loan.installments)).quantize(Decimal('0.01'))
                else:
                    quota = loan.balance
                apply_amount = min(quota, loan.balance)
                if apply_amount > 0:
                    loan_deduction += apply_amount
                    loan.balance = (loan.balance - apply_amount).quantize(Decimal('0.01'))
                    if loan.balance <= 0:
                        loan.balance = Decimal('0.00')
                        loan.status = 'CANCELADO'
                    loan.save(update_fields=['balance', 'status'])

            other_deductions = Decimal(str(request.POST.get(f'other_deduction_{employee.id}', '0') or '0')).quantize(Decimal('0.01'))
            net = (gross - loan_deduction - other_deductions).quantize(Decimal('0.01'))
            if net < 0:
                net = Decimal('0.00')

            EmployeePayrollLine.objects.create(
                payroll_run=run,
                employee=employee,
                gross_salary=gross,
                loan_deduction=loan_deduction,
                other_deductions=other_deductions,
                net_pay=net,
            )

            total_gross += gross
            total_deductions += (loan_deduction + other_deductions)
            total_net += net

        run.total_gross = total_gross
        run.total_deductions = total_deductions
        run.total_net = total_net
        run.is_posted = True
        run.save(update_fields=['total_gross', 'total_deductions', 'total_net', 'is_posted'])

        # Asiento de planilla:
        # Debe: Sueldos y salarios (total bruto)
        # Haber: CxC empleados (descuento préstamos) + Banco (neto)
        if account_salary_code and account_receivable_code and account_bank_code:
            try:
                cuenta_sueldos = Account.objects.get(code=account_salary_code)
                cuenta_cxc = Account.objects.get(code=account_receivable_code)
                cuenta_banco = Account.objects.get(code=account_bank_code)

                entry = JournalEntry.objects.create(
                    date=run.payment_date,
                    concept=f"Nómina {run.period_label}",
                    company=str(company.id),
                )
                JournalEntryLine.objects.create(entry=entry, account=cuenta_sueldos, debit=run.total_gross, credit=Decimal('0.00'))
                JournalEntryLine.objects.create(entry=entry, account=cuenta_cxc, debit=Decimal('0.00'), credit=run.total_deductions)
                JournalEntryLine.objects.create(entry=entry, account=cuenta_banco, debit=Decimal('0.00'), credit=run.total_net)
            except Account.DoesNotExist:
                messages.warning(request, "Nómina generada, pero sin asiento: revisa códigos de cuentas contables.")

        messages.success(request, "Nómina generada correctamente con descuentos aplicados.")
        return redirect('nomina_create')

    return render(request, 'hr/nomina_create.html', {
        'employees': employees,
        'payroll_runs': payroll_runs,
    })


@login_required
def payroll_receipt_pdf(request, line_id):
    line = get_object_or_404(
        EmployeePayrollLine.objects.select_related('employee', 'payroll_run'),
        id=line_id,
        payroll_run__company=request.user.current_company
    )

    headers = ["Concepto", "Monto (Q)"]
    rows = [
        ["Salario bruto", f"{line.gross_salary:.2f}"],
        ["Descuento préstamo/anticipo", f"{line.loan_deduction:.2f}"],
        ["Otros descuentos", f"{line.other_deductions:.2f}"],
        ["Neto a pagar", f"{line.net_pay:.2f}"],
    ]

    title = f"Recibo de Planilla - {line.employee} - {line.payroll_run.period_label}"
    filename = f"recibo_planilla_{line.employee.id}_{line.payroll_run.id}"
    return export_to_pdf(filename=filename, title=title, headers=headers, rows=rows)


@login_required
def prestamos_report_excel(request):
    company = request.user.current_company
    employee_id = request.GET.get('employee')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    prestamos = EmployeeLoanAdvance.objects.filter(company=company).select_related('employee').order_by('-request_date', '-id')
    if employee_id:
        prestamos = prestamos.filter(employee_id=employee_id)
    if fecha_inicio:
        prestamos = prestamos.filter(request_date__gte=fecha_inicio)
    if fecha_fin:
        prestamos = prestamos.filter(request_date__lte=fecha_fin)

    headers = ["Fecha", "Empleado", "Tipo", "Monto", "Saldo", "Cuotas", "Estado"]
    rows = [
        [
            p.request_date.strftime('%Y-%m-%d'),
            str(p.employee),
            p.get_loan_type_display(),
            float(p.amount),
            float(p.balance),
            p.installments,
            p.get_status_display(),
        ]
        for p in prestamos
    ]
    return export_to_excel("reporte_prestamos", headers, rows)


@login_required
def prestamos_report_pdf(request):
    company = request.user.current_company
    employee_id = request.GET.get('employee')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    prestamos = EmployeeLoanAdvance.objects.filter(company=company).select_related('employee').order_by('-request_date', '-id')
    if employee_id:
        prestamos = prestamos.filter(employee_id=employee_id)
    if fecha_inicio:
        prestamos = prestamos.filter(request_date__gte=fecha_inicio)
    if fecha_fin:
        prestamos = prestamos.filter(request_date__lte=fecha_fin)

    headers = ["Fecha", "Empleado", "Tipo", "Monto", "Saldo", "Estado"]
    rows = [
        [
            p.request_date.strftime('%Y-%m-%d'),
            str(p.employee),
            p.get_loan_type_display(),
            f"{p.amount:.2f}",
            f"{p.balance:.2f}",
            p.get_status_display(),
        ]
        for p in prestamos
    ]
    return export_to_pdf("reporte_prestamos", "Reporte de Préstamos y Anticipos", headers, rows)
