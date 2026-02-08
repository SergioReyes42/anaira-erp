from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Prefetch, Sum  # <--- AQUÍ ESTABA EL ERROR
from core.models import Company, Branch, Warehouse
from .models import Product, StockMovement, Stock
from .forms import StockMovementForm, ProductForm, TransferForm

# ========================================================
# 1. VISTA PRINCIPAL (LISTA DE PRODUCTOS)
# ========================================================
@login_required
def product_list(request):
    company_id = request.session.get('company_id')
    if not company_id: 
        return redirect('select_company')

    empresa_actual = Company.objects.filter(id=company_id).first()
    nombre_empresa = empresa_actual.name if empresa_actual else "Empresa no encontrada"

    products = Product.objects.filter(company_id=company_id)

    context = {
        'products': products,
        'current_company_name': nombre_empresa
    }
    return render(request, 'inventory/product_list.html', context)

# ========================================================
# 2. VISTAS DE CREACIÓN (PRODUCTOS Y MOVIMIENTOS)
# ========================================================

@login_required
def product_create(request):
    company_id = request.session.get('company_id')
    if not company_id:
        return redirect('select_company')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.company_id = company_id
            product.stock_quantity = 0
            product.save()
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form})

@login_required
def create_movement(request):
    company_id = request.session.get('company_id')
    if not company_id:
        return redirect('select_company')

    if request.method == 'POST':
        form = StockMovementForm(request.POST, company_id=company_id)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.company_id = company_id
            movement.user = request.user
            movement.save()
            return redirect('movement_list')
    else:
        form = StockMovementForm(company_id=company_id)

    return render(request, 'inventory/movement_form.html', {'form': form})

# ========================================================
# 3. KARDEX (HISTORIAL)
# ========================================================
@login_required
def movement_list(request):
    company_id = request.session.get('company_id')
    if not company_id: 
        return redirect('select_company')

    empresa = Company.objects.get(id=company_id)

    movimientos = StockMovement.objects.filter(
        product__company_id=company_id
    ).select_related('product', 'user').order_by('-date')

    context = {
        'movements': movimientos,
        'current_company_name': empresa.name
    }
    return render(request, 'inventory/movement_list.html', context)

# ========================================================
# 4. MONITOR DE EXISTENCIAS (DASHBOARD INTELIGENTE)
# ========================================================
@login_required
def stock_list(request):
    company_id = request.session.get('company_id')
    if not company_id:
        return redirect('select_company')

    # 1. TRAEMOS LA ESTRUCTURA COMPLETA (OPTIMIZADA)
    branches = Branch.objects.filter(company_id=company_id).prefetch_related(
        Prefetch(
            'warehouses',
            queryset=Warehouse.objects.filter(parent__isnull=True, active=True).prefetch_related(
                'sub_warehouses__sub_warehouses', 
                'stocks_v2__product'
            )
        )
    )

    # 2. CALCULAR TOTALES GLOBALES
    total_products = Product.objects.filter(company_id=company_id).count()
    # Usamos Sum directamente (ya importado arriba)
    total_stock_items = Stock.objects.filter(warehouse__branch__company_id=company_id).aggregate(total=Sum('quantity'))['total'] or 0

    context = {
        'branches': branches,
        'total_products': total_products,
        'total_global_stock': total_stock_items,
    }
    return render(request, 'inventory/stock_dashboard.html', context)

@login_required
def smart_hub(request):
    return HttpResponse("<h3>🤖 Smart Hub: En construcción</h3><a href='/inventario/'>Volver</a>")

# ========================================================
# 5. KARDEX ESPECÍFICO POR PRODUCTO
# ========================================================
@login_required
def product_kardex(request, product_id):
    company_id = request.session.get('company_id')
    if not company_id:
        return redirect('select_company')

    # Buscamos el producto específico (y aseguramos que sea de la empresa)
    product = get_object_or_404(Product, id=product_id, company_id=company_id)

    # Filtramos SOLO los movimientos de este producto
    movimientos = StockMovement.objects.filter(
        product=product
    ).select_related('user').order_by('-date')

    context = {
        'movements': movimientos,
        'current_company_name': product.company.name,
        'subtitle': f"Historial de: {product.name} ({product.sku})" # Para que sepa qué está viendo
    }
    # Reutilizamos la misma plantilla de lista de movimientos
    return render(request, 'inventory/movement_list.html', context)

import random

import random

@login_required
def make_transfer(request):
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            
            # Validación simple
            if data['from_warehouse'] == data['to_warehouse']:
                form.add_error('to_warehouse', '¡La bodega destino no puede ser la misma que la de origen!')
                return render(request, 'inventory/transfer_form.html', {'form': form})

            # Generamos un ID de grupo para saber que estos dos movimientos son hermanos
            transfer_id = random.randint(100000, 999999)

            # 1. SACAMOS DE ORIGEN
            StockMovement.objects.create(
                product=data['product'],
                warehouse=data['from_warehouse'],
                quantity=data['quantity'],
                movement_type='TRANSFER_OUT',
                user=request.user,
                comments=f"Traslado hacia {data['to_warehouse'].name} | {data['comments']}",
                related_transfer_id=transfer_id
            )

            # 2. METEMOS EN DESTINO
            StockMovement.objects.create(
                product=data['product'],
                warehouse=data['to_warehouse'],
                quantity=data['quantity'],
                movement_type='TRANSFER_IN',
                user=request.user,
                comments=f"Recibido desde {data['from_warehouse'].name} | {data['comments']}",
                related_transfer_id=transfer_id
            )
            
            return redirect('movement_list')
    else:
        form = TransferForm()

    return render(request, 'inventory/transfer_form.html', {'form': form})