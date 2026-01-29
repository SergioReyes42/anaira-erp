# anaira_erp/middleware.py
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Marcamos al usuario como 'online' por 300 segundos (5 min)
            # Cada vez que haga clic, este tiempo se reinicia.
            now = timezone.now()
            cache.set(f'seen_{request.user.username}', now, 300)
        
        response = self.get_response(request)
        return response