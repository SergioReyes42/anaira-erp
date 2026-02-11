from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Quotation, Sale
from .forms import QuotationForm, SaleForm
from core.models import Client

@login_required
def quotation_list(request):
    """Listado de Cotizaciones"""
    quotations = Quotation.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'sales/quotation_list.html', {'quotations': quotations})

@login_required
def quotation_create(request):
    """Crear nueva cotización"""
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        if form.is_valid():
            quotation = form.save(commit=False)
            quotation.company = request.user.current_company
            quotation.save()
            messages.success(request, "Cotización creada (Borrador).")
            return redirect('quotation_list')
    else:
        # Filtramos clientes por empresa
        form = QuotationForm()
        form.fields['client'].queryset = Client.objects.filter(company=request.user.current_company)
    
    return render(request, 'sales/quotation_form.html', {'form': form})

@login_required
def client_list(request):
    """Directorio de Clientes"""
    clients = Client.objects.filter(company=request.user.current_company)
    return render(request, 'sales/client_list.html', {'clients': clients})