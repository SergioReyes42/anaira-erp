from django.db import transaction
import datetime
import decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction # <--- Importación vital
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.paginator import Paginator # Agrega esto arriba si no lo tienes
from .decorators import group_required  # <--- Importas el candado
from django.forms import modelformset_factory
from django.db.models import Prefetch
from .models import AccountingPeriod
from sales.models import SaleInvoice
from .forms import DepositForm
from .models import GastoOperativo, Vehiculo

# --- IMPORTACIÓN DE MODELOS ---
from .models import (
    Expense, 
    JournalEntry,
    Account,
    JournalEntryLine,
    JournalItem, 
    BankAccount, 
    BankTransaction, 
    Vehicle,
    CreditCard,
    AccountPayable
)
from .forms import BankAccountForm, BankTransactionForm, VehicleForm
from .utils import analyze_invoice_image

# ========================================================
# 1. HERRAMIENTAS DE INGRESO UNIFICADAS
# ========================================================

@login_required
@group_required('Pilotos', 'Contadora', 'Gerente', 'Administrador')
def pilot_upload(request):
    """VISTA PILOTOS/GERENTES: Carga rápida de ticket personal con auditoría antifraude"""
    
    if not request.user.current_company:
        messages.error(request, "⛔ Tu usuario no tiene una empresa asignada. Contacta al Administrador.")
        return redirect('core:home')

    vehiculos_del_usuario = request.user.vehiculos_asignados.filter(company=request.user.current_company)

    if vehiculos_del_usuario.exists():
        vehicles = vehiculos_del_usuario
    elif request.user.is_superuser or request.user.groups.filter(name__in=['Contadora', 'Administrador', 'Gerente']).exists():
        vehicles = Vehicle.objects.filter(company=request.user.current_company)
    else:
        vehicles = Vehicle.objects.none()

    if request.method == 'POST':
        receipt_image = request.FILES.get('receipt_image')
        pump_image = request.FILES.get('pump_image')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        vehicle_id = request.POST.get('vehicle')

        try:
            with transaction.atomic():
                # 🔥 AHORA SÍ: Solo le mandamos los datos que GastoOperativo realmente tiene
                GastoOperativo.objects.create(
                    user=request.user,
                    receipt_image=receipt_image,
                    pump_image=pump_image,
                    latitude=latitude,
                    longitude=longitude,
                    total_amount=0.00,  # El monto en cero como pediste
                    vehicle_id=vehicle_id if vehicle_id and vehicle_id.isdigit() else None, 
                    estado='Pendiente', 
                    date=timezone.now()
                )
                
            messages.success(request, "🚀 Gasto enviado. El equipo de Supervisión lo revisará.")
            return redirect('core:home')
            
        except Exception as e:
            messages.error(request, f"Error al guardar el gasto: {str(e)}")
            return redirect('accounting:pilot_upload')
            
    return render(request, 'accounting/pilot_upload.html', {'vehicles': vehicles})

# 3. La Aprobación de IA es solo para Contabilidad
@login_required
@group_required('Contadora') 
def smart_scanner(request):
    """VISTA CONTADOR: Escaneo masivo con IA, va a Pendientes"""
    if request.method == 'POST':
        image = request.FILES.get('documento')
        smart_input = request.POST.get('smart_input', '') 
        
        # 1. IA Analiza
        ai_data = analyze_invoice_image(image, smart_input)
        
        # 2. Cálculos Financieros Preliminares
        total = ai_data['total']
        idp = 0.00
        base = 0.00
        iva = 0.00

        if ai_data['is_fuel']:
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

        # 3. Guardar como pendiente con origen SCANNER
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
            
            status='PENDING',
            origin='SCANNER' # Marcamos que viene del scanner
        )
        
        messages.success(request, f"✅ Gasto escaneado enviado a pendientes. IA Detectó: {ai_data['account_type']}")
        return redirect('accounting:expense_pending_list')

    return render(request, 'accounting/smart_hub.html')


@login_required
def upload_expense_photo(request):
    return redirect('smart_scanner')

# ========================================================
# 2. FLUJO DE APROBACIÓN (CENTRO DE COMPRAS/GASTOS)
# ========================================================

@login_required
def expense_pending_list(request):
    """Bandeja de Entrada única para el contador"""
    expenses = Expense.objects.filter(
        company=request.user.current_company, 
        status='PENDING'
    ).order_by('-date')
    return render(request, 'accounting/expense_pending_list.html', {'expenses': expenses})


@login_required
def review_expense(request, pk):
    """El contador revisa, corrige lo de la IA o llena lo del piloto"""
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if request.method == 'POST':
        expense.provider_name = request.POST.get('provider_name')
        expense.provider_nit = request.POST.get('provider_nit')
        expense.invoice_number = request.POST.get('invoice_number')
        expense.description = request.POST.get('description')
        
        total = decimal.Decimal(request.POST.get('total_amount', 0))
        idp = decimal.Decimal(request.POST.get('tax_idp', 0))
        
        expense.total_amount = total
        expense.tax_idp = idp
        
        base = (float(total) - float(idp)) / 1.12
        iva = base * 0.12
        
        expense.tax_base = decimal.Decimal(base)
        expense.tax_iva = decimal.Decimal(iva)
        
        if idp > 0:
            expense.suggested_account = "Combustibles y Lubricantes"
        
        expense.save()
        return redirect('accounting:approve_expense', pk=expense.id)

    return render(request, 'accounting/review_expense.html', {'expense': expense})


