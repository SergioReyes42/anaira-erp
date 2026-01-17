from django.db.models import Sum, Case, When, F, DecimalField
from .models import Account, JournalItem

def get_balance_sheet(company_id, fecha_corte):
    """
    Calcula el saldo de cada cuenta acumulado hasta la fecha de corte.
    Activo = Debe - Haber
    Pasivo/Capital = Haber - Debe
    """
    cuentas = Account.objects.filter(company_id=company_id)
    resultado = []

    for cuenta in cuentas:
        # Sumamos todos los movimientos hasta la fecha
        movimientos = JournalItem.objects.filter(
            entry__date__lte=fecha_corte,
            account=cuenta
        ).aggregate(
            total_debe=Sum('debit'),
            total_haber=Sum('credit')
        )

        debe = movimientos['total_debe'] or 0
        haber = movimientos['total_haber'] or 0

        # Calculamos saldo según el tipo de cuenta
        if cuenta.account_type == 'ASSET' or cuenta.account_type == 'EXPENSE':
            saldo = debe - haber
        else:
            saldo = haber - debe

        if saldo != 0:
            resultado.append({
                'codigo': cuenta.code,
                'nombre': cuenta.name,
                'tipo': cuenta.account_type,
                'saldo': saldo
            })
    
    return resultado
# --- AGREGAR AL FINAL DE accounting/services.py ---

def get_income_statement(company_id, start_date, end_date):
    """
    Calcula el Estado de Resultados (Pérdidas y Ganancias) para un rango de fechas.
    Ingresos (INCOME) - Gastos (EXPENSE)
    """
    # 1. Obtener cuentas de Ingresos y Gastos
    cuentas = Account.objects.filter(
        company_id=company_id, 
        account_type__in=['INCOME', 'EXPENSE']
    )
    
    resultados = []
    total_ingresos = 0
    total_gastos = 0

    for cuenta in cuentas:
        # Sumar movimientos SOLO dentro del rango de fechas
        movimientos = JournalItem.objects.filter(
            entry__date__range=[start_date, end_date],
            account=cuenta
        ).aggregate(
            total_debe=Sum('debit'),
            total_haber=Sum('credit')
        )

        debe = movimientos['total_debe'] or 0
        haber = movimientos['total_haber'] or 0
        saldo = 0

        # Lógica contable:
        # Ingresos aumentan en el Haber (Credit)
        if cuenta.account_type == 'INCOME':
            saldo = haber - debe
            if saldo > 0: total_ingresos += saldo
            
        # Gastos aumentan en el Debe (Debit)
        elif cuenta.account_type == 'EXPENSE':
            saldo = debe - haber
            if saldo > 0: total_gastos += saldo

        # Solo agregamos la cuenta si tuvo movimiento en ese mes
        if saldo != 0:
            resultados.append({
                'nombre': cuenta.name,
                'codigo': cuenta.code,
                'tipo': cuenta.account_type,
                'saldo': saldo
            })

    utilidad_neta = total_ingresos - total_gastos

    return {
        'detalles': resultados,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'utilidad_neta': utilidad_neta
    }