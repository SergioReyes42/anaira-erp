# core/context_processors.py
import datetime

def global_info(request):
    """
    Este código se ejecuta en CADA carga de página.
    Busca la sucursal del usuario para mostrarla en la barra superior.
    """
    nombre_sucursal = "Sede Central" # Valor por defecto
    
    if request.user.is_authenticated:
        # 1. Intentar buscar en el usuario directo
        if getattr(request.user, 'branch', None):
            nombre_sucursal = request.user.branch.name
        # 2. Intentar buscar en el perfil
        elif hasattr(request.user, 'profile'):
            branch = getattr(request.user.profile, 'branch', None)
            if branch:
                nombre_sucursal = branch.name
        
    """Manda el mes de trabajo y el reloj a todas las pantallas de Anaira ERP"""
    
    # 1. Obtenemos la fecha real de hoy
    hoy = datetime.date.today()
    
    # 2. Buscamos en la sesión si el usuario eligió un mes de trabajo. 
    # Si no ha elegido nada, usamos el mes y año actual por defecto.
    working_month = request.session.get('working_month', hoy.month)
    working_year = request.session.get('working_year', hoy.year)
    
    # 3. Nombres de los meses para que se vea bonito en pantalla
    nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    working_month_name = nombres_meses[int(working_month) - 1]

    return {
        'working_month': working_month,
        'working_year': working_year,
        'working_month_name': working_month_name,
        'current_real_date': hoy,
    }

    return {
        'GLOBAL_SUCURSAL': nombre_sucursal,
        'GLOBAL_COMPANY': getattr(request.user, 'company', 'Mi Empresa S.A.')
    }