@login_required
def approve_expense(request, pk):
    """Aprueba, descuenta del banco y genera partida contable NIIF"""
    # IMPORTANTE: Asegúrate de tener importado transaction y decimal arriba en tu archivo
    
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if expense.status == 'APPROVED':
        messages.warning(request, "Este gasto ya fue contabilizado.")
        return redirect('accounting:expense_pending_list') 

    # --- NUEVO CANDADO DE SEGURIDAD ---
    if float(expense.total_amount) <= 0:
        messages.error(request, "🛑 No se puede contabilizar un gasto con monto Q. 0.00. Por favor, edita el gasto e ingresa el valor de la factura antes de aprobarlo.")
        # Opcional: Si tienes una vista para editar, puedes redirigirlo allí. Por ahora lo devolvemos a la lista.
        return redirect('accounting:expense_pending_list') 
    # ----------------------------------

    try:
        # Usamos atomic para que si falla el descuento del banco, no se cree la partida a medias
        with transaction.atomic(): 
            monto_total = float(expense.total_amount)
            idp = float(expense.tax_idp)
            base = float(expense.tax_base)
            iva = float(expense.tax_iva)
            
            # 1. CREACIÓN DE CUENTAS DINÁMICAS (Nuevo Modelo Account)
            nombre_cuenta_gasto = expense.suggested_account or "Gastos Generales"
            cuenta_gasto, _ = Account.objects.get_or_create(
                code=f"5.1-{nombre_cuenta_gasto[:3].upper()}", 
                defaults={'name': nombre_cuenta_gasto, 'account_type': 'EXPENSE'}
            )
            cuenta_iva, _ = Account.objects.get_or_create(code="1.1.2.01", defaults={'name': 'IVA por Cobrar', 'account_type': 'ASSET'})
            cuenta_idp, _ = Account.objects.get_or_create(code="5.1.1.02", defaults={'name': 'Impuesto IDP', 'account_type': 'EXPENSE'})

            # 2. CREACIÓN DEL ENCABEZADO DE PARTIDA (Nuevo Modelo JournalEntry)
            entry = JournalEntry.objects.create(
                date=expense.date.date(),
                company=request.user.current_company,
                concept=f"Prov: {expense.provider_name} - {expense.description[:30]}",
                is_opening_balance=False
            )

            # 3. CREACIÓN DE LAS LÍNEAS DEL DEBE (Nuevo Modelo JournalEntryLine)
            if base > 0:
                JournalEntryLine.objects.create(entry=entry, account=cuenta_gasto, debit=round(base, 2), credit=0)
            if iva > 0:
                JournalEntryLine.objects.create(entry=entry, account=cuenta_iva, debit=round(iva, 2), credit=0)
            if idp > 0:
                JournalEntryLine.objects.create(entry=entry, account=cuenta_idp, debit=round(idp, 2), credit=0)

            # 4. LÓGICA DE BANCOS Y HABER (Tu lógica original adaptada)
            cuenta_banco = BankAccount.objects.filter(company=request.user.current_company).first()
            nombre_banco = cuenta_banco.bank_name if cuenta_banco else "Caja General"
            
            # Buscamos o creamos la cuenta contable para el banco
            cuenta_pago, _ = Account.objects.get_or_create(
                code="1.1.1.01", 
                defaults={'name': nombre_banco, 'account_type': 'ASSET'}
            )
            
            # Línea del Haber
            JournalEntryLine.objects.create(entry=entry, account=cuenta_pago, debit=0, credit=round(monto_total, 2))
            
            # Rebajamos el saldo del módulo de bancos (usando initial_balance si es el que definiste)
            if cuenta_banco:
                if hasattr(cuenta_banco, 'balance'):
                    cuenta_banco.balance -= decimal.Decimal(str(monto_total))
                elif hasattr(cuenta_banco, 'initial_balance'):
                    cuenta_banco.initial_balance -= decimal.Decimal(str(monto_total))
                cuenta_banco.save()

            # 5. FINALIZAR
            expense.status = 'APPROVED'
            expense.save()
            messages.success(request, f"✅ Gasto Contabilizado Exitosamente (Partida #{entry.id}).")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    # Redirige exactamente a donde tú lo tenías configurado
    return redirect('accounting:expense_pending_list')


@login_required
def reject_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    expense.status = 'REJECTED'
    expense.save()
    messages.warning(request, "Gasto rechazado.")
    return redirect('accounting:expense_pending_list')

# ========================================================
# 3. ESTADOS FINANCIEROS Y LIBROS
# ========================================================
# 2. ¡Pero el Libro Diario lo BLINDAMOS!
@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente') # Un piloto jamás pasará de aquí
def libro_diario(request):
    entries = JournalEntry.objects.filter(company=request.user.current_company).order_by('-date', '-id')
    
    # 1. Filtro por fechas
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if fecha_inicio:
        entries = entries.filter(date__gte=fecha_inicio)
    if fecha_fin:
        entries = entries.filter(date__lte=fecha_fin)

    # 2. Paginación (10 partidas por "hoja")
    paginator = Paginator(entries, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounting/libro_diario.html', {
        'page_obj': page_obj,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })

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

# ========================================================
# 4. BANCOS Y FLOTILLA
# ========================================================
@login_required
def bank_list(request):
    accounts = BankAccount.objects.filter(company=request.user.current_company)
    total_balance = sum(acc.saldo_actual for acc in accounts)
    
    recent_transactions = BankTransaction.objects.filter(account__company=request.user.current_company).order_by('-date', '-created_at')[:15]
    return render(request, 'accounting/bank_list.html', {'accounts': accounts, 'total_balance': total_balance, 'recent_transactions': recent_transactions})

@login_required
def bank_create(request):
    if request.method == 'POST':
        form = BankAccountForm(request.POST)
        if form.is_valid():
            bank = form.save(commit=False)
            bank.company = request.user.current_company
            bank.save()
            messages.success(request, "Cuenta creada.")
            return redirect('bank_list')
    else:
        form = BankAccountForm()
    return render(request, 'accounting/bank_form.html', {'form': form})

@login_required
def bank_transaction_create(request):
    """Registra cualquier tipo de movimiento bancario (Notas de débito, crédito, etc)"""
    if request.method == 'POST':
        account_id = request.POST.get('bank_account')
        transaction_type = request.POST.get('transaction_type')
        amount_str = request.POST.get('amount')
        reference = request.POST.get('reference')
        description = request.POST.get('description')
        date = request.POST.get('date')

        cuenta = get_object_or_404(BankAccount, id=account_id, company=request.user.current_company)
        monto = decimal.Decimal(amount_str)

        try:
            with transaction.atomic():
                # 1. Validar fondos si es una salida de dinero
                if transaction_type in ['RETIRO', 'NOTA_DEBITO', 'CHEQUE'] and cuenta.balance < monto:
                    messages.error(request, f"Fondos insuficientes. La cuenta solo tiene Q. {cuenta.balance}")
                    return redirect('accounting:bank_transaction_create')

                # 2. Actualizar el saldo de la cuenta según el tipo
                if transaction_type in ['DEPOSITO', 'NOTA_CREDITO']:
                    cuenta.balance += monto
                elif transaction_type in ['RETIRO', 'NOTA_DEBITO', 'CHEQUE']:
                    cuenta.balance -= monto
                cuenta.save()

                # 3. Guardar el registro en el historial
                BankTransaction.objects.create(
                    bank_account=cuenta,
                    transaction_type=transaction_type,
                    amount=monto,
                    reference=reference,
                    description=description,
                    date=date
                )
                
            messages.success(request, f'Movimiento ({transaction_type}) registrado exitosamente.')
            return redirect('accounting:bank_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error al registrar movimiento: {str(e)}')
            return redirect('accounting:bank_transaction_create')

    # Si es GET, cargamos las cuentas para el formulario
    cuentas = BankAccount.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/bank_transaction_form.html', {'cuentas': cuentas})

@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(company=request.user.current_company)
    return render(request, 'accounting/vehicle_list.html', {'vehicles': vehicles})

