# core/context_processors.py
import datetime


def global_info(request):
    """
    Contexto global para todas las pantallas:
    - Sucursal/empresa actual
    - Fecha y hora de trabajo
    - Mes de trabajo activo (sesión)
    """
    nombre_sucursal = "Sede Central"  # Valor por defecto

    if request.user.is_authenticated:
        # 1) Intentar buscar en el usuario directo
        if getattr(request.user, 'branch', None):
            nombre_sucursal = request.user.branch.name
        # 2) Intentar buscar en el perfil
        elif hasattr(request.user, 'profile'):
            branch = getattr(request.user.profile, 'branch', None)
            if branch:
                nombre_sucursal = branch.name

    hoy = datetime.date.today()
    ahora = datetime.datetime.now()

    # Mes de trabajo desde sesión; si no existe, usar mes/año actuales
    working_month = request.session.get('working_month', hoy.month)
    working_year = request.session.get('working_year', hoy.year)

    nombres_meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    try:
        working_month_int = int(working_month)
        if working_month_int < 1 or working_month_int > 12:
            working_month_int = hoy.month
    except (TypeError, ValueError):
        working_month_int = hoy.month

    working_month_name = nombres_meses[working_month_int - 1]

    return {
        'GLOBAL_SUCURSAL': nombre_sucursal,
        'GLOBAL_COMPANY': getattr(request.user, 'company', 'Mi Empresa S.A.'),
        'working_month': working_month_int,
        'working_year': working_year,
        'working_month_name': working_month_name,
        'current_real_date': hoy,
        'current_datetime': ahora,
    }
