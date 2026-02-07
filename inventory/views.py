from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Prefetch, Sum  # <--- AQUÍ ESTABA EL ERROR
from core.models import Company, Branch, Warehouse
from .models import Product, StockMovement, Stock
from .forms import StockMovementForm, ProductForm

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