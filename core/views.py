import csv
import os
import json
from datetime import datetime
from itertools import chain
from operator import attrgetter
from .ai_brain import analizar_documento_ia
from .models import Client
from .models import Product
from .models import Quotation, QuotationDetail, CompanyProfile, Provider, Purchase, PurchaseDetail


# --- IMPORTS DE DJANGO ---
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth import get_user_model # ✅ ESTO ES LO CORRECTO
from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Count
from django.conf import settings
from .models import BankAccount
from .forms import BankTransactionForm
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from .models import Company, Fleet, BankAccount, Gasto, BankTransaction, JournalEntry, JournalItem
from .ai_brain import analizar_texto_bancario, analizar_documento_ia
# --- MODELOS ---
from .models import (
    UserRoleCompany, Branch, Warehouse, Account,
    # Finanzas
    Gasto, Income, BankAccount, BankMovement, BusinessPartner,
    # Inventario
    Product, InventoryMovement,
    # RRHH
    Employee, Loan, Payroll, PayrollDetail
)

# --- FORMULARIOS ---
from .forms import (
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
    LoanForm,
    ProductForm
)

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
def select_company(request): # <--- AQUÍ ESTABA EL ERROR: FALTABA ESTA LÍNEA
    """
    Vista para seleccionar la empresa activa y guardar sus datos (Logo, NIT, Nombre) en la sesión.
    """
    # 1. Obtener listado de empresas
    companies = Company.objects.all()

    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        
        # 2. Obtener la empresa seleccionada de la Base de Datos
        company = get_object_or_404(Company, id=company_id)
        
        # 3. GUARDAR DATOS EN LA SESIÓN (Esto actualiza el Dashboard)
        request.session['company_id'] = company.id
        
        # Guardar Nombre
        request.session['company_name'] = getattr(company, 'name', getattr(company, 'nombre', 'Empresa'))
        
        # Guardar NIT
        if hasattr(company, 'nit') and company.nit:
            request.session['company_nit'] = company.nit
        else:
            request.session['company_nit'] = None

        # --- GUARDAR EL LOGO ---
        if hasattr(company, 'logo') and company.logo:
            request.session['company_logo'] = company.logo.url
        else:
            request.session['company_logo'] = None 
            
        return redirect('home')

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
class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['bank_name', 'account_number', 'currency', 'balance']
        widgets = {
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Banco Industrial'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GTQ'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

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
class BankTransactionForm(forms.ModelForm):
    class Meta:
        model = BankTransaction
        fields = ['account', 'date', 'movement_type', 'amount', 'description', 'reference', 'evidence']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }

@login_required
def bank_transaction_create(request):
    tipo_operacion = request.GET.get('type', 'OUT') 
    
    if request.method == 'POST':
        form = BankTransactionForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    nueva_transaccion = form.save(commit=False)
                    # NO necesitamos asignar manualmente, el form ya lo trae del HTML
                    
                    cuenta = nueva_transaccion.account
                    monto = nueva_transaccion.amount 
                    
                    # 1. AQUÍ EL CAMBIO: Usamos .movement_type
                    if nueva_transaccion.movement_type == 'IN':
                        cuenta.balance += monto
                        mensaje = f"Depósito de Q{monto} registrado exitosamente."
                    else:
                        if cuenta.balance < monto:
                            messages.error(request, "¡Fondos Insuficientes!")
                            # Pasamos el tipo para que no se pierda si falla
                            return render(request, 'core/treasury/transaction_form.html', {'form': form, 'tipo': tipo_operacion})
                        
                        cuenta.balance -= monto
                        mensaje = f"Débito/Cheque de Q{monto} registrado exitosamente."
                    
                    cuenta.save()
                    nueva_transaccion.save()
                    messages.success(request, mensaje)
                    return redirect('bank_list')
                    
            except Exception as e:
                messages.error(request, f"Error al procesar: {str(e)}")
    else:
        # 2. AQUÍ TAMBIÉN: Pre-llenamos 'movement_type'
        form = BankTransactionForm(initial={'movement_type': tipo_operacion})

    return render(request, 'core/treasury/transaction_form.html', {
        'form': form, 
        'tipo': tipo_operacion
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
    company_id = request.session.get('company_id')
    company = get_object_or_404(Company, id=company_id)
    
    initial_code = request.GET.get('code', '')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.company = company
            prod.save()
            messages.success(request, "Producto creado exitosamente.")
            return redirect('smart_hub')
    else:
        form = ProductForm(initial={'barcode': initial_code, 'sku': initial_code})

    return render(request, 'inventory/product_form.html', {'form': form})

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
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'product_type', 'price', 'cost', 'stock']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control'}),
        }

@login_required
def inventory_list(request):
    productos = Product.objects.filter(is_active=True).order_by('code')
    
    if request.method == 'POST':
        form = ProductForm(request.POST) # Usa el de forms.py
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado.")
            return redirect('inventory_list')
    else:
        form = ProductForm()

    return render(request, 'core/inventory/product_list.html', {
        'productos': productos,
        'form': form
    })

