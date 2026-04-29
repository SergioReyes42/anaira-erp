from django.db import transaction
import datetime
import decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction # <--- Importación vital
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.db.models import Sum, Q, F, Value, DecimalField, Case, When, CharField
from django.core.paginator import Paginator # Agrega esto arriba si no lo tienes
from core.reporting import export_to_excel, export_to_pdf
from .decorators import group_required  # <--- Importas el candado
from django.forms import modelformset_factory
from django.db.models import Prefetch
from .models import AccountingPeriod
from sales.models import SaleInvoice
from .forms import DepositForm
from .models import GastoOperativo, Vehicle

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
    AccountPayable,
    Supplier
)
from .forms import BankAccountForm, BankTransactionForm, VehicleForm
from .utils import normalize_scanner_image, build_scanner_expense_payload, analyze_invoice_image


def _current_company_key(request):
    """
    Estandariza el identificador de empresa para JournalEntry.company (CharField)
    sin romper compatibilidad con registros antiguos.
    """
    company = getattr(request.user, 'current_company', None)
    if not company:
        return None
    return str(getattr(company, 'id', company))


def _safe_int(value, default):
    """
    Convierte a int de forma segura para evitar errores por valores mal codificados
    (ej: '\\x0026') provenientes de querystring.
    """
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default

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
        # 🔥 EL FIX ESTÁ AQUÍ: Cambiamos "Vehicle" por "Vehiculo" para que coincida con GastoOperativo
        vehicles = Vehicle.objects.filter(company=request.user.current_company)
    else:
        # 🔥 Y AQUÍ TAMBIÉN
        vehicles = Vehicle.objects.none()

    if request.method == 'POST':
        receipt_image = request.FILES.get('receipt_image')
        pump_image = request.FILES.get('pump_image')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        vehicle_id = request.POST.get('vehicle')

        try:
            with transaction.atomic():
                GastoOperativo.objects.create(
                    user=request.user,
                    receipt_image=receipt_image,
                    pump_image=pump_image,
                    latitude=latitude,
                    longitude=longitude,
                    total_amount=0.00,  
                    vehicle_id=vehicle_id if vehicle_id and vehicle_id.isdigit() else None, 
                    estado='Pendiente', 
                    date=timezone.now()
                )
                
            messages.success(request, "🚀 Gasto enviado. El equipo de Supervisión lo revisará.")
            return redirect('core:home')
            
        except Exception:
            messages.error(request, "Error al guardar el gasto. Verifica que las fotos sean válidas e intenta de nuevo.")
            return redirect('accounting:pilot_upload')
            
    return render(request, 'accounting/pilot_upload.html', {'vehicles': vehicles})

