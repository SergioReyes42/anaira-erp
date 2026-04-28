from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import UserSessionLog


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    if not request.session.session_key:
        request.session.save()

    UserSessionLog.objects.create(
        user=user,
        company=getattr(user, 'current_company', None),
        session_key=request.session.session_key or '',
        ip_address=_client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:1000],
        login_at=timezone.now(),
        last_seen=timezone.now(),
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if not user:
        return

    session_key = ''
    if request and hasattr(request, 'session'):
        session_key = request.session.session_key or ''

    qs = UserSessionLog.objects.filter(user=user, logout_at__isnull=True)
    if session_key:
        qs = qs.filter(session_key=session_key)

    log = qs.order_by('-login_at').first()
    if log:
        log.logout_at = timezone.now()
        log.last_seen = timezone.now()
        log.save(update_fields=['logout_at', 'last_seen'])
