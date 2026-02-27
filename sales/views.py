from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Client, Quotation, QuotationItem
from .forms import QuotationForm, ClientForm
from inventory.models import Product

@login_required
def quotation_list(request):
    """Lista de cotizaciones"""
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
            quotation.seller = request.user
            quotation.save()
            
            # Guardar productos (Lógica simple)
            products = request.POST.getlist('products[]')
            quantities = request.POST.getlist('quantities[]')
            prices = request.POST.getlist('prices[]')
            
            for i, prod_id in enumerate(products):
                if prod_id:
                    product = Product.objects.get(id=prod_id)
                    QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=int(quantities[i]),
                        unit_price=float(prices[i])
                    )
            
            messages.success(request, "Cotización creada con éxito")
            return redirect('quotation_list')
    else:
        form = QuotationForm()
    
    products = Product.objects.filter(company=request.user.current_company)
    return render(request, 'sales/quotation_form.html', {'form': form, 'products': products})

@login_required
def client_list(request):
    """Lista de clientes"""
    clients = Client.objects.filter(company=request.user.current_company)
    return render(request, 'sales/client_list.html', {'clients': clients})

@login_required
def client_create(request):
    """Crea un nuevo cliente y lo vincula a la empresa del usuario"""
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.company = request.user.current_company # <-- Lo amarramos a tu sucursal
            client.save()
            messages.success(request, f'¡El cliente {client.name} ha sido registrado con éxito!')
            return redirect('sales:client_list')
    else:
        form = ClientForm()
        
    return render(request, 'sales/client_form.html', {'form': form})