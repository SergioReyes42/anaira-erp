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
    """Historial completo de gastos"""
    expenses = Expense.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'accounting/expense_list.html', {'expenses': expenses})

@login_required
def gasto_manual(request):
    messages.info(request, "El Scanner IA estará disponible pronto.")
    return redirect('upload_expense_photo')

# --- NUEVO: APROBACIÓN DE GASTOS ---
@login_required
def expense_pending_list(request):
    """Lista de gastos que requieren aprobación (Status=PENDING)"""
    expenses = Expense.objects.filter(
        company=request.user.current_company, 
        status='PENDING'
    ).order_by('-date')
    return render(request, 'accounting/expense_pending_list.html', {'expenses': expenses})

@login_required
def approve_expense(request, pk):
    """Aprobar un gasto"""
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    expense.status = 'APPROVED'
    expense.save()
    messages.success(request, f"Gasto #{expense.id} aprobado.")
    return redirect('expense_pending_list')

@login_required
def reject_expense(request, pk):
    """Rechazar un gasto"""
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    expense.status = 'REJECTED'
    expense.save()
    messages.warning(request, f"Gasto #{expense.id} rechazado.")
    return redirect('expense_pending_list')

# --- NUEVO: LIBROS CONTABLES (PLACEHOLDERS) ---
@login_required
def libro_diario(request):
    """Vista preliminar del Libro Diario"""
    # Por ahora mostramos transacciones bancarias como 'asientos' simples
    transactions = BankTransaction.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'accounting/libro_diario.html', {'transactions': transactions})

@login_required
def libro_mayor(request):
    """Vista preliminar del Libro Mayor"""
    # Mostramos resumen de cuentas
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/libro_mayor.html', {'accounts': accounts})

# --- FLOTILLA DE VEHÍCULOS ---
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
            messages.success(request, "Vehículo agregado a la flotilla.")
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