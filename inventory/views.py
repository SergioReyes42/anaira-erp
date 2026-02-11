from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Product, Warehouse # Modelos de CORE
from .models import StockMovement # Modelo de INVENTORY
from .forms import StockMovementForm

@login_required
def dashboard(request):
    """Vista principal del Inventario (Dashboard)"""
    company = request.user.current_company
    total_products = Product.objects.filter(company=company).count()
    # Productos con stock bajo (menos de 5)
    stock_alert = Product.objects.filter(company=company, stock__lte=5).count()
    
    recent_movements = StockMovement.objects.filter(
        company=company
    ).order_by('-date')[:5]

    context = {
        'total_products': total_products,
        'stock_alert': stock_alert,
        'recent_movements': recent_movements
    }
    return render(request, 'inventory/dashboard.html', context)

@login_required
def product_list(request):
    """
    Lista de Productos y su Stock actual.
    ESTA ES LA FUNCIÓN QUE FALTABA
    """
    products = Product.objects.filter(company=request.user.current_company)
    return render(request, 'inventory/product_list.html', {'products': products})

@login_required
def movement_list(request):
    """Historial completo de Movimientos"""
    movements = StockMovement.objects.filter(
        company=request.user.current_company
    ).order_by('-date')
    return render(request, 'inventory/movement_list.html', {'movements': movements})

@login_required
def create_movement(request):
    """Registrar Entrada o Salida de Inventario"""
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.company = request.user.current_company
            
            # Lógica de Actualización de Stock
            product = movement.product
            if movement.movement_type == 'IN':
                product.stock += movement.quantity
            elif movement.movement_type == 'OUT':
                if product.stock < movement.quantity:
                    messages.error(request, f"Error: Stock insuficiente. Disponible: {product.stock}")
                    return render(request, 'inventory/movement_form.html', {'form': form})
                product.stock -= movement.quantity
            
            product.save()
            movement.save()
            messages.success(request, "Movimiento registrado correctamente.")
            return redirect('inventory_list')
    else:
        form = StockMovementForm()
        # Filtramos los desplegables por la empresa actual
        form.fields['product'].queryset = Product.objects.filter(company=request.user.current_company)
        form.fields['warehouse'].queryset = Warehouse.objects.filter(company=request.user.current_company)
    
    return render(request, 'inventory/movement_form.html', {'form': form})