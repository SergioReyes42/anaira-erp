from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Duca, TrackingEvent
from .forms import DucaForm, DucaItemFormSet, TrackingEventForm

@login_required
def duca_list(request):
    """Muestra el listado de todas las pólizas"""
    ducas = Duca.objects.filter(company=request.user.current_company).order_by('-date_acceptance')
    return render(request, 'imports/duca_list.html', {'ducas': ducas})

@login_required
def duca_create(request):
    """Pantalla para registrar una nueva póliza con sus productos"""
    if request.method == 'POST':
        form = DucaForm(request.POST)
        formset = DucaItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            duca = form.save(commit=False)
            duca.company = request.user.current_company
            duca.created_by = request.user
            duca.save()
            
            formset.instance = duca
            formset.save()
            
            messages.success(request, f'Póliza {duca.duca_number} registrada con éxito.')
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