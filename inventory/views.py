from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Product, Warehouse, Supplier
from .models import StockMovement, Purchase
from .forms import StockMovementForm, PurchaseForm, TransferForm

# --- VISTAS GENERALES ---
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

# --- ESTA ES LA VISTA QUE PEDÍA EL ERROR (KARDEX) ---
@login_required
def inventory_kardex(request):
    """Vista detallada de movimientos (Kardex)"""
    # Por ahora reutilizamos la lista de movimientos, pero en el futuro
    # aquí pondremos filtros por fecha y producto.
    movements = StockMovement.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'inventory/kardex.html', {'movements': movements})

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

# --- NUEVA VISTA: TRANSFERENCIAS ---
@login_required
def make_transfer(request):
    """Mover productos entre bodegas"""
    if request.method == 'POST':
        form = TransferForm(request.POST)
        # Hack para que valide el queryset en POST
        form.fields['product'].queryset = Product.objects.filter(company=request.user.current_company)
        form.fields['from_warehouse'].queryset = Warehouse.objects.filter(company=request.user.current_company)
        form.fields['to_warehouse'].queryset = Warehouse.objects.filter(company=request.user.current_company)

        if form.is_valid():
            data = form.cleaned_data
            product = data['product']
            qty = data['quantity']
            
            # Validar Stock Global (Simplificado)
            if product.stock < qty:
                messages.error(request, "No hay stock suficiente para transferir.")
            else:
                # 1. Crear Salida de Origen
                StockMovement.objects.create(
                    company=request.user.current_company,
                    product=product,
                    warehouse=data['from_warehouse'],
                    quantity=qty,
                    movement_type='TRF', # Transferencia
                    reason=f"Salida por traslado a {data['to_warehouse'].name}"
                )
                
                # 2. Crear Entrada en Destino
                StockMovement.objects.create(
                    company=request.user.current_company,
                    product=product,
                    warehouse=data['to_warehouse'],
                    quantity=qty,
                    movement_type='TRF',
                    reason=f"Entrada por traslado desde {data['from_warehouse'].name}"
                )
                
                # Nota: El stock total del producto no cambia, solo su ubicación
                messages.success(request, "Transferencia realizada con éxito.")
                return redirect('inventory_kardex')
    else:
        form = TransferForm()
        form.fields['product'].queryset = Product.objects.filter(company=request.user.current_company)
        form.fields['from_warehouse'].queryset = Warehouse.objects.filter(company=request.user.current_company)
        form.fields['to_warehouse'].queryset = Warehouse.objects.filter(company=request.user.current_company)

    return render(request, 'inventory/transfer_form.html', {'form': form})

# --- VISTAS DE COMPRAS ---
@login_required
def purchase_list(request):
    purchases = Purchase.objects.filter(company=request.user.current_company).order_by('-date')
    return render(request, 'inventory/purchase_list.html', {'purchases': purchases})

@login_required
def create_purchase(request):
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.company = request.user.current_company
            purchase.save()
            messages.success(request, "Compra registrada.")
            return redirect('purchase_list')
    else:
        form = PurchaseForm()
        form.fields['supplier'].queryset = Supplier.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/purchase_form.html', {'form': form})

@login_required
def supplier_list(request):
    suppliers = Supplier.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})