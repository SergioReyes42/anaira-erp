from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Product, Warehouse, Supplier
from .models import StockMovement, Purchase
from .forms import StockMovementForm, PurchaseForm

# --- VISTAS DE DASHBOARD E INVENTARIO ---
@login_required
def dashboard(request):
    company = request.user.current_company
    total_products = Product.objects.filter(company=company).count()
    stock_alert = Product.objects.filter(company=company, stock__lte=5).count()
    recent_movements = StockMovement.objects.filter(company=company).order_by('-date')[:5]
    return render(request, 'inventory/dashboard.html', {
        'total_products': total_products, 
        'stock_alert': stock_alert, 
        'recent_movements': recent_movements
    })

@login_required
def product_list(request):
    products = Product.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def movement_list(request):
    movements = StockMovement.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'inventory/movement_list.html', {'movements': movements})

@login_required
def create_movement(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.company = request.user.current_company
            product = movement.product
            
            if movement.movement_type == 'IN':
                product.stock += movement.quantity
            elif movement.movement_type == 'OUT':
                if product.stock < movement.quantity:
                    messages.error(request, f"Stock insuficiente. Disponible: {product.stock}")
                    return render(request, 'inventory/movement_form.html', {'form': form})
                product.stock -= movement.quantity
            
            product.save()
            movement.save()
            messages.success(request, "Movimiento registrado.")
            return redirect('inventory_list')
    else:
        form = StockMovementForm()
        form.fields['product'].queryset = Product.objects.filter(company=request.user.current_company)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/movement_form.html', {'form': form})

# --- NUEVAS: VISTAS DE COMPRAS ---
@login_required
def purchase_list(request):
    """Historial de Compras"""
    purchases = Purchase.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'inventory/purchase_list.html', {'purchases': purchases})

@login_required
def create_purchase(request):
    """Crear nueva compra (simplificada)"""
    # NOTA: En una versión completa, aquí usaríamos formsets para agregar productos.
    # Por ahora, solo creamos el encabezado para que el botón funcione.
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.company = request.user.current_company
            purchase.save()
            messages.success(request, "Compra registrada (Encabezado).")
            return redirect('purchase_list')
    else:
        form = PurchaseForm()
        form.fields['supplier'].queryset = Supplier.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/purchase_form.html', {'form': form})

@login_required
def supplier_list(request):
    """Directorio de Proveedores"""
    suppliers = Supplier.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})