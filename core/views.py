import csv
import os
import json
from .logic import gestionar_salida_stock  # <--- NUEVO IMPORT
from datetime import datetime, date, timedelta
from itertools import chain
from operator import attrgetter
from django.db.models import Q
from .models import Quotation, Sale, SaleDetail, CompanyProfile, BankAccount, BankMovement, Inventory
from .logic import realizar_traslado_entre_bodegas # <--- IMPORTANTE
from .models import StockMovement
from inventory.models import Product # Necesitamos productos
from .forms import CustomUserForm, User
from .models import Expense, Vehicle, CreditCard

# --- IMPORTS DE DJANGO ---
from django.http import JsonResponse, HttpResponse
from django.db import models, transaction
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth import get_user_model, login, logout
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Count, F
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.safestring import mark_safe 
from inventory.models import StockMovement
from .models import Invoice, InvoiceDetail

# --- CEREBRO IA (Si lo está usando) ---
from .ai_brain import analizar_texto_bancario, analizar_documento_ia

# ==========================================
# 1. MODELOS (Tablas de Base de Datos)
# ==========================================
from .models import (
    # Usuarios y Empresa
    UserRoleCompany, Company, CompanyProfile, Branch, Warehouse,
    
    # Terceros
    Client, Supplier, Provider, BusinessPartner, Employee,
    
    # Ventas y Compras
    Product, Sale, SaleDetail, 
    Quotation, QuotationDetail, 
    Purchase, PurchaseDetail, 
    
    # Finanzas
    Account, BankAccount, BankTransaction, BankMovement, 
    Expense, Vehicle, CreditCard, # <--- NUEVOS
    Income, JournalEntry, JournalItem, # <--- SE MANTIENEN
    InventoryMovement, Loan, Payroll, PayrollDetail # <--- SE MANTIENEN
    
)

# ==========================================
# 2. FORMULARIOS (Pantallas / HTML)
# ==========================================
from .forms import (
    # Compras y Ventas (AQUÍ ES DONDE DEBE ESTAR PurchaseForm)
    QuotationForm, 
    PurchaseForm,  # <--- ¡CORRECTO! Aquí sí existe
    ClientForm,
    ProductForm,
    
    # Finanzas y Admin
    CompanySelectForm, 
    PilotExpenseForm, # Reemplaza a PilotExpenseForm
    ExpenseForm,      # Reemplaza a ExpenseForm
    BankAccountForm, 
    BankTransactionForm,
    TransferForm,
    IncomeForm,
    SupplierForm,
    SupplierPaymentForm,
    EmployeeForm, 
    LoanForm
)
User = get_user_model()
# ---------------------------------------------------------
# A PARTIR DE AQUÍ COMIENZAN SUS VISTAS (def home...)
# ---------------------------------------------------------
# ==========================================
# 1. SISTEMA DE ACCESO Y DASHBOARD
# ==========================================

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('select_company')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def select_company(request):
    """Vista para elegir en qué empresa trabajar"""
    
    # 1. Verificar si el usuario tiene perfil y empresas
    if not hasattr(request.user, 'profile'):
        # Si no tiene perfil, lo mandamos al inicio o mostramos error
        return render(request, 'core/error_no_companies.html', {})
        
    companies = request.user.profile.allowed_companies.filter(active=True)

    # 2. Si no tiene ninguna empresa asignada, avisar
    if not companies.exists():
        return render(request, 'core/error_no_companies.html', {})

    # 3. Lógica POST (Cuando el usuario presiona el botón "Entrar")
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        if company_id:
            try:
                selected = companies.get(id=company_id)
                
                # Guardamos la elección en la SESIÓN (Memoria temporal)
                request.session['company_id'] = selected.id
                request.session['company_name'] = selected.name
                request.session['company_logo'] = selected.logo.url if selected.logo else ''
                
                # Guardamos en la BD para recordar la última
                request.user.profile.active_company = selected
                request.user.profile.save()
                
                # REDIRECCIÓN FINAL AL DASHBOARD
                return redirect('home') 
            except Exception as e:
                # Si algo falla (ej: hackearon el ID), recargamos
                print(f"Error seleccionando empresa: {e}")

    # 4. Lógica GET (Mostrar la pantalla)
    
    # TRUCO PRO: Si el usuario solo tiene 1 empresa, lo metemos directo sin preguntar
    if companies.count() == 1:
        unique_company = companies.first()
        request.session['company_id'] = unique_company.id
        request.session['company_name'] = unique_company.name
        return redirect('home')

    # AQUÍ ESTABA EL ERROR: Faltaba retornar el HTML al final
    return render(request, 'core/seleccion_nueva.html', {'companies': companies}
                  )

@login_required
def home(request):
    User = get_user_model()

    # --- 1. LÓGICA DE USUARIOS CONECTADOS ---
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_id_list = []
    for s in sessions:
        data = s.get_decoded()
        if '_auth_user_id' in data:
            user_id_list.append(data['_auth_user_id'])
    
    active_users_list = User.objects.filter(id__in=user_id_list).distinct()
    active_sessions = active_users_list.count()

    # --- 2. LÓGICA DE NEGOCIO (RECUPERADA) ---
    # Ventas Totales
    total_ventas = Sale.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    # Compras Totales
    total_compras = Purchase.objects.aggregate(Sum('total'))['total__sum'] or 0
    
    # Total Clientes
    total_clientes = Client.objects.count()
    
    # Stock Crítico (Productos con menos de 5 unidades)
    productos_bajos = Product.objects.filter(stock__lt=5).count()
    
    # Últimas 5 ventas para la tabla
    ultimas_ventas = Sale.objects.order_by('-date')[:5]

    context = {
        # Datos de Usuarios
        'active_users_list': active_users_list,
        'active_sessions': active_sessions,
        
        # Datos del Tablero (Dashboard)
        'total_ventas': total_ventas,
        'total_compras': total_compras,
        'total_clientes': total_clientes,
        'productos_bajos': productos_bajos,
        'ultimas_ventas': ultimas_ventas,
    }
    return render(request, 'core/home.html', context)

# ==========================================
# 2. GASTOS Y OCR
# ==========================================

