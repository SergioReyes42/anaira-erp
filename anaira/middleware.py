import threading
from django.utils.deprecation import MiddlewareMixin

_thread_locals = threading.local()

def get_current_company():
    return getattr(_thread_locals, 'company', None)

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class ActiveCompanyMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        company_id = request.session.get('company_id')
        _thread_locals.company = None
        request.company = None

        if company_id:
            # CAMBIO AQUÍ: Importamos Company, no CompanyProfile
            from core.models import Company 
            try:
                # Buscamos la Empresa real
                company = Company.objects.get(id=company_id)
                _thread_locals.company = company
                request.company = company
            except Company.DoesNotExist:
                pass