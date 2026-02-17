import decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum

# --- IMPORTACIÓN DE MODELOS ---
from .models import (
    Expense, 
    JournalEntry, 
    JournalItem, 
    BankAccount, 
    BankTransaction, 
    Vehicle
)
# --- IMPORTACIÓN DE FORMULARIOS ---
# (Si alguno no existe, coméntalo, pero aquí están los estándar)
from .forms import (
    # ExpensePhotoForm,  <-- Usamos HTML directo para fotos, no es estricto el form
    BankAccountForm, 
    BankTransactionForm, 
    VehicleForm
)

# --- CEREBRO IA ---
from .utils import analyze_invoice_image

# ========================================================
# 1. FLUJO DE GASTOS (PILOTOS - SCANNER - REVISIÓN)
# ========================================================

@login_required
def pilot_upload(request):
    """
    Vista para Pilotos: Carga rápida de foto y monto.
    """
    if request.method == 'POST':
        image = request.FILES.get('documento')
        description = request.POST.get('description', 'Gasto de Ruta')
        amount = request.POST.get('amount')
        
        try:
            Expense.objects.create(
                user=request.user,
                company=request.user.current_company,
                receipt_image=image,
                description=description,
                total_amount=amount,
                status='PENDING',
                # Valores por defecto
                provider_name="Pendiente Revisión",
                tax_base=0, tax_iva=0, tax_idp=0,
                suggested_account="Por Asignar"
            )
            messages.success(request, "¡Gasto enviado a contabilidad!")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Error al subir: {e}")
            
    return render(request, 'accounting/pilot_upload.html')


@login_required
def smart_scanner(request):
    """
    Vista para Contador: Escaneo con IA y desglose automático.
    (Antes llamada upload_expense_photo)
    """
    if request.method == 'POST':
        image = request.FILES.get('documento')
        smart_input = request.POST.get('smart_input', '') # Texto de ayuda
        
        # 1. ANALISIS IA
        ai_data = analyze_invoice_image(image, smart_input)
        
        # 2. CÁLCULO PRELIMINAR DE IMPUESTOS
        total = ai_data['total']
        idp = 0.00
        base = 0.00
        iva = 0.00

        if ai_data['is_fuel']:
            # Lógica IDP Guatemala
            precio_galon = 28.00 if ai_data['fuel_type'] == 'diesel' else 32.00
            tasa_idp = 4.70
            if ai_data['fuel_type'] == 'regular': tasa_idp = 4.60
            elif ai_data['fuel_type'] == 'diesel': tasa_idp = 1.30

            galones = total / precio_galon
            idp = galones * tasa_idp
            base = (total - idp) / 1.12
        else:
            base = total / 1.12
            
        iva = base * 0.12

        # 3. GUARDAR RESULTADO
        Expense.objects.create(
            user=request.user,
            company=request.user.current_company,
            receipt_image=image,
            
            provider_name=ai_data['provider_name'],
            provider_nit=ai_data['provider_nit'],
            invoice_series=ai_data['invoice_series'],
            invoice_number=ai_data['invoice_number'],
            description=ai_data['description'],
            suggested_account=ai_data['account_type'],
            
            total_amount=total,
            tax_base=base,
            tax_iva=iva,
            tax_idp=idp,
            
            status='PENDING'
        )
        
        messages.success(request, f"✅ IA Detectó: {ai_data['account_type']}")
        return redirect('expense_pending_list')

    return render(request, 'accounting/smart_hub.html')


# Mantenemos compatibilidad por si alguna url vieja llama a esta función
@login_required
def upload_expense_photo(request):
    return redirect('smart_scanner')


@login_required
def expense_pending_list(request):
    """Bandeja de Entrada de Gastos (Pilotos + Scanner)"""
    expenses = Expense.objects.filter(
        company=request.user.current_company, 
        status='PENDING'
    ).order_by('-date')
    return render(request, 'accounting/expense_pending_list.html', {'expenses': expenses})


@login_required
def review_expense(request, pk):
    """
    Paso Intermedio: El contador revisa/corrige datos antes de aprobar.
    """
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if request.method == 'POST':
        # Actualizamos con lo que el contador corrigió
        expense.provider_name = request.POST.get('provider_name')
        expense.provider_nit = request.POST.get('provider_nit')
        expense.invoice_number = request.POST.get('invoice_number')
        expense.description = request.POST.get('description')
        expense.total_amount = decimal.Decimal(request.POST.get('total_amount'))
        
        # Aquí podrías recalcular impuestos si cambió el monto, 
        # pero por ahora confiamos en la aprobación final.
        expense.save()
        
        # Redirigir directo a aprobar
        return redirect('approve_expense', pk=expense.id)

    return render(request, 'accounting/review_expense.html', {'expense': expense})


