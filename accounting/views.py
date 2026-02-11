from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import BankAccount, BankTransaction
from .forms import ExpensePhotoForm, BankAccountForm, BankTransactionForm

# --- GASTOS (LO QUE YA EXISTÍA) ---
@login_required
def upload_expense_photo(request):
    if request.method == 'POST':
        form = ExpensePhotoForm(request.POST, request.FILES)
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
    return render(request, 'accounting/upload_photo.html', {'form': form})

@login_required
def gasto_manual(request):
    messages.info(request, "El Scanner IA estará disponible pronto.")
    return redirect('upload_expense_photo')

# --- NUEVO: BANCOS ---
@login_required
def bank_list(request):
    """Panel de Bancos"""
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    # Calculamos el total global para el dashboard
    total_balance = sum(acc.balance for acc in accounts)
    
    # Obtenemos últimas transacciones
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
    """Crear nueva cuenta bancaria"""
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
    """Registrar Depósito o Retiro"""
    # Obtenemos el tipo de la URL (?type=IN o ?type=OUT)
    tx_type = request.GET.get('type', 'IN') 
    
    if request.method == 'POST':
        form = BankTransactionForm(request.POST)
        # Hack para filtrar cuentas por empresa
        form.fields['bank_account'].queryset = BankAccount.objects.filter(company=request.user.current_company)
        
        if form.is_valid():
            tx = form.save(commit=False)
            tx.company = request.user.current_company
            tx.transaction_type = tx_type # Forzamos el tipo según la URL
            tx.save()
            messages.success(request, "Transacción registrada exitosamente.")
            return redirect('bank_list')
    else:
        form = BankTransactionForm()
        form.fields['bank_account'].queryset = BankAccount.objects.filter(company=request.user.current_company)

    context = {
        'form': form,
        'tx_type': tx_type,
        'title': 'Registrar Depósito' if tx_type == 'IN' else 'Registrar Retiro'
    }
    return render(request, 'accounting/transaction_form.html', context)