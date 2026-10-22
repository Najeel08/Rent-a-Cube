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

    def test_contact_subject_is_saved_with_message(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Visitor', 'email': 'visitor@example.test',
            'subject': 'booking', 'message': 'Please check my booking.',
        })
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(SupportInquiry.objects.get().message,
                         '[Booking Assistance]\n\nPlease check my booking.')

    def test_invalid_contact_subject_retains_input_without_saving(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Visitor', 'email': 'visitor@example.test',
            'subject': 'unknown', 'message': 'Please help.',
        })
        self.assertContains(response, 'Select a valid subject.')
        self.assertContains(response, 'Please help.')
        self.assertFalse(SupportInquiry.objects.exists())

    def test_contact_subject_and_message_respect_storage_limit(self):
        for length, valid in [(1470, True), (1500, False)]:
            SupportInquiry.objects.all().delete()
            response = self.client.post(reverse('contact'), {
                'name': 'Visitor', 'email': 'visitor@example.test',
                'subject': 'workspace', 'message': 'x' * length,
            })
            self.assertEqual(response.status_code, 302 if valid else 200)
            self.assertEqual(SupportInquiry.objects.exists(), valid)


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
