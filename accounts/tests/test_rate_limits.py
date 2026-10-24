"""Rate limits tests and fixtures."""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.utils.crypto import salted_hmac
from accounts import views as customer_views
from config.middleware import PortalSecurityMiddleware
from home.models import AbuseWindow
from owners import views as owner_views


class ViewRateLimitTests(TestCase):
    def test_relocated_views_keep_existing_rate_limit_counters(self):
        now = timezone.now()
        window = int(now.timestamp()) // 900
        for module, view in [
            ('accounts.views', customer_views.sign_in),
            ('owners.views', owner_views.sign_in),
            ('accounts.views', customer_views.checkout),
        ]:
            with self.subTest(view=f'{module}.{view.__name__}'):
                key = salted_hmac(
                    'abuse-window',
                    f'{module}:{view.__name__}:account:demo@example.test:{window}',
                ).hexdigest()
                AbuseWindow.objects.create(
                    key=key, count=10, expires_at=now + timedelta(minutes=16),
                )
                response = PortalSecurityMiddleware._check_limits(
                    view, view.__name__, [('account', 'demo@example.test', 10)], window, now,
                )
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response['Retry-After'], '900')
                self.assertEqual(AbuseWindow.objects.get(pk=key).count, 10)
