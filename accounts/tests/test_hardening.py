"""Regression tests for login timing, session expiry, proxy trust and privacy."""
from html.parser import HTMLParser
from io import StringIO
import logging
import os
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher, get_hasher, make_password
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from admin_portal.models import PlatformAdmin
from config.auth_utils import session_auth_hash
from config.middleware import PortalSecurityMiddleware, TrustedProxyMiddleware
from config.security import RedactedConsoleEmailBackend, SafeFormatter, SetupLinkFilter
from owners.models import Owner, Technician


class LoginHardeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Audit-regression!2026'
        encoded = make_password(cls.password)
        cls.owner = Owner.objects.create(name='Approved owner', email='owner@example.test', password=encoded, accept=True)
        cls.admin = PlatformAdmin.objects.create(email='admin@example.test', password=encoded)
        cls.tech = Technician.objects.create(name='Technician', email='tech@example.test', password=encoded, owner=cls.owner)
        cls.staff = get_user_model().objects.create(username='staff', password=encoded, is_staff=True)

    def signed_in_client(self, role):
        client = Client()
        if role == 'staff':
            client.force_login(self.staff)
        else:
            account = self.admin if role == 'admin' else self.tech
            session = client.session
            session.update({'role': role, 'id': account.pk, 'auth_hash': session_auth_hash(account)})
            session.save()
        return client

    def test_missing_and_existing_accounts_both_run_password_hasher(self):
        encode = PBKDF2PasswordHasher.encode
        for role, account in [('admin', self.admin), ('technician', self.tech)]:
            for email in (account.email, 'missing@example.test'):
                with self.subTest(role=role, missing=email != account.email):
                    with patch.object(PBKDF2PasswordHasher, 'encode', autospec=True, side_effect=encode) as work:
                        response = self.client.post(reverse(role + '_login'), {'email': email, 'password': 'Incorrect-password!2026'})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(work.call_count, 1)
                    self.assertNotIn('role', self.client.session)

    def test_pending_and_unapproved_technicians_do_not_skip_password_work(self):
        encode = PBKDF2PasswordHasher.encode
        for pending in (True, False):
            self.tech.password = '' if pending else make_password(self.password)
            self.tech.save(update_fields=['password'])
            self.owner.accept = False
            self.owner.save(update_fields=['accept'])
            with patch.object(PBKDF2PasswordHasher, 'encode', autospec=True, side_effect=encode) as work:
                response = self.client.post(reverse('technician_login'), {'email': self.tech.email, 'password': self.password})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(work.call_count, 1)
            self.assertNotIn('role', self.client.session)

    def test_all_privileged_sessions_expire_after_inactivity(self):
        now = int(time.time())
        for role, page, login, timeout in [
            ('admin', 'admin_dashboard', 'admin_login', settings.ADMIN_IDLE_TIMEOUT),
            ('technician', 'technician_dashboard', 'technician_login', settings.TECHNICIAN_IDLE_TIMEOUT),
            ('staff', 'admin:index', 'admin:login', settings.ADMIN_IDLE_TIMEOUT),
        ]:
            with self.subTest(role=role):
                client = self.signed_in_client(role)
                with patch('config.middleware.time.time', return_value=now):
                    self.assertEqual(client.get(reverse(page)).status_code, 200)
                self.assertTrue(client.session.get_expire_at_browser_close())
                with patch('config.middleware.time.time', return_value=now + timeout):
                    self.assertRedirects(client.get(reverse(page)), reverse(login), fetch_redirect_response=False)
                self.assertNotIn('role', client.session)
                self.assertNotIn('_auth_user_id', client.session)

    def test_active_session_cannot_exceed_absolute_lifetime(self):
        client = self.signed_in_client('admin')
        now = int(time.time())
        session = client.session
        session['privileged_started_at'] = now - settings.PRIVILEGED_SESSION_MAX_AGE
        session['privileged_last_active'] = now
        session.save()
        with patch('config.middleware.time.time', return_value=now):
            self.assertRedirects(client.get(reverse('admin_dashboard')), reverse('admin_login'), fetch_redirect_response=False)
        self.assertNotIn('role', client.session)

    def test_expired_session_cannot_perform_an_admin_mutation(self):
        self.owner.accept = False
        self.owner.save(update_fields=['accept'])
        client = self.signed_in_client('admin')
        session = client.session
        session['privileged_last_active'] = int(time.time()) - settings.ADMIN_IDLE_TIMEOUT - 1
        session.save()
        self.assertRedirects(client.post(reverse('admin_owner_approve', args=[self.owner.pk])), reverse('admin_login'), fetch_redirect_response=False)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.accept)

    def test_activity_tracking_does_not_write_session_on_every_request(self):
        client = self.signed_in_client('technician')
        now = int(time.time())
        with patch('config.middleware.time.time', return_value=now):
            client.get(reverse('technician_dashboard'))
        with patch('config.middleware.time.time', return_value=now + 30):
            client.get(reverse('technician_dashboard'))
        self.assertEqual(client.session['privileged_last_active'], now)
        with patch('config.middleware.time.time', return_value=now + 61):
            client.get(reverse('technician_dashboard'))
        self.assertEqual(client.session['privileged_last_active'], now + 61)

    def test_legacy_django_staff_hash_upgrades_with_real_password_login(self):
        self.staff.password = PBKDF2PasswordHasher().encode(self.password, 'synthetic-salt', iterations=260000)
        self.staff.save(update_fields=['password'])
        self.assertTrue(get_hasher().must_update(self.staff.password))
        response = self.client.post(reverse('admin:login'), {'username': self.staff.username, 'password': self.password, 'next': reverse('admin:index')})
        self.assertEqual(response.status_code, 302)
        self.staff.refresh_from_db()
        self.assertFalse(get_hasher().must_update(self.staff.password))


