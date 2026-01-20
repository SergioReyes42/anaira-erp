import csv
import os
import json
from datetime import datetime
from itertools import chain
from operator import attrgetter

# --- IMPORTS DE DJANGO ---
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Q, Count
from django.conf import settings
from .models import BankAccount
from .forms import BankTransactionForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from .models import Company, Fleet, BankAccount, Gasto
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
def select_company(request):
    user_companies = UserRoleCompany.objects.filter(user=request.user).select_related('company')
    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        try:
            access = user_companies.get(company_id=company_id)
            company = access.company
            request.session['company_id'] = company.id
            request.session['company_name'] = company.name
            return redirect('home')
        except UserRoleCompany.DoesNotExist:
            pass
    return render(request, 'core/seleccion_nueva.html', {'companies': [uc.company for uc in user_companies]})

@login_required
def home(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.get(id=company_id)
    return render(request, 'core/home.html', {'company': company})

@login_required
def admin_control_panel(request): 
    return redirect('dashboard_gastos')

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
    # Obtener empresa actual
    company_name = request.session.get('company_name')
    if request.method == 'POST':
        if not company_name:
            return redirect('select_company')
    
    # Usamos get_object_or_404 para evitar errores si no encuentra la empresa
    company_obj = get_object_or_404(Company, name=company_name)
    try:
            # 1. Recopilar datos del formulario HTML
            gasto = Gasto()
            gasto.fecha = request.POST.get('fecha')
            gasto.proveedor = request.POST.get('nombre_emisor') # O nit_emisor
            gasto.descripcion = request.POST.get('concepto')
            gasto.total = request.POST.get('monto_total')
            
            # Datos calculados por el JS (Hidden inputs)
            gasto.amount_untaxed = request.POST.get('base_imponible') or 0
            gasto.iva = request.POST.get('impuesto_iva') or 0
            gasto.categoria = "Combustible" if request.POST.get('es_combustible') else "General"
            
            # 2. Asignar Vehículo (Si seleccionó uno)
            vehicle_id = request.POST.get('vehicle_id')
            if vehicle_id:
                gasto.vehicle = Fleet.objects.get(id=vehicle_id)

            # 3. Asignar Banco y Descontar Dinero
            bank_id = request.POST.get('bank_id')
            if bank_id:
                cuenta = BankAccount.objects.get(id=bank_id)
                # Validación de fondos
                if cuenta.current_balance >= float(gasto.total):
                    cuenta.current_balance -= float(gasto.total)
                    cuenta.save()
                    gasto.bank_account = cuenta
                else:
                    messages.error(request, "Fondos insuficientes en el banco seleccionado.")
                    return redirect('gasto_manual')

            # Guardar imagen si hay
            if 'imagen_factura' in request.FILES:
                gasto.imagen = request.FILES['imagen_factura']

            gasto.save()
            messages.success(request, "Gasto registrado correctamente.")
            return redirect('expense_list')

    except Exception as e:
            messages.error(request, f"Error al guardar: {e}")

    # Enviar listas al HTML
    vehiculos = Fleet.objects.filter(company=Company)
    bancos = BankAccount.objects.filter(company=Company)
    
    return render(request, 'core/gasto_manual.html', {
        'vehiculos': vehiculos,
        'bancos': bancos,
        'today': datetime.date.today()
    })

@csrf_exempt
def api_ocr_process(request):
    if request.method == 'POST':
        return JsonResponse({'status': 'success', 'message': 'OCR recibido (Simulado)'})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})

# ==========================================
# 3. BANCOS, INGRESOS Y PROVEEDORES
# ==========================================

@login_required
def bank_list(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank = form.save(commit=False)
            bank.company_id = company_id
            bank.save()
            return redirect('bank_list')
            
    cuentas = BankAccount.objects.filter(company_id=company_id)
    form = BankAccountForm()
    return render(request, 'core/bank_list.html', {'cuentas': cuentas, 'form': form})

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
def bank_transaction_create(request):
    # 1. Obtener la empresa actual
    company_name = request.session.get('company_name')
    if not company_name:
        return redirect('select_company')
    
    company = get_object_or_404(Company, name=company_name)

    # 2. Manejar el tipo de movimiento (Entrada o Salida) desde la URL
    # Si la URL es /bancos/transaccion/?type=OUT es un Cheque/Retiro
    initial_type = request.GET.get('type', 'OUT') 

    if request.method == 'POST':
        # OJO AQUÍ: Pasamos 'company' PRIMERO, luego 'request.POST'
        form = BankTransactionForm(company, request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            
            # Asignar tipo automático si el usuario no lo eligió
            if not transaction.movement_type:
                 transaction.movement_type = initial_type
                 
            transaction.save()
            
            # Actualizar saldo de la cuenta
            cuenta = transaction.account
            if transaction.movement_type == 'IN':
                cuenta.current_balance += transaction.amount
            else: # OUT
                cuenta.current_balance -= transaction.amount
            cuenta.save()
            
            messages.success(request, f"Transacción de {transaction.amount} registrada correctamente.")
            return redirect('bank_list')
    else:
        # GET: Pasamos 'company' y prellenamos el tipo de movimiento
        form = BankTransactionForm(company, initial={'movement_type': initial_type})

    return render(request, 'core/bank_transaction_form.html', {
        'form': form,
        'company': company,
        'tipo': initial_type
    })

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
    products = Product.objects.filter(company_id=company_id, is_active=True)
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

    products = Product.objects.filter(company=company, is_active=True)
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
    
    employees = Employee.objects.filter(company=company, is_active=True)
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