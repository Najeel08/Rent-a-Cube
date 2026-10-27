"""Templates tests and fixtures."""
from pathlib import Path
from importlib import import_module
from inspect import signature
import re
from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import RequestFactory, TestCase
from django.template.loader import get_template
from django.urls import reverse

from config.validation import ALLOWED_IMAGE_EXTENSIONS


class TemplateAndAssetSmokeTests(TestCase):
    def test_search_logout_matches_the_existing_post_and_csrf_contract(self):
        request = RequestFactory().get(reverse('workspace_search'))
        request.session = {'id': 1, 'Name': 'Review Customer'}
        html = get_template('accounts/workspace_search_results.html').render(request=request)
        logout = re.search(r'<form\b([^>]*)action="/logout/"([^>]*)>(.*?)</form>', html, re.S)
        self.assertIsNotNone(logout)
        self.assertIn('method="post"', logout.group(1) + logout.group(2))
        self.assertIn('name="csrfmiddlewaretoken"', logout.group(3))

    def test_owner_proof_picker_matches_the_server_supported_formats(self):
        response = self.client.get(reverse('owner_register'))
        proof = re.search(r'<input\b[^>]*name="proof"[^>]*>', response.content.decode())
        self.assertIsNotNone(proof)
        accept = re.search(r'accept="([^"]+)"', proof.group())
        self.assertEqual(set(accept.group(1).split(',')), ALLOWED_IMAGE_EXTENSIONS)

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
