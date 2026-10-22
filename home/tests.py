from pathlib import Path
from importlib import import_module
from inspect import signature
import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.template.loader import get_template
from django.urls import reverse

from .models import SupportInquiry


class PublicPageTests(TestCase):
    def test_landing_page_is_available(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/index.html')

    def test_contact_page_is_available(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/contact.html')

    def test_contact_submission_is_saved(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Test User',
                'email': 'test@example.com',
                'message': 'Please help with a booking.',
            },
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertTrue(
            SupportInquiry.objects.filter(
                name='Test User', email='test@example.com'
            ).exists()
        )

    def test_logout_is_post_only_and_clears_session(self):
        session = self.client.session
        session['role'] = 'user'
        session['id'] = 99
        session.save()

        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, reverse('index'))
        self.assertNotIn('role', self.client.session)
        self.assertNotIn('id', self.client.session)


class TemplateAndAssetSmokeTests(TestCase):
    def test_canonical_and_legacy_routes_match_view_arguments(self):
        for package in ['home', 'accounts', 'owners', 'technicians', 'admin_portal']:
            for pattern in import_module(f'{package}.urls').urlpatterns:
                arguments = {name: converter.to_python('1') for name, converter in pattern.pattern.converters.items()}
                with self.subTest(package=package, route=str(pattern.pattern)):
                    signature(pattern.callback).bind(object(), **arguments)

    def test_every_project_template_compiles(self):
        template_root = Path(settings.BASE_DIR) / 'templates'
        template_names = [
            path.relative_to(template_root).as_posix()
            for path in template_root.rglob('*.html')
        ]

        self.assertTrue(template_names, 'The template smoke test must discover templates.')

        for template_name in template_names:
            with self.subTest(template=template_name):
                get_template(template_name)

    def test_repaired_javascript_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find('js/responsive_navbar.js'))
        self.assertIsNotNone(finders.find('css/conversation.css'))
        self.assertIsNotNone(finders.find('admin/js/jquery.min.js'))
        self.assertIsNotNone(finders.find('admin/js/bootstrap.bundle.min.js'))
        self.assertIsNotNone(finders.find('admin/js/Chart.min.js'))

    def test_static_files_referenced_by_templates_exist(self):
        for template in (Path(settings.BASE_DIR) / 'templates').rglob('*.html'):
            paths = re.findall(r"{%\s*static\s+['\"]([^'\"]+)['\"]", template.read_text(encoding='utf-8'))
            for path in paths:
                with self.subTest(template=template.name, static_file=path):
                    self.assertIsNotNone(finders.find(path))
