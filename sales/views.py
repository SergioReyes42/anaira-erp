from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Client, Quotation, QuotationItem
from .forms import QuotationForm, ClientForm
from inventory.models import Product
from core.models import Warehouse  # 🔥 AQUÍ ESTÁ LA LÍNEA MÁGICA QUE FALTABA 🔥

@login_required
def quotation_list(request):
    """Lista de cotizaciones"""
    quotations = Quotation.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'sales/quotation_list.html', {'quotations': quotations})

@login_required
def quotation_create(request):
    """Crea cotizaciones aislando las bodegas por sucursal y aplicando el Libro Negro"""
    # 1. Identificamos la sucursal exacta del usuario
    company = request.user.current_company
    
    if request.method == 'POST':
        form = QuotationForm(request.POST)
        
        if form.is_valid():
            quotation = form.save(commit=False)
            
            # 🔥 CANDADO 1: EL LIBRO NEGRO 🔥
            if quotation.client.is_blacklisted:
                messages.error(
                    request, 
                    f"⛔ ALERTA DE SISTEMA: Bloqueo activo. El cliente {quotation.client.name} está en el Libro Negro. Motivo: {quotation.client.blacklist_reason}"
                )
                return redirect('sales:quotation_create')
            
            # Asignamos la sucursal y el vendedor de forma invisible y segura
            quotation.company = company
            quotation.seller = request.user
            quotation.save()
            
            # Procesamos las listas de productos que vienen del HTML
            products = request.POST.getlist('products[]')
            quantities = request.POST.getlist('quantities[]')
            prices = request.POST.getlist('prices[]')
            
            total_cotizacion = 0
            
            for i, prod_id in enumerate(products):
                if prod_id:
                    # 🔥 CANDADO 2: AISLAMIENTO DE SUCURSAL 🔥
                    # Nos aseguramos de que el producto extraído pertenezca a la sucursal actual
                    product = get_object_or_404(Product, id=prod_id, company=company)
                    qty = int(quantities[i])
                    price = float(prices[i])
                    
                    QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=qty,
                        unit_price=price
                    )
                    total_cotizacion += (qty * price)
            
            # Calculamos totales y guardamos
            quotation.total = total_cotizacion
            quotation.save()
            
            messages.success(request, f"¡Cotización #{quotation.id} generada y guardada con éxito!")
            return redirect('sales:quotation_list')
    else:
        form = QuotationForm()
        # 🔥 MAGIA DE AISLAMIENTO: Filtramos los menús desplegables del formulario
        form.fields['client'].queryset = Client.objects.filter(company=company)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(company=company)
    
    # Enviamos al HTML solo los productos de la sucursal actual
    products = Product.objects.filter(company=company)
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