# === VISTA DE LISTA DE GASTOS (Si no la tenía) ===
@login_required
def expense_list(request):
    # Si ya tenía una vista de lista de gastos, ignore esto.
    # Si no, esto evita el error en el menú de compras.
    gastos = Gasto.objects.filter(company_id=request.session.get('company_id')).order_by('-fecha')
    return render(request, 'core/expense_list.html', {'gastos': gastos})

# FORMULARIO DE CLIENTE
class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nit', 'name', 'address', 'phone', 'email', 'contact_name', 'credit_days', 'credit_limit']
        widgets = {
            'nit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CF o NIT'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
        }
# --- VISTAS DE CLIENTES ---

@login_required
def client_list(request):
    """Muestra el listado de clientes"""
    clientes = Client.objects.filter(is_active=True).order_by('name')
    return render(request, 'core/sales/client_list.html', {'clientes': clientes})

@login_required
def client_create(request):
    """Formulario para crear cliente"""
    # Definimos el formulario aquí mismo para ir rápido
    class ClientForm(forms.ModelForm):
        class Meta:
            model = Client
            fields = ['nit', 'name', 'address', 'phone', 'email', 'contact_name', 'credit_days', 'credit_limit']
            widgets = {
                'nit': forms.TextInput(attrs={'class': 'form-control'}),
                'name': forms.TextInput(attrs={'class': 'form-control'}),
                'address': forms.TextInput(attrs={'class': 'form-control'}),
                'phone': forms.TextInput(attrs={'class': 'form-control'}),
                'email': forms.EmailInput(attrs={'class': 'form-control'}),
                'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
                'credit_days': forms.NumberInput(attrs={'class': 'form-control'}),
                'credit_limit': forms.NumberInput(attrs={'class': 'form-control'}),
            }

    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente registrado exitosamente.")
            return redirect('client_list')
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
def create_quotation(request):
    if request.method == 'POST':
        client_id = request.POST.get('client')
        valid_until = request.POST.get('valid_until')
        
        # 1. Crear la Cabecera
        cliente = Client.objects.get(id=client_id)
        cotizacion = Quotation.objects.create(
            client=cliente,
            valid_until=valid_until,
            total=0 # Iniciamos en 0, luego actualizamos
        )
        
        # 2. Guardar los Detalles
        products = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        
        total_general = 0
        
        for i in range(len(products)):
            if products[i] and quantities[i]:
                producto = Product.objects.get(id=products[i])
                cantidad = int(quantities[i])
                precio = producto.price
                
                # --- CORRECCIÓN AQUÍ ---
                # Calculamos el subtotal ANTES de guardar para evitar el error "null value"
                subtotal_linea = precio * cantidad
                
                QuotationDetail.objects.create(
                    quotation=cotizacion,
                    product=producto,
                    quantity=cantidad,
                    unit_price=precio,
                    subtotal=subtotal_linea  # <--- ¡ESTO FALTABA!
                )
                
                total_general += subtotal_linea
        
        # 3. Actualizar el total final de la cotización
        cotizacion.total = total_general
        cotizacion.save()
        
        messages.success(request, 'Cotización creada exitosamente')
        return redirect('quotation_list')

    else:
        # Modo GET: Mostrar el formulario
        clients = Client.objects.all()
        products = Product.objects.all()
        return render(request, 'core/sales/quotation_form.html', {
            'clients': clients,
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
    # Mostramos las compras ordenadas por fecha (la más reciente arriba)
    purchases = Purchase.objects.all().order_by('-date')
    return render(request, 'core/purchases/purchase_list.html', {'purchases': purchases})

@login_required
def create_purchase(request):
    if request.method == 'POST':
        provider_id = request.POST.get('provider')
        reference = request.POST.get('reference')
        
        # 1. Crear Cabecera de Compra
        proveedor = Provider.objects.get(id=provider_id)
        nueva_compra = Purchase.objects.create(
            company=CompanyProfile.objects.first(), # Asignamos a la empresa principal
            provider=proveedor,
            reference=reference,
            total=0 # Se calcula abajo
        )
        
        # 2. Guardar Detalles
        products = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        costs = request.POST.getlist('costs[]') # Precio de Costo
        
        total_compra = 0
        
        for i in range(len(products)):
            if products[i] and quantities[i]:
                producto = Product.objects.get(id=products[i])
                cantidad = int(quantities[i])
                costo = float(costs[i])
                
                # Al crear esto, la "Señal" automática que hicimos antes 
                # aumentará el stock sola. No hay que programarlo aquí.
                PurchaseDetail.objects.create(
                    purchase=nueva_compra,
                    product=producto,
                    quantity=cantidad,
                    cost_price=costo
                )
                
                total_compra += (cantidad * costo)
        
        # 3. Actualizar Total
        nueva_compra.total = total_compra
        nueva_compra.save()
        
        messages.success(request, f'Compra #{nueva_compra.id} registrada y Stock actualizado.')
        return redirect('purchase_list')

    else:
        # Modo GET: Mostrar formulario
        providers = Provider.objects.all()
        products = Product.objects.all()
        return render(request, 'core/purchases/purchase_form.html', {
            'providers': providers,
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
from .forms import ProductForm # <--- Asegúrese de importar esto arriba

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado exitosamente.")
            return redirect('product_list')
    else:
        form = ProductForm()
    
    return render(request, 'core/inventory/product_form.html', {'form': form})