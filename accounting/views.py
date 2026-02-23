from django.db import transaction
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

# --- IMPORTACIÓN DE MODELOS ---
from .models import (
    Expense, 
    JournalEntry,
    Account,
    JournalEntryLine,
    JournalItem, 
    BankAccount, 
    BankTransaction, 
    Vehicle
)
from .forms import BankAccountForm, BankTransactionForm, VehicleForm
from .utils import analyze_invoice_image

# ========================================================
# 1. HERRAMIENTAS DE INGRESO UNIFICADAS
# ========================================================

@login_required
@group_required('Pilotos', 'Contadora', 'Gerente', 'Administrador')
def pilot_upload(request):
    """VISTA PILOTOS/GERENTES: Carga rápida de ticket personal"""
    
    # 1. ESCUDO ANTI-ERRORES
    if not request.user.current_company:
        messages.error(request, "⛔ Tu usuario no tiene una empresa asignada. Contacta al Administrador.")
        return redirect('home')

    # ==========================================
    # MAGIA DE FILTRADO DE VEHÍCULOS (INTELIGENTE)
    # ==========================================
    # Buscamos si el usuario actual tiene vehículos a su nombre
    vehiculos_del_usuario = request.user.vehiculos_asignados.filter(company=request.user.current_company)

    if vehiculos_del_usuario.exists():
        # REGLA 1: Si tiene un carro asignado (sea Gerente o Piloto), SOLO le mostramos su carro.
        # Esto agiliza su trabajo y evita que le meta gastos a otra placa por error.
        vehicles = vehiculos_del_usuario
        
    elif request.user.is_superuser or request.user.groups.filter(name__in=['Contadora', 'Administrador', 'Gerente']).exists():
        # REGLA 2: Si NO tiene carro a su nombre, pero es Jefe o Contadora, 
        # le mostramos TODA la flotilla por si está subiendo el gasto de alguien más.
        vehicles = Vehicle.objects.filter(company=request.user.current_company)
        
    else:
        # REGLA 3: Es un piloto, pero en el sistema olvidaron asignarle su placa.
        vehicles = Vehicle.objects.none()
    # ==========================================

    if request.method == 'POST':
        image = request.FILES.get('documento')
        description = request.POST.get('description', 'Gasto de Ruta')
        vehicle_id = request.POST.get('vehicle')
        
        # NUEVO: Capturamos la placa de emergencia si la escribió
        placa_emergencia = request.POST.get('placa_emergencia', '').strip()
        
        vehicle_obj = None

        # LÓGICA DE CONTINGENCIA
        if vehicle_id == 'emergencia':
            # Si eligió otro vehículo, modificamos la descripción para avisarle a Contabilidad
            description = f"🚨 CONTINGENCIA | Placa reportada: {placa_emergencia} | {description}"
        elif vehicle_id and vehicle_id.isdigit():
            # Si eligió su vehículo normal
            vehicle_obj = Vehicle.objects.filter(id=vehicle_id).first()

        try:
            with transaction.atomic():
                Expense.objects.create(
                    user=request.user,
                    company=request.user.current_company,
                    receipt_image=image,
                    description=description,
                    total_amount=0.00, 
                    vehicle=vehicle_obj, # Si fue emergencia, esto se guarda vacío
                    status='PENDING',
                    origin='PILOT', 
                    provider_name="Pendiente",
                    date=timezone.now(), 
                    tax_base=0, 
                    tax_iva=0, 
                    tax_idp=0
                )
            messages.success(request, "🚀 Gasto enviado. Contabilidad lo revisará.")
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f"Error al guardar el gasto: {str(e)}")
            return redirect('pilot_upload') 
            
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
        return redirect('expense_pending_list')

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
        return redirect('approve_expense', pk=expense.id)

    return render(request, 'accounting/review_expense.html', {'expense': expense})


@login_required
def approve_expense(request, pk):
    """Aprueba, descuenta del banco y genera partida contable NIIF"""
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if expense.status == 'APPROVED':
        messages.warning(request, "Este gasto ya fue contabilizado.")
        return redirect('expense_pending_list') # Tu redirección original

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
                # Ya no usamos created_by, total, ni expense_ref porque los borramos en la migración
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
            
            # Rebajamos el saldo del módulo de bancos
            if cuenta_banco:
                cuenta_banco.balance -= decimal.Decimal(str(monto_total))
                cuenta_banco.save()

            # 5. FINALIZAR
            expense.status = 'APPROVED'
            expense.save()
            messages.success(request, f"✅ Gasto Contabilizado Exitosamente (Partida #{entry.id}).")

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    # Redirige exactamente a donde tú lo tenías configurado
    return redirect('expense_pending_list')


@login_required
def reject_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    expense.status = 'REJECTED'
    expense.save()
    messages.warning(request, "Gasto rechazado.")
    return redirect('expense_pending_list')

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
    total_balance = sum(acc.balance for acc in accounts)
    recent_transactions = BankTransaction.objects.filter(company=request.user.current_company).order_by('-date')[:10]
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
    return render(request, 'accounting/transaction_form.html', {'form': form, 'tx_type': tx_type, 'title': 'Registrar Transacción'})

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
def chart_of_accounts(request):
    simulated_accounts = [
        {'code': '1', 'name': 'ACTIVO', 'level': 1, 'type': 'Rubro', 'niif_tag': 'ESF'},
        {'code': '1.1', 'name': 'ACTIVO CORRIENTE', 'level': 2, 'type': 'Grupo', 'niif_tag': 'NIC 1'},
    ]
    return render(request, 'accounting/chart_of_accounts.html', {'accounts': simulated_accounts})

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