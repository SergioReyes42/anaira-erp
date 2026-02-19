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
from .forms import BankAccountForm, BankTransactionForm, VehicleForm
from .utils import analyze_invoice_image

# ========================================================
# 1. HERRAMIENTAS DE INGRESO (PILOTOS Y CONTADOR)
# ========================================================

@login_required
def pilot_upload(request):
    """
    VISTA PILOTOS: Carga rápida.
    CORRECCIÓN: Quitamos el filtro 'active=True' que daba error.
    """
    # 1. Obtenemos todos los vehículos de la empresa (sin filtrar por active)
    vehicles = Vehicle.objects.filter(company=request.user.current_company)

    if request.method == 'POST':
        image = request.FILES.get('documento')
        description = request.POST.get('description', 'Gasto de Ruta')
        vehicle_id = request.POST.get('vehicle')
        
        # Buscar vehículo
        vehicle_obj = None
        if vehicle_id:
            vehicle_obj = Vehicle.objects.filter(id=vehicle_id).first()

        try:
            Expense.objects.create(
                user=request.user,
                company=request.user.current_company,
                receipt_image=image,
                description=description,
                total_amount=0.00, # Automático en 0
                vehicle=vehicle_obj,
                status='PENDING',
                provider_name="Pendiente",
                suggested_account="Por Asignar",
                tax_base=0, tax_iva=0, tax_idp=0
            )
            messages.success(request, "🚀 Gasto enviado. Contabilidad lo revisará.")
            return redirect('home')
        except Exception as e:
            messages.error(request, f"Error: {e}")
            
    return render(request, 'accounting/pilot_upload.html', {'vehicles': vehicles})


@login_required
def smart_scanner(request):
    """
    VISTA CONTADOR: Escaneo con IA.
    Aquí SÍ calcula impuestos y lee la factura.
    """
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
            # Lógica IDP (Aprox)
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

        # 3. Guardar
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


# Compatibilidad para enlaces viejos
@login_required
def upload_expense_photo(request):
    return redirect('smart_scanner')


# ========================================================
# 2. FLUJO DE APROBACIÓN Y REVISIÓN
# ========================================================

@login_required
def expense_pending_list(request):
    """Bandeja de Entrada"""
    expenses = Expense.objects.filter(
        company=request.user.current_company, 
        status='PENDING'
    ).order_by('-date')
    return render(request, 'accounting/expense_pending_list.html', {'expenses': expenses})


@login_required
def review_expense(request, pk):
    """
    El contador revisa, edita el monto y define si hubo IDP.
    """
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if request.method == 'POST':
        # 1. Guardar datos básicos
        expense.provider_name = request.POST.get('provider_name')
        expense.provider_nit = request.POST.get('provider_nit')
        expense.invoice_number = request.POST.get('invoice_number')
        expense.description = request.POST.get('description')
        
        # 2. Guardar Montos e Impuestos (Calculados en el HTML)
        total = decimal.Decimal(request.POST.get('total_amount', 0))
        idp = decimal.Decimal(request.POST.get('tax_idp', 0))
        
        expense.total_amount = total
        expense.tax_idp = idp
        
        # Recalcular Base e IVA aquí también por seguridad
        base = (float(total) - float(idp)) / 1.12
        iva = base * 0.12
        
        expense.tax_base = decimal.Decimal(base)
        expense.tax_iva = decimal.Decimal(iva)
        
        # Si hay IDP, sugerimos la cuenta de Combustibles
        if idp > 0:
            expense.suggested_account = "Combustibles y Lubricantes"
        
        expense.save()
        
        # Redirigir a la aprobación final (generar partida)
        return redirect('approve_expense', pk=expense.id)

    return render(request, 'accounting/review_expense.html', {'expense': expense})


