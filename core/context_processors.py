# core/context_processors.py
import datetime

from .models import Company


def global_info(request):
    """
    Contexto global para todas las pantallas:
    - Sucursal/empresa actual
    - Fecha y hora de trabajo
    - Mes de trabajo activo (sesión)
    """
    nombre_sucursal = "Sede Central"  # Valor por defecto
    global_company = "Mi Empresa S.A."

    if request.user.is_authenticated:
        # Priorizamos empresa seleccionada en sesión
        session_company_id = request.session.get('company_id')
        selected_company = None

        if session_company_id:
            selected_company = Company.objects.filter(id=session_company_id).first()

        # Fallback a empresa actual del usuario
        if not selected_company:
            selected_company = getattr(request.user, 'current_company', None)

        if selected_company:
            nombre_sucursal = selected_company.name
            global_company = selected_company.name

        # Compatibilidad con estructuras previas de branch/profile
        elif getattr(request.user, 'branch', None):
            nombre_sucursal = request.user.branch.name
            global_company = request.user.branch.name
        elif hasattr(request.user, 'profile'):
            branch = getattr(request.user.profile, 'branch', None)
            if branch:
                nombre_sucursal = branch.name
                global_company = branch.name

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
        'GLOBAL_COMPANY': global_company,
        'working_month': working_month_int,
        'working_year': working_year,
        'working_month_name': working_month_name,
        'current_real_date': hoy,
        'current_datetime': ahora,
    }
