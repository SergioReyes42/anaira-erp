import decimal  # <--- ¡ESTA ES LA QUE FALTA! (Agrégala al principio)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Expense, JournalEntry, JournalItem, BankAccount
import random 
from .utils import analyze_invoice_image  # <--- Importar el cerebro que creamos

# Importación de Modelos (Asegúrate que existen en accounting/models.py)
from .models import BankAccount, BankTransaction, Vehicle, Expense
# Importación de Formularios (Los que acabamos de crear)
from .forms import ExpensePhotoForm, BankAccountForm, BankTransactionForm, VehicleForm

# --- GASTOS Y SMART SCANNER ---
@login_required
def upload_expense_photo(request):
    if request.method == 'POST':
        image = request.FILES.get('documento')
        smart_input = request.POST.get('smart_input', '') # Texto manual o del OCR
        
        # 1. ANALISIS IA (Extraer datos y categorizar)
        ai_data = analyze_invoice_image(image, smart_input)
        
        # 2. MATEMÁTICA FINANCIERA (Cálculo de Impuestos)
        total = ai_data['total']
        idp = 0.00
        base = 0.00
        iva = 0.00

        if ai_data['is_fuel']:
            # Lógica de IDP (Impuesto Distribución Petróleo - Guatemala)
            # Precios aprox para sacar galones: Super Q32, Diesel Q28
            precio_galon = 28.00 if ai_data['fuel_type'] == 'diesel' else 32.00
            
            # Impuesto por galón: Super Q4.70, Regular Q4.60, Diesel Q1.30
            tasa_idp = 4.70
            if ai_data['fuel_type'] == 'regular': tasa_idp = 4.60
            elif ai_data['fuel_type'] == 'diesel': tasa_idp = 1.30

            galones = total / precio_galon
            idp = galones * tasa_idp
            
            # Base = (Total - IDP) / 1.12
            base = (total - idp) / 1.12
        else:
            # Gasto Normal: Base = Total / 1.12
            base = total / 1.12
            
        # IVA siempre es 12% sobre la base
        iva = base * 0.12

        # 3. GUARDAR RESULTADO (Pendiente de Aprobar)
        Expense.objects.create(
            user=request.user,
            company=request.user.current_company,
            receipt_image=image,
            
            # Datos extraídos
            provider_name=ai_data['provider_name'],
            provider_nit=ai_data['provider_nit'],
            invoice_series=ai_data['invoice_series'],
            invoice_number=ai_data['invoice_number'],
            description=ai_data['description'],
            suggested_account=ai_data['account_type'], # <--- AQUÍ LA IA DICE LA CUENTA
            
            # Desglose Financiero guardado
            total_amount=total,
            tax_base=base,
            tax_iva=iva,
            tax_idp=idp,
            
            status='PENDING'
        )
        
        messages.success(request, f"✅ Factura analizada: Clasificada como '{ai_data['account_type']}'")
        return redirect('expense_pending_list')

    return render(request, 'accounting/smart_hub.html')


@login_required
def expense_list(request):
    expenses = Expense.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'accounting/expense_list.html', {'expenses': expenses})

@login_required
def gasto_manual(request):
    # Por ahora redirigimos al scanner o podrías crear una vista específica
    return redirect('pilot_upload.html')

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
    # 1. Obtener el gasto
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if expense.status == 'APPROVED':
        messages.warning(request, "Este gasto ya fue contabilizado.")
        return redirect('expense_pending_list')

    try:
        # --- CÁLCULOS FINANCIEROS INTELIGENTES ---
        monto_total = float(expense.total_amount)
        descripcion = expense.description.lower()
        
        # Variables iniciales
        idp = 0.00
        base = 0.00
        iva = 0.00
        cuenta_gasto = "Gastos Generales" # Cuenta por defecto

        # DETECCIÓN DE GASOLINA (Lógica Guatemala)
        if 'gasolina' in descripcion or 'combustible' in descripcion or 'shell' in descripcion or 'texaco' in descripcion or 'puma' in descripcion:
            cuenta_gasto = "Combustibles y Lubricantes"
            
            # Estimación de Galones (Precio aprox Q32/gal para calcular IDP)
            # En un sistema real, podrías pedir ingresar galones exactos, aquí estimamos.
            galones_estimados = monto_total / 32.00 
            
            # IDP Promedio (Superior Q4.70, Regular Q4.60). Usamos Q4.70 por seguridad fiscal.
            idp = galones_estimados * 4.70
            
            # Fórmula: Base = (Total - IDP) / 1.12
            base = (monto_total - idp) / 1.12
            iva = base * 0.12
            
        else:
            # GASTO NORMAL (Solo IVA)
            base = monto_total / 1.12
            iva = base * 0.12

        # --- CREAR PARTIDA CONTABLE (LIBRO DIARIO) ---
        
        # A) Encabezado de la Partida
        entry = JournalEntry.objects.create(
            company=request.user.current_company,
            description=f"Pago: {expense.description[:40]} (Ref Gasto #{expense.id})",
            created_by=request.user,
            total=monto_total,
            expense_ref=expense
        )

        # B) DEBE: Gasto Neto (Base)
        JournalItem.objects.create(
            entry=entry, 
            account_name=cuenta_gasto, 
            debit=round(base, 2), 
            credit=0
        )

        # C) DEBE: IVA por Cobrar
        JournalItem.objects.create(
            entry=entry, 
            account_name="IVA por Cobrar", 
            debit=round(iva, 2), 
            credit=0
        )

        # D) DEBE: IDP (Solo si existe)
        if idp > 0:
            JournalItem.objects.create(
                entry=entry, 
                account_name="Impuesto IDP (Gasto no deducible)", 
                debit=round(idp, 2), 
                credit=0
            )

        # E) HABER: Banco / Caja (Salida de dinero completa)
        # Aquí asumimos que sale de la primera cuenta bancaria que encuentre (o podrías pedir seleccionarla)
        cuenta_banco = BankAccount.objects.filter(company=request.user.current_company).first()
        nombre_banco = cuenta_banco.bank_name if cuenta_banco else "Caja General"
        
        JournalItem.objects.create(
            entry=entry, 
            account_name=nombre_banco, 
            debit=0, 
            credit=round(monto_total, 2)
        )
        
        # Si existe cuenta bancaria, restamos el saldo real
        if cuenta_banco:
            cuenta_banco.balance -=  decimal.Decimal(monto_total)
            cuenta_banco.save()

        # 4. Actualizar Estado del Gasto
        expense.status = 'APPROVED'
        expense.save()
        
        messages.success(request, f"✅ Gasto Aprobado. Partida #{entry.id} generada con desglose de impuestos.")

    except Exception as e:
        messages.error(request, f"Error generando partida: {e}")

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