@login_required
def approve_expense(request, pk):
    """Genera la Partida Contable"""
    expense = get_object_or_404(Expense, pk=pk, company=request.user.current_company)
    
    if expense.status == 'APPROVED':
        messages.warning(request, "Este gasto ya fue contabilizado.")
        return redirect('expense_pending_list')

    try:
        monto_total = float(expense.total_amount)
        descripcion = expense.description.lower()
        
        # Recálculo final de impuestos
        idp, base, iva = 0.00, 0.00, 0.00
        cuenta_gasto = expense.suggested_account or "Gastos Generales"

        es_combustible = any(x in descripcion for x in ['gasolina', 'combustible', 'diesel'])
        
        if es_combustible:
            cuenta_gasto = "Combustibles y Lubricantes"
            galones_estimados = monto_total / 32.00 
            idp = galones_estimados * 4.70
            base = (monto_total - idp) / 1.12
            iva = base * 0.12
        else:
            base = monto_total / 1.12
            iva = base * 0.12

        # Actualizar gasto
        expense.tax_base = decimal.Decimal(base)
        expense.tax_iva = decimal.Decimal(iva)
        expense.tax_idp = decimal.Decimal(idp)
        
        # Crear Partida
        entry = JournalEntry.objects.create(
            company=request.user.current_company,
            description=f"Prov: {expense.provider_name} - {expense.description[:30]}",
            created_by=request.user,
            total=monto_total,
            expense_ref=expense
        )

        # DEBE
        JournalItem.objects.create(entry=entry, account_name=cuenta_gasto, debit=round(base, 2), credit=0)
        JournalItem.objects.create(entry=entry, account_name="IVA por Cobrar", debit=round(iva, 2), credit=0)
        if idp > 0:
            JournalItem.objects.create(entry=entry, account_name="Impuesto IDP", debit=round(idp, 2), credit=0)

        # HABER
        cuenta_banco = BankAccount.objects.filter(company=request.user.current_company).first()
        nombre_banco = cuenta_banco.bank_name if cuenta_banco else "Caja General"
        
        JournalItem.objects.create(entry=entry, account_name=nombre_banco, debit=0, credit=round(monto_total, 2))
        
        if cuenta_banco:
            cuenta_banco.balance -= decimal.Decimal(monto_total)
            cuenta_banco.save()

        expense.status = 'APPROVED'
        expense.save()
        messages.success(request, "✅ Gasto Contabilizado.")

    except Exception as e:
        messages.error(request, f"Error: {e}")

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

@login_required
def libro_diario(request):
    entries = JournalEntry.objects.filter(company=request.user.current_company).order_by('-date', '-id')
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
            
            acc = tx.bank_account
            if tx_type == 'IN': acc.balance += tx.amount
            else: acc.balance -= tx.amount
            acc.save()
            
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

import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
import json
import os

# --- CONFIGURACIÓN DE GEMINI ---
# ¡IMPORTANTE! Reemplaza esto con tu API KEY real
GENAI_API_KEY = "AIzaSyCZkHsDpbhRWiQvUJcuEdRLlI8s-192VU0" 
genai.configure(api_key=GENAI_API_KEY)

def analyze_receipt_api(request):
    """
    Recibe una imagen por POST, la manda a Gemini Pro Vision
    y devuelve el JSON estructurado con los datos de la factura.
    """
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            img = Image.open(image_file)

            # Prompt Maestro para Gemini
            prompt = """
            Actúa como un asistente contable experto en facturas de Guatemala.
            Analiza esta imagen y extrae la siguiente información en formato JSON estricto:
            {
                "supplier": "Nombre del proveedor",
                "nit": "NIT sin guiones ni espacios extra",
                "date": "YYYY-MM-DD",
                "serie": "Serie de la factura",
                "number": "Número de factura o DTE",
                "total": 0.00 (número decimal),
                "is_fuel": true/false (si es factura de gasolina),
                "idp": 0.00 (si encuentras desglose de IDP, extráelo, si no 0)
            }
            Si algún dato no es visible, pon null. No inventes datos.
            """

            # Llamamos al modelo Gemini 1.5 Flash (Más rápido y barato para esto)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content([prompt, img])
            
            # Limpiamos la respuesta (Gemini a veces pone ```json ... ```)
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(text_response)

            return JsonResponse({'success': True, **data})

        except Exception as e:
            print(f"Error IA: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'No image provided'})

login_required
def mobile_expense(request):
    """Vista para crear un nuevo gasto con IA"""
    if request.method == 'POST':
        # ... aquí va tu lógica de guardar el gasto ...
        # (Si ya la tenías, déjala igual, solo cambia el render del final)
        pass 
    
    # IMPORTANTE: Aquí pasamos la lista de vehículos para el select
    vehicles = Vehicle.objects.filter(company=request.user.current_company, active=True)
    
    # OJO AQUÍ: Asegúrate que apunte al nuevo archivo 'expense_form.html'
    return render(request, 'accounting/expense_form.html', {'vehicles': vehicles})