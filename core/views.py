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
    Gasto, Income, JournalEntry, JournalItem,
    
    # Otros
    Fleet, InventoryMovement, Loan, Payroll, PayrollDetail
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
    MobileExpenseForm, 
    GastoForm,
    BankAccountForm, 
    BankTransactionForm,
    TransferForm,
    IncomeForm,
    SupplierForm,
    SupplierPaymentForm,
    EmployeeForm, 
    LoanForm
)
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
    # 1. Filtramos empresas (GET)
    if request.user.is_superuser:
        companies = CompanyProfile.objects.all()
    else:
        companies = CompanyProfile.objects.filter(allowed_users=request.user)

    # 2. Procesamos selección (POST)
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        if company_id:
            company = get_object_or_404(CompanyProfile, id=company_id)
            
            # Seguridad
            if not request.user.is_superuser and request.user not in company.allowed_users.all():
                messages.error(request, "Acceso Denegado.")
                return redirect('select_company')

            # Guardar en sesión
            request.session['company_id'] = company.id
            request.session['company_name'] = company.name
            if company.logo:
                request.session['company_logo'] = company.logo.url
            
            messages.success(request, f"Bienvenido a {company.name}")
            return redirect('home')

# 👇👇👇 ESTA LÍNEA ES LA CLAVE - TIENE QUE ESTAR PEGADA A LA IZQUIERDA 👇👇👇
        return render(request, 'core/seleccion_nueva.html', {'companies': companies})

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
    
    queryset = Gasto.objects.filter(company=company).order_by('-fecha')
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
    expenses = Gasto.objects.filter(company=company).order_by('-fecha')
    return render(request, 'core/expense_list.html', {'expenses': expenses})