@login_required 
def smart_scanner(request):
    """VISTA CONTADOR: Scanner con IA + fallback operativo si la IA o storage fallan."""
    
    vehiculos = Vehicle.objects.filter(company=request.user.current_company, active=True) if request.user.current_company else []

    if request.method == 'POST':
        image = request.FILES.get('documento') or request.FILES.get('receipt_image') or request.FILES.get('factura')
        smart_input = request.POST.get('smart_input', '')
        vehicle_id = request.POST.get('vehicle')
        vehicle_obj = Vehicle.objects.filter(id=vehicle_id).first() if vehicle_id else None

        if not request.user.current_company:
            messages.error(request, "⛔ Tu usuario no tiene una empresa asignada. Contacta al Administrador.")
            return redirect('core:home')

        if not image:
            messages.error(request, "Debes adjuntar una imagen de factura.")
            return redirect('accounting:smart_scanner')

        try:
            normalized_image = normalize_scanner_image(image)
            safe_name = f"scanner_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            image_file = ContentFile(normalized_image.read(), name=safe_name)

            payload = build_scanner_expense_payload(
                user=request.user,
                company=request.user.current_company,
                vehicle_obj=vehicle_obj,
                smart_input=smart_input,
                include_storage_flag=False,
            )

            # Intento IA (no bloqueante)
            ai_ok = False
            try:
                normalized_image.seek(0)
                ai_data = analyze_invoice_image(normalized_image, smart_input=smart_input)

                payload["provider_name"] = (ai_data.get("provider_name") or payload["provider_name"])[:255]
                payload["provider_nit"] = (ai_data.get("provider_nit") or payload["provider_nit"])[:50]
                payload["invoice_series"] = (ai_data.get("invoice_series") or payload["invoice_series"])[:50]
                payload["invoice_number"] = (ai_data.get("invoice_number") or payload["invoice_number"])[:50]
                payload["description"] = (ai_data.get("description") or payload["description"])[:255]
                payload["suggested_account"] = (ai_data.get("account_type") or payload["suggested_account"])[:100]
                payload["total_amount"] = decimal.Decimal(str(ai_data.get("total") or 0.00))
                ai_ok = True
            except Exception as ai_err:
                print(f"[smart_scanner][IA] fallo no bloqueante: {repr(ai_err)}")

            payload["receipt_image"] = image_file

            with transaction.atomic():
                Expense.objects.create(**payload)

            if ai_ok:
                messages.success(request, "✅ Factura enviada a Pendientes (scanner con IA).")
            else:
                messages.warning(request, "⚠️ IA no disponible temporalmente, factura guardada para revisión.")
            return redirect('accounting:expense_pending_list')

        except Exception as e:
            print(f"[smart_scanner] storage={default_storage.__class__.__name__} error al guardar con imagen: {repr(e)}")
            # Fallback operativo: no bloquear el proceso por fallo de storage en producción
            try:
                fallback_payload = build_scanner_expense_payload(
                    user=request.user,
                    company=request.user.current_company,
                    vehicle_obj=vehicle_obj,
                    smart_input=smart_input,
                    include_storage_flag=True,
                )
                with transaction.atomic():
                    Expense.objects.create(**fallback_payload)
                messages.warning(request, "⚠️ Factura guardada en Pendientes sin imagen. Configura CLOUDINARY_URL en Railway para guardar adjuntos.")
                return redirect('accounting:expense_pending_list')
            except Exception as e2:
                print(f"[smart_scanner] error en fallback sin imagen: {e2}")
                messages.error(request, "❌ No se pudo guardar la factura. Intenta nuevamente.")
                return redirect('accounting:smart_scanner')

    return render(request, 'accounting/smart_hub.html', {'vehiculos': vehiculos})


@login_required
def upload_expense_photo(request):
    return redirect('accounting:smart_scanner')

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
                company=_current_company_key(request),
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
    company_key = _current_company_key(request)
    entries = JournalEntry.objects.filter(
        company__in=[company_key, str(request.user.current_company)]
    ).prefetch_related(
        Prefetch('lines', queryset=JournalEntryLine.objects.select_related('account'))
    ).order_by('-date', '-id')
    
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
            return redirect('accounting:bank_dashboard')
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
                    account=cuenta,
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
    if not request.user.current_company:
        messages.error(request, "⛔ Tu usuario no tiene una empresa asignada. Contacta al Administrador.")
        return redirect('core:home')

    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            v = form.save(commit=False)
            v.company = request.user.current_company
            v.save()
            messages.success(request, "Vehículo creado.")
            return redirect('accounting:vehicle_list')
        messages.error(request, "Revisa el formulario. Hay campos inválidos.")
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
            return redirect('accounting:chart_of_accounts')

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

from django.http import JsonResponse

