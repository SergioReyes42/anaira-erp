
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if hasattr(user, "is_admin_or_staff") and user.is_admin_or_staff():
            return view_func(request, *args, **kwargs)
        messages.error(request, "Acceso restringido a administradores.")
        return redirect("accounts:login")
    return _wrapped
# FIN accounts/decorators.py
