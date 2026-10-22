from datetime import time, timedelta
from io import BytesIO, StringIO
from unittest.mock import patch

from PIL import Image
from django.core import mail, signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Customer, ServiceRequest, Booking
from accounts.tests import UserTestCase
from config.auth_utils import password_matches, session_auth_hash, upgrade_password_if_needed
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from config.validation import validate_image_upload
from django.core.exceptions import ValidationError
from home.models import SupportInquiry
from owners.models import ServiceAssignment, Technician
from admin_portal.models import PlatformAdmin


class WorkflowRegressionTests(UserTestCase):
    def test_owner_password_change_requires_current_password(self):
        self.set_role('owner', self.owner)
        old = self.owner.password
        self.client.post(reverse('owner_profile_edit', args=[self.owner.pk]), {
            'name': self.owner.name, 'email': self.owner.email, 'phonenumber': '9876543210',
            'workex': '5 years', 'place': 'Kochi', 'password': 'A-new-owner-password!29',
            'cpassword': 'A-new-owner-password!29', 'current_password': 'incorrect',
        })
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.password, old)

    def test_cart_with_missing_optional_photo_renders(self):
        self.login_as_user()
        Booking.objects.create(workspace_name='Desk', hourly_rate=250, location='Kochi', user=self.user,
            owner=self.owner, workspace=self.workspace, duration_hours=2,
            date=(timezone.localdate() + timedelta(days=7)).isoformat(), start_time=time(10))
        for url in [reverse('cart_list'), reverse('cart_detail', args=[self.owner.pk])]:
            self.assertContains(self.client.get(url), 'photo-unavailable.svg')

    def test_supported_old_password_hash_is_upgraded_on_login(self):
        password = 'A-long-local-test-password!'
        self.user.password = PBKDF2PasswordHasher().encode(password, 'testsalt', iterations=1000)
        self.user.save()
        old = self.user.password
        upgrade_password_if_needed(self.user, 'password', password)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, old)
        self.assertTrue(password_matches(password, self.user.password))

    def test_refunded_slot_can_be_booked_again(self):
        self.login_as_user()
        day = (timezone.localdate() + timedelta(days=7)).isoformat()
        Booking.objects.create(workspace_name='Desk', hourly_rate=250, location='Kochi', user=self.user,
            owner=self.owner, workspace=self.workspace, duration_hours=2, total_amount=500,
            date=day, start_time=time(10), is_paid=True, is_refunded=True)
        self.client.post(reverse('workspace_book', args=[self.workspace.pk]),
                         {'date': day, 'start_time': '10:00', 'nohrs': '2'})
        self.assertEqual(Booking.objects.filter(user=self.user, date=day).count(), 2)

    def set_role(self, role, obj):
        session = self.client.session
        session.update({'role': role, 'id': obj.pk, 'auth_hash': session_auth_hash(obj)})
        session.save()

    def test_weak_password_registration_is_rejected(self):
        buf = BytesIO()
        Image.new('RGB', (2, 2)).save(buf, format='PNG')
        response = self.client.post(reverse('register'), dict(name='New', email='new@example.test',
            phone='0987654321', place='Kochi', password='12345678', cpassword='12345678',
            image=SimpleUploadedFile('profile.png', buf.getvalue(), content_type='image/png')))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.filter(email='new@example.test').exists())

    def test_invalid_and_oversized_images_are_rejected(self):
        for file in [SimpleUploadedFile('x.png', b'not an image'), SimpleUploadedFile('x.svg', b'<svg/>'),
                     SimpleUploadedFile('x.jpg', b'x' * (5 * 1024 * 1024 + 1))]:
            with self.assertRaises(ValidationError):
                validate_image_upload(file, 'Image')

    def test_case_insensitive_email_uniqueness_enforced(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Customer.objects.create(name='Duplicate', email=self.user.email.upper(), phone_number='0123456789',
                                    place='Kochi', password='unused')

    def test_phone_number_preserves_leading_zero(self):
        self.user.phone_number = '0123456789'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '0123456789')

    def test_assignment_is_idempotent_and_cross_owner_technician_rejected(self):
        self.set_role('owner', self.owner)
        req = ServiceRequest.objects.create(name=self.user.name, email=self.user.email,
            phone_number=self.user.phone_number, subject='Projector help', user=self.user, owner=self.owner)
        tech = Technician.objects.create(name='Tech', email='tech@example.test', phone_number='0123456789', owner=self.owner)
        for _ in range(2):
            self.client.post(reverse('service_assignment_create', args=[req.pk]), {'tech': tech.pk})
        self.assertEqual(ServiceAssignment.objects.filter(request=req).count(), 1)
        response = self.client.post(reverse('service_assignment_create', args=[req.pk]), {'tech': 999999})
        self.assertEqual(response.status_code, 404)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_technician_setup_link_is_single_use_and_does_not_email_password(self):
        tech = Technician.objects.create(name='Tech', email='tech@example.test', phone_number='0123456789', owner=self.owner)
        self.set_role('owner', self.owner)
        self.client.post(reverse('technician_login_email', args=[tech.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/technicians/activate/', mail.outbox[0].body)
        self.assertNotIn('You can login with this password', mail.outbox[0].body)
        token = signing.dumps({'id': tech.pk, 'auth': session_auth_hash(tech)}, salt='technician-setup')
        url = reverse('technician_activate', args=[token])
        response = self.client.post(url, {'password': 'Unique-Tech-Password!27', 'cpassword': 'Unique-Tech-Password!27'})
        self.assertRedirects(response, reverse('technician_login'))
        tech.refresh_from_db()
        self.assertTrue(password_matches('Unique-Tech-Password!27', tech.password))
        self.assertEqual(self.client.get(url).status_code, 400)
        self.assertEqual(self.client.get(reverse('technician_activate', args=['tampered-token'])).status_code, 400)

    def test_support_portal_displays_real_inquiries_and_resolves_them(self):
        admin = PlatformAdmin.objects.create(email='admin@example.test', password='hash-not-used')
        self.set_role('admin', admin)
        inquiry = SupportInquiry.objects.create(name='Help', email='help@example.test', message='My real support question')
        self.assertContains(self.client.get(reverse('admin_support_inquiry_list')), inquiry.message)
        self.client.post(reverse('admin_support_inquiry_list'), {'inquiry_id': inquiry.pk})
        inquiry.refresh_from_db()
        self.assertTrue(inquiry.resolved)

    def test_invalid_legacy_admin_identifier_is_404(self):
        admin = PlatformAdmin.objects.create(email='admin@example.test', password='hash-not-used')
        self.set_role('admin', admin)
        self.assertEqual(self.client.get(reverse('admin_owner_proof', args=['not-a-number'])).status_code, 404)

    @patch('accounts.management.commands.reconcile_payments.razorpay_client')
    def test_payment_recovery_after_browser_callback_is_lost(self, factory):
        booking = Booking.objects.create(workspace_name='Desk', hourly_rate=250, location='Kochi', user=self.user,
            owner=self.owner, workspace=self.workspace, duration_hours=2, total_amount=500,
            date=(timezone.localdate() + timedelta(days=7)).isoformat(), start_time=time(10),
            razorpay_order_id='order_recover', payment_mode='razorpay')
        factory.return_value.order.payments.return_value = {'items': [dict(id='pay_recover',
            order_id='order_recover', amount=50000, currency='INR', status='captured')]}
        call_command('reconcile_payments', booking.pk, stdout=StringIO())
        booking.refresh_from_db()
        self.assertTrue(booking.is_paid)
        self.assertEqual(booking.razorpay_payment_id, 'pay_recover')
        factory.return_value.payment.refund.assert_not_called()

    def test_workspace_links_target_selected_workspace(self):
        self.login_as_user()
        response = self.client.get(reverse('workspace_list'))
        self.assertContains(response, reverse('workspace_book', args=[self.workspace.pk]))
        self.assertNotContains(response, reverse('workspace_overview'))
