# core/context_processors.py

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

    return {
        'GLOBAL_SUCURSAL': nombre_sucursal,
        'GLOBAL_COMPANY': getattr(request.user, 'company', 'Mi Empresa S.A.')
    }