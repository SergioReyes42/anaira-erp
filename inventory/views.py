from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

# Importamos del Core (Lo compartido)
from core.models import Company, Warehouse, BusinessPartner

# Importamos del Inventario (Lo específico)
from .models import Product, Category, Stock, InventoryMovement, MovementDetail

# ==========================================
# 1. LISTADO DE PRODUCTOS
# ==========================================
@login_required
def product_list(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    products = Product.objects.filter(company_id=company_id).order_by('name')
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def product_create(request):
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    categories = Category.objects.filter(company=company)

    if request.method == 'POST':
        Product.objects.create(
            company=company,
            sku=request.POST.get('sku'),
            name=request.POST.get('name'),
            category_id=request.POST.get('category'),
            cost_price=request.POST.get('cost_price', 0),
            sale_price=request.POST.get('sale_price', 0),
            min_stock=request.POST.get('min_stock', 0),
            product_type=request.POST.get('product_type', 'PRODUCT')
        )
        messages.success(request, "Producto creado correctamente.")
        return redirect('product_list')

    return render(request, 'inventory/product_form.html', {'categories': categories})

# ==========================================
# 2. CONTROL DE EXISTENCIAS (STOCK)
# ==========================================
@login_required
def stock_list(request):
    """Ver existencias por Bodega"""
    company_id = request.session.get('company_id')
    # Obtenemos las bodegas de las sucursales de esta empresa
    warehouses = Warehouse.objects.filter(branch__company_id=company_id)
    
    # Stocks generales
    stocks = Stock.objects.filter(product__company_id=company_id).select_related('product', 'warehouse')
    
    return render(request, 'inventory/stock_list.html', {
        'stocks': stocks,
        'warehouses': warehouses
    })

# ==========================================
# 3. MOVIMIENTOS (ENTRADAS/SALIDAS)
# ==========================================
@login_required
def movement_list(request):
    company_id = request.session.get('company_id')
    movements = InventoryMovement.objects.filter(company_id=company_id).order_by('-date')
    return render(request, 'inventory/movement_list.html', {'movements': movements})

@login_required
def create_movement(request):
    """Registrar entrada o salida manual"""
    company_id = request.session.get('company_id')
    company = Company.objects.get(id=company_id)
    
    products = Product.objects.filter(company=company, is_active=True)
    warehouses = Warehouse.objects.filter(branch__company=company)
    
    if request.method == 'POST':
        tipo = request.POST.get('movement_type')
        wh_id = request.POST.get('warehouse')
        ref = request.POST.get('reference')
        
        # Usamos transacción para asegurar consistencia
        with transaction.atomic():
            # 1. Crear Cabecera
            mov = InventoryMovement.objects.create(
                company=company,
                movement_type=tipo,
                reference=ref,
                description=request.POST.get('description'),
                user=request.user
            )
            
            # 2. Crear Detalle (Simplificado para 1 producto por ahora)
            prod_id = request.POST.get('product')
            qty = float(request.POST.get('quantity'))
            cost = float(request.POST.get('unit_cost', 0))
            
            MovementDetail.objects.create(
                movement=mov,
                product_id=prod_id,
                warehouse_id=wh_id,
                quantity=qty,
                unit_cost=cost
            )
            
            # 3. Actualizar Stock (Lógica simple)
            warehouse = Warehouse.objects.get(id=wh_id)
            product = Product.objects.get(id=prod_id)
            
            stock_item, created = Stock.objects.get_or_create(
                product=product, 
                warehouse=warehouse,
                defaults={'quantity': 0}
            )
            
            # Si es entrada suma, si es salida resta
            if 'IN' in tipo:
                stock_item.quantity = float(stock_item.quantity) + qty
            else:
                stock_item.quantity = float(stock_item.quantity) - qty
            
            stock_item.save()

        messages.success(request, "Movimiento registrado y stock actualizado.")
        return redirect('movement_list')

    return render(request, 'inventory/movement_form.html', {
        'products': products,
        'warehouses': warehouses
    })