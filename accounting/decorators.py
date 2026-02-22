from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

def group_required(*group_names):
    """
    Bloquea el acceso a la vista si el usuario NO pertenece a los grupos indicados.
    Uso: @group_required('Contadora', 'Gerente')
    """
    def in_groups(u):
        if u.is_superuser:
            return True # El superusuario siempre pasa
        if bool(u.groups.filter(name__in=group_names)) | u.is_superuser:
            return True
        return False

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if in_groups(request.user):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Acceso Denegado. Tu rol no tiene permisos para esta área.")
                return redirect('home') # O mándalo a una página de error 403
        return _wrapped_view
    return decorator