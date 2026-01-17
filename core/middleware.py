from threading import local

_thread_locals = local()

def get_current_db():
    return getattr(_thread_locals, 'db', 'default')

class CompanyRoutingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si el usuario tiene una empresa en su sesión, cambiamos la DB
        company_db = request.session.get('active_company_db', 'default')
        _thread_locals.db = company_db
        
        response = self.get_response(request)
        return response