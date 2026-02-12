from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import BankAccount, BankTransaction, Vehicle, Expense
from .forms import ExpensePhotoForm, BankAccountForm, BankTransactionForm, VehicleForm

# --- GASTOS Y REPORTES ---
@login_required
def upload_expense_photo(request):
    if request.method == 'POST':
        form = ExpensePhotoForm(request.POST, request.FILES)
        form.fields['vehicle'].queryset = Vehicle.objects.filter(company=request.user.current_company)
        
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            if hasattr(request.user, 'current_company'):
                expense.company = request.user.current_company
            expense.save()
            messages.success(request, "¡Gasto subido correctamente!")
            return redirect('home')
    else:
        form = ExpensePhotoForm()
        form.fields['vehicle'].queryset = Vehicle.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/upload_photo.html', {'form': form})

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'accounting/expense_list.html', {'expenses': expenses})

@login_required
def gasto_manual(request):
    messages.info(request, "El Scanner IA estará disponible pronto.")
    return redirect('upload_expense_photo')

# --- APROBACIÓN DE GASTOS ---
@login_required
def expense_pending_list(request):
    expenses = Expense.objects.filter(
        company=request.user.current_company, 
        status='PENDING'
    ).order_by('-date')
    return render(request, 'accounting/expense_pending_list.html', {'expenses': expenses})

@login_required
def approve_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    expense.status = 'APPROVED'
    expense.save()
    messages.success(request, f"Gasto #{expense.id} aprobado.")
    return redirect('expense_pending_list')

@login_required
def reject_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    expense.status = 'REJECTED'
    expense.save()
    messages.warning(request, f"Gasto #{expense.id} rechazado.")
    return redirect('expense_pending_list')

# --- LIBROS Y ESTADOS FINANCIEROS (PLACEHOLDERS) ---
@login_required
def libro_diario(request):
    transactions = BankTransaction.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'accounting/libro_diario.html', {'transactions': transactions})

@login_required
def libro_mayor(request):
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/libro_mayor.html', {'accounts': accounts})

@login_required
def balance_saldos(request):
    """Vista preliminar Balance de Saldos"""
    # Por ahora mostramos resumen de cuentas
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/balance_saldos.html', {'accounts': accounts})

@login_required
def estado_resultados(request):
    """Vista preliminar Estado de Resultados"""
    # Calculamos Ingresos (Depósitos) vs Gastos (Retiros + Gastos Reportados)
    expenses = Expense.objects.filter(company=request.user.current_company, status='APPROVED')
    return render(request, 'accounting/estado_resultados.html', {'expenses': expenses})

@login_required
def balance_general(request):
    """Vista preliminar Balance General"""
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/balance_general.html', {'accounts': accounts})

# --- FLOTILLA ---
@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/vehicle_list.html', {'vehicles': vehicles})

@login_required
def vehicle_create(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.company = request.user.current_company
            vehicle.save()
            messages.success(request, "Vehículo agregado.")
            return redirect('vehicle_list')
    else:
        form = VehicleForm()
    return render(request, 'accounting/vehicle_form.html', {'form': form})

# --- BANCOS ---
@login_required
def bank_list(request):
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    total_balance = sum(acc.balance for acc in accounts)
    recent_transactions = BankTransaction.objects.filter(
        company=request.user.current_company
    ).order_by('-date', '-id')[:10]

    return render(request, 'accounting/bank_list.html', {
        'accounts': accounts, 
        'total_balance': total_balance,
        'recent_transactions': recent_transactions
    })

@login_required
def bank_create(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank = form.save(commit=False)
            bank.company = request.user.current_company
            bank.save()
            messages.success(request, "Cuenta bancaria creada.")
            return redirect('bank_list')
    else:
        form = BankAccountForm()
    return render(request, 'accounting/bank_form.html', {'form': form})

@login_required
def bank_transaction_create(request):
    tx_type = request.GET.get('type', 'IN') 
    if request.method == 'POST':
        form = BankTransactionForm(request.POST)
        form.fields['bank_account'].queryset = BankAccount.objects.filter(company=request.user.current_company)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.company = request.user.current_company
            tx.transaction_type = tx_type
            tx.save()
            messages.success(request, "Transacción registrada.")
            return redirect('bank_list')
    else:
        form = BankTransactionForm()
        form.fields['bank_account'].queryset = BankAccount.objects.filter(company=request.user.current_company)

    context = {'form': form, 'tx_type': tx_type, 'title': 'Registrar Depósito' if tx_type == 'IN' else 'Registrar Retiro'}
    return render(request, 'accounting/transaction_form.html', context)

@login_required
def chart_of_accounts(request):
    """
    Dashboard del Plan de Cuentas (NIC/NIIF).
    Aquí se gestionará la jerarquía de cuentas contables.
    """
    # En el futuro, esto vendrá de la base de datos (Modelo Account)
    # Por ahora simulamos la estructura NIIF para la visualización
    simulated_accounts = [
        {'code': '1', 'name': 'ACTIVO', 'level': 1, 'type': 'Rurbro', 'niif_tag': 'Estado de Situación Financiera'},
        {'code': '1.1', 'name': 'ACTIVO CORRIENTE', 'level': 2, 'type': 'Grupo', 'niif_tag': 'NIC 1'},
        {'code': '1.1.01', 'name': 'Efectivo y Equivalentes', 'level': 3, 'type': 'Cuenta Mayor', 'niif_tag': 'NIC 7'},
        {'code': '1.1.01.001', 'name': 'Caja General', 'level': 4, 'type': 'Sub-cuenta', 'niif_tag': ''},
        {'code': '1.1.01.002', 'name': 'Banco Industrial Monetaria', 'level': 4, 'type': 'Sub-cuenta', 'niif_tag': ''},
        {'code': '1.2', 'name': 'ACTIVO NO CORRIENTE', 'level': 2, 'type': 'Grupo', 'niif_tag': 'NIC 16'},
        {'code': '2', 'name': 'PASIVO', 'level': 1, 'type': 'Rubro', 'niif_tag': 'Estado de Situación Financiera'},
        {'code': '2.1', 'name': 'PASIVO CORRIENTE', 'level': 2, 'type': 'Grupo', 'niif_tag': 'NIC 1'},
        {'code': '2.1.01', 'name': 'Cuentas por Pagar Comerciales', 'level': 3, 'type': 'Cuenta Mayor', 'niif_tag': 'NIIF 9'},
    ]
    
    return render(request, 'accounting/chart_of_accounts.html', {'accounts': simulated_accounts})