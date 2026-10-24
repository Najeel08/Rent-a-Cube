"""Profile validation, failed edits, and session continuity."""
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.urls import reverse

from accounts.tests.base import UserTestCase
from config.auth_utils import password_matches, session_auth_hash


class OwnerProfileTests(UserTestCase):
    def setUp(self):
        super().setUp()
        session = self.client.session
        session.update({'role': 'owner', 'id': self.owner.pk, 'auth_hash': session_auth_hash(self.owner)})
        session.save()
        self.url = reverse('owner_profile_edit', args=[self.owner.pk])
        self.fields = dict(
            name='Updated Owner', email=self.owner.email, phonenumber='0123456789',
            workex='6 years', place='New Place',
        )

    def test_ordinary_edits_keep_password_and_photo_and_refresh_the_session(self):
        previous_key = self.client.session.session_key
        previous_password, previous_image = self.owner.password, self.owner.image.name
        self.assertRedirects(self.client.post(self.url, self.fields), reverse('owner_profile'))
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.name, 'Updated Owner')
        self.assertEqual(self.owner.phone_number, '0123456789')
        self.assertEqual(self.owner.work_experience, '6 years')
        self.assertEqual(self.owner.password, previous_password)
        self.assertEqual(self.owner.image.name, previous_image)
        self.assertNotEqual(self.client.session.session_key, previous_key)
        self.assertEqual(self.client.session['Name'], 'Updated Owner')
        self.assertEqual(self.client.session['auth_hash'], session_auth_hash(self.owner))

    def test_email_changes_require_the_current_password(self):
        fields = self.fields | {'email': 'NEW@example.test'}
        for current_password in ['', 'incorrect']:
            response = self.client.post(self.url, fields | {'current_password': current_password})
            self.assertContains(response, 'Enter your current password to change your email or password.')
            self.owner.refresh_from_db()
            self.assertEqual(self.owner.email, 'owner@example.com')
            self.assertEqual(response.context['pl'].name, self.owner.name)
        self.assertRedirects(
            self.client.post(self.url, fields | {'current_password': 'owner-password'}),
            reverse('owner_profile'),
        )
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, 'new@example.test')

    def test_password_change_keeps_the_current_session_authenticated(self):
        password = 'A-new-owner-password!29'
        self.assertRedirects(self.client.post(self.url, self.fields | {
            'password': password, 'cpassword': password, 'current_password': 'owner-password',
        }), reverse('owner_profile'))
        self.owner.refresh_from_db()
        self.assertTrue(password_matches(password, self.owner.password))
        self.assertFalse(password_matches('owner-password', self.owner.password))
        self.assertEqual(self.client.session['auth_hash'], session_auth_hash(self.owner))
        self.assertEqual(self.client.get(reverse('owner_dashboard')).status_code, 200)

    def test_failed_password_validation_keeps_database_values_and_rendered_edits(self):
        previous_key = self.client.session.session_key
        previous_password = self.owner.password
        for password, confirmation in [('A-new-owner-password!29', 'different'), ('tiny', 'tiny')]:
            with self.subTest(password=password):
                response = self.client.post(self.url, self.fields | {
                    'password': password, 'cpassword': confirmation, 'current_password': 'owner-password',
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['pl'].name, 'Updated Owner')
                self.owner.refresh_from_db()
                self.assertEqual(self.owner.name, 'Owner One')
                self.assertEqual(self.owner.password, previous_password)
                self.assertEqual(self.client.session.session_key, previous_key)

    def test_invalid_upload_and_failed_save_do_not_persist_edits(self):
        image = SimpleUploadedFile('invalid.png', b'not an image', content_type='image/png')
        response = self.client.post(self.url, self.fields | {'image': image})
        self.assertContains(response, 'Profile image is not a valid image file.')
        self.assertEqual(response.context['pl'].name, 'Owner One')
        previous_key = self.client.session.session_key
        with patch('owners.models.Owner.save', side_effect=IntegrityError):
            response = self.client.post(self.url, self.fields)
        self.assertContains(response, 'This email address is already registered.')
        self.assertEqual(response.context['pl'].name, 'Updated Owner')
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.name, 'Owner One')
        self.assertEqual(self.client.session.session_key, previous_key)
