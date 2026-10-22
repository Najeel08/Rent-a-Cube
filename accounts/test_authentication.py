"""Role authentication and missing-migration regressions, using test data only."""
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch
import re

from PIL import Image
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.tests import UserTestCase
from admin_portal.models import PlatformAdmin
from config.auth_utils import hash_password, password_matches
from home.models import AbuseWindow
from owners.models import Technician


class AuthenticationFlowTests(UserTestCase):
    def setUp(self):
        super().setUp()
        self.password = 'Role-login-test!2026'
        encoded = hash_password(self.password)
        self.technician = Technician.objects.create(
            owner=self.owner, name='Auth Technician', email='tech-auth@example.test',
            password=encoded, phone_number='9876543210', place='Kochi',
        )
        self.admin = PlatformAdmin.objects.create(email='admin-auth@example.test', password=encoded)

    def sign_in(self, role, password=None, client=None):
        account = self.technician if role == 'technician' else self.admin
        return (client or self.client).post(reverse(role + '_login'), {
            'email': ' ' + account.email.upper() + ' ',
            'password': self.password if password is None else password,
        })

    def test_technician_login_persists_and_denies_admin_access(self):
        old_session = self.client.session
        old_session['untrusted_marker'] = True
        old_session.save()
        response = self.sign_in('technician')
        self.assertRedirects(response, reverse('technician_dashboard'))
        self.assertEqual(self.client.session['role'], 'technician')
        self.assertNotEqual(self.client.session.session_key, old_session.session_key)
        self.assertNotIn('untrusted_marker', self.client.session)
        self.assertEqual(self.client.get(reverse('technician_service_request_list')).status_code, 200)
        self.assertRedirects(self.client.get(reverse('admin_dashboard')), reverse('admin_login'))

    def test_platform_admin_login_persists_and_denies_technician_access(self):
        self.assertRedirects(self.sign_in('admin'), reverse('admin_dashboard'))
        self.assertEqual(self.client.session['role'], 'admin')
        self.assertEqual(self.client.get(reverse('admin_owner_list')).status_code, 200)
        self.assertRedirects(self.client.get(reverse('technician_dashboard')), reverse('technician_login'))

    def test_invalid_passwords_and_unknown_accounts_do_not_authenticate(self):
        for role in ['technician', 'admin']:
            with self.subTest(role=role):
                self.assertEqual(self.sign_in(role, 'wrong-password').status_code, 200)
                self.assertNotIn('role', self.client.session)
                response = self.client.post(reverse(role + '_login'), {'email': 'absent@example.test', 'password': self.password})
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('role', self.client.session)

    def test_django_admin_credentials_do_not_grant_platform_admin_role(self):
        get_user_model().objects.create_user('django-only', email='django-only@example.test', password=self.password, is_staff=True)
        self.client.post(reverse('admin_login'), {'email': 'django-only@example.test', 'password': self.password})
        self.assertNotIn('role', self.client.session)

    def test_separate_django_admin_login_requires_active_staff_and_logs_out(self):
        account = get_user_model().objects.create_user('staff-test', password=self.password, is_staff=True)
        url = reverse('admin:login')
        credentials = {'username': account.username, 'password': self.password, 'next': reverse('admin:index')}
        self.assertEqual(self.client.post(url, {**credentials, 'password': 'wrong'}).status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(url, credentials), reverse('admin:index'))
        self.assertNotIn('role', self.client.session)
        self.assertRedirects(self.client.get(reverse('admin_dashboard')), reverse('admin_login'))
        self.assertEqual(self.client.post(reverse('admin:logout')).status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        account.is_active = False
        account.save(update_fields=['is_active'])
        self.assertEqual(self.client.post(url, credentials).status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        account.is_active = True
        account.is_staff = False
        account.save(update_fields=['is_active', 'is_staff'])
        self.assertEqual(self.client.post(url, credentials).status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_unapproved_owner_blocks_technician_login(self):
        self.owner.accept = False
        self.owner.save(update_fields=['accept'])
        self.assertEqual(self.sign_in('technician').status_code, 200)
        self.assertNotIn('role', self.client.session)

    def test_csrf_and_post_only_logout_for_both_roles(self):
        for role in ['technician', 'admin']:
            with self.subTest(role=role):
                client = Client(enforce_csrf_checks=True)
                client.get(reverse(role + '_login'))
                self.assertEqual(self.sign_in(role, client=client).status_code, 403)
                token = client.cookies['csrftoken'].value
                account = self.technician if role == 'technician' else self.admin
                response = client.post(reverse(role + '_login'), {
                    'email': account.email, 'password': self.password, 'csrfmiddlewaretoken': token,
                })
                self.assertEqual(response.status_code, 302)
                self.assertNotEqual(client.cookies['csrftoken'].value, token)
                self.assertEqual(client.get(reverse('logout')).status_code, 405)
                self.assertEqual(client.post(reverse('logout')).status_code, 403)
                client.post(reverse('logout'), {'csrfmiddlewaretoken': client.cookies['csrftoken'].value})
                self.assertNotIn('role', client.session)
                self.assertRedirects(client.get(reverse(role + '_dashboard')), reverse(role + '_login'))

    def test_role_login_rate_limits_expire_without_permanent_account_lock(self):
        now = timezone.now()
        for role in ['technician', 'admin']:
            with self.subTest(role=role), patch('config.middleware.timezone.now', return_value=now):
                for _ in range(10):
                    self.assertEqual(self.sign_in(role, 'wrong').status_code, 200)
                blocked = self.sign_in(role)
                self.assertEqual(blocked.status_code, 429)
                self.assertEqual(blocked['Retry-After'], '900')
            with patch('config.middleware.timezone.now', return_value=now + timedelta(minutes=16)):
                self.assertEqual(self.sign_in(role).status_code, 302)
            self.client.logout()

    @patch('config.middleware.PortalSecurityMiddleware._check_limits', side_effect=OperationalError('database is locked'))
    def test_abuse_storage_outage_fails_closed_without_database_details(self, check):
        with self.assertLogs('config.middleware', level='ERROR'):
            response = self.sign_in('admin')
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, 'database is locked', status_code=503)
        self.assertNotIn('role', self.client.session)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_owner_creates_technician_duplicate_is_rejected_then_setup_and_login(self):
        self.client.post(reverse('owner_login'), {'email': self.owner.email, 'password': 'owner-password'})
        with override_settings(STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }):
            def payload():
                data = BytesIO()
                Image.new('RGB', (2, 2)).save(data, 'PNG')
                return dict(name='New Technician', email='new-tech@example.test', phonenumber='9876543210',
                            workex='2 years', place='Kochi', qualification='Facilities',
                            image=SimpleUploadedFile('photo.png', data.getvalue(), content_type='image/png'))
            self.assertRedirects(self.client.post(reverse('technician_create'), payload()), reverse('owner_technician_list'))
            tech = Technician.objects.get(email='new-tech@example.test')
            self.assertFalse(tech.password)
            self.assertEqual(self.client.post(reverse('technician_create'), payload()).status_code, 200)
            self.assertEqual(Technician.objects.filter(email=tech.email).count(), 1)
            self.client.post(reverse('technician_login_email', args=[tech.pk]))
            link = re.search(r'https?://\S+', mail.outbox[-1].body).group()
            visitor = Client()
            response = visitor.post(link, {'password': self.password, 'cpassword': self.password})
            self.assertRedirects(response, reverse('technician_login'))
            tech.refresh_from_db()
            self.assertTrue(password_matches(self.password, tech.password))
            self.assertRedirects(visitor.post(reverse('technician_login'), {'email': tech.email, 'password': self.password}), reverse('technician_dashboard'))
            self.assertEqual(visitor.get(link).status_code, 400)


class AbuseWindowMigrationTests(TransactionTestCase):
    def test_unapplied_migration_blocks_login_and_migration_restores_it(self):
        """Reproduce the exact missing table, only inside Django's test database."""
        self.assertIn('homeapp_abusewindow', connection.introspection.table_names())
        try:
            MigrationExecutor(connection).migrate([('homeapp', '0001_supportinquiry')])
            self.assertNotIn('homeapp_abusewindow', connection.introspection.table_names())
            for role in ['technician', 'admin']:
                with self.assertLogs('config.middleware', level='ERROR'):
                    response = self.client.post(reverse(role + '_login'), {'email': 'unknown@example.test', 'password': 'wrong'})
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('role', self.client.session)
        finally:
            MigrationExecutor(connection).migrate([('homeapp', '0002_abusewindow')])
        self.assertIn('homeapp_abusewindow', connection.introspection.table_names())
        for role in ['technician', 'admin']:
            response = self.client.post(reverse(role + '_login'), {'email': 'unknown@example.test', 'password': 'wrong'})
            self.assertEqual(response.status_code, 200)
        self.assertGreater(AbuseWindow.objects.count(), 0)
