from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Duca, TrackingEvent
from .forms import DucaForm, DucaItemFormSet, TrackingEventForm
from .models import PurchaseOrder
from .forms import PurchaseOrderForm
from .models import WarehouseReception
from .forms import WarehouseReceptionForm
from inventory.models import StockMovement


@login_required
def duca_list(request):
    """Muestra el listado de todas las pólizas"""
    ducas = Duca.objects.filter(company=request.user.current_company).order_by('-date_acceptance')
    return render(request, 'imports/duca_list.html', {'ducas': ducas})

@login_required
def duca_create(request):
    """Crea una nueva Póliza DUCA y sus productos"""
    if request.method == 'POST':
        form = DucaForm(request.POST)
        formset = DucaItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # 1. Guardar la cabecera
            duca = form.save(commit=False)
            duca.company = request.user.current_company
            duca.save()
            form.save_m2m() # Guarda las Órdenes de Compra vinculadas
            
            # 2. Guardar los productos
            items = formset.save(commit=False)
            for item in items:
                item.duca = duca
                item.save()
            
            # 🔥 3. ENCENDER EL MOTOR MATEMÁTICO 🔥
            duca.calcular_liquidaciones()
            
            messages.success(request, 'DUCA registrada y prorrateada con éxito.')
            return redirect('imports:duca_detail', pk=duca.pk)
    else:
        form = DucaForm()
        formset = DucaItemFormSet()
        
    return render(request, 'imports/duca_form.html', {'form': form, 'formset': formset})

@login_required
def duca_detail(request, pk):
    """Pantalla de resumen matemático y prorrateo de la póliza"""
    duca = get_object_or_404(Duca, pk=pk, company=request.user.current_company)
    return render(request, 'imports/duca_detail.html', {'duca': duca})

@login_required
def tracking_add(request, pk):
    """Agrega un nuevo punto de ubicación en el mapa de la DUCA"""
    duca = get_object_or_404(Duca, pk=pk, company=request.user.current_company)
    
    if request.method == 'POST':
        form = TrackingEventForm(request.POST)
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.duca = duca
            tracking.save()
            messages.success(request, f'¡Ubicación actualizada! El contenedor ahora está en: {tracking.location}')
            return redirect('imports:duca_detail', pk=duca.pk)
    else:
        form = TrackingEventForm()
        
    return render(request, 'imports/tracking_form.html', {'form': form, 'duca': duca})

@login_required
def po_list(request):
    """Muestra el listado de Órdenes de Compra"""
    pos = PurchaseOrder.objects.all().order_by('-issue_date')
    return render(request, 'imports/po_list.html', {'pos': pos})

@login_required
def po_create(request):
    """Pantalla para registrar una nueva Orden de Compra"""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Orden de Compra registrada exitosamente.')
            return redirect('imports:po_list')
    else:
        form = PurchaseOrderForm()
        
    return render(request, 'imports/po_form.html', {'form': form})

@login_required
def reception_add(request, pk):
    """Registra el acta física y auto-inyecta los productos al Kardex"""
    duca = get_object_or_404(Duca, pk=pk, company=request.user.current_company)
    reception, created = WarehouseReception.objects.get_or_create(duca=duca)
    
    if request.method == 'POST':
        form = WarehouseReceptionForm(request.POST, instance=reception)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.received_by = request.user
            
            # 🔥 LA MAGIA DE LA INYECCIÓN AUTOMÁTICA 🔥
            # Solo inyecta si hay bodega seleccionada y si NO se ha procesado antes
            if rec.warehouse and not rec.inventory_processed:
                for item in duca.items.all():
                    # Validamos que el ítem tenga un producto del catálogo asignado
                    if item.product_catalog and item.quantity > 0:
                        StockMovement.objects.create(
                            company=duca.company,
                            product=item.product_catalog,
                            warehouse=rec.warehouse,
                            movement_type='IN',
                            quantity=item.quantity,
                            user=request.user,
                            reference=f"DUCA-{duca.duca_number}",
                            description=f"Ingreso por Importación Automático - Póliza {duca.duca_number}"
                        )
                # Ponemos el candado para que no vuelva a sumar si editan el acta mañana
                rec.inventory_processed = True
                
            rec.save()
            messages.success(request, '¡Acta de Recepción guardada e Inventario actualizado automáticamente!')
            return redirect('imports:duca_detail', pk=duca.pk)
    else:
        form = WarehouseReceptionForm(instance=reception)
        
    return render(request, 'imports/reception_form.html', {'form': form, 'duca': duca})