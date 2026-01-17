
from rest_framework.permissions import BasePermission
from .models import UserRoleCompany, RolePermission

class HasModuleActionPermission(BasePermission):
    """
    Verifica que el usuario tenga el permiso (module:action) en la empresa indicada por cabecera X-Company-ID.
    """
    def has_permission(self, request, view):
        company_id = request.headers.get("X-Company-ID")
        if not company_id:
            return False

        required = getattr(view, "required_permissions", [])
        # Si no se especifica nada, basta con pertenecer a la empresa
        urcs = UserRoleCompany.objects.filter(user=request.user, company_id=company_id)
        if not urcs.exists():
            return False
        if not required:
            return True

        roles = [u.role for u in urcs]
        perms = RolePermission.objects.filter(role__in=roles).select_related("permission")
        perm_set = {(p.permission.module, p.permission.action) for p in perms}
        return any(rp in perm_set for rp in required)