@override_settings(TRUSTED_PROXY_IPS=['192.0.2.10/32'], SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class ProxyTrustTests(SimpleTestCase):
    def request(self, peer, client='198.51.100.12', scheme='https'):
        request = RequestFactory().get('/', REMOTE_ADDR=peer, HTTP_X_REAL_IP=client,
                                       HTTP_X_FORWARDED_PROTO=scheme, HTTP_X_FORWARDED_FOR='forged-address')
        response = TrustedProxyMiddleware(lambda req: HttpResponse('ok'))(request)
        return request, response

    def test_untrusted_peer_cannot_spoof_client_address_or_https(self):
        request, response = self.request('198.51.100.99')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.META['REMOTE_ADDR'], '198.51.100.99')
        self.assertFalse(request.is_secure())
        self.assertNotIn('HTTP_X_FORWARDED_FOR', request.META)

    def test_trusted_proxy_preserves_distinct_client_addresses(self):
        for ip in ('198.51.100.12', '198.51.100.13', '2001:db8::1'):
            request, response = self.request('192.0.2.10', client=ip)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(request.META['REMOTE_ADDR'], ip)
            self.assertTrue(request.is_secure())

    def test_trusted_proxy_rejects_ambiguous_addresses_and_protocols(self):
        for client, scheme in [('', 'https'), ('198.51.100.12, 198.51.100.13', 'https'), ('invalid', 'https'), ('198.51.100.12', 'https,http')]:
            self.assertEqual(self.request('192.0.2.10', client, scheme)[1].status_code, 400)


