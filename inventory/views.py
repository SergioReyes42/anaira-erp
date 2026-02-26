from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

# IMPORTACIONES CORRECTAS
from core.models import Company, Warehouse
# Aquí importamos StockMovement (no InventoryMovement) y Supplier
from .models import Product, StockMovement, Category, Brand, Stock, Supplier
from .forms import ProductForm, WarehouseForm, InventoryMovementForm, SupplierForm

# ==========================================
# 1. DASHBOARD
# ==========================================
@login_required
def dashboard(request):
    """Dashboard gerencial de Logística (Monitor de Existencias)"""
    company = request.user.current_company
    
    # 1. KPIs (Tarjetas Superiores)
    total_products = Product.objects.filter(company=company).count()
    
    stock_data = Product.objects.filter(company=company).aggregate(total=Sum('stock_quantity'))
    total_stock = stock_data['total'] or 0
    
    # 2. Alertas Críticas (Productos con 5 o menos unidades)
    low_stock = Product.objects.filter(company=company, stock_quantity__lte=5).order_by('stock_quantity')[:6]
    
    # 3. Actividad Reciente (Últimos 6 movimientos del Kardex)
    recent_movements = StockMovement.objects.filter(company=company).order_by('-date')[:6]
    
    context = {
        'total_products': total_products,
        'total_stock': total_stock,
        'low_stock': low_stock,
        'low_stock_count': Product.objects.filter(company=company, stock_quantity__lte=5).count(),
        'recent_movements': recent_movements,
    }
    return render(request, 'inventory/dashboard.html', context)

# ==========================================
# 2. LISTAS Y CREACIÓN
# ==========================================
@login_required
def product_list(request):
    products = Product.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.company = request.user.current_company
            prod.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'inventory/product_form.html', {'form': form})

@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/warehouse_list.html', {'warehouses': warehouses})

@login_required
def warehouse_create(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            wh = form.save(commit=False)
            wh.company = request.user.current_company
            wh.save()
            return redirect('warehouse_management')
    else:
        form = WarehouseForm()
    return render(request, 'inventory/warehouse_form.html', {'form': form})

# ==========================================
# 3. MOVIMIENTOS
# ==========================================
@login_required
def movement_list(request):
    # Usamos StockMovement
    movements = StockMovement.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'inventory/movement_list.html', {'movements': movements})

@login_required
def create_movement(request):
    if request.method == 'POST':
        form = InventoryMovementForm(request.POST)
        if form.is_valid():
            mov = form.save(commit=False)
            mov.company = request.user.current_company
            mov.user = request.user
            mov.save()
            return redirect('movement_list')
    else:
        form = InventoryMovementForm()
    return render(request, 'inventory/movement_form.html', {'form': form})

# ==========================================
# 4. OTROS (Placeholders para URLs)
# ==========================================
@login_required
def supplier_list(request):
    suppliers = Supplier.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

def inventory_kardex(request): 
    """Muestra el historial completo de entradas y salidas de bodega"""
    movements = StockMovement.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'inventory/kardex_list.html', {'movements': movements})

def make_transfer(request): return redirect('dashboard')
def purchase_list(request): return redirect('dashboard')
def create_purchase(request): return redirect('dashboard')