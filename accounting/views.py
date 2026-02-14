from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import random 

# Importación de Modelos (Asegúrate que existen en accounting/models.py)
from .models import BankAccount, BankTransaction, Vehicle, Expense
# Importación de Formularios (Los que acabamos de crear)
from .forms import ExpensePhotoForm, BankAccountForm, BankTransactionForm, VehicleForm

# --- GASTOS Y SMART SCANNER ---
@login_required
def upload_expense_photo(request):
    # Si el piloto envía el formulario (POST)
    if request.method == 'POST':
        foto = request.FILES.get('invoice_file')
        vehicle_id = request.POST.get('vehicle_id')
        
        if foto:
            # Creamos el gasto en modo "Borrador"
            gasto = Expense.objects.create(
                user=request.user,
                invoice_file=foto,
                date=timezone.now().date(),      # Fecha de hoy
                provider="Pendiente de Revisión",# Texto temporal
                description="Gasto reportado por Piloto",
                total_amount=0,                  # Monto 0 (Contador lo llenará)
                status='PENDING',                # <--- ESTADO CLAVE
                is_fuel=False                    # Por defecto false
            )
            
            # Si seleccionó placa, la guardamos
            if vehicle_id:
                gasto.vehicle_id = vehicle_id
                gasto.save()
            
            messages.success(request, "✅ ¡Foto enviada! Contabilidad revisará tu gasto.")
            return redirect('home') # Lo regresa al inicio
        else:
            messages.error(request, "⚠️ Debes tomar una foto o subir un archivo.")

    # Si entra a la página (GET), le mostramos los vehículos
    vehiculos = Vehicle.objects.filter(status='ACTIVO')
    return render(request, 'accounting/pilot_upload.html', {'vehiculos': vehiculos})

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'accounting/expense_list.html', {'expenses': expenses})

@login_required
def gasto_manual(request):
    # Por ahora redirigimos al scanner o podrías crear una vista específica
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

# --- LIBROS Y ESTADOS FINANCIEROS ---
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
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/balance_saldos.html', {'accounts': accounts})

@login_required
def estado_resultados(request):
    expenses = Expense.objects.filter(company=request.user.current_company, status='APPROVED')
    return render(request, 'accounting/estado_resultados.html', {'expenses': expenses})

@login_required
def balance_general(request):
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
        # Filtramos cuentas solo de la empresa actual
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
    """Dashboard del Plan de Cuentas (NIC/NIIF)"""
    simulated_accounts = [
        {'code': '1', 'name': 'ACTIVO', 'level': 1, 'type': 'Rurbro', 'niif_tag': 'Estado de Situación Financiera'},
        {'code': '1.1', 'name': 'ACTIVO CORRIENTE', 'level': 2, 'type': 'Grupo', 'niif_tag': 'NIC 1'},
        {'code': '1.1.01', 'name': 'Efectivo y Equivalentes', 'level': 3, 'type': 'Cuenta Mayor', 'niif_tag': 'NIC 7'},
    ]
    
    return render(request, 'accounting/chart_of_accounts.html', {'accounts': simulated_accounts})