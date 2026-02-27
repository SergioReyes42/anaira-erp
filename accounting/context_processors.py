from .models import Expense

def expense_notifications(request):
    """Calcula cuántos gastos pendientes hay y los envía a todas las pantallas del ERP"""
    # Verificamos que el usuario esté logueado y tenga una sucursal activa
    if request.user.is_authenticated and hasattr(request.user, 'current_company') and request.user.current_company:
        comp = request.user.current_company
        return {
            'count_pre_review': Expense.objects.filter(status='PRE_REVIEW', company=comp).count(),
            'count_pending': Expense.objects.filter(status='PENDING', company=comp).count(),
        }
    return {'count_pre_review': 0, 'count_pending': 0}