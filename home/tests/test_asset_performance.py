"""Guard the measured image payload and its responsive loading contract."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse
from PIL import Image


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.images.append(dict(attrs))
        elif tag == 'link' and dict(attrs).get('rel') == 'stylesheet':
            self.stylesheets.append(dict(attrs).get('href', ''))


class ResponsiveAssetTests(SimpleTestCase):
    def test_fonts_load_once_from_html_instead_of_a_nested_css_import(self):
        for route in ['index', 'login', 'owner_register']:
            parser = Images()
            parser.feed(self.client.get(reverse(route)).content.decode())
            self.assertEqual(sum('fonts.googleapis.com' in href for href in parser.stylesheets), 1)
        css = (Path(settings.BASE_DIR) / 'static/css/rentacube-core.css').read_text(encoding='utf-8')
        self.assertNotIn('fonts.googleapis.com', css)

    def test_workspace_variants_keep_the_originals_and_reduce_each_image_payload(self):
        root = Path(settings.BASE_DIR) / 'static' / 'images'
        manifest = json.loads((root / 'optimized' / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(manifest), {'1u', '2u', '4u', '3u', '5u', '10', '12', '13', '14', '15'})
        for name, photo in manifest.items():
            original = root / photo['source']
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), photo['source_sha256'])
            for variant in photo['variants']:
                with self.subTest(photo=name, width=variant['width']):
                    path = root / 'optimized' / variant['file']
                    with Image.open(path) as image:
                        self.assertEqual(image.format, 'WEBP')
                        self.assertEqual(image.size, (variant['width'], variant['height']))
                    self.assertEqual(path.stat().st_size, variant['bytes'])
                    self.assertLess(path.stat().st_size, original.stat().st_size)
        for names in [('1u', '2u', '4u', '3u', '5u'), ('10', '12', '13', '14', '15')]:
            originals = sum(manifest[name]['source_bytes'] for name in names)
            responsive = sum(manifest[name]['variants'][1]['bytes'] for name in names)
            self.assertLess(responsive, originals * 0.25)

    def test_homepage_prioritizes_one_photo_and_defers_the_remaining_slides(self):
        response = self.client.get(reverse('index'))
        parser = Images()
        parser.feed(response.content.decode())
        slides = [image for image in parser.images if 'hero-slide' in image.get('class', '').split()]
        self.assertEqual(len(slides), 5)
        self.assertIn('/optimized/1u-', slides[0]['src'])
        self.assertEqual(slides[0]['fetchpriority'], 'high')
        self.assertIn('srcset', slides[0])
        for slide in slides[1:]:
            self.assertNotIn('src', slide)
            self.assertIn('data-src', slide)
            self.assertIn('data-srcset', slide)
            self.assertEqual(slide['aria-hidden'], 'true')


class LegacyStylesheetTests(SimpleTestCase):
    def test_delivered_stylesheet_stays_within_its_size_budget(self):
        root = Path(settings.BASE_DIR)
        original = (root / 'static/css/main.css').read_text(encoding='utf-8')
        stylesheet_bytes = (root / 'static/css/legacy-layout.css').stat().st_size
        self.assertGreater(stylesheet_bytes, 0)
        self.assertLess(stylesheet_bytes, len(original.encode()) * 0.1)
