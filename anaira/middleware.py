import threading
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

_thread_locals = threading.local()

def get_current_company():
    return getattr(_thread_locals, 'company', None)

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class ActiveCompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)
        _thread_locals.user = user
        _thread_locals.company = None
        request.company = None

        if not user or not user.is_authenticated:
            return

        from core.models import Company, UserSessionLog

        user_company = getattr(user, 'current_company', None)
        session_company_id = request.session.get('company_id')
        active_company = None

        # 1) Prioridad a sesión (si existe), con validación de permisos
        if session_company_id:
            try:
                session_company = Company.objects.get(id=session_company_id)
                is_allowed = (
                    user.is_superuser
                    or session_company == user_company
                    or user.allowed_companies.filter(id=session_company.id).exists()
                )
                if is_allowed:
                    active_company = session_company
                else:
                    request.session.pop('company_id', None)
            except Company.DoesNotExist:
                request.session.pop('company_id', None)

        # 2) Fallback a current_company del usuario
        if not active_company and user_company:
            is_allowed_user_company = (
                user.is_superuser
                or user.allowed_companies.filter(id=user_company.id).exists()
                or user_company == user_company
            )
            if is_allowed_user_company:
                active_company = user_company
                request.session['company_id'] = user_company.id

        # 3) Sincronizar user.current_company con la empresa activa
        if active_company and user_company != active_company:
            user.current_company = active_company
            try:
                user.save(update_fields=['current_company'])
            except Exception:
                pass

        _thread_locals.company = active_company
        request.company = active_company

        session_key = request.session.session_key or ''
        if session_key:
            UserSessionLog.objects.filter(
                user=user,
                session_key=session_key,
                logout_at__isnull=True
            ).update(last_seen=timezone.now(), company=active_company)