class PrivacyAndPolicyTests(SimpleTestCase):
    def test_checkout_policy_can_be_rolled_out_without_disabling_existing_protection(self):
        from accounts.views import checkout
        request = RequestFactory().get('/')
        request.session = {}
        request.csp_nonce = 'synthetic-nonce'
        request.resolver_match = SimpleNamespace(func=checkout)
        with override_settings(CHECKOUT_CSP_ENFORCE=False):
            response = PortalSecurityMiddleware._secure_response(request, HttpResponse('checkout'))
        self.assertIn("script-src 'self'", response['Content-Security-Policy-Report-Only'])
        self.assertIn("frame-ancestors 'none'", response['Content-Security-Policy'])
        with override_settings(CHECKOUT_CSP_ENFORCE=True):
            response = PortalSecurityMiddleware._secure_response(request, HttpResponse('checkout'))
        self.assertNotIn('Content-Security-Policy-Report-Only', response)
        self.assertIn("script-src 'self'", response['Content-Security-Policy'])

    def test_console_email_and_tracebacks_do_not_disclose_setup_token(self):
        link = 'https://example.test/technicians/activate/synthetic-bearer-token/'
        stream = StringIO()
        backend = RedactedConsoleEmailBackend(stream=stream)
        backend.send_messages([EmailMessage('Setup', 'Use this link: ' + link, to=['demo@example.test'])])
        self.assertNotIn('synthetic-bearer-token', stream.getvalue())
        self.assertIn('[redacted]', stream.getvalue())
        try:
            raise ValueError(link)
        except ValueError:
            record = logging.LogRecord('django.request', logging.ERROR, __file__, 1, 'Not Found: %s', (link,), sys.exc_info())
        SetupLinkFilter().filter(record)
        result = SafeFormatter().format(record)
        self.assertNotIn('synthetic-bearer-token', result)
        self.assertIn('[redacted]', result)

    def test_templates_have_no_executable_inline_event_attributes(self):
        class Events(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for name, value in attrs:
                    if name.startswith('on'):
                        raise AssertionError('Inline event handler: ' + name)
        for path in (settings.BASE_DIR / 'templates').rglob('*.html'):
            with self.subTest(template=str(path.relative_to(settings.BASE_DIR))):
                Events().feed(path.read_text(encoding='utf-8'))

    def test_production_rejects_insecure_environment_without_printing_secrets(self):
        base = {key: value for key, value in os.environ.items() if not key.startswith('DJANGO_')}
        base.update(DJANGO_SETTINGS_MODULE='config.settings', DJANGO_LOAD_ENV='0', DJANGO_DEBUG='False',
                    DJANGO_SECRET_KEY='synthetic-test-only-production-check-key-of-at-least-fifty-characters',
                    DJANGO_ALLOWED_HOSTS='example.test', DJANGO_DB_PATH=':memory:')
        for overrides, succeeds in [({}, True), ({'DJANGO_ALLOWED_HOSTS': '*'}, False),
                                    ({'DJANGO_SECRET_KEY': 'weak'}, False),
                                    ({'DJANGO_SECRET_KEY': 'a' * 60}, False),
                                    ({'DJANGO_TRUSTED_PROXY_IPS': '0.0.0.0/0'}, False),
                                    ({'DJANGO_SESSION_COOKIE_SECURE': 'False'}, False),
                                    ({'DJANGO_CSRF_COOKIE_SECURE': 'False'}, False),
                                    ({'DJANGO_SECURE_SSL_REDIRECT': 'False'}, False),
                                    ({'DJANGO_USE_X_FORWARDED_PROTO': 'True'}, False),
                                    ({'DJANGO_USE_X_FORWARDED_PROTO': 'True', 'DJANGO_TRUSTED_PROXY_IPS': '192.0.2.10'}, True)]:
            with self.subTest(overrides=list(overrides)):
                result = subprocess.run([sys.executable, '-B', '-c', 'from django.conf import settings; settings.DEBUG'],
                                        env={**base, **overrides}, cwd=settings.BASE_DIR, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode == 0, succeeds)
                self.assertNotIn(base['DJANGO_SECRET_KEY'], result.stderr)


class ContentPolicyTests(TestCase):
    def test_registration_inline_scripts_use_the_response_nonce(self):
        class Scripts(HTMLParser):
            def __init__(self):
                super().__init__()
                self.inline = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'script' and 'src' not in attrs:
                    self.inline.append(attrs.get('nonce'))
        previous = None
        for page in ('register', 'owner_register'):
            response = self.client.get(reverse(page))
            self.assertEqual(response.status_code, 200)
            policy = response['Content-Security-Policy']
            self.assertIn("default-src 'self'", policy)
            self.assertIn("script-src 'self' 'nonce-", policy)
            parser = Scripts()
            parser.feed(response.content.decode())
            self.assertTrue(parser.inline)
            for nonce in parser.inline:
                self.assertTrue(nonce)
                self.assertIn("'nonce-" + nonce + "'", policy)
                self.assertNotEqual(nonce, previous)
            previous = parser.inline[0]