@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def analyze_receipt_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido.'}, status=405)

    if not request.user.current_company:
        return JsonResponse({'success': False, 'error': 'Usuario sin empresa asignada.'}, status=400)

    image = request.FILES.get('receipt_image') or request.FILES.get('documento') or request.FILES.get('factura')
    smart_input = (request.POST.get('smart_input') or '').strip()

    if not image:
        return JsonResponse({'success': False, 'error': 'Debes adjuntar una imagen o PDF de factura/recibo.'}, status=400)

    try:
        normalized = normalize_scanner_image(image)
        normalized.seek(0)

        ai_data = analyze_invoice_image(normalized, smart_input=smart_input) or {}

        provider_name = (ai_data.get("provider_name") or "").strip()
        provider_nit = (ai_data.get("provider_nit") or "").strip()
        invoice_series = (ai_data.get("invoice_series") or "").strip()
        invoice_number = (ai_data.get("invoice_number") or "").strip()
        description = (ai_data.get("description") or "").strip()
        account_type = (ai_data.get("account_type") or "").strip()
        total_raw = ai_data.get("total", "0")

        try:
            total_amount = str(decimal.Decimal(str(total_raw or "0")).quantize(decimal.Decimal('0.01')))
        except Exception:
            total_amount = "0.00"

        invoice_full = "-".join([v for v in [invoice_series, invoice_number] if v]).strip("-")
        if not invoice_full:
            invoice_full = invoice_number

        return JsonResponse({
            'success': True,
            'data': {
                'provider_name': provider_name,
                'provider_nit': provider_nit,
                'invoice_number': invoice_full,
                'description': description,
                'total_amount': total_amount,
                'suggested_account': account_type,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'No se pudo analizar el documento con IA: {str(e)}'
        }, status=500)

@login_required
def mobile_expense(request):
    vehicles = Vehicle.objects.filter(company=request.user.current_company, active=True)
    return render(request, 'accounting/expense_form.html', {'vehicles': vehicles})

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def fleet_expense_report(request):
    """Reporte profesional de gastos de flotilla con filtros y clasificación robusta."""
    vehicles = Vehicle.objects.filter(company=request.user.current_company).order_by('plate')
    qs = Expense.objects.filter(company=request.user.current_company, vehicle__isnull=False)

    vehicle_id = request.GET.get('vehicle_id', '').strip()
    category = request.GET.get('category', 'both').strip() or 'both'

    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)

    fuel_q = Q(description__icontains='combustible') | Q(description__icontains='diesel') | Q(description__icontains='gasolina')
    maint_q = Q(description__icontains='mantenimiento') | Q(description__icontains='repuesto') | Q(description__icontains='taller') | Q(description__icontains='llanta')

    if category == 'fuel':
        qs = qs.filter(fuel_q)
    elif category == 'maint':
        qs = qs.filter(maint_q)
    else:
        qs = qs.filter(fuel_q | maint_q)

    qs = qs.annotate(
        expense_type=Case(
            When(fuel_q, then=Value('Combustible')),
            When(maint_q, then=Value('Mantenimiento')),
            default=Value('Otro'),
            output_field=CharField()
        )
    ).order_by('-date')

    total_fuel = qs.filter(expense_type='Combustible').aggregate(t=Sum('total_amount'))['t'] or decimal.Decimal('0.00')
    total_maint = qs.filter(expense_type='Mantenimiento').aggregate(t=Sum('total_amount'))['t'] or decimal.Decimal('0.00')
    gran_total = total_fuel + total_maint

    selected_vehicle_obj = None
    if vehicle_id:
        selected_vehicle_obj = vehicles.filter(id=vehicle_id).first()

    context = {
        'expenses': qs,
        'vehicles': vehicles,
        'total_fuel': total_fuel,
        'total_maint': total_maint,
        'gran_total': gran_total,
        'selected_vehicle': vehicle_id,
        'selected_vehicle_obj': selected_vehicle_obj,
        'selected_category': category,
    }
    return render(request, 'accounting/fleet_report.html', context)


