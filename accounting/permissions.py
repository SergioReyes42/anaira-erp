
from rest_framework.permissions import BasePermission

class GroupsRequired(BasePermission):
    """
    Permiso que valida si el usuario pertenece a al menos uno
    de los grupos permitidos definidos en la vista (atributo allowed_groups).
    Si no se define allowed_groups en la vista, exige sólo autenticación.
    """
    message = "No tiene permisos para acceder a este recurso."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        allowed = getattr(view, "allowed_groups", None)
        # Superusuario siempre pasa
        if request.user.is_superuser:
            return True

        if not allowed:
            return True  # sólo autenticado

        user_groups = set(request.user.groups.values_list("name", flat=True))
        return bool(user_groups.intersection(set(allowed)))
# FIN accounting/permissions.py
