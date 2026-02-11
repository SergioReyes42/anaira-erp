import threading
from django.utils.deprecation import MiddlewareMixin

# Almacén de memoria temporal (Thread Local)
_thread_locals = threading.local()

def get_current_company():
    """ Devuelve la empresa activa del usuario actual """
    return getattr(_thread_locals, 'company', None)

def get_current_user():
    """ Devuelve el usuario actual """
    return getattr(_thread_locals, 'user', None)

class ActiveCompanyMiddleware(MiddlewareMixin):
    """
    Este middleware captura la empresa activa de la sesión y la pone disponible 
    globalmente para que los Modelos puedan auto-filtrarse.
    """
    def process_request(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        
        # Intentamos obtener la empresa de la sesión
        company_id = request.session.get('company_id')
        if company_id:
            # Importamos aquí para evitar referencia circular
            from core.models import CompanyProfile
            try:
                company = CompanyProfile.objects.get(id=company_id)
                _thread_locals.company = company
                request.company = company # Disponible en views también
            except CompanyProfile.DoesNotExist:
                _thread_locals.company = None
                request.company = None
        else:
            _thread_locals.company = None
            request.company = None