@login_required
def vehicle_create(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            v = form.save(commit=False)
            v.company = request.user.current_company
            v.save()
            messages.success(request, "Vehículo creado.")
            return redirect('vehicle_list')
    else:
        form = VehicleForm()
    return render(request, 'accounting/vehicle_form.html', {'form': form})

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def chart_of_accounts(request):
    """Módulo: Plan de Cuentas (Catálogo NIIF)"""
    
    # Si la contadora envía el formulario para crear una nueva cuenta
    if request.method == 'POST':
        code = request.POST.get('code').strip()
        name = request.POST.get('name').strip().upper()
        account_type = request.POST.get('account_type')
        is_transactional = request.POST.get('is_transactional') == 'on'

        # Verificamos que el código no exista ya
        if Account.objects.filter(code=code).exists():
            messages.error(request, f"Error: El código de cuenta {code} ya existe en el catálogo.")
        else:
            Account.objects.create(
                code=code,
                name=name,
                account_type=account_type,
                is_transactional=is_transactional
            )
            messages.success(request, f"✅ Cuenta NIIF {code} - {name} agregada con éxito.")
            return redirect('chart_of_accounts')

    # Para mostrar el catálogo, buscamos si el usuario usó la barra de búsqueda
    search_query = request.GET.get('q', '')
    if search_query:
        cuentas = Account.objects.filter(
            Q(code__icontains=search_query) | Q(name__icontains=search_query)
        ).order_by('code')
    else:
        cuentas = Account.objects.all().order_by('code')

    return render(request, 'accounting/chart_of_accounts.html', {
        'cuentas': cuentas, 
        'search_query': search_query
    })

# --- API GEMINI ---
import google.generativeai as genai
from django.http import JsonResponse
from PIL import Image
import json

GENAI_API_KEY = "AIzaSyCZkHsDpbhRWiQvUJcuEdRLlI8s-192VU0" 
genai.configure(api_key=GENAI_API_KEY)

def analyze_receipt_api(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            img = Image.open(image_file)

            # PROMPT MEJORADO: IA con Rol de Contador NIIF
            prompt = """
            Actúa como un Contador Público y Auditor experto en NIIF (Normas Internacionales de Información Financiera) y en contabilidad de Guatemala.
            Analiza esta factura/recibo y extrae la información solicitada.

            REGLA DE CLASIFICACIÓN (NIIF):
            Para el campo "account_type", DEBES analizar el concepto de la compra y asignarlo a UNA Y SOLO UNA de estas cuentas exactas de nuestro catálogo:
            - "Combustibles y Lubricantes" (Gasolina, diésel, aditivos)
            - "Mantenimiento y Reparación de Vehículos" (Repuestos, llantas, talleres, servicios)
            - "Papelería y Útiles de Oficina" (Hojas, tinta, cuadernos)
            - "Atenciones al Personal y Clientes" (Comidas, restaurantes, refacciones)
            - "Servicios Públicos y Telefonía" (Luz, agua, internet, recargas)
            - "Mobiliario y Equipo de Computo" (PCs, teclados, herramientas mayores)
            - "Inventario de Mercadería" (Si es compra de mercancía para la venta)
            - "Gastos Generales" (ÚNETE a esta solo si no encaja en ninguna de las anteriores)

            Devuelve UNICAMENTE el siguiente formato JSON estricto:
            {
                "supplier": "Nombre del proveedor comercial",
                "nit": "NIT sin guiones ni letras extra, solo números y K",
                "date": "YYYY-MM-DD",
                "serie": "Serie de la factura (si aplica)",
                "number": "Número de factura o DTE",
                "total": 0.00,
                "is_fuel": true/false,
                "idp": 0.00,
                "account_type": "CUENTA_EXACTA_DEL_LISTADO_DE_ARRIBA"
            }
            Si algún dato no es visible, pon null. No inventes datos. No incluyas markdown como ```json.
            """
            
            # Usamos Gemini 1.5 Flash (ideal para OCR rápido y barato)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, img])
            
            # Limpiamos posibles caracteres basura antes de parsear el JSON
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text_response)
            
            return JsonResponse({'success': True, **data})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'No se proporcionó ninguna imagen'})

