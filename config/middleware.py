"""Shared abuse limits and private-page cache policy for custom role portals."""
from datetime import timedelta
import logging

from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.cache import patch_cache_control

from home.models import AbuseWindow


logger = logging.getLogger(__name__)


class PortalSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != 'POST':
            return None
        name = view_func.__name__
        business_actions = {'checkout', 'workspace_book', 'customer_conversation', 'conversation', 'service_request_create'}
        sensitive = name in {'sign_in', 'register', 'contact', 'send_technician_login', 'login', 'activate'} | business_actions
        if not sensitive:
            return None
        now = timezone.now()
        window = int(now.timestamp()) // 900
        # Trust only REMOTE_ADDR. Forwarded headers must be normalized at the
        # trusted reverse proxy; arbitrary X-Forwarded-For is never accepted.
        identities = [('ip', request.META.get('REMOTE_ADDR', ''), 60)]
        if name in {'sign_in', 'login'}:
            identities.append(('account', request.POST.get('email', request.POST.get('username', '')).strip().lower(), 10))
        if name in business_actions and request.session.get('id'):
            limit = 10 if name == 'checkout' else 60
            identities.append(('actor', f"{request.session.get('role')}:{request.session['id']}", limit))
        try:
            return self._check_limits(view_func, name, identities, window, now)
        except DatabaseError:
            # Fail closed: never bypass abuse protection when storage is absent
            # or unavailable. Keep schema details out of the public response.
            logger.error('Abuse-prevention storage unavailable. Check migrations and database connectivity.')
            response = HttpResponse('Sign-in and submissions are temporarily unavailable. Please try again later.', status=503)
            response['Retry-After'] = '60'
            return response

    @staticmethod
    def _check_limits(view_func, name, identities, window, now):
        with transaction.atomic():
            AbuseWindow.objects.filter(expires_at__lte=now).delete()
            for kind, value, limit in identities:
                key = salted_hmac('abuse-window', f'{view_func.__module__}:{name}:{kind}:{value}:{window}').hexdigest()
                counter, _ = AbuseWindow.objects.select_for_update().get_or_create(
                    key=key, defaults={'expires_at': now + timedelta(minutes=16)},
                )
                if counter.count >= limit:
                    response = HttpResponse('Too many attempts. Please try again in 15 minutes.', status=429)
                    response['Retry-After'] = '900'
                    return response
                counter.count += 1
                counter.save(update_fields=['count'])

    def __call__(self, request):
        response = self.get_response(request)
        if request.session.get('role') or request.path.startswith(('/admin/', '/admin-portal/', '/technicians/activate/')):
            patch_cache_control(response, private=True, no_store=True)
        if request.path.startswith('/technicians/activate/'):
            response['Referrer-Policy'] = 'no-referrer'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['Content-Security-Policy'] = "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        return response
