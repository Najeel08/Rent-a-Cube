"""Shared abuse limits and private-page cache policy for custom role portals."""
from datetime import timedelta
from ipaddress import ip_address, ip_network
import logging
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.cache import patch_cache_control

from home.models import AbuseWindow


logger = logging.getLogger(__name__)


class TrustedProxyMiddleware:
    """Only an explicitly trusted peer may supply the client IP or HTTPS scheme."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.networks = [ip_network(value, strict=False) for value in settings.TRUSTED_PROXY_IPS]

    def __call__(self, request):
        try:
            peer = ip_address(request.META.get('REMOTE_ADDR', ''))
            trusted = any(peer in network for network in self.networks)
        except ValueError:
            trusted = False
        if not trusted:
            request.META.pop('HTTP_X_FORWARDED_PROTO', None)
            request.META.pop('HTTP_X_REAL_IP', None)
        else:
            # The proxy must replace these headers, never append browser values.
            client = request.META.get('HTTP_X_REAL_IP')
            if not client:
                return HttpResponseBadRequest('Missing proxy client address.')
            try:
                request.META['REMOTE_ADDR'] = str(ip_address(client))
            except ValueError:
                return HttpResponseBadRequest('Invalid proxy client address.')
            protocol = request.META.get('HTTP_X_FORWARDED_PROTO')
            if protocol and protocol not in ('http', 'https'):
                return HttpResponseBadRequest('Invalid proxy protocol.')
        # No part of this application trusts arbitrary forwarded address chains.
        request.META.pop('HTTP_X_FORWARDED_FOR', None)
        request.META.pop('HTTP_X_FORWARDED_HOST', None)
        return self.get_response(request)


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
        # TrustedProxyMiddleware normalizes this before any limits are checked.
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
            # Bound cleanup work so an expired backlog cannot hold the SQLite
            # writer lock for an entire bulk delete during someone else's login.
            expired = list(AbuseWindow.objects.filter(expires_at__lte=now).values_list('pk', flat=True)[:100])
            if expired:
                AbuseWindow.objects.filter(pk__in=expired).delete()
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
        request.csp_nonce = secrets.token_urlsafe(24)
        expired = self._check_session_age(request)
        if expired:
            return self._secure_response(request, expired)
        response = self.get_response(request)
        return self._secure_response(request, response)

    @staticmethod
    def _check_session_age(request):
        role = request.session.get('role')
        staff = request.user.is_authenticated and request.user.is_staff
        if role not in ('admin', 'technician') and not staff:
            return None
        now = int(time.time())
        started = request.session.get('privileged_started_at', now)
        last_active = request.session.get('privileged_last_active', now)
        idle_limit = settings.ADMIN_IDLE_TIMEOUT if role == 'admin' or staff else settings.TECHNICIAN_IDLE_TIMEOUT
        if now - last_active >= idle_limit or now - started >= settings.PRIVILEGED_SESSION_MAX_AGE:
            request.session.flush()
            messages.info(request, 'Your session has expired. Please sign in again.')
            return redirect('admin:login' if staff else 'admin_login' if role == 'admin' else 'technician_login')
        if 'privileged_started_at' not in request.session:
            request.session['privileged_started_at'] = now
            request.session.set_expiry(0)
        # Avoid a database session write on every request. At most one minute of
        # activity is rounded down; this never extends the inactivity limit.
        if 'privileged_last_active' not in request.session or now - last_active >= 60:
            request.session['privileged_last_active'] = now
        return None

    @staticmethod
    def _secure_response(request, response):
        if request.session.get('role') or request.path.startswith(('/admin/', '/admin-portal/', '/technicians/activate/')):
            patch_cache_control(response, private=True, no_store=True)
        if request.path.startswith('/technicians/activate/'):
            response['Referrer-Policy'] = 'no-referrer'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        policy = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{request.csp_nonce}' https://checkout.razorpay.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https://*.razorpay.com; "
            "connect-src 'self' https://*.razorpay.com; "
            "frame-src https://*.razorpay.com; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        view = getattr(getattr(request, 'resolver_match', None), 'func', None)
        checkout = view and view.__module__ == 'accounts.views' and view.__name__ == 'checkout'
        if checkout and not settings.CHECKOUT_CSP_ENFORCE:
            # The provider's iframe/scripts can change independently of this
            # repository. Validate in its sandbox before enforcing on checkout.
            response['Content-Security-Policy-Report-Only'] = policy
            response['Content-Security-Policy'] = "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        else:
            response['Content-Security-Policy'] = policy
        if response.get('Content-Type', '').startswith('text/html'):
            patch_cache_control(response, private=True, no_cache=True)
        return response
