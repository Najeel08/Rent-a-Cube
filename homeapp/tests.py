from pathlib import Path

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
        self.assertTemplateUsed(response, 'index.html')

    def test_contact_page_is_available(self):
        response = self.client.get(reverse('contact4'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact4.html')

    def test_contact_submission_is_saved(self):
        response = self.client.post(
            reverse('contact4'),
            {
                'name': 'Test User',
                'email': 'test@example.com',
                'message': 'Please help with a booking.',
            },
        )

        self.assertRedirects(response, reverse('contact4'))
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
    def test_every_project_template_compiles(self):
        template_root = Path(settings.BASE_DIR) / 'Template'
        template_names = [
            path.relative_to(template_root).as_posix()
            for path in template_root.rglob('*.html')
        ]

        for template_name in template_names:
            with self.subTest(template=template_name):
                get_template(template_name)

    def test_repaired_javascript_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find('admin/js/jquery.min.js'))
        self.assertIsNotNone(finders.find('admin/js/bootstrap.bundle.min.js'))
        self.assertIsNotNone(finders.find('admin/js/Chart.min.js'))
