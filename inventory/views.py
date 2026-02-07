from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product
from core.models import Company

@login_required
def product_list(request):
    # 1. Obtener el ID de la empresa de la sesión
    company_id = request.session.get('company_id')
    
    # 2. Si no hay empresa seleccionada, mandar a seleccionarla
    if not company_id: 
        return redirect('select_company')

    # 3. Buscar el nombre de la empresa (para que no salga vacío)
    empresa_actual = Company.objects.filter(id=company_id).first()
    nombre_empresa = empresa_actual.name if empresa_actual else "Empresa no encontrada"

    # 4. Filtrar los productos SOLO de esa empresa
    products = Product.objects.filter(company_id=company_id)

    # 5. Preparar los datos para el HTML
    context = {
        'products': products,
        'current_company_name': nombre_empresa
    }
    
    # 6. Mostrar la página
    return render(request, 'inventory/product_list.html', context)