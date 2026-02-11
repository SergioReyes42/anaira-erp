import csv
import io
from decimal import Decimal
from django.db.models import Sum, F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .forms import ExpensePhotoForm

# Imports de API
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

# Modelos y Serializers
from core.models import Company
from .models import Account, JournalEntry, JournalItem
from .serializers import AccountSerializer, JournalEntrySerializer
from .services import get_balance_sheet, get_income_statement

# =========================================
# 1. REPORTES CONTABLES
# =========================================

@login_required
def libro_diario(request):
    """Vista para ver todas las partidas contables (Journal)"""
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    company = Company.objects.using('default').get(id=company_id)
    
    # Traemos las partidas ordenadas por fecha
    entries = JournalEntry.objects.filter(company=company).prefetch_related('items').order_by('-date', '-id')
    
    return render(request, 'accounting/libro_diario.html', {
        'company': company, 
        'entries': entries
    })

@login_required
def balance_general(request):
    """Vista del Balance General (Estado de Situación Financiera)"""
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    company = Company.objects.using('default').get(id=company_id)
    fecha_corte = request.GET.get('fecha', timezone.now().date())
    
    # Usamos el servicio de cálculo
    datos_balance = get_balance_sheet(company.id, fecha_corte)
    
    return render(request, 'accounting/balance_general.html', {
        'empresa': company, 
        'datos': datos_balance, 
        'fecha': fecha_corte
    })

@login_required
def estado_resultados(request):
    """Vista de Pérdidas y Ganancias"""
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.using('default').get(id=company_id)

    # Fechas por defecto: Primer día del mes actual hasta hoy
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    
    start_date = request.GET.get('start_date', str(inicio_mes))
    end_date = request.GET.get('end_date', str(hoy))

    data = get_income_statement(company.id, start_date, end_date)

    return render(request, 'accounting/estado_resultados.html', {
        'company': company,
        'data': data,
        'start_date': start_date,
        'end_date': end_date
    })

# =========================================
# 2. GESTIÓN DE CATÁLOGO DE CUENTAS
# =========================================

@login_required
def chart_of_accounts(request):
    """Muestra el listado de cuentas EXCLUSIVO de la empresa activa"""
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    company = Company.objects.using('default').get(id=company_id)
    
    accounts = Account.objects.filter(company=company).order_by('code')
    
    return render(request, 'accounting/account_list.html', {
        'company': company,
        'accounts': accounts
    })

@login_required
def account_create(request):
    """Permite crear una cuenta contable personalizada"""
    company_id = request.session.get('company_id')
    company = Company.objects.using('default').get(id=company_id)

    if request.method == 'POST':
        try:
            Account.objects.create(
                company=company,
                code=request.POST.get('code'),
                name=request.POST.get('name'),
                account_type=request.POST.get('account_type'),
                description=request.POST.get('description')
            )
            messages.success(request, "Cuenta contable creada exitosamente.")
            return redirect('chart_of_accounts')
        except Exception as e:
            messages.error(request, f"Error al crear cuenta: {e}")

    return render(request, 'accounting/account_form.html', {'company': company})

@login_required
def account_edit(request, account_id):
    """Editar nombre o tipo de cuenta"""
    company_id = request.session.get('company_id')
    company = Company.objects.using('default').get(id=company_id)
    account = get_object_or_404(Account, id=account_id, company=company)

    if request.method == 'POST':
        account.code = request.POST.get('code')
        account.name = request.POST.get('name')
        account.account_type = request.POST.get('account_type')
        account.description = request.POST.get('description')
        account.save()
        messages.success(request, "Cuenta actualizada.")
        return redirect('chart_of_accounts')

    return render(request, 'accounting/account_form.html', {
        'company': company,
        'account': account
    })

# =========================================
# 3. UTILIDADES (IMPORTAR/EXPORTAR)
# =========================================

@login_required
def import_accounts_view(request):
    """Importar cuentas desde CSV"""
    if request.method == 'POST' and request.FILES.get('file'):
        csv_file = request.FILES['file']
        data_set = csv_file.read().decode('UTF-8')
        io_string = io.StringIO(data_set)
        next(io_string) 

        count = 0
        company_id = request.session.get('company_id')
        
        for row in csv.reader(io_string, delimiter=',', quotechar='"'):
            Account.objects.update_or_create(
                code=row[0],
                company_id=company_id,
                defaults={
                    'name': row[1],
                    'account_type': row[2]
                }
            )
            count += 1
        
        messages.success(request, f'¡Éxito! Se cargaron {count} cuentas.')
        return redirect('libro_diario')

    return render(request, 'accounting/import_accounts.html')

@login_required
def download_account_template(request):
    """Descargar plantilla CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="plantilla_cuentas.csv"'
    writer = csv.writer(response)
    writer.writerow(['Codigo', 'Nombre', 'Tipo'])
    writer.writerow(['1.1.01', 'Caja General', 'ASSET'])
    writer.writerow(['5.1.01', 'Gastos Combustible', 'EXPENSE'])
    return response

# =========================================
# 4. API (PARA APP MÓVIL)
# =========================================

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

class JournalEntryViewSet(viewsets.ModelViewSet):
    queryset = JournalEntry.objects.all()
    serializer_class = JournalEntrySerializer

class BalanceSheetAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({"message": "Balance General API"})

@login_required
def upload_expense_photo(request):
    """Vista para subir foto rápida de gasto"""
    if request.method == 'POST':
        form = ExpensePhotoForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            # Asignamos la empresa actual del usuario si existe
            if hasattr(request.user, 'current_company'):
                expense.company = request.user.current_company
            
            expense.save()
            messages.success(request, "¡Gasto subido correctamente!")
            return redirect('home')
    else:
        form = ExpensePhotoForm()
    
    return render(request, 'accounting/upload_photo.html', {'form': form})

@login_required
def gasto_manual(request):
    """
    Vista placeholder para el Scanner IA.
    ESTA ES LA FUNCIÓN QUE FALTABA Y QUE CAUSABA EL ERROR.
    """
    messages.info(request, "El Scanner IA estará disponible pronto. Por ahora usa la subida de fotos.")
    return redirect('upload_expense_photo')