@login_required
def approve_expense(request, pk):
    """
    GENERADOR DE PARTIDA CONTABLE (LIBRO DIARIO)
    """
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if expense.status == 'APPROVED':
        messages.warning(request, "Este gasto ya fue contabilizado.")
        return redirect('expense_pending_list')

    try:
        # --- CÁLCULOS FINALES ---
        # Usamos float para cálculos, luego decimal para DB si es necesario
        monto_total = float(expense.total_amount)
        descripcion = expense.description.lower()
        
        idp = 0.00
        base = 0.00
        iva = 0.00
        cuenta_gasto = expense.suggested_account or "Gastos Generales"

        # RE-VERIFICACIÓN DE COMBUSTIBLE (Por si el contador editó la descripción)
        es_combustible = any(x in descripcion for x in ['gasolina', 'combustible', 'shell', 'texaco', 'puma', 'diesel'])
        
        if es_combustible:
            cuenta_gasto = "Combustibles y Lubricantes"
            # Recálculo de IDP seguro
            galones_estimados = monto_total / 32.00 
            idp = galones_estimados * 4.70
            base = (monto_total - idp) / 1.12
            iva = base * 0.12
        else:
            # Gasto Normal
            base = monto_total / 1.12
            iva = base * 0.12

        # Actualizamos los valores fiscales en el objeto expense por si cambiaron
        expense.tax_base = decimal.Decimal(base)
        expense.tax_iva = decimal.Decimal(iva)
        expense.tax_idp = decimal.Decimal(idp)
        
        # --- CREAR PARTIDA (JOURNAL ENTRY) ---
        entry = JournalEntry.objects.create(
            company=request.user.current_company,
            description=f"Prov: {expense.provider_name} - {expense.description[:30]}",
            created_by=request.user,
            total=monto_total,
            expense_ref=expense
        )

        # 1. DEBE: Gasto Neto
        JournalItem.objects.create(
            entry=entry, 
            account_name=cuenta_gasto, 
            debit=round(base, 2), 
            credit=0
        )

        # 2. DEBE: IVA
        JournalItem.objects.create(
            entry=entry, 
            account_name="IVA por Cobrar", 
            debit=round(iva, 2), 
            credit=0
        )

        # 3. DEBE: IDP (Si aplica)
        if idp > 0:
            JournalItem.objects.create(
                entry=entry, 
                account_name="Impuesto IDP (No deducible)", 
                debit=round(idp, 2), 
                credit=0
            )

        # 4. HABER: Salida de Banco
        cuenta_banco = BankAccount.objects.filter(company=request.user.current_company).first()
        nombre_banco = cuenta_banco.bank_name if cuenta_banco else "Caja General"
        
        JournalItem.objects.create(
            entry=entry, 
            account_name=nombre_banco, 
            debit=0, 
            credit=round(monto_total, 2)
        )
        
        # Restar saldo
        if cuenta_banco:
            cuenta_banco.balance -= decimal.Decimal(monto_total)
            cuenta_banco.save()

        # Finalizar
        expense.status = 'APPROVED'
        expense.save()
        
        messages.success(request, f"✅ Partida #{entry.id} generada con éxito.")

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


# ========================================================
# 2. LIBROS CONTABLES Y ESTADOS FINANCIEROS
# ========================================================

@login_required
def libro_diario(request):
    # Ahora mostramos las PARTIDAS (JournalEntry), no solo transacciones de banco
    entries = JournalEntry.objects.filter(
        company=request.user.current_company
    ).order_by('-date', '-id').prefetch_related('items')
    return render(request, 'accounting/libro_diario.html', {'entries': entries})

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

@login_required
def chart_of_accounts(request):
    """Simulación del Plan de Cuentas NIIF"""
    simulated_accounts = [
        {'code': '1', 'name': 'ACTIVO', 'level': 1, 'type': 'Rubro', 'niif_tag': 'ESF'},
        {'code': '1.1', 'name': 'ACTIVO CORRIENTE', 'level': 2, 'type': 'Grupo', 'niif_tag': 'NIC 1'},
        {'code': '1.1.01', 'name': 'Efectivo y Equivalentes', 'level': 3, 'type': 'Cuenta Mayor', 'niif_tag': 'NIC 7'},
    ]
    return render(request, 'accounting/chart_of_accounts.html', {'accounts': simulated_accounts})


# ========================================================
# 3. MÓDULOS AUXILIARES (FLOTILLA Y BANCOS)
# ========================================================

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

@login_required
def bank_list(request):
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    total_balance = sum(acc.balance for acc in accounts)
    # Mostramos ultimas transacciones
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
            bank.company = request.user.current_