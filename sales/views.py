# sales/views.py
from django.shortcuts import render, redirect
from .forms import InvoiceForm
from core.models import Company

def create_invoice_view(request):
    company_id = request.session.get('active_company_id')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, company=company)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.company = company
            invoice.pending_amount = invoice.total # Al inicio, todo está pendiente
            invoice.save()
            return redirect('workspace')
    else:
        form = InvoiceForm(company=company)
    
    return render(request, 'sales/invoice_form.html', {'form': form, 'company': company})

# sales/views.py
from .forms import PaymentForm
from .models import Payment, Invoice

def create_payment_view(request):
    company_id = request.session.get('active_company_id')
    company = Company.objects.get(id=company_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST, company=company)
        if form.is_valid():
            payment = form.save(commit=False)
            
            # LÓGICA DE SALDOS
            invoice = payment.invoice
            invoice.pending_amount -= payment.amount
            
            # Si ya no debe nada, marcamos como pagada
            if invoice.pending_amount <= 0:
                invoice.pending_amount = 0
                invoice.status = 'PAID'
            
            invoice.save()
            payment.save()
            return redirect('workspace')
    else:
        form = PaymentForm(company=company)
    
    return render(request, 'sales/payment_form.html', {'form': form, 'company': company})

# sales/views.py
from django.db.models import Sum
from .models import Invoice, BusinessPartner

def cxc_report_view(request):
    company_id = request.session.get('active_company_id')
    
    # Obtenemos todos los clientes que tienen deuda (pending_amount > 0)
    customers_with_debt = BusinessPartner.objects.filter(
        company_id=company_id,
        invoice__pending_amount__gt=0
    ).annotate(
        total_debt=Sum('invoice__pending_amount')
    ).distinct()

    # Obtenemos el detalle de facturas pendientes
    pending_invoices = Invoice.objects.filter(
        company_id=company_id, 
        status='OPEN'
    ).order_by('due_date')

    return render(request, 'sales/cxc_report.html', {
        'customers': customers_with_debt,
        'invoices': pending_invoices
    })