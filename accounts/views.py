
# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from .forms import AdminLoginForm

MAX_ATTEMPTS = 5
BLOCK_MINUTES = 15

def _rate_limit_key(request):
    ip = request.META.get("REMOTE_ADDR", "unknown")
    return f"login_attempts:{ip}"

def _blocked_key(request):
    return f"blocked:{request.META.get('REMOTE_ADDR','unknown')}"

def _is_blocked(request):
    return cache.get(_blocked_key(request)) is not None

def _block_ip(request):
    cache.set(_blocked_key(request), True, BLOCK_MINUTES * 60)

@csrf_protect
def admin_login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "is_admin_or_staff") and request.user.is_admin_or_staff():
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.warning(request, "No tienes permisos de administrador.")
            logout(request)

    if _is_blocked(request):
        messages.error(request, "Demasiados intentos. Intenta de nuevo en unos minutos.")
        return render(request, "admin/login.html", {"form": AdminLoginForm()})

    form = AdminLoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"].strip()
        password = form.cleaned_data["password"]
        remember_me = form.cleaned_data["remember_me"]
        totp_code = form.cleaned_data.get("totp_code")

        key = _rate_limit_key(request)
        attempts = cache.get(key, 0)

        user = authenticate(request, username=username, password=password)

        if user is None:
            attempts += 1
            cache.set(key, attempts, 60 * BLOCK_MINUTES)
            if attempts >= MAX_ATTEMPTS:
                _block_ip(request)
                messages.error(request, "Has superado el límite de intentos. Bloqueo temporal activado.")
            else:
                remaining = MAX_ATTEMPTS - attempts
                messages.error(request, f"Credenciales inválidas. Intentos restantes: {remaining}")
            return render(request, "admin/login.html", {"form": form})

        if not hasattr(user, "is_admin_or_staff") or not user.is_admin_or_staff():
            messages.error(request, "Tu cuenta no tiene permisos de administrador.")
            return render(request, "admin/login.html", {"form": form})

        # Hook opcional para 2FA TOTP si activas:
        # import pyotp
        # if user.totp_secret:
        #     totp = pyotp.TOTP(user.totp_secret)
        #     if not totp.verify(totp_code):
        #         messages.error(request, "Código 2FA inválido.")
        #         return render(request, "admin/login.html", {"form": form})

        login(request, user)

        if remember_me:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
        else:
            request.session.set_expiry(0)

        cache.delete(key)
        messages.success(request, f"Bienvenido a Anaira Systems, {user.get_full_name() or user.username}.")
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, "admin/login.html", {"form": form})


def admin_logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect(reverse("accounts:login"))
# FIN accounts/views.py