@login_required
def mobile_expense(request):
    vehicles = Vehicle.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/expense_form.html', {'vehicles': vehicles})

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def fleet_expense_report(request):
    """Reporte de Gastos de Flotilla: Combustible vs Mantenimiento"""
    
    # 1. Traemos todos los vehículos de la empresa
    vehicles = Vehicle.objects.filter(company=request.user.current_company)
    
    # 2. Filtramos los gastos base: Solo los que pertenecen a un vehículo y a esta empresa
    # (Opcional: puedes agregar status='APPROVED' si solo quieres ver los ya revisados por contabilidad)
    qs = Expense.objects.filter(company=request.user.current_company, vehicle__isnull=False)
    
    # 3. Leer los filtros que el usuario eligió en la pantalla
    vehicle_id = request.GET.get('vehicle_id')
    category = request.GET.get('category', 'both') # Por defecto muestra ambos
    
    # Aplicar filtro de vehículo si eligió uno específico
    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)
        
    # Aplicar filtro de categoría (Buscamos la palabra clave en la descripción que manda el piloto)
    if category == 'fuel':
        qs = qs.filter(description__icontains='Combustible')
    elif category == 'maint':
        qs = qs.filter(description__icontains='Mantenimiento')
    elif category == 'both':
        qs = qs.filter(Q(description__icontains='Combustible') | Q(description__icontains='Mantenimiento'))

    # 4. CALCULADORA MAESTRA (Suma los totales de la flotilla o del vehículo)
    total_fuel = qs.filter(description__icontains='Combustible').aggregate(t=Sum('total_amount'))['t'] or 0
    total_maint = qs.filter(description__icontains='Mantenimiento').aggregate(t=Sum('total_amount'))['t'] or 0
    gran_total = total_fuel + total_maint

    context = {
        'expenses': qs.order_by('-date'), # Ordenados del más reciente al más viejo
        'vehicles': vehicles,
        'total_fuel': total_fuel,
        'total_maint': total_maint,
        'gran_total': gran_total,
        'selected_vehicle': vehicle_id,
        'selected_category': category,
    }
    return render(request, 'accounting/fleet_report.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def opening_balance_migration(request):
    """Pantalla para ingresar el Balance de Cierre 2025 de Monica 8.5"""
    
    # Traemos solo las cuentas donde se puede ingresar dinero
    cuentas = Account.objects.filter(is_transactional=True).order_by('code')

    if request.method == 'POST':
        # 1. Creamos la Partida Contable Maestra
        partida = JournalEntry.objects.create(
            date=request.POST.get('fecha_apertura', '2026-01-01'),
            concept="MIGRACIÓN DE SALDOS INICIALES - CIERRE 2025 (MONICA 8.5)",
            company=request.user.current_company,
            is_opening_balance=True # Marcamos que esta es la migración
        )

        # 2. Recorremos los datos que la contadora tecleó
        total_debe = 0
        total_haber = 0
        
        # Como es un formulario dinámico, leemos las listas de arrays que llegan del HTML
        account_ids = request.POST.getlist('account_id[]')
        debits = request.POST.getlist('debit[]')
        credits = request.POST.getlist('credit[]')

        try:
            with transaction.atomic():
                for i in range(len(account_ids)):
                    if account_ids[i]: # Si seleccionó una cuenta
                        debe_val = float(debits[i]) if debits[i] else 0.00
                        haber_val = float(credits[i]) if credits[i] else 0.00
                        
                        if debe_val > 0 or haber_val > 0:
                            cuenta = Account.objects.get(id=account_ids[i])
                            JournalEntryLine.objects.create(
                                entry=partida,
                                account=cuenta,
                                debit=debe_val,
                                credit=haber_val
                            )
                            total_debe += debe_val
                            total_haber += haber_val
                
                # REGLA DE ORO CONTABLE: El Debe y el Haber deben cuadrar
                if round(total_debe, 2) != round(total_haber, 2):
                    raise Exception(f"Descuadre contable: El Debe (Q{total_debe}) no cuadra con el Haber (Q{total_haber}). Revisa los datos de Monica 8.5.")

            messages.success(request, "✅ ¡Migración de Saldos Iniciales guardada con éxito! El 2026 ha iniciado correctamente.")
            return redirect('home')

        except Exception as e:
            # Si descuadra, borramos la partida fallida y le avisamos
            partida.delete()
            messages.error(request, str(e))
            return redirect('opening_balance')

    return render(request, 'accounting/opening_balance.html', {'cuentas': cuentas})

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def general_journal(request):
    """Libro Diario General Profesional (NIIF)"""
    
    # Por defecto, cargamos el mes y año actuales
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year
    
    mes = int(request.GET.get('mes', mes_actual))
    anio = int(request.GET.get('anio', anio_actual))

    # TÉCNICA AVANZADA: prefetch_related trae todas las líneas y cuentas en 2 consultas a la BD, 
    # en lugar de hacer 1 consulta por cada línea. ¡Velocidad pura!
    partidas = JournalEntry.objects.filter(
        company=request.user.current_company,
        date__year=anio,
        date__month=mes
    ).prefetch_related(
        Prefetch('lines', queryset=JournalEntryLine.objects.select_related('account'))
    ).order_by('date', 'id')

    # Calculamos los totales del mes en memoria para el pie de página
    total_debe_mes = sum(linea.debit for partida in partidas for linea in partida.lines.all())
    total_haber_mes = sum(linea.credit for partida in partidas for linea in partida.lines.all())

    context = {
        'partidas': partidas,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'meses': range(1, 13),
        'anios': range(2025, 2030),
        'total_debe_mes': total_debe_mes,
        'total_haber_mes': total_haber_mes,
    }
    return render(request, 'accounting/general_journal.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def general_ledger(request):
    """Libro Mayor General (Movimientos por Cuenta Específica)"""
    
    # Solo mostramos cuentas que reciben movimientos
    cuentas = Account.objects.filter(is_transactional=True).order_by('code')
    
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year
    
    account_id = request.GET.get('account_id')
    mes = int(request.GET.get('mes', mes_actual))
    anio = int(request.GET.get('anio', anio_actual))
    
    lineas = []
    cuenta_seleccionada = None
    saldo_acumulado = 0
    total_debe = 0
    total_haber = 0

    if account_id:
        cuenta_seleccionada = Account.objects.get(id=account_id)
        
        # Traemos todas las líneas de esa cuenta en ese mes
        lineas = JournalEntryLine.objects.filter(
            account=cuenta_seleccionada,
            entry__date__year=anio,
            entry__date__month=mes
        ).select_related('entry').order_by('entry__date', 'entry__id')
        
        # Calculamos el saldo dinámico fila por fila
        for linea in lineas:
            total_debe += linea.debit
            total_haber += linea.credit
            
            # Naturaleza de las cuentas (NIIF)
            if cuenta_seleccionada.account_type in ['ASSET', 'EXPENSE']:
                saldo_acumulado += (linea.debit - linea.credit) # Naturaleza Deudora
            else:
                saldo_acumulado += (linea.credit - linea.debit) # Naturaleza Acreedora
                
            # Le inyectamos el saldo actual a la línea para mostrarlo en el HTML
            linea.saldo_actual = saldo_acumulado 

    context = {
        'cuentas': cuentas,
        'lineas': lineas,
        'cuenta_seleccionada': cuenta_seleccionada,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'meses': range(1, 13),
        'anios': range(2025, 2030),
        'total_debe': total_debe,
        'total_haber': total_haber,
        'saldo_final': saldo_acumulado
    }
    return render(request, 'accounting/general_ledger.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def balance_sheet(request):
    """Estado de Situación Financiera (Balance General)"""
    
    anio = int(request.GET.get('anio', timezone.now().year))
    mes = int(request.GET.get('mes', timezone.now().month))

    # Calculamos el corte hasta el ÚLTIMO día del mes seleccionado
    if mes == 12:
        siguiente_mes = datetime.date(anio + 1, 1, 1)
    else:
        siguiente_mes = datetime.date(anio, mes + 1, 1)
    
    # Traemos la suma total de Debe y Haber de todas las cuentas hasta esa fecha
    lineas = JournalEntryLine.objects.filter(
        entry__date__lt=siguiente_mes,
        entry__company=request.user.current_company
    ).values('account__id', 'account__code', 'account__name', 'account__account_type').annotate(
        total_debe=Sum('debit'),
        total_haber=Sum('credit')
    )

    activos, pasivos, patrimonio = [], [], []
    total_activos = total_pasivos = total_patrimonio = utilidad_ejercicio = 0

    # Clasificamos y calculamos saldos según la NIIF
    for linea in lineas:
        tipo = linea['account__account_type']
        debe = linea['total_debe'] or 0
        haber = linea['total_haber'] or 0
        
        if tipo == 'ASSET':
            saldo = debe - haber
            if saldo != 0:
                activos.append({'codigo': linea['account__code'], 'nombre': linea['account__name'], 'saldo': saldo})
                total_activos += saldo
                
        elif tipo == 'LIABILITY':
            saldo = haber - debe
            if saldo != 0:
                pasivos.append({'codigo': linea['account__code'], 'nombre': linea['account__name'], 'saldo': saldo})
                total_pasivos += saldo
                
        elif tipo == 'EQUITY':
            saldo = haber - debe
            if saldo != 0:
                patrimonio.append({'codigo': linea['account__code'], 'nombre': linea['account__name'], 'saldo': saldo})
                total_patrimonio += saldo
                
        # Calculamos la utilidad en tiempo real (Ingresos - Gastos)
        elif tipo == 'REVENUE':
            utilidad_ejercicio += (haber - debe)
        elif tipo == 'EXPENSE':
            utilidad_ejercicio -= (debe - haber)

    # Ordenamos las cuentas para que se vean presentables
    activos.sort(key=lambda x: x['codigo'])
    pasivos.sort(key=lambda x: x['codigo'])
    patrimonio.sort(key=lambda x: x['codigo'])

    # Ecuación Contable: Activo = Pasivo + Patrimonio + Utilidad
    total_pasivo_patrimonio = total_pasivos + total_patrimonio + utilidad_ejercicio

    context = {
        'activos': activos, 'pasivos': pasivos, 'patrimonio': patrimonio,
        'total_activos': total_activos, 'total_pasivos': total_pasivos, 
        'total_patrimonio': total_patrimonio, 'utilidad_ejercicio': utilidad_ejercicio,
        'total_pasivo_patrimonio': total_pasivo_patrimonio,
        'mes_seleccionado': mes, 'anio_seleccionado': anio,
        'meses': range(1, 13), 'anios': range(2025, 2030),
    }
    return render(request, 'accounting/balance_sheet.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def income_statement(request):
    """Estado de Resultados (Pérdidas y Ganancias)"""
    
    anio = int(request.GET.get('anio', timezone.now().year))
    mes = int(request.GET.get('mes', timezone.now().month))

    # Calculamos el rango exacto del mes seleccionado
    fecha_inicio = datetime.date(anio, mes, 1)
    if mes == 12:
        fecha_fin = datetime.date(anio + 1, 1, 1)
    else:
        fecha_fin = datetime.date(anio, mes + 1, 1)

    # Solo traemos cuentas de INGRESOS (REVENUE) y GASTOS (EXPENSE) de este mes
    lineas = JournalEntryLine.objects.filter(
        entry__date__gte=fecha_inicio,
        entry__date__lt=fecha_fin,
        entry__company=request.user.current_company,
        account__account_type__in=['REVENUE', 'EXPENSE']
    ).values('account__id', 'account__code', 'account__name', 'account__account_type').annotate(
        total_debe=Sum('debit'),
        total_haber=Sum('credit')
    )

    ingresos = []
    gastos = []
    total_ingresos = total_gastos = 0

    for linea in lineas:
        tipo = linea['account__account_type']
        debe = linea['total_debe'] or 0
        haber = linea['total_haber'] or 0

        # Naturaleza Acreedora (Suma con el Haber)
        if tipo == 'REVENUE':
            saldo = haber - debe
            if saldo != 0:
                ingresos.append({'codigo': linea['account__code'], 'nombre': linea['account__name'], 'saldo': saldo})
                total_ingresos += saldo
                
        # Naturaleza Deudora (Suma con el Debe)
        elif tipo == 'EXPENSE':
            saldo = debe - haber
            if saldo != 0:
                gastos.append({'codigo': linea['account__code'], 'nombre': linea['account__name'], 'saldo': saldo})
                total_gastos += saldo

    # Ordenar por código contable
    ingresos.sort(key=lambda x: x['codigo'])
    gastos.sort(key=lambda x: x['codigo'])

    # El Número Mágico
    utilidad_neta = total_ingresos - total_gastos

    context = {
        'ingresos': ingresos, 'gastos': gastos,
        'total_ingresos': total_ingresos, 'total_gastos': total_gastos,
        'utilidad_neta': utilidad_neta,
        'mes_seleccionado': mes, 'anio_seleccionado': anio,
        'meses': range(1, 13), 'anios': range(2025, 2030),
    }
    return render(request, 'accounting/income_statement.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def trial_balance(request):
    """Balance de Comprobación de Sumas y Saldos"""
    
    anio = int(request.GET.get('anio', timezone.now().year))
    mes = int(request.GET.get('mes', timezone.now().month))

    # Corte hasta el último día del mes seleccionado
    if mes == 12:
        fecha_fin = datetime.date(anio + 1, 1, 1)
    else:
        fecha_fin = datetime.date(anio, mes + 1, 1)

    # Traemos la suma de DEBE y HABER de todas las cuentas con movimientos
    lineas = JournalEntryLine.objects.filter(
        entry__date__lt=fecha_fin,
        entry__company=request.user.current_company
    ).values(
        'account__id', 'account__code', 'account__name', 'account__account_type'
    ).annotate(
        total_debe=Sum('debit'),
        total_haber=Sum('credit')
    ).order_by('account__code')

    cuentas_balance = []
    gran_total_debe = gran_total_haber = 0
    gran_total_deudor = gran_total_acreedor = 0

    for linea in lineas:
        debe = linea['total_debe'] or 0
        haber = linea['total_haber'] or 0
        tipo = linea['account__account_type']

        # 1. Acumulamos las SUMAS
        gran_total_debe += debe
        gran_total_haber += haber

        # 2. Calculamos los SALDOS según la naturaleza de la cuenta
        saldo_deudor = 0
        saldo_acreedor = 0

        # Naturaleza Deudora (Activos y Gastos)
        if tipo in ['ASSET', 'EXPENSE']: 
            saldo = debe - haber
            if saldo > 0:
                saldo_deudor = saldo
            elif saldo < 0:
                saldo_acreedor = abs(saldo) # Caso atípico (Ej. sobregiro)
                
        # Naturaleza Acreedora (Pasivos, Patrimonio e Ingresos)
        else: 
            saldo = haber - debe
            if saldo > 0:
                saldo_acreedor = saldo
            elif saldo < 0:
                saldo_deudor = abs(saldo)

        # 3. Acumulamos los SALDOS GLOBALES
        gran_total_deudor += saldo_deudor
        gran_total_acreedor += saldo_acreedor

        cuentas_balance.append({
            'codigo': linea['account__code'],
            'nombre': linea['account__name'],
            'debe': debe,
            'haber': haber,
            'saldo_deudor': saldo_deudor,
            'saldo_acreedor': saldo_acreedor
        })

    context = {
        'cuentas_balance': cuentas_balance,
        'gran_total_debe': gran_total_debe,
        'gran_total_haber': gran_total_haber,
        'gran_total_deudor': gran_total_deudor,
        'gran_total_acreedor': gran_total_acreedor,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'meses': range(1, 13),
        'anios': range(2025, 2030),
    }
    return render(request, 'accounting/trial_balance.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def purchase_ledger(request):
    """Libro de Compras y Servicios (Formato SAT Guatemala)"""
    
    anio = int(request.GET.get('anio', timezone.now().year))
    mes = int(request.GET.get('mes', timezone.now().month))

    # Filtramos solo los gastos del mes que ya fueron contabilizados (APPROVED)
    gastos = Expense.objects.filter(
        company=request.user.current_company,
        date__year=anio,
        date__month=mes,
        status='APPROVED'
    ).order_by('date')

    # Sumatorias automáticas para Declaraguate
    total_base = sum(g.tax_base for g in gastos)
    total_iva = sum(g.tax_iva for g in gastos)
    total_idp = sum(g.tax_idp for g in gastos)
    gran_total = sum(g.total_amount for g in gastos)

    context = {
        'gastos': gastos,
        'total_base': total_base,
        'total_iva': total_iva,
        'total_idp': total_idp,
        'gran_total': gran_total,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'meses': range(1, 13),
        'anios': range(2025, 2030),
    }
    return render(request, 'accounting/purchase_ledger.html', context)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def fiscal_close(request):
    """Módulo de Cierres Fiscales Mensuales"""
    
    # Traemos el historial de meses que ya han sido gestionados
    periodos = AccountingPeriod.objects.filter(
        company=request.user.current_company
    ).order_by('-year', '-month')
    
    if request.method == 'POST':
        anio = int(request.POST.get('year'))
        mes = int(request.POST.get('month'))
        
        # Buscamos el mes o lo creamos si no existe en la tabla de control
        periodo, created = AccountingPeriod.objects.get_or_create(
            company=request.user.current_company,
            year=anio,
            month=mes
        )
        
        if not periodo.is_closed:
            periodo.is_closed = True
            periodo.closed_by = request.user
            periodo.closed_at = timezone.now()
            periodo.save()
            messages.success(request, f"🔒 Período {mes}/{anio} cerrado exitosamente. El candado fiscal está activo.")
        else:
            messages.warning(request, f"El período {mes}/{anio} ya estaba cerrado.")
            
        return redirect('fiscal_close')
        
    return render(request, 'accounting/fiscal_close.html', {
        'periodos': periodos, 
        'meses': range(1, 13), 
        'anios': range(2025, 2030)
    })
@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def sales_ledger(request):
    """Libro de Ventas y Servicios Prestados (Formato SAT Guatemala)"""
    
    anio = int(request.GET.get('anio', timezone.now().year))
    mes = int(request.GET.get('mes', timezone.now().month))

    ventas = SaleInvoice.objects.filter(
        company=request.user.current_company,
        date__year=anio,
        date__month=mes,
        status='APPROVED' 
    ).order_by('date')

    total_base = sum(v.tax_base for v in ventas)
    total_iva = sum(v.tax_iva for v in ventas)
    gran_total = sum(v.total_amount for v in ventas)

    context = {
        'ventas': ventas,
        'total_base': total_base,
        'total_iva': total_iva,
        'gran_total': gran_total,
        'mes_seleccionado': mes,
        'anio_seleccionado': anio,
        'meses': range(1, 13),
        'anios': range(2025, 2030),
    }
    return render(request, 'accounting/sales_ledger.html', context)

@login_required
def expense_pre_review_list(request): 
    # 1. ATRAPAMOS EL CLIC EN LOS BOTONES (MÉTODO POST)
    if request.method == 'POST':
        expense_id = request.POST.get('expense_id')
        action = request.POST.get('action')
        
        # Buscamos el gasto exacto al que le dieron clic
        gasto = get_object_or_404(GastoOperativo, id=expense_id)
        
        # Verificamos qué botón presionaron y guardamos la firma
        if action == 'sup1':
            gasto.supervisor_1_ok = True
            messages.success(request, 'Firma de Supervisor 1 registrada exitosamente.')
        
        elif action == 'sup2':
            gasto.supervisor_2_ok = True
            messages.success(request, 'Firma de Supervisor 2 registrada exitosamente.')
        
        elif action == 'asist':
            gasto.assistant_ok = True
            messages.success(request, 'Firma de Asistente registrada exitosamente.')
        
        elif action == 'reject':
            gasto.estado = 'Rechazado'
            messages.error(request, f'El gasto de {gasto.total_amount} ha sido marcado como fraude/rechazado.')
        
        # Guardamos los cambios en la base de datos
        gasto.save()
        
        # Ejecutamos la magia: Si ya están las 3 firmas, se pasa a Contabilidad
        if action != 'reject':
            gasto.verificar_pase_contabilidad()
        
        # Recargamos la misma página para que se actualicen los semáforos
        return redirect('accounting:expense_pre_review_list')

    # 2. SI SOLO ENTRAN A VER LA PÁGINA (MÉTODO GET)
    # CORRECCIÓN: Traemos TODOS los gastos, excepto los que ya terminaron su ciclo
    gastos_pendientes = GastoOperativo.objects.all().order_by('-date')
    
    return render(request, 'accounting/expense_pre_review_list.html', {
        'expenses': gastos_pendientes
    })

@login_required
def bank_dashboard(request):
    """Tablero Financiero: Cuentas y transacciones en tiempo real"""
    
    # 1. Traemos las cuentas de la empresa en la que está trabajando el usuario
    # (Usamos el request.user.current_company que configuramos en la aduana)
    if hasattr(request.user, 'current_company') and request.user.current_company:
        accounts = BankAccount.objects.filter(company=request.user.current_company, active=True)
        recent_transactions = BankTransaction.objects.filter(
    account__company=request.user.current_company
    ).order_by('-date', '-created_at')[:15]
    else:
        accounts = BankAccount.objects.filter(active=True)
        recent_transactions = BankTransaction.objects.all().order_by('-date', '-created_at')[:15]

    # 2. 🔥 EL MOTOR CONTABLE: Calculamos el saldo real de cada cuenta
    total_global = 0
    for account in accounts:
        # Sumamos Depósitos
        deposits = account.transactions.filter(transaction_type='DEPOSIT').aggregate(Sum('amount'))['amount__sum'] or 0
        # Sumamos Retiros
        withdrawals = account.transactions.filter(transaction_type='WITHDRAWAL').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Matemáticas de Arquitecto: Saldo Inicial + Entradas - Salidas
        account.current_balance = account.initial_balance + deposits - withdrawals
        total_global += account.current_balance

    context = {
        'accounts': accounts,
        'recent_transactions': recent_transactions,
        'total_global': total_global,
    }
    return render(request, 'accounting/bank_dashboard.html', context)

def register_deposit(request):
    """Vista profesional para registrar depósitos bancarios"""
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            # Pausamos el guardado para inyectar datos automáticos
            deposito = form.save(commit=False)
            deposito.transaction_type = 'DEPOSIT' # Asegúrate de que esto coincida con las opciones de tu modelo
            deposito.registered_by = request.user
            deposito.save()
            
            messages.success(request, f'¡Éxito! Depósito por Q.{deposito.amount} registrado en {deposito.account}.')
            return redirect('accounting:bank_dashboard')
        else:
            messages.error(request, 'Hubo un error en el formulario. Por favor, revisa los campos en rojo.')
    else:
        form = DepositForm()

    context = {
        'form': form,
        'title': 'Registrar Nuevo Depósito'
    }
    return render(request, 'accounting/register_deposit.html', context)

@login_required
def guardar_gasto_piloto(request):
    if request.method == 'POST':
        # 1. Atrapar los datos de texto y selects que vienen del HTML
        vehicle_id = request.POST.get('vehicle')
        tipo_gasto = request.POST.get('tipo_gasto')
        payment_method = request.POST.get('payment_method')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        # 2. Atrapar los archivos (Fotos)
        receipt_image = request.FILES.get('receipt_image')
        pump_image = request.FILES.get('pump_image') # Si seleccionó repuestos, esto vendrá vacío automáticamente

        # 3. Buscar la instancia del vehículo en la base de datos
        vehiculo_obj = None
        if vehicle_id:
            try:
                vehiculo_obj = Vehiculo.objects.get(id=vehicle_id)
            except Vehiculo.DoesNotExist:
                pass # Manejo de error por si mandan un ID que no existe

        # 4. Crear el registro en la base de datos
        nuevo_gasto = GastoOperativo.objects.create(
            user=request.user,                  # El piloto logueado actualmente
            vehicle=vehiculo_obj,
            tipo_gasto=tipo_gasto,
            payment_method=payment_method,
            latitude=latitude,
            longitude=longitude,
            receipt_image=receipt_image,
            pump_image=pump_image,              # Guarda la foto de la bomba, o null si no hay
            estado='En_Supervision'             # Entra directo a tu bandeja de firmas
            # Nota: No enviamos total_amount, así que toma el default de 0.00
        )

        # 5. Mensaje de éxito y redirección al inicio
        messages.success(request, '¡Evidencia enviada a auditoría exitosamente!')
        return redirect('core:home') 

    # Si la petición es GET (el usuario solo entró a ver la página del formulario)
    # Mandamos los vehículos a la vista para que el `<select>` se llene
    vehiculos_disponibles = Vehiculo.objects.all() 
    return render(request, 'accounting/pilot_upload.html', {'vehicles': vehiculos_disponibles})

@login_required
def subir_gasto_scanner(request):
    if request.method == 'POST':
        # Capturas los datos que mande el formulario del Smart Scanner
        monto = request.POST.get('monto')
        metodo_pago = request.POST.get('metodo_pago')
        foto_factura = request.FILES.get('factura') # Suponiendo que tienes un campo de imagen
        
        # MAGIA: Se crea el gasto saltándose la auditoría de los supervisores
        nuevo_gasto = GastoOperativo.objects.create(
            # Acá pones los datos correspondientes, ej: no hay piloto, lo sube el auxiliar
            monto=monto,
            metodo_pago=metodo_pago,
            foto_factura=foto_factura,
            
            # ESTA ES LA CLAVE: Va directo al contador
            estado='Pendiente_Contabilidad', 
            
            # Marcamos que las 3 firmas no aplican o las damos por hechas (opcional)
            sup1_firmado=True,
            sup2_firmado=True,
            asist_firmado=True
        )
        
        return redirect('accountig:smart_hub') # Lo mandas a donde quieras tras guardar

    return render(request, 'accounting/smart_hub')

@login_required
def registrar_retiro(request):
    if request.method == 'POST':
        account_id = request.POST.get('bank_account')
        amount = request.POST.get('amount')
        reference = request.POST.get('reference')
        description = request.POST.get('description')
        date = request.POST.get('date')

        cuenta = get_object_or_404(BankAccount, id=account_id, company=request.user.current_company)
        monto_retiro = decimal.Decimal(amount)

        # Validación de fondos
        if cuenta.balance < monto_retiro:
            messages.error(request, f"Fondos insuficientes. La cuenta {cuenta.bank_name} solo tiene Q. {cuenta.balance}")
            return redirect('accounting:registrar_retiro')

        try:
            with transaction.atomic():
                # 1. Restar el saldo de la cuenta
                cuenta.balance -= monto_retiro
                cuenta.save()

                # 2. Registrar el movimiento en el historial del banco
                BankTransaction.objects.create(
                    bank_account=cuenta,
                    transaction_type='RETIRO',
                    amount=monto_retiro,
                    reference=reference,
                    description=description,
                    date=date
                )
                
            messages.success(request, f'Retiro de Q. {monto_retiro} registrado exitosamente.')
            return redirect('accounting:bank_dashboard') 
            
        except Exception as e:
            messages.error(request, f'Error al procesar el retiro: {str(e)}')
            return redirect('accounting:registrar_retiro') # <-- Agregué esto por seguridad

    # Si es GET, mandamos las cuentas activas al formulario
    cuentas = BankAccount.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/registrar_retiro.html', {'cuentas': cuentas})

@login_required
def nueva_cuenta_bancaria(request):
    if request.method == 'POST':
        # 1. Atrapamos los datos del formulario
        bank_name = request.POST.get('bank_name')
        account_name = request.POST.get('account_name')
        account_number = request.POST.get('account_number')
        currency = request.POST.get('currency')
        initial_balance = request.POST.get('initial_balance', '0.00')

        try:
            # 2. Convertimos el texto del saldo a un número decimal real
            saldo_inicial = decimal.Decimal(initial_balance)

            # 3. Creamos la cuenta en la base de datos
            BankAccount.objects.create(
                company=request.user.current_company,
                bank_name=bank_name,
                account_name=account_name,
                account_number=account_number,
                currency=currency,
                initial_balance=saldo_inicial,
                balance=saldo_inicial, # El saldo actual arranca siendo igual al inicial
                active=True
            )
            
            messages.success(request, f'¡Cuenta {account_number} de {bank_name} creada exitosamente!')
            # Cambia esto por la URL de tu panel principal de bancos
            return redirect('accounting:panel_bancos') 
            
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            
    # Si la petición es GET (solo entran a ver la pantalla), mostramos el HTML vacío
    return render(request, 'acounting/nueva_cuenta.html')

@login_required
def panel_tarjetas(request):
    """Dashboard principal para el control de Tarjetas de Crédito"""
    # Traemos todas las tarjetas activas de la empresa actual
    tarjetas = CreditCard.objects.filter(company=request.user.current_company, active=True)
    
    # Calculamos los totales consolidados para los indicadores principales
    total_limite = sum(t.credit_limit for t in tarjetas)
    total_deuda = sum(t.current_debt for t in tarjetas)
    total_disponible = total_limite - total_deuda
    
    context = {
        'tarjetas': tarjetas,
        'total_limite': total_limite,
        'total_deuda': total_deuda,
        'total_disponible': total_disponible,
    }
    return render(request, 'accounting/panel_tarjetas.html', context)

@login_required
def nueva_tarjeta(request):
    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        card_name = request.POST.get('card_name')
        last_four_digits = request.POST.get('last_four_digits')
        credit_limit = request.POST.get('credit_limit')
        cutoff_day = request.POST.get('cutoff_day')
        payment_day = request.POST.get('payment_day')
        current_debt = request.POST.get('current_debt', '0.00')

        try:
            CreditCard.objects.create(
                company=request.user.current_company,
                bank_name=bank_name,
                card_name=card_name,
                last_four_digits=last_four_digits,
                credit_limit=decimal.Decimal(credit_limit),
                cutoff_day=int(cutoff_day),
                payment_day=int(payment_day),
                current_debt=decimal.Decimal(current_debt),
                active=True
            )
            messages.success(request, f'¡Tarjeta {card_name} registrada exitosamente!')
            return redirect('accounting:panel_tarjetas')
            
        except Exception as e:
            messages.error(request, f'Error al crear la tarjeta: {str(e)}')
            return redirect('accounting:nueva_tarjeta')

    return render(request, 'accounting/nueva_tarjeta.html')

@login_required
def transferencia_interna(request):
    """Procesa el traslado de fondos entre dos cuentas bancarias de la misma empresa"""
    if request.method == 'POST':
        origen_id = request.POST.get('cuenta_origen')
        destino_id = request.POST.get('cuenta_destino')
        amount_str = request.POST.get('amount')
        reference = request.POST.get('reference')
        description = request.POST.get('description')
        date = request.POST.get('date')

        # 1. Validación básica: No se puede transferir a la misma cuenta
        if origen_id == destino_id:
            messages.error(request, "La cuenta de origen y destino no pueden ser la misma.")
            return redirect('accounting:transferencia_interna')

        cuenta_origen = get_object_or_404(BankAccount, id=origen_id, company=request.user.current_company)
        cuenta_destino = get_object_or_404(BankAccount, id=destino_id, company=request.user.current_company)
        monto = decimal.Decimal(amount_str)

        # 2. Validación de fondos en la cuenta de salida
        if cuenta_origen.balance < monto:
            messages.error(request, f"Fondos insuficientes. {cuenta_origen.bank_name} solo tiene Q. {cuenta_origen.balance}")
            return redirect('accounting:transferencia_interna')

        try:
            with transaction.atomic():
                # 3. Rebajar de la cuenta origen
                cuenta_origen.balance -= monto
                cuenta_origen.save()

                # 4. Sumar a la cuenta destino
                cuenta_destino.balance += monto
                cuenta_destino.save()

                # 5. Registrar la salida en el historial (Origen)
                BankTransaction.objects.create(
                    bank_account=cuenta_origen,
                    transaction_type='TRANSFERENCIA_OUT',
                    amount=monto,
                    reference=reference,
                    description=f"Transferencia a: {cuenta_destino.bank_name} - {description}",
                    date=date
                )

                # 6. Registrar la entrada en el historial (Destino)
                BankTransaction.objects.create(
                    bank_account=cuenta_destino,
                    transaction_type='TRANSFERENCIA_IN', # Asegúrate de que tu HTML del dashboard lea esto como verde (ingreso)
                    amount=monto,
                    reference=reference,
                    description=f"Transferencia desde: {cuenta_origen.bank_name} - {description}",
                    date=date
                )

            messages.success(request, f'Traslado de Q. {monto} completado exitosamente.')
            return redirect('accounting:bank_dashboard')

        except Exception as e:
            messages.error(request, f'Error al procesar la transferencia: {str(e)}')
            return redirect('accounting:transferencia_interna')

    # GET: Enviamos las cuentas para que el usuario elija
    cuentas = BankAccount.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/transferencia_interna.html', {'cuentas': cuentas})

@login_required
def registrar_consumo_tarjeta(request):
    """Suma deuda a la tarjeta de crédito por un gasto realizado"""
    if request.method == 'POST':
        tarjeta_id = request.POST.get('tarjeta_id')
        monto_str = request.POST.get('amount')
        description = request.POST.get('description')
        
        tarjeta = get_object_or_404(CreditCard, id=tarjeta_id, company=request.user.current_company)
        monto = decimal.Decimal(monto_str)

        # Validamos que no se pase del límite de crédito
        if (tarjeta.current_debt + monto) > tarjeta.credit_limit:
            messages.error(request, f"Límite excedido. La tarjeta solo tiene Q. {tarjeta.available_credit} disponibles.")
            return redirect('accounting:registrar_consumo_tarjeta')

        try:
            tarjeta.current_debt += monto
            tarjeta.save()
            
            messages.success(request, f'Consumo de Q. {monto} registrado en {tarjeta.card_name}.')
            return redirect('accounting:panel_tarjetas')
            
        except Exception as e:
            messages.error(request, f'Error al registrar consumo: {str(e)}')
            return redirect('accounting:registrar_consumo_tarjeta')

    tarjetas = CreditCard.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/tarjeta_consumo.html', {'tarjetas': tarjetas})


@login_required
def pagar_tarjeta_credito(request):
    """Rebaja la deuda de la tarjeta sacando fondos de una cuenta bancaria"""
    if request.method == 'POST':
        tarjeta_id = request.POST.get('tarjeta_id')
        cuenta_id = request.POST.get('cuenta_origen')
        monto_str = request.POST.get('amount')
        reference = request.POST.get('reference')
        date = request.POST.get('date')

        tarjeta = get_object_or_404(CreditCard, id=tarjeta_id, company=request.user.current_company)
        cuenta = get_object_or_404(BankAccount, id=cuenta_id, company=request.user.current_company)
        monto = decimal.Decimal(monto_str)

        # Validamos que el banco tenga fondos
        if cuenta.balance < monto:
            messages.error(request, f"Fondos insuficientes en {cuenta.bank_name}. Saldo: Q. {cuenta.balance}")
            return redirect('accounting:pagar_tarjeta_credito')

        try:
            with transaction.atomic():
                # 1. Sacamos el dinero del banco
                cuenta.balance -= monto
                cuenta.save()

                # 2. Registramos la salida en el historial bancario
                BankTransaction.objects.create(
                    bank_account=cuenta,
                    transaction_type='PAGO_TARJETA', # Nuevo tipo lógico
                    amount=monto,
                    reference=reference,
                    description=f"Pago de Tarjeta de Crédito: {tarjeta.card_name} - {tarjeta.last_four_digits}",
                    date=date
                )

                # 3. Rebajamos la deuda de la tarjeta
                tarjeta.current_debt -= monto
                if tarjeta.current_debt < 0:
                    tarjeta.current_debt = decimal.Decimal('0.00') # Evitamos saldos negativos raros
                tarjeta.save()

            messages.success(request, f'Pago de Q. {monto} a la tarjeta {tarjeta.card_name} procesado exitosamente.')
            return redirect('accounting:panel_tarjetas')

        except Exception as e:
            messages.error(request, f'Error al procesar el pago: {str(e)}')
            return redirect('accounting:pagar_tarjeta_credito')

    tarjetas = CreditCard.objects.filter(company=request.user.current_company, active=True)
    cuentas = BankAccount.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/tarjeta_pago.html', {'tarjetas': tarjetas, 'cuentas': cuentas})

@login_required
def cxp_dashboard(request):
    """Panel de Control de Cuentas por Pagar (CxP)"""
    # Traemos todas las deudas de la empresa, ordenadas por fecha de vencimiento (las más urgentes primero)
    cuentas = AccountPayable.objects.filter(company=request.user.current_company).order_by('due_date')
    
    # Cálculos para los indicadores superiores
    total_deuda = sum(c.balance for c in cuentas if c.status != 'PAGADO')
    total_vencido = sum(c.balance for c in cuentas if c.is_overdue)
    total_al_dia = total_deuda - total_vencido
    
    context = {
        'cuentas': cuentas,
        'total_deuda': total_deuda,
        'total_vencido': total_vencido,
        'total_al_dia': total_al_dia,
    }
    return render(request, 'accounting/cxp_dashboard.html', context)

@login_required
def registrar_factura_cxp(request):
    """Registra una nueva cuenta por pagar (deuda con proveedor)"""
    if request.method == 'POST':
        supplier_name = request.POST.get('supplier_name')
        invoice_number = request.POST.get('invoice_number')
        description = request.POST.get('description')
        issue_date = request.POST.get('issue_date')
        due_date = request.POST.get('due_date')
        total_amount_str = request.POST.get('total_amount')

        try:
            monto_total = decimal.Decimal(total_amount_str)

            # Validar que la fecha de vencimiento no sea menor a la de emisión
            if due_date < issue_date:
                messages.error(request, "La fecha de vencimiento no puede ser anterior a la fecha de emisión.")
                return redirect('accounting:registrar_factura_cxp')

            AccountPayable.objects.create(
                company=request.user.current_company,
                supplier_name=supplier_name,
                invoice_number=invoice_number,
                description=description,
                issue_date=issue_date,
                due_date=due_date,
                total_amount=monto_total,
                balance=monto_total,  # Al inicio, se debe el 100% de la factura
                status='PENDIENTE'
            )
            
            messages.success(request, f'Deuda con {supplier_name} (Fac: {invoice_number}) registrada exitosamente.')
            return redirect('accounting:cxp_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error al registrar la factura: {str(e)}')
            return redirect('accounting:registrar_factura_cxp')

    return render(request, 'accounting/cxp_nueva_factura.html')