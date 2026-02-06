from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

# IMPORTACIONES CLAVE (Asegúrese de tener inventory/forms.py creado)
from .forms import ProductForm 
from .models import Product, Category, Stock, InventoryMovement, MovementDetail
from core.models import Company, Warehouse

# ==========================================
# 1. LISTADO DE PRODUCTOS (Blindado por Empresa)
# ==========================================
@login_required
def product_list(request):
    # --- PRUEBA DE VIDA (ESTO ROMPERÁ LA PÁGINA) ---
    raise Exception("🛑 ¡SERVIDOR ACTUALIZADO! (Ahora borra esta línea)")
    # -----------------------------------------------

    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    # DEBUG: Imprimir en los logs de Railway
    print(f"👀 USUARIO: {request.user.username} | EMPRESA ID: {company_id}")

    products = Product.objects.filter(company_id=company_id).order_by('name')
    
    # También pasamos el nombre de la empresa al HTML para verlo en el título
    company_name = request.session.get('company_name', 'Sin Empresa')
    
    return render(request, 'inventory/product_list.html', {
        'products': products,
        'current_company_name': company_name # <--- Nueva variable
    })

# ==========================================
# 2. CREACIÓN DE PRODUCTOS (¡Ahora con Forms!)
# ==========================================
@login_required
def product_create(request):
    company_id = request.session.get('company_id')
    if not company_id: 
        return redirect('select_company')
    
    company = Company.objects.get(id=company_id)

    if request.method == 'POST':
        # Usamos el Formulario para validar datos automáticamente
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False) # Pausa, no guardar aún
            product.company = company         # INYECTAMOS LA EMPRESA AQUÍ 💉
            product.save()                    # Ahora sí, guardar
            
            messages.success(request, f"Producto '{product.name}' creado correctamente.")
            return redirect('product_list')
        else:
            messages.error(request, "Error en el formulario. Revise los datos.")
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form})

# ==========================================
# 3. CONTROL DE EXISTENCIAS (STOCK)
# ==========================================
@login_required
def stock_list(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')

    # Solo mostrar bodegas de ESTA empresa
    warehouses = Warehouse.objects.filter(branch__company_id=company_id)
    
    # Solo mostrar stock de productos de ESTA empresa
    stocks = Stock.objects.filter(product__company_id=company_id).select_related('product', 'warehouse')
    
    return render(request, 'inventory/stock_list.html', {
        'stocks': stocks,
        'warehouses': warehouses
    })

# ==========================================
# 4. MOVIMIENTOS E HISTORIAL
# ==========================================
@login_required
def movement_list(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')

    # Historial filtrado
    movements = InventoryMovement.objects.filter(company_id=company_id).order_by('-date')
    return render(request, 'inventory/movement_list.html', {'movements': movements})

@login_required
def create_movement(request):
    company_id = request.session.get('company_id')
    if not company_id: return redirect('select_company')
    
    company = Company.objects.get(id=company_id)
    
    # Filtros para los selectores del HTML (Que no salgan cosas de otra empresa)
    products = Product.objects.filter(company=company, is_active=True)
    warehouses = Warehouse.objects.filter(branch__company=company)
    
    if request.method == 'POST':
        tipo = request.POST.get('movement_type')
        wh_id = request.POST.get('warehouse')
        ref = request.POST.get('reference')
        prod_id = request.POST.get('product')
        qty = float(request.POST.get('quantity'))
        cost = float(request.POST.get('unit_cost', 0))
        desc = request.POST.get('description')

        try:
            with transaction.atomic():
                # 1. Crear Cabecera del Movimiento
                mov = InventoryMovement.objects.create(
                    company=company,
                    movement_type=tipo,
                    reference=ref,
                    description=desc,
                    user=request.user
                )
                
                # 2. Crear Detalle
                MovementDetail.objects.create(
                    movement=mov,
                    product_id=prod_id,
                    warehouse_id=wh_id,
                    quantity=qty,
                    unit_cost=cost
                )
                
                # 3. Actualizar Stock (Matemática simple)
                warehouse = Warehouse.objects.get(id=wh_id)
                product = Product.objects.get(id=prod_id)
                
                stock_item, created = Stock.objects.get_or_create(
                    product=product, 
                    warehouse=warehouse,
                    defaults={'quantity': 0}
                )
                
                if 'IN' in tipo:
                    stock_item.quantity = float(stock_item.quantity) + qty
                else:
                    stock_item.quantity = float(stock_item.quantity) - qty
                
                stock_item.save()

            messages.success(request, "Movimiento registrado y stock actualizado.")
            return redirect('movement_list')
            
        except Exception as e:
            messages.error(request, f"Error al registrar: {e}")

    return render(request, 'inventory/movement_form.html', {
        'products': products,
        'warehouses': warehouses
    })