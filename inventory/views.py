from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, StockMovement
from core.models import Company
from django.http import HttpResponse

# ========================================================
# 1. VISTA PRINCIPAL (INVENTARIO)
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
# 2. VISTAS FANTASMA (PARA QUE NO DE ERROR EL MENÚ)
# ========================================================

@login_required
def smart_hub(request):
    return HttpResponse("<h3>🤖 Smart Hub: En construcción</h3><a href='/inventario/'>Volver</a>")

@login_required
def product_create(request):
    return HttpResponse("<h3>➕ Nuevo Producto: En construcción</h3><a href='/inventario/'>Volver</a>")

@login_required
def stock_list(request):
    return HttpResponse("<h3>📦 Existencias: En construcción</h3><a href='/inventario/'>Volver</a>")

# ========================================================
# 3. KARDEX REAL (HISTORIAL DE MOVIMIENTOS)
# ========================================================
@login_required
def movement_list(request):
    # 1. Seguridad: Obtener empresa
    company_id = request.session.get('company_id')
    if not company_id: 
        return redirect('select_company')

    # 2. Obtener datos de la empresa (para el título)
    empresa = Company.objects.get(id=company_id)

    # 3. CONSULTA A LA BASE DE DATOS
    # Traemos los movimientos donde el producto pertenece a esta empresa
    # .select_related('product') hace que la consulta sea más rápida
    # .order_by('-date') pone los más recientes primero
    movimientos = StockMovement.objects.filter(
        product__company_id=company_id
    ).select_related('product', 'user').order_by('-date')

    context = {
        'movements': movimientos,
        'current_company_name': empresa.name
    }
    return render(request, 'inventory/movement_list.html', context)

@login_required
def create_movement(request):
    return HttpResponse("<h3>📝 Registrar Movimiento: En construcción</h3><a href='/inventario/'>Volver</a>")