@login_required
def dashboard_gastos(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.get(id=company_id)
    
    queryset = Expense.objects.filter(company=company).order_by('-fecha')
    totales = queryset.aggregate(
        total_general=Sum('total'),
        total_iva=Sum('impuesto_iva')
    )
    return render(request, 'core/dashboard_gastos.html', {
        'company': company, 'totales': totales, 'gastos': queryset[:50]
    })

@login_required
def expense_list(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.get(id=company_id)
    expenses = Expense.objects.filter(company=company).order_by('-fecha')
    return render(request, 'core/expense_list.html', {'expenses': expenses})

@login_required
def mobile_expense(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = PilotExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.company = company
            gasto.usuario_registra = request.user
            gasto.save()
            messages.success(request, "Gasto rápido registrado correctamente.")
            return redirect('dashboard_gastos')
    return render(request, 'core/mobile_expense.html', {'company': company})

@login_required
def gasto_manual(request):
    # 1. Validación de Seguridad
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    # Contexto Inicial
    contexto_form = {
        'fecha': date.today(),
        'proveedor': '',
        'descripcion': '',
        'total': '',
        'idp': 0,
        'base': '',
        'iva': '',
        'es_combustible': False
    }

    # Helper para limpiar Q1,200.00
    def limpiar_monto(valor):
        if not valor: return 0.0
        s = str(valor).upper().replace('Q', '').replace(',', '').replace(' ', '')
        try: return float(s)
        except ValueError: return 0.0

    if request.method == 'POST':
        # --- RAMA A: IA / OCR ---
        if 'analizar_ia' in request.POST and request.FILES.get('imagen_factura'):
            # ... (Tu código de IA se queda igual, solo asegúrate que mapee a los campos nuevos) ...
            pass 

        # --- RAMA B: GUARDAR (ESTO ES LO QUE CAMBIA) ---
        else:
            try:
                # 1. Crear Objeto Expense
                gasto = Expense()
                gasto.user = request.user # Ahora se liga al usuario, no directo a company
                
                # Mapeo de campos HTML -> Modelo Expense
                gasto.date = request.POST.get('fecha') or timezone.now().date()
                gasto.provider = request.POST.get('nombre_emisor')
                gasto.description = request.POST.get('concepto')
                
                # Montos
                gasto.total_amount = limpiar_monto(request.POST.get('monto_total'))
                gasto.idp_amount = limpiar_monto(request.POST.get('monto_idp'))
                gasto.is_fuel = True if request.POST.get('es_combustible') else False
                
                # Calcular Base e IVA
                monto_sujeto = float(gasto.total_amount) - float(gasto.idp_amount)
                gasto.base_amount = round(monto_sujeto / 1.12, 2)
                gasto.vat_amount = round(float(gasto.total_amount) - float(gasto.idp_amount) - float(gasto.base_amount), 2)
                
                gasto.status = 'APPROVED' # Manual = Aprobado

                # Guardar Vehículo
                vid = request.POST.get('vehicle_id')
                if vid: gasto.vehicle_id = vid

                # Guardar Foto
                if 'imagen_factura' in request.FILES:
                    gasto.invoice_file = request.FILES['imagen_factura']

                gasto.save()

                # --- 2. CONTABILIDAD AUTOMÁTICA (JOURNAL) ---
                try:
                    partida = JournalEntry.objects.create(
                        date=gasto.date,
                        description=f"Gasto: {gasto.provider}",
                        reference=f"EXP-{gasto.id}",
                        expense=gasto,
                        is_posted=True
                    )
                    
                    # DEBE: Gasto
                    JournalItem.objects.create(entry=partida, account_id=1, debit=gasto.base_amount, credit=0) # ID 1 placeholder
                    
                    # DEBE: IVA
                    if gasto.vat_amount > 0:
                        JournalItem.objects.create(entry=partida, account_id=2, debit=gasto.vat_amount, credit=0) # ID 2 placeholder

                    # HABER: Caja/Banco
                    JournalItem.objects.create(entry=partida, account_id=3, debit=0, credit=gasto.total_amount) # ID 3 placeholder

                except Exception as e_conta:
                    print(f"Alerta Contable: {e_conta}")

                messages.success(request, "Gasto registrado y contabilizado.")
                return redirect('expense_list')

            except Exception as e:
                messages.error(request, f"Error al guardar: {e}")

    # GET Request
    vehiculos = Vehicle.objects.all() # Usamos el nuevo modelo Vehicle
    bancos = BankAccount.objects.filter(company_id=company_id)
    
    full_context = {'vehiculos': vehiculos, 'bancos': bancos}
    full_context.update(contexto_form)
    
    return render(request, 'core/gasto_manual.html', full_context)

@csrf_exempt
def api_ocr_process(request):
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'OCR recibido (Simulado)'})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

# --- 9. TESORERÍA / BANCOS ---

@login_required
def bank_list(request):
    cuentas = BankAccount.objects.all()
    # Calculamos el total de dinero disponible sumando todas las cuentas
    total_disponible = sum(c.balance for c in cuentas)
    
    return render(request, 'core/treasury/bank_list.html', {
        'cuentas': cuentas,
        'total_disponible': total_disponible
    })

# =========================================================
# VISTA 2: CREAR NUEVA CUENTA (El formulario nuevo)
# =========================================================

@login_required
def bank_create(request):
    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        account_number = request.POST.get('account_number')
        currency = request.POST.get('currency')
        initial_balance = request.POST.get('initial_balance')
        
        empresa = CompanyProfile.objects.first()
        
        BankAccount.objects.create(
            company=empresa,
            bank_name=bank_name,
            account_number=account_number,
            currency=currency,
            balance=initial_balance
        )
        messages.success(request, 'Cuenta bancaria creada exitosamente.')
        return redirect('bank_list')
        
    return render(request, 'core/treasury/bank_form.html')

# =========================================================
# VISTA 3: TRANSACCIONES + IA (La lógica potente)
# =========================================================

@login_required
def bank_transaction_create(request):
    # Detectamos si es IN (Depósito) o OUT (Retiro) desde la URL (?type=IN)
    movement_type = request.GET.get('type', 'IN') 
    
    if request.method == 'POST':
        form = BankTransactionForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.movement_type = movement_type # Asignamos el tipo automáticamente
            
            # Lógica de saldo
            account = movement.account
            if movement_type == 'IN':
                account.balance += movement.amount
                msg = "Depósito registrado correctamente."
            else:
                account.balance -= movement.amount
                msg = "Retiro/Cheque registrado correctamente."
            
            account.save()
            movement.save()
            
            messages.success(request, msg)
            return redirect('bank_list')
    else:
        form = BankTransactionForm(initial={'date': timezone.now()})

        return render(request, 'core/treasury/transaction_form.html', {
            'form': form,
        'movement_type': movement_type
    })

# =========================================================
# VISTAS 4 y 5: HERRAMIENTAS DE CORRECCIÓN
# =========================================================
@login_required
def recalcular_saldo(request, bank_id):
    cuenta = get_object_or_404(BankAccount, id=bank_id)
    total_in = BankTransaction.objects.filter(account=cuenta, movement_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
    total_out = BankTransaction.objects.filter(account=cuenta, movement_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
    cuenta.current_balance = total_in - total_out
    cuenta.save()
    messages.success(request, f"Saldo recalculado: Q{cuenta.current_balance}")
    return redirect('bank_list')

@login_required
def delete_transaction(request, pk):
    transaccion = get_object_or_404(BankTransaction, pk=pk)
    cuenta = transaccion.account
    # Reversar saldo
    if transaccion.movement_type == 'IN': cuenta.current_balance -= transaccion.amount
    else: cuenta.current_balance += transaccion.amount
    cuenta.save()
    transaccion.delete()
    messages.warning(request, "Transacción eliminada.")
    return redirect('bank_list')

@login_required
def bank_detail(request, bank_id):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    cuenta = get_object_or_404(BankAccount, id=bank_id, company_id=company_id)
    movimientos = BankMovement.objects.filter(account=cuenta).order_by('-date', '-created_at')
    
    return render(request, 'core/bank_detail.html', {'cuenta': cuenta, 'movimientos': movimientos})

@login_required
def income_list(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    incomes = Income.objects.filter(company_id=company_id).order_by('-date')
    return render(request, 'core/income_list.html', {'incomes': incomes})

@login_required
def income_create(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = IncomeForm(request.POST, request.FILES)
        if form.is_valid():
            income = form.save(commit=False)
            income.company = company
            income.save()
            
            if income.bank_account:
                BankMovement.objects.create(
                    account=income.bank_account,
                    movement_type='IN',
                    category='Venta',
                    description=f"Ingreso: {income.description}",
                    amount=income.amount,
                    date=income.date,
                    evidence=income.evidence
                )
                messages.success(request, f"Ingreso registrado en {income.bank_account.bank_name}.")
            return redirect('income_list')
    else:
        form = IncomeForm()
        form.fields['bank_account'].queryset = BankAccount.objects.filter(company=company)
    return render(request, 'core/income_form.html', {'form': form})

@login_required
def transfer_create(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = TransferForm(company, request.POST, request.FILES)
        if form.is_valid():
            origen = form.cleaned_data['from_account']
            destino = form.cleaned_data['to_account']
            monto = form.cleaned_data['amount']
            fecha = form.cleaned_data['date']
            evidencia = form.cleaned_data['evidence']
            
            # 1. Retiro del Origen
            BankMovement.objects.create(
                account=origen, movement_type='OUT', category='Transferencia',
                description=f"Transf. a {destino.bank_name}", amount=monto, date=fecha, evidence=evidencia
            )
            # 2. Depósito en Destino
            BankMovement.objects.create(
                account=destino, movement_type='IN', category='Transferencia',
                description=f"Transf. de {origen.bank_name}", amount=monto, date=fecha, evidence=evidencia
            )
            
            messages.success(request, "Transferencia realizada con éxito.")
            return redirect('bank_list')
    else:
        form = TransferForm(company)
        
    return render(request, 'core/transfer_form.html', {'form': form})



@login_required
def supplier_list(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            partner = form.save(commit=False)
            partner.company = company
            partner.save()
            messages.success(request, "Proveedor agregado correctamente.")
            return redirect('supplier_list')
    
    partners = BusinessPartner.objects.filter(company=company)
    form = SupplierForm()
    return render(request, 'core/supplier_list.html', {'partners': partners, 'form': form})

@login_required
def pay_supplier(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = SupplierPaymentForm(company, request.POST, request.FILES)
        if form.is_valid():
            provider = form.cleaned_data['provider']
            my_account = form.cleaned_data['my_account']
            amount = form.cleaned_data['amount']
            
            desc = f"Pago a: {provider.name} (Destino: {provider.bank_name} - {provider.bank_account})"
            
            BankMovement.objects.create(
                account=my_account,
                movement_type='OUT',
                category='Pago Proveedor',
                description=desc,
                amount=amount,
                date=form.cleaned_data['date'],
                evidence=form.cleaned_data['evidence']
            )
            
            messages.success(request, f"Transferencia de Q{amount} a {provider.name} registrada.")
            return redirect('bank_list')
    else:
        form = SupplierPaymentForm(company)

    return render(request, 'core/pay_supplier.html', {'form': form})

# ==========================================
# 4. CONTABILIDAD (LIBROS Y ESTADOS)
# ==========================================

@login_required
def libro_diario(request):
    """
    Libro Diario Operativo:
    Une Gastos, Ingresos y Movimientos Bancarios en una sola línea de tiempo.
    """
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    
    # 1. TRAER LOS GASTOS (Corregido: Filtra por empresa del usuario)
    # Nota: Como Expense no tiene 'company', filtramos por los usuarios de esta empresa
    gastos = Expense.objects.filter(
        user__profile__active_company_id=company_id
    ).order_by('-date')
    
    # 2. TRAER LOS INGRESOS
    ingresos = Income.objects.filter(company_id=company_id).order_by('-date')
    
    # 3. TRAER MOVIMIENTOS BANCARIOS (Excluyendo los que ya son Ingresos/Gastos para no duplicar visualmente si se desea)
    bancos = BankMovement.objects.filter(account__company_id=company_id).order_by('-date')

    # 4. UNIFICAR TODO EN UNA LISTA NORMALIZADA
    # Convertimos todo a un diccionario común para que el HTML no sufra con los nombres distintos
    movimientos_unificados = []

    # A. Procesar Gastos
    for g in gastos:
        movimientos_unificados.append({
            'fecha': g.date,
            'descripcion': f"GASTO: {g.provider or 'Sin proveedor'} - {g.description}",
            'referencia': f"EXP-{g.id}",
            'debe': g.total_amount,  # Gasto es salida (Debe contable / Haber banco) - Aquí lo mostramos como monto
            'haber': 0,
            'saldo': -g.total_amount, # Resta
            'tipo': 'GASTO',
            'objeto': g
        })

    # B. Procesar Ingresos
    for i in ingresos:
        movimientos_unificados.append({
            'fecha': i.date,
            'descripcion': f"INGRESO: {i.description}",
            'referencia': i.reference_doc or f"INC-{i.id}",
            'debe': 0,
            'haber': i.amount,
            'saldo': i.amount, # Suma
            'tipo': 'INGRESO',
            'objeto': i
        })

    # C. Procesar Bancos (Solo transferencias o ajustes manuales para no duplicar)
    # Si quieres ver TODO el banco, descomenta todo. Aquí filtramos solo lo que no venga de Gasto/Ingreso
    for b in bancos:
        # Simple lógica para evitar duplicados visuales si ya registraste el ingreso arriba
        # (Opcional: Si prefieres ver todo, quita el 'if')
        es_ingreso = 'Ingreso' in b.category
        es_gasto = 'Pago' in b.category or 'Gasto' in b.category
        
        # Solo agregamos si es una transferencia pura o ajuste, o si quieres ver el flujo bancario puro
        movimientos_unificados.append({
            'fecha': b.date,
            'descripcion': f"BANCO: {b.description} ({b.category})",
            'referencia': b.reference or f"BNK-{b.id}",
            'debe': b.amount if b.movement_type == 'OUT' else 0,
            'haber': b.amount if b.movement_type == 'IN' else 0,
            'saldo': b.amount if b.movement_type == 'IN' else -b.amount,
            'tipo': 'BANCO',
            'objeto': b
        })

    # 5. ORDENAR POR FECHA (Del más reciente al más antiguo)
    movimientos_unificados.sort(key=lambda x: x['fecha'], reverse=True)

    # 6. CALCULAR TOTALES
    total_debe = sum(m['debe'] for m in movimientos_unificados)
    total_haber = sum(m['haber'] for m in movimientos_unificados)
    balance = total_haber - total_debe

    return render(request, 'accounting/libro_diario.html', {
        'movimientos': movimientos_unificados,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'balance': balance,
        'company': company
    })

@login_required
def libro_mayor(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    cuentas = Account.objects.filter(company=company)
    resumen_gastos = Expense.objects.filter(company=company).values('categoria').annotate(
        total=Sum('total')
    ).order_by('categoria')

    bancos = BankAccount.objects.filter(company=company)

    return render(request, 'accounting/libro_mayor.html', {
        'cuentas': cuentas,
        'resumen_gastos': resumen_gastos,
        'bancos': bancos,
        'hoy': datetime.now()
    })

@login_required
def balance_saldos(request):
    company_id = request.session.get('company_id')
    
    total_ingresos = Income.objects.filter(company_id=company_id).aggregate(Sum('amount'))['amount__sum'] or 0
    total_gastos = Expense.objects.filter(company_id=company_id).aggregate(Sum('total'))['total__sum'] or 0
    saldo_neto = total_ingresos - total_gastos

    return render(request, 'core/accounting/balance_saldos.html', {
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'saldo_neto': saldo_neto
    })

@login_required
def estado_resultados(request):
    return render(request, 'core/reports/estado_resultados.html')

@login_required
def balance_general(request):
    return render(request, 'core/reports/balance_general.html')

# ==========================================
# 5. INVENTARIO & SMART SCANNER
# ==========================================

@login_required
def smart_hub(request):
    """
    CENTRO DE RECEPCIÓN INTELIGENTE
    Detecta si la entrada es un código de barras (Inventario) o un archivo (Gasto).
    """
    if request.method == 'POST':
        # 1. ¿Viene un archivo? (Entonces es FACTURA/OCR)
        if 'documento' in request.FILES:
            messages.info(request, "Documento recibido. Enviando a módulo de GASTOS para análisis OCR...")
            return redirect('dashboard_gastos')

        # 2. ¿Viene texto? (Posible CÓDIGO DE BARRAS)
        codigo = request.POST.get('smart_input', '').strip()
        
        if codigo:
            company_id = request.session.get('company_id')
            
            # Buscamos si existe el producto por SKU o Código de Barras
            producto = Product.objects.filter(company_id=company_id).filter(
                Q(sku=codigo) | Q(barcode=codigo)
            ).first()

            if producto:
                # Si existe, vamos al detalle del producto o a crear movimiento
                messages.success(request, f"Producto encontrado: {producto.name}")
                return redirect('create_movement') 
            else:
                # Si no existe, sugerimos crearlo
                messages.warning(request, f"El código '{codigo}' no existe. ¿Desea registrarlo?")
                return redirect(f"/inventory/product/new/?code={codigo}")

    return render(request, 'inventory/smart_hub.html')

@login_required
def product_list(request):
    company_id = request.session.get('company_id')
    products = Product.objects.filter(company_id=company_id, active=True)
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        # Aquí creamos el formulario vacío para enviarlo
        form = ProductForm() 
    
    # Aquí lo enviamos al HTML. Fíjese en la parte {'form': form}
    return render(request, 'core/inventory/product_form.html', {'form': form})

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventory/product_detail.html', {'product': product})

@login_required
def create_movement(request):
    """
    Registra entradas o salidas y RECALCULA el Costo Promedio y Stock.
    """
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    
    pre_selected_product = request.GET.get('product_id')
    
    if request.method == 'POST':
        product_id = request.POST.get('product')
        tipo = request.POST.get('movement_type')
        cantidad = int(request.POST.get('quantity'))
        costo_unitario = float(request.POST.get('unit_cost', 0))
        referencia = request.POST.get('reference')
        
        producto = get_object_or_404(Product, id=product_id)
        
        # VALIDACIÓN: No permitir salidas si no hay stock
        if tipo == 'OUT' and producto.stock < cantidad:
            messages.error(request, f"Error: No hay suficiente stock. Disponible: {producto.stock}")
            return redirect('create_movement')

        # 1. Crear el movimiento en el historial
        InventoryMovement.objects.create(
            company=company,
            product=producto,
            movement_type=tipo,
            quantity=cantidad,
            unit_cost=costo_unitario if tipo == 'IN' else producto.cost_price,
            reference=referencia,
            user=request.user
        )
        
        # 2. ACTUALIZAR EL PRODUCTO (CÁLCULO DE COSTO PROMEDIO)
        if tipo == 'IN':
            val_actual = producto.stock * float(producto.cost_price)
            val_nuevo = cantidad * costo_unitario
            nuevo_stock = producto.stock + cantidad
            
            if nuevo_stock > 0:
                producto.cost_price = (val_actual + val_nuevo) / nuevo_stock
            
            producto.stock = nuevo_stock
            
        elif tipo == 'OUT':
            producto.stock -= cantidad
            
        producto.save()
        messages.success(request, f"Movimiento registrado. Nuevo Stock: {producto.stock}")
        return redirect('product_list')

    products = Product.objects.filter(company=company, active=True)
    return render(request, 'inventory/movement_form.html', {
        'products': products, 
        'pre_selected': int(pre_selected_product) if pre_selected_product else None
    })

# ==========================================
# 6. RECURSOS HUMANOS (RRHH)
# ==========================================

@login_required
def employee_list(request):
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = company
            emp.save()
            messages.success(request, "Empleado registrado correctamente.")
            return redirect('employee_list')
    
    employees = Employee.objects.filter(company=company, active=True)
    form = EmployeeForm()
    return render(request, 'hr/employee_list.html', {'employees': employees, 'form': form})

@login_required
def nomina_create(request):
    """
    1. Calcula la nómina en memoria.
    2. Guarda en BD.
    3. Genera el Gasto contable.
    """
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    employees = Employee.objects.filter(company=company, is_active=True)            
    # CÁLCULO PREVIO (GET)
    preview_data = []
    total_planilla = 0
    
    for emp in employees:
        igss = float(emp.base_salary) * 0.0483 
        # Cálculo simplificado ISR
        renta_neta = (float(emp.base_salary) * 12) - 48000 - (igss * 12)
        isr_mensual = (renta_neta * 0.05) / 12 if renta_neta > 0 else 0
        
        liquido = float(emp.base_salary) + float(emp.bonus) - igss - isr_mensual
        
        preview_data.append({
            'employee': emp,
            'igss': round(igss, 2),
            'isr': round(isr_mensual, 2),
            'liquido': round(liquido, 2)
        })
        total_planilla += liquido

    # GUARDAR Y CONTABILIZAR (POST)
    if request.method == 'POST':
        periodo_txt = request.POST.get('periodo', datetime.now().strftime('%Y-%m-%d'))
        mes_anio = datetime.strptime(periodo_txt, '%Y-%m-%d')
        
        # 1. Crear Cabecera
        nomina = Payroll.objects.create(
            company=company,
            month=mes_anio.month,
            year=mes_anio.year,
            total_amount=total_planilla
        )

        # 2. Guardar Detalles
        for item in preview_data:
            PayrollDetail.objects.create(
                payroll=nomina,
                employee=item['employee'],
                # CORRECCIÓN: Usamos base_salary y bonus directos del modelo
                base_salary=item['employee'].base_salary,
                bonus=item['employee'].bonus,
                igss_deduction=item['igss'],
                isr_deduction=item['isr'],
                loan_deduction=0,
                other_deductions=0,
                total_income=item['employee'].base_salary + item['employee'].bonus,
                total_deductions=item['igss'] + item['isr'],
                net_salary=item['liquido']
            )
        
        # 3. CONEXIÓN AL LIBRO DIARIO (GASTO)
        Expense.objects.create(
            company=company,
            fecha=periodo_txt,
            proveedor="Nómina de Empleados",
            descripcion=f"Pago de planilla {periodo_txt}",
            total=total_planilla,
            categoria="Sueldos y Salarios",
            usuario_registra=request.user
        )
        
        messages.success(request, f"Nómina generada exitosamente.")
        return redirect('libro_salarios')

    return render(request, 'hr/nomina_form.html', {'preview': preview_data, 'total': total_planilla})

@login_required
def gestion_isr(request):
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    context = {'company': company}
    
    if request.method == 'POST':
        try:
            nombre_empleado = request.POST.get('nombre_empleado')
            sueldo_mensual = float(request.POST.get('sueldo', 0))
            bono_incentivo = float(request.POST.get('bono', 250))
            tipo_calculo = request.POST.get('tipo_calculo')
            credito_iva = float(request.POST.get('planilla_iva', 0)) if tipo_calculo == 'final' else 0
            
            ingreso_anual = (sueldo_mensual + bono_incentivo) * 12
            igss_anual = (sueldo_mensual * 12) * 0.0483 
            deduccion_fija = 48000.00
            
            renta_imponible = ingreso_anual - igss_anual - deduccion_fija
            impuesto_determinado = 0
            if renta_imponible > 0:
                if renta_imponible <= 300000:
                    impuesto_determinado = renta_imponible * 0.05
                else:
                    impuesto_determinado = 15000 + ((renta_imponible - 300000) * 0.07)
            
            impuesto_a_pagar = max(0, impuesto_determinado - credito_iva)

            context.update({
                'calculado': True,
                'nombre': nombre_empleado,
                'impuesto_final': impuesto_a_pagar,
                'retencion_mensual': impuesto_a_pagar / 12,
                'fecha': datetime.now()
            })
        except ValueError:
            context['error'] = 'Datos inválidos.'

    return render(request, 'hr/gestion_isr.html', context)

@login_required
def libro_salarios(request):
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    
    ultima_nomina = Payroll.objects.filter(company=company).order_by('-date_generated').first()
    detalles = []
    totales = {'devengado': 0, 'igss': 0, 'isr': 0, 'liquido': 0}
    
    if ultima_nomina:
        detalles_bd = PayrollDetail.objects.filter(payroll=ultima_nomina).select_related('employee')
        for d in detalles_bd:
            detalles.append(d)
            totales['devengado'] += float(d.base_salary + d.bonus)
            totales['igss'] += float(d.igss_deduction)
            totales['isr'] += float(d.isr_deduction)
            totales['liquido'] += float(d.net_salary)
    else:
        messages.warning(request, "Aún no ha generado ninguna nómina.")

    return render(request, 'hr/libro_salarios.html', {
        'company': company, 'nomina': ultima_nomina, 'detalles': detalles, 'totales': totales
    })

@login_required
def prestamo_list(request):
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = LoanForm(company, request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            # Asignamos company indirectamente via employee, pero guardamos el objeto
            loan.save()
            messages.success(request, "Préstamo registrado correctamente.")
            return redirect('prestamo_list')
    else:
        form = LoanForm(company=company)
        
    loans = Loan.objects.filter(employee__company=company)
    return render(request, 'hr/prestamo_list.html', {'loans': loans, 'form': form})

# ==========================================
# 7. REPORTES Y EXTRAS
# ==========================================

@login_required
def reports_dashboard(request):
    return render(request, 'core/reports/dashboard.html')

@login_required
def fleet_report(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    expenses = Expense.objects.filter(company=company).exclude(placa_vehiculo__isnull=True)
    return render(request, 'core/fleet_report.html', {'company': company, 'expenses': expenses})

@login_required
def export_expenses_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="gastos.csv"'
    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Proveedor', 'Total'])
    # Lógica de escritura pendiente
    return response

@login_required
def report_bank_statement(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    cuentas = BankAccount.objects.filter(company=company)
    
    movimientos = []
    selected_account = None
    saldo_inicial = 0
    saldo_final = 0
    
    hoy = datetime.now().date()
    start_date = request.GET.get('start_date', hoy.replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', hoy.strftime('%Y-%m-%d'))
    account_id = request.GET.get('account_id')

    if account_id:
        selected_account = get_object_or_404(BankAccount, id=account_id)
        
        movimientos = BankMovement.objects.filter(
            account=selected_account,
            date__range=[start_date, end_date]
        ).order_by('date', 'created_at')
        
        # Saldo Inicial
        ingresos_prev = BankMovement.objects.filter(account=selected_account, date__lt=start_date, movement_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
        egresos_prev = BankMovement.objects.filter(account=selected_account, date__lt=start_date, movement_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
        saldo_inicial = ingresos_prev - egresos_prev
        
        # Calcular saldo línea por línea
        saldo_corriendo = saldo_inicial
        for mov in movimientos:
            if mov.movement_type == 'IN': saldo_corriendo += mov.amount
            else: saldo_corriendo -= mov.amount
            mov.saldo_acumulado = saldo_corriendo
            
        saldo_final = saldo_corriendo

    return render(request, 'core/reports/bank_statement.html', {
        'cuentas': cuentas, 'movimientos': movimientos, 'selected_account': selected_account,
        'start_date': start_date, 'end_date': end_date,
        'saldo_inicial': saldo_inicial, 'saldo_final': saldo_final, 'company': company
    })

@login_required
def report_inventory(request):
    company_id = request.session.get('company_id')
    hoy = datetime.now().date()
    start_date = request.GET.get('start_date', hoy.replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', hoy.strftime('%Y-%m-%d'))
    
    movimientos = InventoryMovement.objects.filter(
        company_id=company_id,
        date__range=[start_date, end_date]
    ).order_by('-date')
    
    return render(request, 'core/reports/inventory_report.html', {
        'movimientos': movimientos, 'start_date': start_date, 'end_date': end_date
    })

# En core/views.py (Agregue esto al final)

from django.contrib.auth import get_user_model # Asegúrese de tener este import arriba

@login_required
def admin_control_panel(request):
    """Panel de Control personalizado para el Administrador del Sistema"""
    # Solo permitimos entrar si es Staff (Admin)
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido al Panel de Control.")
        return redirect('dashboard_gastos')

    User = get_user_model()
    
    context = {
        'total_empresas': Company.objects.count(),
        'total_usuarios': User.objects.count(),
        'total_gastos': Expense.objects.count(),
        'usuarios_recientes': User.objects.order_by('-date_joined')[:5],
        'empresas_list': Company.objects.all()
    }
    
    return render(request, 'core/control_panel.html', context)

# En core/views.py (al final)

@login_required
def bank_statement(request, bank_id):
    # Obtenemos la cuenta o damos error 404 si no existe
    cuenta = get_object_or_404(BankAccount, id=bank_id)
    
    # Traemos TODOS los movimientos ordenados por fecha (del más reciente al más viejo)
    movimientos = BankTransaction.objects.filter(account=cuenta).order_by('-date', '-created_at')
    
    return render(request, 'core/bank_statement.html', {
        'cuenta': cuenta,
        'movimientos': movimientos
    })

# Vista simple para "En Construcción" (Evita que el sistema falle)
def pagina_construccion(request, titulo):
    return render(request, 'core/construction.html', {'titulo': titulo})

# === VISTAS DE CONTABILIDAD ===
@login_required
def journal_list(request):
    # Esta sí la mostramos real porque ya guardamos partidas
    partidas = JournalEntry.objects.all().order_by('-date', '-id')
    return render(request, 'core/accounting/journal_list.html', {'partidas': partidas})

@login_required
def ledger_list(request):
    return pagina_construccion(request, 'Libro Mayor')

@login_required
def trial_balance(request):
    return pagina_construccion(request, 'Balance de Saldos')

@login_required
def income_statement(request):
    return pagina_construccion(request, 'Estado de Resultados')

@login_required
def balance_sheet(request):
    return pagina_construccion(request, 'Balance General')

# === VISTAS DE RRHH ===
@login_required
def employee_list(request):
    return pagina_construccion(request, 'Listado de Empleados')

# === VISTAS DE LOGÍSTICA (Aquí estaba el error) ===
# FORMULARIO RÁPIDO

@login_required
def inventory_list(request):
    # CORRECCIÓN: Usamos .all() porque el modelo Product no tiene campo 'is_active' todavía
    products = Product.objects.all().order_by('-id')
    
    # Manejo del formulario de creación rápida (si lo tiene en esa vista)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado.")
            return redirect('inventory_list')
    else:
        form = ProductForm()

    return render(request, 'core/inventory/product_list.html', {
        'products': products,
        'form': form
    })

# === VISTA DE LISTA DE GASTOS (Si no la tenía) ===
@login_required
def expense_list(request):
    # Si ya tenía una vista de lista de gastos, ignore esto.
    # Si no, esto evita el error en el menú de compras.
    gastos = Expense.objects.filter(company_id=request.session.get('company_id')).order_by('-fecha')
    return render(request, 'core/expense_list.html', {'gastos': gastos})

# --- VISTAS DE CLIENTES ---

@login_required
def client_list(request):
    # Listamos todos los clientes activos
    clientes = Client.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'core/client_list.html', {'clientes': clientes})

@login_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            # Asignamos la empresa actual si usas multi-empresa
            # cliente.company = ... (si tienes la lógica de empresa en sesión)
            cliente.save()
            return redirect('client_list')
    else:
        form = ClientForm()
    
    return render(request, 'core/client_form.html', {'form': form})

# --- 1. LISTA DE COTIZACIONES ---
@login_required
def quotation_list(request):
    cotizaciones = Quotation.objects.all().order_by('-created_at')
    return render(request, 'core/quotation_list.html', {'cotizaciones': cotizaciones})

@login_required
def quotation_create(request):
    # 1. DETECCIÓN SEGURA DE SUCURSAL
    # Valores por defecto (si no se encuentra nada)
    sucursal_nombre = "Sede Central" 
    branch_id = None
    
    # Intento 1: Ver si el usuario tiene el campo 'branch' directo
    if getattr(request.user, 'branch', None):
        sucursal_nombre = request.user.branch.name
        branch_id = request.user.branch.id
        
    # Intento 2: Ver si está en el perfil (UserProfile) usando getattr para evitar el AttributeError
    elif hasattr(request.user, 'profile'):
        # Aquí es donde fallaba antes. Ahora usamos getattr para preguntar "¿Tienes branch?"
        branch_perfil = getattr(request.user.profile, 'branch', None)
        if branch_perfil:
            sucursal_nombre = branch_perfil.name
            branch_id = branch_perfil.id

    # 2. Configurar el Formulario
    form = QuotationForm(initial={
        'date': timezone.now().date(),
        'valid_until': timezone.now().date() + timezone.timedelta(days=15)
    })
    
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                cotizacion = form.save(commit=False)
                cotizacion.user = request.user
                
                # Solo asignamos branch si lo encontramos
                if branch_id and hasattr(cotizacion, 'branch'):
                    cotizacion.branch_id = branch_id
                    
                cotizacion.save()
                
                # Variables para calcular el total general
                total_cotizacion = 0

                # 1. OBTENEMOS LAS LISTAS DEL FORMULARIO
                product_ids = request.POST.getlist('product_id[]')
                qtys = request.POST.getlist('qty[]')
                prices = request.POST.getlist('price[]') # <--- ESTO ES NUEVO: Traemos los precios del form
                
                total_cotizacion = 0

                for i in range(len(product_ids)):
                    if product_ids[i]:
                        prod = get_object_or_404(Product, id=product_ids[i])
                        cant = float(qtys[i])
                        precio = float(prices[i])

                        # --- NUEVA VALIDACIÓN DE STOCK ---
                    if prod.stock < cant:
                    # Si pides 10 y hay 5, lanzamos error y cancelamos todo
                        messages.error(request, f"⚠️ STOCK INSUFICIENTE: Intentas cotizar {cant} de '{prod.name}', pero solo tienes {prod.stock} en existencia.")
                    # Opcional: Podrías hacer un 'break' o 'return' para no guardar nada
                    # Por ahora, dejaremos que guarde pero con la advertencia, o puedes poner:
                    # transaction.set_rollback(True)
                    # return redirect('quotation_create') 

                    # --- FIN VALIDACIÓN ---
                        
                        # Calculamos subtotal
                    subtotal_linea = cant * precio
                    total_cotizacion += subtotal_linea

                        # Guardamos
                    QuotationDetail.objects.create(
                            quotation=cotizacion,
                            product=prod,
                            quantity=cant,
                            unit_price=precio # Guardamos el precio real (4,500)
                        )
                
                cotizacion.total_amount_amount_amount = total_cotizacion
                cotizacion.save()
                
                return redirect('quotation_list')

    # 3. PRODUCTOS (Sin filtro de sucursal por ahora para evitar errores)
    products = Product.objects.all()

    return render(request, 'core/quotation_form.html', {
        'form': form,
        'products': products,
        'sucursal_nombre': sucursal_nombre,
        'company': getattr(request.user, 'company', "Mi Empresa")
    })

# --- 3. GENERAR PDF (CON EMPRESA DINÁMICA) ---
@login_required
def quotation_pdf(request, pk):
    cotizacion = get_object_or_404(Quotation, pk=pk)
    
    # Busca la empresa del usuario (la primera disponible)
    empresa = CompanyProfile.objects.first()
    
    context = {
        'c': cotizacion, 
        'empresa': empresa, 
    }
    return render(request, 'core/sales/quotation_pdf.html', context)
# --- AGREGAR AL FINAL DE core/views.py ---
from django.contrib import messages
from .models import Sale, SaleDetail # Asegúrese de importar estos arriba

# --- 4. CONVERTIR A VENTA (BOTÓN MÁGICO) ---
@login_required
def convertir_a_venta(request, pk):
    cotizacion = get_object_or_404(Quotation, pk=pk)
    
    # 1. Evitar duplicados
    if hasattr(cotizacion, 'sale'):
        messages.warning(request, f"La cotización #{cotizacion.id} ya fue convertida anteriormente.")
        return redirect('quotation_list')

    # 2. Buscar o Crear Empresa (Salvavidas)
    empresa = CompanyProfile.objects.first()
    if not empresa:
        empresa = CompanyProfile.objects.create(
            name="Mi Empresa (Auto-generada)",
            nit="CF",
            address="Ciudad",
            phone="0000-0000",
            email="admin@ejemplo.com"
        )

    # 3. Crear Venta
    nueva_venta = Sale.objects.create(
        company=empresa,
        client=cotizacion.client,
        quotation_origin=cotizacion,
        total=cotizacion.total_amount_amount_amount,
        payment_method='EFECTIVO'
    )

    # 4. Copiar Detalles y RESTAR INVENTARIO 📉
    errores_stock = []
    
    for item in cotizacion.details.all():
        # A. Crear el detalle de la venta
        SaleDetail.objects.create(
            sale=nueva_venta,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.quantity * item.unit_price
        )
        
        # B. Lógica de Inventario (Solo para productos tangibles)
        producto = item.product
        
        # Verificamos si es un producto físico (asumiendo que tiene control de stock)
        # Si su modelo tiene un campo 'type' o similar, aquí es donde sirve.
        # Por ahora restamos a todo lo que tenga stock.
        
        if producto.stock >= item.quantity:
            producto.stock -= item.quantity
            producto.save()
        else:
            # Si no hay suficiente stock, lo anotamos pero permitimos la venta (o podríamos bloquearla)
            errores_stock.append(f"Producto {producto.name}: Stock insuficiente (Tiene {producto.stock}, vendió {item.quantity})")
            # Forzamos la resta para que quede en negativo y avise que debe reponer
            producto.stock -= item.quantity 
            producto.save()

    # 5. Mensaje Final
    if errores_stock:
        messages.warning(request, f"Venta creada, pero con alertas de stock: {', '.join(errores_stock)}")
    else:
        messages.success(request, f"¡Éxito! Venta #{nueva_venta.id} generada y stock actualizado.")
        
    return redirect('quotation_list')

# --- AGREGAR O REEMPLAZAR EN core/views.py ---

# Asegúrese de tener estos imports al inicio del archivo:
from django.shortcuts import render, redirect, get_object_or_404
from .models import Client, Product, Quotation, QuotationDetail, Sale, SaleDetail, CompanyProfile
from django.contrib import messages

# --- 2. CREAR COTIZACIÓN (CORREGIDO: CÁLCULO DE SUBTOTAL) ---
@login_required
@transaction.atomic
def create_quotation(request):
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        if form.is_valid():
            try:
                # 1. Guardar encabezado
                quotation = form.save(commit=False)
                quotation.user = request.user
                
                # Asignar Empresa (Si es multi-empresa)
                company_id = request.session.get('company_id')
                if company_id:
                    quotation.company = CompanyProfile.objects.get(id=company_id)
                else:
                    quotation.company = CompanyProfile.objects.first()

                # Calcular validez
                days = int(request.POST.get('validity_days', 15))
                quotation.valid_until = quotation.date + timedelta(days=days)
                
                quotation.save() 

                # 2. Guardar Productos
                product_ids = request.POST.getlist('products[]')
                quantities = request.POST.getlist('quantities[]')
                prices = request.POST.getlist('prices[]')

                total_general = 0

                for p_id, qty, price in zip(product_ids, quantities, prices):
                    # Validación para no procesar filas vacías
                    if p_id and qty.strip() and price.strip(): 
                        product = Product.objects.get(id=p_id)
                        cantidad = int(qty)
                        precio_unitario = float(price)
                        
                        # Calculamos subtotal solo para sumar al Total General
                        subtotal_fila = cantidad * precio_unitario
                        
                        QuotationDetail.objects.create(
                            quotation=quotation,
                            product=product,
                            quantity=cantidad,
                            unit_price=precio_unitario
                            # --- CORRECCIÓN AQUÍ ---
                            # Borramos la línea 'subtotal=subtotal' porque la base de datos no la tiene.
                        )
                        
                        # Apartar stock
                        product.stock_reserved += cantidad
                        product.save()
                        
                        total_general += subtotal_fila

                # 3. Guardar total final
                quotation.total_amount_amount_amount = total_general
                quotation.save()

                messages.success(request, f"Cotización #{quotation.id} creada exitosamente.")
                return redirect('quotation_list')
            
            except Exception as e:
                print(f"Error detallado: {e}") 
                messages.error(request, f"Error interno: {str(e)}")
        else:
            messages.error(request, f"Faltan datos obligatorios: {form.errors.as_text()}")
    else:
        form = QuotationForm()

    products = Product.objects.filter(stock__gt=0)
    return render(request, 'core/sales/quotation_form.html', {
        'form': form,
        'products': products
    })
    
@login_required
def invoice_pdf(request, pk):
    # Buscamos la VENTA (Sale), no la cotización
    venta = get_object_or_404(Sale, pk=pk)
    
    return render(request, 'core/sales/invoice_pdf.html', {
        'sale': venta
    })

# --- 5. COMPRAS (MÓDULO NUEVO) ---

@login_required
def purchase_list(request):
    # Filtramos compras por empresa
    if request.user.is_superuser:
        purchases = Purchase.objects.all().order_by('-date')
    else:
        # Si es usuario normal, solo ve las de su empresa permitida (o la de sesión)
        company_id = request.session.get('company_id')
        if company_id:
            purchases = Purchase.objects.filter(company_id=company_id).order_by('-date')
        else:
            purchases = Purchase.objects.none()

    return render(request, 'core/purchases/purchase_list.html', {'purchases': purchases})

@login_required
@transaction.atomic
def create_purchase(request):
    if request.method == 'POST':
        # Nota: Asumo que creará un PurchaseForm similar al de cotización
        form = PurchaseForm(request.POST) 
        
        if form.is_valid():
            try:
                # 1. Crear Encabezado de Compra
                purchase = form.save(commit=False)
                purchase.user = request.user
                
                # Asignar Empresa
                company_id = request.session.get('company_id')
                if company_id:
                    purchase.company = CompanyProfile.objects.get(id=company_id)
                else:
                    purchase.company = CompanyProfile.objects.first()
                
                purchase.save()

                # 2. Procesar Productos
                product_ids = request.POST.getlist('products[]')
                quantities = request.POST.getlist('quantities[]')
                costs = request.POST.getlist('costs[]') # Ojo: Aquí le llamamos "costos"

                total_compra = 0

                for p_id, qty, cost in zip(product_ids, quantities, costs):
                    if p_id and qty.strip() and cost.strip():
                        product = Product.objects.get(id=p_id)
                        cantidad = int(qty)
                        costo_unitario = float(cost)
                        subtotal = cantidad * costo_unitario

                        # Crear Detalle
                        PurchaseDetail.objects.create(
                            purchase=purchase,
                            product=product,
                            quantity=cantidad,
                            unit_cost=costo_unitario
                            # No guardamos subtotal si la base de datos no lo tiene
                        )

                        # --- LA MAGIA: SUMAR AL INVENTARIO ---
                        product.stock += cantidad 
                        
                        # Actualizamos el último costo para referencia futura
                        product.cost = costo_unitario 
                        product.save()

                        total_compra += subtotal

                # 3. Guardar Total
                purchase.total_amount_amount_amount = total_compra
                purchase.save()

                messages.success(request, f"Compra #{purchase.id} registrada. Stock actualizado.")
                return redirect('purchase_list') # Asegúrese de tener esta URL

            except Exception as e:
                messages.error(request, f"Error al procesar la compra: {str(e)}")
        else:
             messages.error(request, f"Error en formulario: {form.errors.as_text()}")
    
    else:
        form = PurchaseForm()

    suppliers = Supplier.objects.all() # Necesita tener proveedores creados
    products = Product.objects.all()
    
    return render(request, 'core/purchases/purchase_form.html', {
        'form': form,
        'suppliers': suppliers,
        'products': products
    })

@login_required
def create_client(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        nit = request.POST.get('nit')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        contact_name = request.POST.get('contact_name')
        
        # Buscamos la empresa principal para asignarle el cliente
        empresa = CompanyProfile.objects.first()
        
        Client.objects.create(
            company=empresa,
            name=name,
            nit=nit,
            address=address,
            phone=phone,
            email=email,
            contact_name=contact_name
        )
        
        messages.success(request, 'Cliente registrado exitosamente.')
        return redirect('client_list')
        
    return render(request, 'core/sales/client_form.html')

# Al final de core/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .ai_brain import analizar_texto_bancario, analizar_documento_ia

@csrf_exempt
def api_ai_transaction(request):
    if request.method == 'POST':
        try:
            # A. DETECCIÓN DE IMAGEN (Gemini Vision)
            if 'image' in request.FILES:
                imagen = request.FILES['image']
                # Obtenemos el contexto (si es IN o OUT) para guiar a la IA
                contexto = request.POST.get('context', 'GENERIC') 
                
                # Llamamos a Gemini
                resultado = analizar_documento_ia(imagen, contexto=contexto)
                
                if resultado['exito']:
                    return JsonResponse({'status': 'ok', 'data': resultado['datos']})
                else:
                    return JsonResponse({'status': 'error', 'message': 'No pude leer la imagen.'})

            # B. DETECCIÓN DE TEXTO (Lógica Regex)
            else:
                data = json.loads(request.body)
                prompt = data.get('prompt', '')
                resultado = analizar_texto_bancario(prompt)
                return JsonResponse({'status': 'ok', 'data': resultado})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error'}, status=400)

# 1. LISTADO DE PRODUCTOS
@login_required
def product_list(request):
    products = Product.objects.all().order_by('-id')
    return render(request, 'core/inventory/product_list.html', {'products': products})

# 2. CREAR PRODUCTO (Aquí usamos el form con IA que hicimos antes)

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES) # <--- Aquí se llena
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm() # <--- Aquí se crea vacío para mostrarlo
    
    return render(request, 'core/inventory/product_form.html', {'form': form})

@login_required
def inventory_kardex(request):
    # Obtener todos los movimientos ordenados por fecha (del más reciente al más viejo)
    movements = InventoryMovement.objects.all().select_related('product', 'user').order_by('-date')
    
    # Filtros simples
    query = request.GET.get('q')
    if query:
        movements = movements.filter(
            Q(product__name__icontains=query) | 
            Q(product__code__icontains=query) |
            Q(reference__icontains=query)
        )

    return render(request, 'core/inventory/kardex.html', {
        'movements': movements
    })

@login_required
@transaction.atomic
def convert_quote_to_sale(request, quote_id):
    quotation = get_object_or_404(Quotation, pk=quote_id)
    
    # 1. Validación de seguridad
    if quotation.status == 'BILLED':
        messages.warning(request, "Esta cotización ya fue facturada.")
        return redirect('quotation_list')

    # 2. Definir Empresa
    empresa = None
    if hasattr(request.user, 'employee') and request.user.employee.company:
        empresa = request.user.employee.company
    else:
        empresa = CompanyProfile.objects.first()
        if not empresa:
            empresa = CompanyProfile.objects.create(name="Empresa Default", nit="CF", phone="0000")

    # 3. Crear la Venta
    sale = Sale.objects.create(
        client=quotation.client,
        total=quotation.total_amount_amount_amount,
        payment_method='Efectivo', 
        user=request.user,
        company=empresa
    )

    errores_stock = []

    # 4. PROCESAR PRODUCTOS CON INTELIGENCIA DE BODEGAS 🧠
    for item in quotation.details.all():
        # Crear detalle de venta visual
        SaleDetail.objects.create(
            sale=sale, product=item.product, 
            quantity=item.quantity, unit_price=item.unit_price
        )
        
        # --- AQUÍ LLAMAMOS A LA IA DE BODEGAS ---
        exito, mensaje = gestionar_salida_stock(
            user=request.user,
            product=item.product,
            quantity=item.quantity,
            reference=f"Venta #{sale.id}"
        )
        
        if not exito:
            errores_stock.append(mensaje)

    # Si hubo errores de stock, avisamos (aunque la venta ya se creó, queda como pendiente de regularizar)
    if errores_stock:
        messages.warning(request, f"Venta creada, pero hubo alertas de stock: {'; '.join(errores_stock)}")
    else:
        messages.success(request, f"¡Venta #{sale.id} exitosa! Inventario descontado correctamente.")
        
        # B) DESCUENTO DIRECTO DEL STOCK (Aquí obligamos la resta)
        product = item.product
        product.stock -= item.quantity
        product.save()

        # C) REGISTRO EN KARDEX (Para que quede historial)
        InventoryMovement.objects.create(
            product=product,
            quantity=item.quantity,
            type='OUT', # Salida
            reference=f"Venta #{sale.id} - {sale.client} (Salida por Venta)", 
            
            user=request.user,
            date=timezone.now()
        )

    # 5. COBRO BANCARIO (Su código original)
    if sale.payment_method != 'CREDITO':
        cuenta_destino = BankAccount.objects.filter(company=empresa).first()
        if cuenta_destino:
            cuenta_destino.balance += sale.total_amount_amount_amount
            cuenta_destino.save()
            BankMovement.objects.create(
                account=cuenta_destino,
                movement_type='IN',
                category='Venta',
                amount=sale.total_amount_amount_amount,
                date=timezone.now()
            
            )
            messages.success(request, f"¡Venta #{sale.id} procesada! Stock descontado y Dinero ingresado.")
        else:
            messages.warning(request, "Venta procesada y Stock descontado, pero NO se cobró (Falta Banco).")

    # 6. Cerrar Cotización
    quotation.status = 'BILLED'
    quotation.save()

    return redirect('quotation_list')

@login_required
def admin_control_panel(request):
    if not request.user.is_staff:
        return redirect('home')
    return render(request, 'core/admin_panel.html')

@login_required
def quotation_print(request, id):
    quote = get_object_or_404(Quotation, id=id)
    
    # 1. Traemos los detalles
    details = QuotationDetail.objects.filter(quotation=quote)
    
    # 2. TRUCO DE MAGIA: Calculamos el subtotal al vuelo
    # Como no está en la base de datos, se lo pegamos a cada objeto aquí
    for d in details:
        d.subtotal = d.quantity * d.unit_price

    # 3. Lógica de empresa (la misma de antes)
    try:
        company = CompanyProfile.objects.first()
    except:
        company = None

    return render(request, 'core/quotation_print.html', {
        'quote': quote,
        'details': details, # Ahora llevan el subtotal calculado en memoria
        'company': company,
        'user_company': getattr(request.user, 'company', 'Mi Empresa'),
        'user_branch': getattr(request.user, 'branch', 'Sede Central')
    })

# --- Vista para verificar PIN de autorización ---
@login_required
def validate_price_unlock(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        pin = data.get('pin', '')
        
        # AQUÍ DEFINIMOS EL PIN MAESTRO PARA LOS SUPERVISORES
        # Puede cambiar "2026" por la clave que usted quiera darles.
        MASTER_PIN = "2026" 
        
        # También validamos si la contraseña es la del superusuario actual
        if pin == MASTER_PIN or request.user.check_password(pin):
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'PIN Incorrecto'})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def dashboard_inventario(request):
    query = request.GET.get('q', '') # Esto captura lo que escribes en el buscador
    
    # 1. IDENTIFICAR LA SUCURSAL DEL USUARIO
    my_branch = None
    try:
        # Buscamos si el usuario actual es un empleado y tiene sucursal
        if hasattr(request.user, 'employee'):
            my_branch = request.user.employee.branch
    except:
        pass # Si falla, my_branch se queda como None

    # 2. PREPARAR LAS CONSULTAS (AQUÍ ESTÁ LA LÓGICA QUE PREGUNTASTE)
    local_inventory = []
    global_inventory = []

    if query:
        # A) Primero buscamos en TU Sucursal (inventario_local)
        if my_branch:
            local_inventory = Inventory.objects.filter(
                warehouse__branch=my_branch, 
                product__name__icontains=query
            ).select_related('product', 'warehouse')

        # B) Luego buscamos en TODO lo demás, EXCLUYENDO tu sucursal
        global_inventory = Inventory.objects.filter(
            product__name__icontains=query
        ).exclude(
            warehouse__branch=my_branch 
        ).select_related('product', 'warehouse')

    return render(request, 'core/inventory/dashboard.html', {
        'my_branch': my_branch,
        'local_stock': local_inventory,
        'global_stock': global_inventory,
        'search_query': query
    })

@login_required
def create_transfer(request):
    # 1. Cargar datos para los selectores
    products = Product.objects.all()
    warehouses = Warehouse.objects.filter(active=True)

    if request.method == 'POST':
        # 2. Recibir datos del formulario
        product_id = request.POST.get('product')
        origen_id = request.POST.get('warehouse_from')
        destino_id = request.POST.get('warehouse_to')
        cantidad = int(request.POST.get('quantity'))
        notas = request.POST.get('comments')

        # Validaciones básicas
        if origen_id == destino_id:
            messages.error(request, "La bodega de origen y destino no pueden ser la misma.")
            return redirect('create_transfer')

        # Obtener objetos reales
        producto = get_object_or_404(Product, id=product_id)
        bodega_origen = get_object_or_404(Warehouse, id=origen_id)
        bodega_destino = get_object_or_404(Warehouse, id=destino_id)

        # 3. LLAMAR A LA LÓGICA (El archivo logic.py que creamos antes)
        exito, mensaje = realizar_traslado_entre_bodegas(
            user=request.user,
            product=producto,
            bodega_origen=bodega_origen,
            bodega_destino=bodega_destino,
            cantidad=cantidad,
            comentario=notas
        )

        if exito:
            messages.success(request, mensaje)
            return redirect('product_list') # O a donde quiera volver
        else:
            messages.error(request, f"Error: {mensaje}")

    return render(request, 'core/inventory_transfer.html', {
        'products': products,
        'warehouses': warehouses
    })

@login_required
def kardex_list(request):
    # Traemos los movimientos optimizados (select_related evita consultas lentas)
    movements = StockMovement.objects.select_related('product', 'warehouse', 'user').order_by('-date')[:100] # Últimos 100 para empezar
    
    return render(request, 'core/kardex_list.html', {
        'movements': movements
    })

# --- PEGAR AL FINAL DE core/views.py ---
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from .models import UserProfile

def fix_profiles_view(request):
    """Vista de emergencia para crear perfiles faltantes"""
    User = get_user_model()
    users = User.objects.all()
    resultado = ["<h1>REPORTE DE REPARACIÓN 🔧</h1>"]
    
    for u in users:
        try:
            profile, created = UserProfile.objects.get_or_create(user=u)
            if created:
                resultado.append(f"<p style='color:green'>✅ Perfil CREADO para: <strong>{u.username}</strong></p>")
            else:
                resultado.append(f"<p style='color:blue'>ℹ️ {u.username} ya tenía perfil.</p>")
        except Exception as e:
            resultado.append(f"<p style='color:red'>❌ Error con {u.username}: {str(e)}</p>")
            
    resultado.append("<a href='/admin/'>Ir al Admin ahora</a>")
    return HttpResponse("".join(resultado))

# --- AGREGAR AL FINAL DE core/views.py ---

def force_password_reset(request):
    """Vista de emergencia para resetear contraseñas en Producción"""
    User = get_user_model()
    reporte = ["<h1>🔧 RESETEO DE CONTRASEÑAS 🔧</h1>"]
    
    # Lista de usuarios a los que les pondremos clave "123456"
    usuarios_a_resetear = ['admin', 'Pedro', 'SergioReyes'] 
    
    for nombre in usuarios_a_resetear:
        try:
            u = User.objects.get(username=nombre)
            u.set_password("123456") # <--- Aquí ocurre la magia
            u.save()
            reporte.append(f"<p style='color:green'>✅ Contraseña de <strong>{nombre}</strong> cambiada a: 123456</p>")
        except Exception as e:
            reporte.append(f"<p style='color:red'>❌ No se encontró al usuario: {nombre} ({e})</p>")
            
    reporte.append("<br><a href='/accounts/login/' style='font-size:20px'>👉 IR AL LOGIN AHORA</a>")
    return HttpResponse("".join(reporte))

@login_required
def convert_quote_to_invoice(request, quote_id):
    # 1. Buscamos la cotización
    cotizacion = get_object_or_404(Quotation, id=quote_id)
    
    if cotizacion.status == 'BILLED':
        # Evitar duplicados
        return redirect('invoice_view', id=cotizacion.invoice_set.first().id)

    with transaction.atomic():
        # 2. Crear el Encabezado de la Factura
        factura = Invoice.objects.create(
            client=cotizacion.client,
            payment_method=cotizacion.payment_method,
            due_date=timezone.now().date() + timedelta(days=cotizacion.client.credit_days), # Calc fecha vencimiento
            total=cotizacion.total_amount_amount_amount,
            origin_quotation=cotizacion,
            user=request.user
        )

        # 3. Copiar Detalles y RESTAR STOCK
        for item in cotizacion.details.all():
            # A. Crear detalle de factura
            InvoiceDetail.objects.create(
                invoice=factura,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price
            )
            
            # B. MOVIMIENTO DE INVENTARIO (Salida por Venta)
            # Aquí asumimos que sale de la Bodega Principal (o podrías pedir seleccionarla)
            # Para este ejemplo, usamos la primera bodega activa de la empresa.
            bodega_salida = item.product.company.branch_set.first().warehouses.filter(active=True).first()
            
            if bodega_salida:
                StockMovement.objects.create(
                    product=item.product,
                    warehouse=bodega_salida,
                    quantity=item.quantity,
                    movement_type='OUT_SALE',
                    user=request.user,
                    reference=f"Factura #{factura.id}",
                    description=f"Venta desde Cotización #{cotizacion.id}"
                )

        # 4. Actualizar estado de Cotización
        cotizacion.status = 'BILLED'
        cotizacion.save()
        
        return redirect('invoice_view', id=factura.id)

# Vista para VER la Factura (similar a la de cotización)
@login_required
def invoice_view(request, id):
    factura = get_object_or_404(Invoice, id=id)
    return render(request, 'core/invoice_view.html', {'f': factura, 'company': request.user.company})

@login_required
def quotation_convert(request, id):
    # Buscamos la cotización
    cotizacion = get_object_or_404(Quotation, id=id)

    # SEGURIDAD: Si ya está facturada, no hacer nada
    if cotizacion.status == 'BILLED':
        messages.warning(request, "Esta cotización ya fue facturada.")
        return redirect('quotation_list')

    # INICIO DE TRANSACCIÓN (Todo o Nada)
    # Si algo falla a la mitad, no se descuenta inventario ni se crea factura incompleta
    with transaction.atomic():
        # A. Crear la Factura (Encabezado)
        factura = Invoice.objects.create(
            client=cotizacion.client,
            user=request.user,
            date=timezone.now(),
            valid_until=timezone.now() + timezone.timedelta(days=30),
            payment_method=cotizacion.payment_method,
            total=cotizacion.total_amount_amount_amount,
            # Si tienes campo sucursal/branch en Invoice, agrégalo aquí:
            # branch=cotizacion.branch 
        )

        # B. Mover los Detalles y Descontar Inventario
        detalles_cotizacion = QuotationDetail.objects.filter(quotation=cotizacion)
        
        for item in detalles_cotizacion:
            # 1. Crear detalle de factura
            InvoiceDetail.objects.create(
                invoice=factura,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal
            )

            # 2. DESCONTAR INVENTARIO (La parte crítica)
            producto = item.product
            # Restamos la cantidad
            producto.stock -= item.quantity 
            producto.save()

        # C. Actualizar estado de la Cotización
        cotizacion.status = 'BILLED'
        cotizacion.save()

    messages.success(request, f"Factura #{factura.id} creada exitosamente y stock actualizado.")
    
    # Redirigir a la lista de cotizaciones (o a la nueva factura si tienes esa vista)
    return redirect('quotation_list')

# 1. LISTA DE USUARIOS (DASHBOARD RRHH)
@login_required
def user_list(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('home')

    # Ahora 'User' se refiere a tu modelo 'accounts.User'
    users = User.objects.all() 
    return render(request, 'core/config/user_list.html', {'users': users})

@login_required
def user_create(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Intentamos guardar la sucursal si tu modelo lo permite
            branch = form.cleaned_data.get('branch')
            if branch:
                # OJO: Si tu usuario personalizado YA tiene campo 'branch', úsalo directo:
                # user.branch = branch
                # user.save()
                
                # Si usas perfil aparte:
                try:
                    profile, created = UserProfile.objects.get_or_create(user=user)
                    profile.branch = branch
                    profile.save()
                except:
                    pass # Evitamos errores si la estructura es diferente

            messages.success(request, f"Usuario {user.username} creado exitosamente.")
            return redirect('user_list')
    else:
        form = CustomUserForm()

    return render(request, 'core/config/user_form.html', {'form': form})

@login_required
def control_panel(request):
    # 1. Seguridad: Solo Staff/Admin puede ver esto
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido al Panel de Control.")
        return redirect('home')

    # 2. Recopilar Estadísticas Reales
    context = {
        # Contadores (Tarjetas de arriba)
        'total_empresas': CompanyProfile.objects.count() if hasattr(CompanyProfile, 'objects') else 1,
        'total_usuarios': User.objects.count(),
        'total_gastos': Quotation.objects.count(), # Usamos Cotizaciones como "Registros Globales" por ahora
        
        # Listas (Tablas de abajo)
        'empresas_list': CompanyProfile.objects.all() if hasattr(CompanyProfile, 'objects') else [],
        'usuarios_recientes': User.objects.order_by('-date_joined')[:5], # Los últimos 5 usuarios
    }

    return render(request, 'core/config/control_panel.html', context)

from .forms import CompanyForm # Importar el form nuevo

# LISTAR EMPRESAS
@login_required
def company_list(request):
    if not request.user.is_staff:
        return redirect('home')
    empresas = CompanyProfile.objects.all()
    return render(request, 'core/config/company_list.html', {'empresas': empresas})

# CREAR / EDITAR EMPRESA
@login_required
def company_create(request):
    if not request.user.is_staff:
        return redirect('home')

    if request.method == 'POST':
        # OJO: request.FILES es necesario para subir el LOGO
        form = CompanyForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            messages.success(request, "Empresa guardada exitosamente.")
            return redirect('company_list')
    else:
        form = CompanyForm()

    return render(request, 'core/config/company_form.html', {'form': form})

from .models import Expense, Vehicle
from .forms import ExpenseForm, VehicleForm
from decimal import Decimal

# --- GASTOS ---
@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.user = request.user
            
            # --- PROTECCIÓN DE DATOS: RE-CÁLCULO EN SERVIDOR ---
            # Convertimos a Decimal para precisión monetaria (evita errores de centavos)
            total = Decimal(str(gasto.total_amount_amount_amount_amount))
            idp = Decimal(str(gasto.idp_amount)) if gasto.idp_amount else Decimal('0.00')
            
            # 1. Validar Tipo de Gasto (Combustible vs Normal)
            if gasto.is_fuel:
                # Fórmula: (Total - IDP) / 1.12
                monto_sujeto_iva = total - idp
                gasto.base_amount = monto_sujeto_iva / Decimal('1.12')
                gasto.vat_amount = monto_sujeto_iva - gasto.base_amount
            else:
                # Fórmula: Total / 1.12
                gasto.idp_amount = Decimal('0.00') # Forzamos 0 si no es combustible
                gasto.base_amount = total / Decimal('1.12')
                gasto.vat_amount = total - gasto.base_amount
            
            # 2. IA de Texto (Opcional: Detecta si olvidaron marcar el switch)
            texto = (gasto.description + " " + gasto.provider).lower()
            if 'gasolina' in texto or 'diesel' in texto or 'combustible' in texto:
                if not gasto.is_fuel:
                    # Podríamos auto-corregirlo o solo avisar. 
                    # Por ahora, confiamos en lo que mandó el form validado arriba.
                    pass 

            gasto.save()
            messages.success(request, f"Gasto de Q{total} registrado. Partida contable generada correctamente.")
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    
    return render(request, 'core/expenses/expense_form.html', {'form': form})

@login_required
def expense_list(request):
    gastos = Expense.objects.filter(user=request.user).order_by('-date')
    return render(request, 'templates/core/gasto_manual.html', {'gastos': gastos})

# --- VEHÍCULOS ---
@login_required
def vehicle_list(request):
    vehiculos = Vehicle.objects.all()
    # Si quieres un modal para crear rápido, pasamos el form aquí
    form = VehicleForm()
    
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehículo agregado.")
            return redirect('vehicle_list')

    return render(request, 'core/expenses/vehicle_list.html', {'vehiculos': vehiculos, 'form': form})

# Vista Rápida para Pilotos (Solo Foto)
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
    return render(request, 'core/expenses/pilot_upload.html', {'vehiculos': vehiculos})

# 1. BANDEJA DE ENTRADA (Solo muestra lo PENDIENTE)
@login_required
def expense_pending_list(request):
    # Filtramos solo los que están en estatus 'PENDING'
    pendientes = Expense.objects.filter(status='PENDING').order_by('-created_at')
    return render(request, 'core/expenses/expense_pending_list.html', {'pendientes': pendientes})

# 2. VISTA DE APROBACIÓN (El Contador llena los datos)
@login_required
def expense_approve(request, pk):
    # Obtenemos el gasto pendiente
    gasto = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=gasto)
        if form.is_valid():
            gasto_final = form.save(commit=False)
            
            # 1. Cambiamos estado a APROBADO
            gasto_final.status = 'APPROVED'
            
            # 2. Convertimos a Decimales y Calculamos
            total = Decimal(str(gasto_final.total_amount))
            idp = Decimal(str(gasto_final.idp_amount)) if gasto_final.idp_amount else Decimal('0.00')
            
            if gasto_final.is_fuel:
                monto_sujeto = total - idp
                gasto_final.base_amount = monto_sujeto / Decimal('1.12')
                gasto_final.vat_amount = monto_sujeto - gasto_final.base_amount
            else:
                gasto_final.idp_amount = Decimal('0.00')
                gasto_final.base_amount = total / Decimal('1.12')
                gasto_final.vat_amount = total - gasto_final.base_amount
            
            gasto_final.save()
            
            messages.success(request, f"✅ Gasto aprobado y contabilizado (ID #{gasto_final.id})")
            return redirect('expense_pending_list')
    else:
        # Cargamos el formulario
        form = ExpenseForm(instance=gasto)
    
    # --- CORRECCIÓN AQUÍ: Definimos la variable que faltaba ---
    tarjetas = CreditCard.objects.all() 
    
    return render(request, 'core/expenses/expense_approve.html', {
        'form': form, 
        'gasto': gasto, 
        'tarjetas': tarjetas # Ahora sí existe
    })

@login_required
def accounting_dashboard(request):
    """ Panel Principal de Contabilidad """
    # Gastos aprobados que AÚN NO tienen partida contable
    gastos_por_contabilizar = Expense.objects.filter(status='APPROVED', journal_entry__isnull=True)
    
    return render(request, 'core/accounting/dashboard.html', {
        'gastos_pendientes': gastos_por_contabilizar
    })

@login_required
def create_entry_from_expense(request, expense_id):
    """ Convierte un Gasto en Partida Contable """
    gasto = get_object_or_404(Expense, pk=expense_id)
    cuentas = Account.objects.filter(is_group=False) # Solo cuentas de movimiento
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 1. Crear Cabecera de Partida
                partida = JournalEntry.objects.create(
                    date=gasto.date,
                    description=f"Reg. Gasto Prov: {gasto.provider} - {gasto.description}",
                    reference=f"Gasto ID {gasto.id}",
                    expense=gasto,
                    is_posted=True
                )
                
                # 2. Obtener cuentas del formulario (El contador las selecciona)
                cta_debe_id = request.POST.get('account_debit') # Ej: Combustibles
                cta_haber_id = request.POST.get('account_credit') # Ej: Bancos / Caja
                cta_iva_id = request.POST.get('account_iva') # Ej: IVA Crédito Fiscal
                
                # 3. Crear DEBE (Gasto Base)
                JournalItem.objects.create(
                    entry=partida,
                    account_id=cta_debe_id,
                    debit=gasto.base_amount,
                    credit=0
                )
                
                # 4. Crear DEBE (IVA)
                if gasto.vat_amount > 0 and cta_iva_id:
                    JournalItem.objects.create(
                        entry=partida,
                        account_id=cta_iva_id,
                        debit=gasto.vat_amount,
                        credit=0
                    )
                
                # 5. Crear DEBE (IDP - Si aplica)
                if gasto.idp_amount > 0:
                     # Asumimos que IDP va a la misma cuenta de gasto o una especifica
                     # Por simplicidad lo sumamos al gasto base o creamos otro item si seleccionan cuenta
                     pass 

                # 6. Crear HABER (Salida de dinero: Banco/Caja)
                JournalItem.objects.create(
                    entry=partida,
                    account_id=cta_haber_id,
                    debit=0,
                    credit=gasto.total_amount_amount_amount_amount
                )
                
                messages.success(request, f"✅ Partida #{partida.id} generada correctamente.")
                return redirect('accounting_dashboard')
                
        except Exception as e:
            messages.error(request, f"Error generando partida: {e}")

    return render(request, 'core/accounting/entry_form.html', {
        'gasto': gasto,
        'cuentas': cuentas
    })

@login_required
def create_opening_entry(request):
    """ Crear Partida de Apertura (Partida #1) """
    if request.method == 'POST':
        # Lógica para guardar manualmente Debe y Haber de varias cuentas
        # (Esto requiere un formulario dinámico con JavaScript para agregar filas)
        pass 
    
    return render(request, 'core/accounting/opening_entry.html')