@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def fleet_expense_report_pdf(request):
    """Descarga PDF profesional del reporte de flotilla respetando filtros."""
    vehicles = Vehicle.objects.filter(company=request.user.current_company).order_by('plate')
    qs = Expense.objects.filter(company=request.user.current_company, vehicle__isnull=False)

    vehicle_id = request.GET.get('vehicle_id', '').strip()
    category = request.GET.get('category', 'both').strip() or 'both'

    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)

    fuel_q = Q(description__icontains='combustible') | Q(description__icontains='diesel') | Q(description__icontains='gasolina')
    maint_q = Q(description__icontains='mantenimiento') | Q(description__icontains='repuesto') | Q(description__icontains='taller') | Q(description__icontains='llanta')

    if category == 'fuel':
        qs = qs.filter(fuel_q)
    elif category == 'maint':
        qs = qs.filter(maint_q)
    else:
        qs = qs.filter(fuel_q | maint_q)

    qs = qs.annotate(
        expense_type=Case(
            When(fuel_q, then=Value('Combustible')),
            When(maint_q, then=Value('Mantenimiento')),
            default=Value('Otro'),
            output_field=CharField()
        )
    ).order_by('-date')

    total_fuel = qs.filter(expense_type='Combustible').aggregate(t=Sum('total_amount'))['t'] or decimal.Decimal('0.00')
    total_maint = qs.filter(expense_type='Mantenimiento').aggregate(t=Sum('total_amount'))['t'] or decimal.Decimal('0.00')
    gran_total = total_fuel + total_maint

    selected_vehicle_obj = vehicles.filter(id=vehicle_id).first() if vehicle_id else None
    vehicle_label = f"{selected_vehicle_obj.plate} - {selected_vehicle_obj.brand}" if selected_vehicle_obj else "Toda la Flotilla"
    category_label = {
        'both': 'Combustible + Mantenimiento',
        'fuel': 'Solo Combustible',
        'maint': 'Solo Mantenimiento'
    }.get(category, 'Combustible + Mantenimiento')

    headers = ["Fecha", "Vehículo", "Piloto", "Tipo", "Estado", "Monto (Q)"]
    rows = [
        ["Filtro Vehículo", vehicle_label, "", "Filtro Rubro", category_label, ""],
        ["Total Combustible", f"{float(total_fuel):.2f}", "", "Total Mantenimiento", f"{float(total_maint):.2f}", f"Total General: {float(gran_total):.2f}"],
        ["", "", "", "", "", ""],
    ]

    for expense in qs:
        rows.append([
            expense.date.strftime("%d/%m/%Y %H:%M") if expense.date else "",
            f"{expense.vehicle.plate} - {expense.vehicle.brand}" if expense.vehicle else "",
            expense.user.get_full_name() if expense.user and expense.user.get_full_name() else (expense.user.username if expense.user else ""),
            expense.expense_type,
            "Pendiente" if expense.status == "PENDING" else "Aprobado",
            f"{float(expense.total_amount or 0):.2f}",
        ])

    title = f"Reporte Profesional de Flotilla - {vehicle_label}"
    filename = f"reporte_flotilla_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
    return export_to_pdf(filename, title, headers, rows)

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def export_general_journal_excel(request):
    """Exporta Libro Diario General a Excel"""
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year

    mes = _safe_int(request.GET.get('mes', mes_actual), mes_actual)
    anio = _safe_int(request.GET.get('anio', anio_actual), anio_actual)
    company_key = _current_company_key(request)

    partidas = JournalEntry.objects.filter(
        company__in=[company_key, str(request.user.current_company)],
        date__year=anio,
        date__month=mes
    ).prefetch_related(
        Prefetch('lines', queryset=JournalEntryLine.objects.select_related('account'))
    ).order_by('date', 'id')

    headers = ["Fecha", "Partida", "Concepto", "Cuenta", "Código", "Debe", "Haber"]
    rows = []
    for partida in partidas:
        for line in partida.lines.all():
            rows.append([
                partida.date.strftime("%d/%m/%Y"),
                partida.id,
                partida.concept or "",
                line.account.name if line.account else "",
                line.account.code if line.account else "",
                float(line.debit or 0),
                float(line.credit or 0),
            ])

    filename = f"libro_diario_{anio}_{mes:02d}"
    return export_to_excel(filename, headers, rows)


@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def export_general_journal_pdf(request):
    """Exporta Libro Diario General a PDF"""
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year

    mes = _safe_int(request.GET.get('mes', mes_actual), mes_actual)
    anio = _safe_int(request.GET.get('anio', anio_actual), anio_actual)
    company_key = _current_company_key(request)

    partidas = JournalEntry.objects.filter(
        company__in=[company_key, str(request.user.current_company)],
        date__year=anio,
        date__month=mes
    ).prefetch_related(
        Prefetch('lines', queryset=JournalEntryLine.objects.select_related('account'))
    ).order_by('date', 'id')

    headers = ["Fecha", "Partida", "Concepto", "Cuenta", "Código", "Debe", "Haber"]
    rows = []
    for partida in partidas:
        for line in partida.lines.all():
            rows.append([
                partida.date.strftime("%d/%m/%Y"),
                str(partida.id),
                (partida.concept or "")[:60],
                (line.account.name if line.account else "")[:40],
                line.account.code if line.account else "",
                f"{float(line.debit or 0):.2f}",
                f"{float(line.credit or 0):.2f}",
            ])

    title = f"Libro Diario General - {mes:02d}/{anio}"
    filename = f"libro_diario_{anio}_{mes:02d}"
    return export_to_pdf(filename, title, headers, rows)


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
            return redirect('core:home')

        except Exception as e:
            # Si descuadra, borramos la partida fallida y le avisamos
            partida.delete()
            messages.error(request, str(e))
            return redirect('accounting:opening_balance')

    return render(request, 'accounting/opening_balance.html', {'cuentas': cuentas})