@login_required
def mobile_expense(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = MobileExpenseForm(request.POST, request.FILES)
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
    # 1. Validación de Seguridad (Empresa)
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company_obj = get_object_or_404(Company, id=company_id)

    # Contexto Inicial del Formulario
    contexto_form = {
        'fecha': date.today(),
        'proveedor': '',
        'descripcion': '',
        'total': '',
        'monto_idp': 0,
        'base_imponible': '',
        'iva': '',
        'es_combustible': False
    }

    # --- FUNCIÓN HELPER: LIMPIAR DINERO ---
    # Esto evita errores si la IA manda "Q300" o "1,200.00"
    def limpiar_monto(valor):
        if not valor: return 0.0
        s = str(valor).upper().replace('Q', '').replace(',', '').replace(' ', '')
        try:
            return float(s)
        except ValueError:
            return 0.0
    # --------------------------------------

    if request.method == 'POST':
        
        # =================================================
        # RAMA A: SMART SCANNER (IA)
        # =================================================
        if 'analizar_ia' in request.POST and request.FILES.get('imagen_factura'):
            imagen = request.FILES['imagen_factura']
            # Llamamos al cerebro (Gemini)
            resultado = analizar_documento_ia(imagen, contexto='GASTO')
            
            if resultado['exito']:
                datos = resultado['datos']
                messages.success(request, f"IA Detectada: {resultado['tipo_detectado']}. Datos extraídos.")
                
                # 1. Limpiamos los datos crudos
                total_factura = limpiar_monto(datos.get('total'))
                monto_idp = limpiar_monto(datos.get('idp'))
                es_fuel = datos.get('es_combustible', False)
                
                # 2. Cálculos Contables Guatemala
                # Al total le quitamos el IDP (El IDP no paga IVA)
                monto_sujeto_iva = total_factura - monto_idp
                
                # Base = Monto / 1.12
                base_imponible = round(monto_sujeto_iva / 1.12, 2)
                
                # IVA = Base * 0.12
                iva_calculado = round(base_imponible * 0.12, 2)

                # 3. Actualizamos el formulario para que el usuario revise
                contexto_form.update({
                    'proveedor': datos.get('proveedor', ''),
                    'total': total_factura,
                    'descripcion': f"Combustible ({datos.get('galones', '?')} gal) - Fact: {datos.get('serie', '')}" if es_fuel else f"Gasto detectado: {datos.get('serie', '')}",
                    'es_combustible': es_fuel,
                    'monto_idp': monto_idp,
                    'base_imponible': base_imponible,
                    'iva': iva_calculado,
                    'fecha': datos.get('fecha', date.today())
                })
            else:
                error_real = resultado.get('mensaje', 'Error desconocido')
                messages.error(request, f"Fallo IA: {error_real}")

        # =================================================
        # RAMA B: GUARDAR GASTO Y CONTABILIZAR
        # =================================================
        else:
            try:
                # 1. Recopilar datos limpios del formulario
                monto_total = float(request.POST.get('monto_total', 0))
                monto_idp = float(request.POST.get('monto_idp', 0))
                monto_base = float(request.POST.get('base_imponible', 0))
                monto_iva = float(request.POST.get('impuesto_iva', 0))
                
                # 2. Crear Objeto Gasto
                gasto = Gasto()
                gasto.company = company_obj
                gasto.fecha = request.POST.get('fecha')
                gasto.proveedor = request.POST.get('nombre_emisor')
                gasto.descripcion = request.POST.get('concepto')
                gasto.total = monto_total
                gasto.amount_untaxed = monto_base
                gasto.iva = monto_iva
                gasto.categoria = "Combustible" if request.POST.get('es_combustible') else "General"
                
                # Asignación Vehículo
                vehicle_id = request.POST.get('vehicle_id')
                if vehicle_id: gasto.vehicle = Fleet.objects.get(id=vehicle_id)

                # Asignación Banco (Descontar Saldo)
                bank_id = request.POST.get('bank_id')
                if bank_id:
                    cuenta = BankAccount.objects.get(id=bank_id)
                    if cuenta.current_balance >= monto_total:
                        cuenta.current_balance -= sum([monto_total]) # Truco decimal
                        cuenta.current_balance = round(cuenta.current_balance, 2)
                        cuenta.save()
                        gasto.bank_account = cuenta
                    else:
                        raise Exception("Fondos insuficientes en la cuenta seleccionada.")

                # Imagen
                if 'imagen_factura' in request.FILES:
                    gasto.imagen = request.FILES['imagen_factura']

                gasto.save()

                # --------------------------------------------------------
                # 3. AUTOMATIZACIÓN CONTABLE (CREAR PARTIDA)
                # --------------------------------------------------------
                try:
                    # A. Cabecera
                    partida = JournalEntry.objects.create(
                        date=gasto.fecha,
                        description=f"Compra: {gasto.proveedor} - {gasto.descripcion}",
                        reference=f"Gasto #{gasto.id}"
                    )
                    
                    # B. Detalle (DEBE)
                    if request.POST.get('es_combustible'):
                        # Cuenta Gasto Combustible
                        JournalItem.objects.create(entry=partida, account_name="Combustibles y Lubricantes", debit=monto_base, credit=0)
                        # Cuenta IDP
                        if monto_idp > 0:
                            JournalItem.objects.create(entry=partida, account_name="Impuesto IDP", debit=monto_idp, credit=0)
                    else:
                        # Cuenta Gasto General
                        JournalItem.objects.create(entry=partida, account_name="Gastos Generales", debit=monto_base, credit=0)

                    # Cuenta IVA (Común)
                    if monto_iva > 0:
                        JournalItem.objects.create(entry=partida, account_name="IVA por Cobrar", debit=monto_iva, credit=0)

                    # C. Detalle (HABER) - Salida de dinero
                    cuenta_salida = "Caja y Bancos" if bank_id else "Cuentas por Pagar"
                    JournalItem.objects.create(entry=partida, account_name=cuenta_salida, debit=0, credit=monto_total)

                except Exception as e_contable:
                    print(f"Error generando partida contable: {e_contable}")
                # --------------------------------------------------------

                messages.success(request, "Gasto registrado y contabilizado correctamente.")
                return redirect('expense_list') # O 'dashboard_gastos' según su url

            except Exception as e:
                messages.error(request, f"Error al guardar: {str(e)}")
                # Mantenemos los datos en pantalla para no borrar lo que escribió el usuario
                contexto_form.update(request.POST.dict())

    # GET Request: Cargar listas para selects
    vehiculos = Fleet.objects.filter(company_id=company_id) 
    bancos = BankAccount.objects.filter(company_id=company_id)
    
    full_context = {
        'vehiculos': vehiculos,
        'bancos': bancos
    }
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
    Une 3 fuentes de datos en un solo flujo contable:
    1. Gastos (Salidas)
    2. Ingresos/Ventas (Entradas)
    3. Movimientos Bancarios (Depósitos/Retiros/Transferencias)
    """
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    # 1. Traemos los Gastos
    gastos = Gasto.objects.filter(company=company).order_by('-fecha')
    
    # 2. Traemos los Ingresos
    ingresos = Income.objects.filter(company=company).order_by('-date')
    
    # 3. Traemos los Movimientos Bancarios directos
    bancos = BankMovement.objects.filter(account__company=company).order_by('-date')

    # Unificamos las listas (Chain)
    for g in gastos: g.fecha_unificada = g.fecha
    for i in ingresos: i.fecha_unificada = i.date
    for b in bancos: b.fecha_unificada = b.date

    # Ordenamos todo por fecha (lo más reciente arriba)
    movimientos = sorted(
        chain(gastos, ingresos, bancos),
        key=attrgetter('fecha_unificada'),
        reverse=True
    )

    t_gastos = gastos.aggregate(Sum('total'))['total__sum'] or 0
    t_ingresos = ingresos.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'accounting/libro_diario.html', {
        'movimientos': movimientos,
        't_gastos': t_gastos,
        't_ingresos': t_ingresos,
        'balance': t_ingresos - t_gastos
    })

@login_required
def libro_mayor(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    cuentas = Account.objects.filter(company=company)
    resumen_gastos = Gasto.objects.filter(company=company).values('categoria').annotate(
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
    total_gastos = Gasto.objects.filter(company_id=company_id).aggregate(Sum('total'))['total__sum'] or 0
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
        Gasto.objects.create(
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
    expenses = Gasto.objects.filter(company=company).exclude(placa_vehiculo__isnull=True)
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
        'total_gastos': Gasto.objects.count(),
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
    gastos = Gasto.objects.filter(company_id=request.session.get('company_id')).order_by('-fecha')
    return render(request, 'core/expense_list.html', {'gastos': gastos})

# --- VISTAS DE CLIENTES ---

@login_required
def client_list(request):
    """Muestra el listado de clientes"""
    clientes = Client.objects.filter(is_active=True).order_by('name')
    return render(request, 'core/sales/client_list.html', {'clientes': clientes})

@login_required
def client_create(request):
    """Formulario para crear cliente"""
    
    if request.method == 'POST':
        # Llamamos al formulario que definimos en forms.py
        form = ClientForm(request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente registrado exitosamente.")
            return redirect('client_list') # Asegúrese de tener esta URL o cambie a 'home'
        else:
            messages.error(request, "Error al registrar cliente. Verifique los datos.")
    else:
        form = ClientForm()
    
    return render(request, 'core/sales/client_form.html', {'form': form})

from datetime import timedelta

# --- 1. LISTA DE COTIZACIONES ---
@login_required
def quotation_list(request):
    quotations = Quotation.objects.all().order_by('-id')
    return render(request, 'core/sales/quotation_list.html', {'quotations': quotations})

@login_required
def quotation_create(request):
    """Crear Nueva Cotización (Con lógica Maestro-Detalle)"""
    if request.method == 'POST':
        try:
            # 1. Guardar Encabezado
            cliente_id = request.POST.get('client')
            fecha = request.POST.get('date')
            validez = request.POST.get('valid_until')
            total_cotizacion = request.POST.get('total_general')
            
            cotizacion = Quotation.objects.create(
                client_id=cliente_id,
                date=fecha,
                valid_until=validez,
                total=total_cotizacion,
                status='DRAFT'
            )
            
            # 2. Guardar Productos (Vienen en listas)
            productos = request.POST.getlist('product_id[]')
            cantidades = request.POST.getlist('qty[]')
            precios = request.POST.getlist('price[]')
            subtotales = request.POST.getlist('subtotal[]')
            
            for i in range(len(productos)):
                QuotationDetail.objects.create(
                    quotation=cotizacion,
                    product_id=productos[i],
                    quantity=cantidades[i],
                    unit_price=precios[i],
                    subtotal=subtotales[i]
                )
                
            messages.success(request, f"Cotización #{cotizacion.id} creada exitosamente.")
            return redirect('quotation_list')
            
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")

    # GET: Cargar datos para el formulario
    clientes = Client.objects.filter(is_active=True)
    productos = Product.objects.filter(is_active=True)
    fecha_hoy = date.today()
    fecha_vencimiento = date.today() + timedelta(days=15) # 15 días de vigencia por defecto
    
    return render(request, 'core/sales/quotation_form.html', {
        'clientes': clientes,
        'productos': productos,
        'fecha_hoy': fecha_hoy,
        'validez': fecha_vencimiento
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
        total=cotizacion.total,
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
                quotation.total = total_general
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
                purchase.total = total_compra
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
        total=quotation.total,
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
            cuenta_destino.balance += sale.total
            cuenta_destino.save()
            BankMovement.objects.create(
                account=cuenta_destino,
                movement_type='IN',
                category='Venta',
                amount=sale.total,
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
def quotation_print(request, quote_id):
    quote = get_object_or_404(Quotation, id=quote_id)
    # Buscamos la primera empresa configurada (o la activa si tuviéramos lógica multi-empresa)
    company = CompanyProfile.objects.first()
    
    return render(request, 'core/sales/quotation_print.html', {
        'quote': quote,
        'company': company, # <--- ¡Aquí va el logo dinámico!
        'details': quote.details.all()
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