from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Client, Quotation, QuotationItem, CRMInteraction, SaleInvoice
from .forms import QuotationForm, ClientForm
from inventory.models import Product
from core.models import Warehouse  # 🔥 AQUÍ ESTÁ LA LÍNEA MÁGICA QUE FALTABA 🔥

@login_required
def quotation_list(request):
    """Lista de cotizaciones"""
    quotations = Quotation.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'sales/quotation_list.html', {'quotations': quotations})

def quotation_create(request):
    """Crea cotizaciones aislando las bodegas por sucursal y aplicando el Libro Negro"""
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
            
            # Asignamos la sucursal y el vendedor
            quotation.company = company
            quotation.seller = request.user
            quotation.save()
            
            # 🔥 AQUÍ ESTÁ LA LÍNEA QUE FALTABA (Atrapamos el descuento) 🔥
            products = request.POST.getlist('products[]')
            quantities = request.POST.getlist('quantities[]')
            prices = request.POST.getlist('prices[]')
            discounts = request.POST.getlist('discounts[]') 
            
            total_cotizacion = 0
            
            for i, prod_id in enumerate(products):
                if prod_id:
                    # CANDADO 2: AISLAMIENTO DE SUCURSAL
                    product = get_object_or_404(Product, id=prod_id, company=company)
                    qty = int(quantities[i])
                    price = float(prices[i])
                    
                    # Extraemos el descuento con seguridad (por si viene vacío)
                    discount = 0.0
                    if discounts and i < len(discounts) and discounts[i]:
                        discount = float(discounts[i])
                    
                    # Calculamos el subtotal con el descuento aplicado
                    line_total = (qty * price) * (1 - (discount / 100))
                    
                    QuotationItem.objects.create(
                        quotation=quotation,
                        product=product,
                        quantity=qty,
                        unit_price=price,
                        discount_percent=discount,
                        total_line=line_total
                    )
                    total_cotizacion += line_total
            
            # Calculamos totales y guardamos
            quotation.total = total_cotizacion
            quotation.save()
            
            messages.success(request, f"¡Cotización #{quotation.id} generada y guardada con éxito!")
            return redirect('sales:quotation_list')
    else:
        form = QuotationForm()
        # Filtramos los menús desplegables del formulario para la sucursal actual
        form.fields['client'].queryset = Client.objects.filter(company=company)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(company=company)
    
    products = Product.objects.filter(company=company)
    return render(request, 'sales/quotation_form.html', {'form': form, 'products': products})
    

@login_required
def quotation_history(request):
    """Historial de cotizaciones con filtros y paginación"""
    company = request.user.current_company
    qs = Quotation.objects.filter(company=company).select_related('client', 'seller').order_by('-date', '-id')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()

    if q:
        qs = qs.filter(
            Q(client__name__icontains=q) |
            Q(client__nit__icontains=q) |
            Q(id__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    if fecha_inicio:
        qs = qs.filter(date__gte=fecha_inicio)

    if fecha_fin:
        qs = qs.filter(date__lte=fecha_fin)

    paginator = Paginator(qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'status_choices': Quotation._meta.get_field('status').choices,
    }
    return render(request, 'sales/quotation_history.html', context)


@login_required
def sales_orders_list(request):
    """Listado de pedidos de venta (cotizaciones aprobadas)"""
    orders = Quotation.objects.filter(
        company=request.user.current_company,
        status='APPROVED'
    ).select_related('client', 'seller').order_by('-date', '-id')
    return render(request, 'sales/sales_orders_list.html', {'orders': orders})


@login_required
def electronic_invoicing_dashboard(request):
    """Dashboard de facturación electrónica (FEL)"""
    invoices = SaleInvoice.objects.filter(
        company=request.user.current_company
    ).order_by('-date', '-id')
    return render(request, 'sales/electronic_invoicing_dashboard.html', {'invoices': invoices})


@login_required
def crm_tracking_dashboard(request):
    """Dashboard de seguimiento CRM"""
    interactions = CRMInteraction.objects.filter(
        company=request.user.current_company
    ).select_related('client', 'seller').order_by('-date')
    return render(request, 'sales/crm_tracking_dashboard.html', {'interactions': interactions})


@login_required
def blacklist_dashboard(request):
    """Clientes en libro negro"""
    clients = Client.objects.filter(
        company=request.user.current_company,
        is_blacklisted=True
    ).order_by('name')
    return render(request, 'sales/blacklist_dashboard.html', {'clients': clients})


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