@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def general_journal(request):
    """Libro Diario General Profesional (NIIF)"""
    
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year
    
    mes = _safe_int(request.GET.get('mes', mes_actual), mes_actual)
    anio = _safe_int(request.GET.get('anio', anio_actual), anio_actual)
    company_key = _current_company_key(request)

    partidas = JournalEntry.objects.filter(
        company__in=[company_key, str(request.user.current_company)],
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
    
    cuentas = Account.objects.filter(is_transactional=True).order_by('code')
    
    mes_actual = timezone.now().month
    anio_actual = timezone.now().year
    
    account_id = request.GET.get('account_id')
    mes = _safe_int(request.GET.get('mes', mes_actual), mes_actual)
    anio = _safe_int(request.GET.get('anio', anio_actual), anio_actual)
    company_key = _current_company_key(request)
    
    lineas = []
    cuenta_seleccionada = None
    saldo_acumulado = decimal.Decimal('0.00')
    total_debe = decimal.Decimal('0.00')
    total_haber = decimal.Decimal('0.00')

    if account_id:
        cuenta_seleccionada = Account.objects.get(id=account_id)
        
        lineas = JournalEntryLine.objects.filter(
            account=cuenta_seleccionada,
            entry__company__in=[company_key, str(request.user.current_company)],
            entry__date__year=anio,
            entry__date__month=mes
        ).select_related('entry').order_by('entry__date', 'entry__id')
        
        for linea in lineas:
            total_debe += linea.debit
            total_haber += linea.credit
            
            if cuenta_seleccionada.account_type in ['ASSET', 'EXPENSE']:
                saldo_acumulado += (linea.debit - linea.credit)
            else:
                saldo_acumulado += (linea.credit - linea.debit)
                
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
    
    anio = _safe_int(request.GET.get('anio', timezone.now().year), timezone.now().year)
    mes = _safe_int(request.GET.get('mes', timezone.now().month), timezone.now().month)
    company_key = _current_company_key(request)

    if mes == 12:
        siguiente_mes = datetime.date(anio + 1, 1, 1)
    else:
        siguiente_mes = datetime.date(anio, mes + 1, 1)
    
    lineas = JournalEntryLine.objects.filter(
        entry__date__lt=siguiente_mes,
        entry__company__in=[company_key, str(request.user.current_company)]
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
    
    anio = _safe_int(request.GET.get('anio', timezone.now().year), timezone.now().year)
    mes = _safe_int(request.GET.get('mes', timezone.now().month), timezone.now().month)
    company_key = _current_company_key(request)

    fecha_inicio = datetime.date(anio, mes, 1)
    if mes == 12:
        fecha_fin = datetime.date(anio + 1, 1, 1)
    else:
        fecha_fin = datetime.date(anio, mes + 1, 1)

    lineas = JournalEntryLine.objects.filter(
        entry__date__gte=fecha_inicio,
        entry__date__lt=fecha_fin,
        entry__company__in=[company_key, str(request.user.current_company)],
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
    
    anio = _safe_int(request.GET.get('anio', timezone.now().year), timezone.now().year)
    mes = _safe_int(request.GET.get('mes', timezone.now().month), timezone.now().month)
    company_key = _current_company_key(request)

    if mes == 12:
        fecha_fin = datetime.date(anio + 1, 1, 1)
    else:
        fecha_fin = datetime.date(anio, mes + 1, 1)

    lineas = JournalEntryLine.objects.filter(
        entry__date__lt=fecha_fin,
        entry__company__in=[company_key, str(request.user.current_company)]
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
    
    anio = _safe_int(request.GET.get('anio', timezone.now().year), timezone.now().year)
    mes = _safe_int(request.GET.get('mes', timezone.now().month), timezone.now().month)

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
            
        return redirect('accounting:fiscal_close')
        
    return render(request, 'accounting/fiscal_close.html', {
        'periodos': periodos, 
        'meses': range(1, 13), 
        'anios': range(2025, 2030)
    })
@login_required
@group_required('Contadora', 'Gerente', 'Administrador')
def sales_ledger(request):
    """Libro de Ventas y Servicios Prestados (Formato SAT Guatemala)"""
    
    anio = _safe_int(request.GET.get('anio', timezone.now().year), timezone.now().year)
    mes = _safe_int(request.GET.get('mes', timezone.now().month), timezone.now().month)

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
                vehiculo_obj = Vehicle.objects.get(id=vehicle_id)
            except Vehicle.DoesNotExist:
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
    vehiculos_disponibles = Vehicle.objects.all() 
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
        
        return redirect('accounting:smart_hub') # Lo mandas a donde quieras tras guardar

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
                    account=cuenta,
                    transaction_type='WITHDRAWAL',
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
                    account=cuenta_origen,
                    transaction_type='WITHDRAWAL',
                    amount=monto,
                    reference=reference,
                    description=f"Transferencia a: {cuenta_destino.bank_name} - {description}",
                    date=date
                )

                # 6. Registrar la entrada en el historial (Destino)
                BankTransaction.objects.create(
                    account=cuenta_destino,
                    transaction_type='DEPOSIT', # Ingreso a cuenta destino
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
                    account=cuenta,
                    transaction_type='WITHDRAWAL', # Salida de banco por pago de tarjeta
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
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def manual_journal_entry_create(request):
    """Creación manual de partidas contables (Libro Diario)."""
    cuentas = Account.objects.filter(is_transactional=True).order_by('code')

    if request.method == 'POST':
        fecha = request.POST.get('date')
        concepto = (request.POST.get('concept') or '').strip()
        account_ids = request.POST.getlist('account_id[]')
        debits = request.POST.getlist('debit[]')
        credits = request.POST.getlist('credit[]')

        if not fecha or not concepto:
            messages.error(request, "La fecha y el concepto son obligatorios.")
            return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

        lineas = []
        total_debe = decimal.Decimal('0.00')
        total_haber = decimal.Decimal('0.00')

        for i in range(len(account_ids)):
            account_id = (account_ids[i] or '').strip()
            debit_raw = (debits[i] or '0').strip()
            credit_raw = (credits[i] or '0').strip()

            if not account_id:
                continue

            try:
                cuenta = Account.objects.get(id=account_id, is_transactional=True)
            except Account.DoesNotExist:
                messages.error(request, "Se seleccionó una cuenta inválida.")
                return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

            try:
                debe = decimal.Decimal(debit_raw or '0')
                haber = decimal.Decimal(credit_raw or '0')
            except decimal.InvalidOperation:
                messages.error(request, "Hay valores numéricos inválidos en Debe/Haber.")
                return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

            if debe < 0 or haber < 0:
                messages.error(request, "Debe/Haber no permiten valores negativos.")
                return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

            if debe == 0 and haber == 0:
                continue

            if debe > 0 and haber > 0:
                messages.error(request, "Cada línea debe tener valor solo en Debe o solo en Haber.")
                return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

            lineas.append({
                'cuenta': cuenta,
                'debe': debe,
                'haber': haber,
            })
            total_debe += debe
            total_haber += haber

        if not lineas:
            messages.error(request, "Debes ingresar al menos una línea contable válida.")
            return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

        if total_debe != total_haber:
            messages.error(request, f"La partida no cuadra. Debe: Q {total_debe} / Haber: Q {total_haber}")
            return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})

        try:
            with transaction.atomic():
                partida = JournalEntry.objects.create(
                    date=fecha,
                    concept=concepto,
                    company=_current_company_key(request),
                    is_opening_balance=False
                )

                for linea in lineas:
                    JournalEntryLine.objects.create(
                        entry=partida,
                        account=linea['cuenta'],
                        debit=linea['debe'],
                        credit=linea['haber']
                    )

            messages.success(request, f"✅ Partida manual creada exitosamente (Pda #{partida.id}).")
            return redirect('accounting:general_journal')

        except Exception as e:
            messages.error(request, f"Error al guardar la partida manual: {str(e)}")

    return render(request, 'accounting/manual_journal_entry_create.html', {'cuentas': cuentas})


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def cxc_dashboard_view(request):
    return render(request, 'accounting/cxc_dashboard.html')


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def payment_schedule_view(request):
    return render(request, 'accounting/payment_schedule.html')


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def credit_debit_notes_view(request):
    return render(request, 'accounting/credit_debit_notes.html')


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def purchase_history(request):
    return render(request, 'accounting/purchase_history.html')


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def purchase_create(request):
    if not request.user.current_company:
        messages.error(request, "⛔ Tu usuario no tiene una empresa asignada.")
        return redirect('core:home')

    suppliers = Supplier.objects.filter(company=request.user.current_company, active=True).order_by('name')
    vehicles = Vehicle.objects.filter(company=request.user.current_company, active=True).order_by('plate')

    if request.method == 'POST':
        supplier_id = (request.POST.get('supplier_id') or '').strip()
        provider_name_manual = (request.POST.get('provider_name_manual') or '').strip()
        provider_nit_manual = (request.POST.get('provider_nit_manual') or '').strip()
        expense_category = (request.POST.get('expense_category') or 'otros').strip()
        invoice_number = (request.POST.get('invoice_number') or '').strip()
        description = (request.POST.get('description') or '').strip()
        total_amount_raw = (request.POST.get('total_amount') or '0').strip()
        payment_method = (request.POST.get('payment_method') or 'EFECTIVO').strip()
        vehicle_id = (request.POST.get('vehicle') or '').strip()
        receipt_file = request.FILES.get('receipt_image')

        supplier_obj = None
        provider_name = provider_name_manual
        provider_nit = provider_nit_manual

        if supplier_id:
            supplier_obj = Supplier.objects.filter(
                id=supplier_id,
                company=request.user.current_company,
                active=True
            ).first()
            if not supplier_obj:
                messages.error(request, "Proveedor inválido.")
                return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})
            provider_name = supplier_obj.name
            provider_nit = supplier_obj.nit or provider_nit

        if not provider_name or not description:
            messages.error(request, "Proveedor y descripción son obligatorios.")
            return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})

        try:
            total_amount = decimal.Decimal(total_amount_raw)
        except decimal.InvalidOperation:
            messages.error(request, "Monto inválido.")
            return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})

        if total_amount <= 0:
            messages.error(request, "El monto debe ser mayor a cero.")
            return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})

        vehicle_obj = None
        if vehicle_id:
            vehicle_obj = Vehicle.objects.filter(id=vehicle_id, company=request.user.current_company).first()

        account_map = {
            'sueldos': 'Sueldos y Salarios',
            'servicios': 'Servicios Básicos',
            'alquiler': 'Alquileres',
            'viaticos': 'Viáticos',
            'combustible_varios': 'Combustible Varios (Sin Placa)',
            'combustible_flotilla': 'Combustible y Lubricantes',
            'otros': 'Gastos Generales',
        }
        suggested_account = account_map.get(expense_category, 'Gastos Generales')

        # Regla solicitada: combustible sin placa = cuenta separada, no afecta reporte por placa
        if expense_category == 'combustible_varios':
            vehicle_obj = None
            suggested_account = 'Combustible Varios (Sin Placa)'

        if expense_category == 'combustible_flotilla' and not vehicle_obj:
            messages.error(request, "Para combustible de flotilla debes seleccionar una placa.")
            return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})

        if not receipt_file:
            messages.error(request, "Debes adjuntar factura/recibo.")
            return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})

        try:
            with transaction.atomic():
                Expense.objects.create(
                    user=request.user,
                    company=request.user.current_company,
                    status='PENDING',
                    origin='MANUAL',
                    payment_method=payment_method,
                    receipt_image=receipt_file,
                    description=description,
                    provider_name=provider_name,
                    provider_nit=provider_nit or None,
                    vehicle=vehicle_obj,
                    suggested_account=suggested_account,
                    total_amount=total_amount,
                    tax_base=total_amount,
                    tax_iva=decimal.Decimal('0.00'),
                    tax_idp=decimal.Decimal('0.00'),
                    invoice_number=invoice_number or f"CMP-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                )

            if vehicle_obj:
                messages.success(request, f"✅ Compra registrada para placa {vehicle_obj.plate}.")
            else:
                messages.success(request, "✅ Compra registrada como gasto general sin placa (no afecta reporte por vehículo).")
            return redirect('accounting:expense_pending_list')
        except Exception as e:
            messages.error(request, f"Error al registrar compra: {str(e)}")

    return render(request, 'accounting/purchase_create.html', {'suppliers': suppliers, 'vehicles': vehicles})


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def suppliers_list(request):
    if not request.user.current_company:
        messages.error(request, "⛔ Tu usuario no tiene una empresa asignada.")
        return redirect('core:home')

    editing_id = (request.GET.get('edit') or '').strip()
    supplier_edit = None
    if editing_id.isdigit():
        supplier_edit = Supplier.objects.filter(
            id=int(editing_id),
            company=request.user.current_company
        ).first()

    if request.method == 'POST':
        action = (request.POST.get('action') or 'create').strip()
        supplier_id = (request.POST.get('supplier_id') or '').strip()
        name = (request.POST.get('name') or '').strip()
        nit = (request.POST.get('nit') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        email = (request.POST.get('email') or '').strip()
        address = (request.POST.get('address') or '').strip()
        active = (request.POST.get('active') == 'on')

        if not name:
            messages.error(request, "El nombre del proveedor es obligatorio.")
            return redirect('accounting:suppliers_list')

        if action == 'update' and supplier_id.isdigit():
            sup = Supplier.objects.filter(id=int(supplier_id), company=request.user.current_company).first()
            if not sup:
                messages.error(request, "Proveedor no encontrado.")
                return redirect('accounting:suppliers_list')

            sup.name = name
            sup.nit = nit or None
            sup.phone = phone or None
            sup.email = email or None
            sup.address = address or None
            sup.active = active
            try:
                sup.save()
                messages.success(request, "✅ Proveedor actualizado.")
            except Exception as e:
                messages.error(request, f"Error al actualizar proveedor: {str(e)}")
            return redirect('accounting:suppliers_list')

        try:
            Supplier.objects.create(
                company=request.user.current_company,
                name=name,
                nit=nit or None,
                phone=phone or None,
                email=email or None,
                address=address or None,
                active=True
            )
            messages.success(request, "✅ Proveedor registrado.")
        except Exception as e:
            messages.error(request, f"Error al registrar proveedor: {str(e)}")

        return redirect('accounting:suppliers_list')

    suppliers = Supplier.objects.filter(company=request.user.current_company).order_by('name')
    return render(request, 'accounting/suppliers_list.html', {
        'suppliers': suppliers,
        'supplier_edit': supplier_edit,
    })


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def ai_expense_register(request):
    vehicles = Vehicle.objects.filter(company=request.user.current_company, active=True) if request.user.current_company else []

    if request.method == 'POST':
        if not request.user.current_company:
            messages.error(request, "⛔ Tu usuario no tiene una empresa asignada.")
            return redirect('core:home')

        expense_category = (request.POST.get('expense_category') or 'otros').strip()
        provider_name = (request.POST.get('provider_name') or '').strip()
        provider_nit = (request.POST.get('provider_nit') or '').strip()
        description = (request.POST.get('description') or '').strip()
        total_amount_raw = (request.POST.get('total_amount') or '0').strip()
        payment_method = (request.POST.get('payment_method') or 'EFECTIVO').strip()
        vehicle_id = (request.POST.get('vehicle') or '').strip()
        receipt_file = request.FILES.get('receipt_image')
        invoice_number = (request.POST.get('invoice_number') or '').strip()

        if not provider_name or not description:
            messages.error(request, "Proveedor/beneficiario y descripción son obligatorios.")
            return render(request, 'accounting/ai_expense_register.html', {'vehicles': vehicles})

        try:
            total_amount = decimal.Decimal(total_amount_raw)
        except decimal.InvalidOperation:
            messages.error(request, "Monto inválido.")
            return render(request, 'accounting/ai_expense_register.html', {'vehicles': vehicles})

        if total_amount <= 0:
            messages.error(request, "El monto debe ser mayor a cero.")
            return render(request, 'accounting/ai_expense_register.html', {'vehicles': vehicles})

        vehicle_obj = None
        if vehicle_id:
            vehicle_obj = Vehicle.objects.filter(
                id=vehicle_id,
                company=request.user.current_company
            ).first()

        account_map = {
            'sueldos': 'Sueldos y Salarios',
            'servicios': 'Servicios Básicos',
            'alquiler': 'Alquileres',
            'viaticos': 'Viáticos',
            'combustible_varios': 'Combustible Varios (Sin Placa)',
            'otros': 'Gastos Generales',
        }
        suggested_account = account_map.get(expense_category, 'Gastos Generales')

        try:
            with transaction.atomic():
                expense = Expense.objects.create(
                    user=request.user,
                    company=request.user.current_company,
                    status='PENDING',
                    origin='MANUAL',
                    payment_method=payment_method,
                    receipt_image=receipt_file,
                    description=description,
                    provider_name=provider_name,
                    provider_nit=provider_nit or None,
                    vehicle=vehicle_obj,
                    suggested_account=suggested_account,
                    total_amount=total_amount,
                    tax_base=total_amount,
                    tax_iva=decimal.Decimal('0.00'),
                    tax_idp=decimal.Decimal('0.00'),
                    invoice_number=invoice_number or f"MAN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                )

            if vehicle_obj:
                messages.success(request, f"✅ Gasto registrado y vinculado a placa {vehicle_obj.plate}. Se enviará a contabilización.")
            else:
                messages.success(request, "✅ Gasto registrado como gasto general (sin placa). No afectará reportes por vehículo.")
            return redirect('accounting:expense_pending_list')

        except Exception as e:
            messages.error(request, f"Error al registrar gasto: {str(e)}")

    return render(request, 'accounting/ai_expense_register.html', {'vehicles': vehicles})


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def operating_expenses(request):
    return render(request, 'accounting/operating_expenses.html')


@login_required
@group_required('Contadora', 'Auxiliar Contable', 'Gerente', 'Administrador')
def purchase_orders(request):
    return render(request, 'accounting/purchase_orders.html')


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