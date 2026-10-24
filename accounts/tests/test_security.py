from datetime import time, timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Booking, Customer, Message
from accounts.tests.base import UserTestCase
from config.auth_utils import hash_password, session_auth_hash
from owners.models import Owner


@override_settings(DEBUG=True, ALLOW_DEMO_PAYMENTS=True)
class SecurityRegressionTests(UserTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_user()
        self.item = self.make_booking()

    def make_booking(self, **changes):
        values = dict(workspace_name=self.workspace.name, hourly_rate=250,
                      location=self.workspace.location, image='id/desk.jpg',
                      user=self.user, owner=self.owner, workspace=self.workspace,
                      duration_hours=2, date=(timezone.localdate() + timedelta(days=7)).isoformat(), start_time=time(10))
        values.update(changes)
        return Booking.objects.create(**values)

    def as_owner(self):
        session = self.client.session
        session.update({'role': 'owner', 'id': self.owner.pk, 'auth_hash': session_auth_hash(self.owner)})
        session.save()

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_unlinked_paid_legacy_booking_requires_operator_review(self, factory):
        self.make_booking(workspace=None, start_time=None, is_paid=True)
        self.client.post(reverse('checkout', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.razorpay_order_id, '')

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_checkout_attempts_are_limited_per_account(self, factory):
        for _ in range(10):
            self.client.post(reverse('checkout', args=[self.item.pk]))
        response = self.client.post(reverse('checkout', args=[self.item.pk]))
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '900')

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    @override_settings(DEBUG=False, ALLOW_DEMO_PAYMENTS=True)
    def test_production_never_allows_demo_checkout(self, factory):
        self.client.post(reverse('checkout', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.razorpay_order_id, '')
        self.assertFalse(self.item.is_paid)

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_checkout_get_is_safe_and_post_reuses_order(self, factory):
        self.assertContains(self.client.get(reverse('checkout', args=[self.item.pk])), 'Review your booking')
        self.item.refresh_from_db()
        self.assertEqual(self.item.razorpay_order_id, '')
        self.client.post(reverse('checkout', args=[self.item.pk]))
        self.item.refresh_from_db()
        order, expiry = self.item.razorpay_order_id, self.item.checkout_expires_at
        self.client.post(reverse('checkout', args=[self.item.pk]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.razorpay_order_id, order)
        self.assertEqual(self.item.checkout_expires_at, expiry)

    def test_paid_bookings_cannot_be_deleted_as_cart_items(self):
        self.item.is_paid = True
        self.item.save()
        self.assertEqual(self.client.post(reverse('cart_remove', args=[self.item.pk])).status_code, 404)
        self.assertTrue(Booking.objects.filter(pk=self.item.pk).exists())

    def test_unpaid_carts_do_not_block_other_customers(self):
        other = Customer.objects.create(name='Other', email='other@example.com', phone_number=1234567890,
                                        place='Kochi', password=hash_password('other-pass'), image='id/other.jpg')
        self.login_as_user(other)
        self.client.post(reverse('workspace_book', args=[self.workspace.pk]), {
            'date': self.item.date, 'start_time': '10:00', 'nohrs': '2', 'price': '1', 'uid': str(self.user.pk),
        })
        created = Booking.objects.get(user=other)
        self.assertEqual(created.hourly_rate, 250)
        self.assertEqual(created.owner, self.owner)

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_checkout_hold_blocks_overlaps_but_allows_adjacent_time(self, factory):
        self.client.post(reverse('checkout', args=[self.item.pk]))
        overlap = self.make_booking(start_time=time(11))
        adjacent = self.make_booking(start_time=time(12))
        self.client.post(reverse('checkout', args=[overlap.pk]))
        overlap.refresh_from_db()
        self.assertEqual(overlap.razorpay_order_id, '')
        self.client.post(reverse('checkout', args=[adjacent.pk]))
        adjacent.refresh_from_db()
        self.assertTrue(adjacent.razorpay_order_id)

    @patch('accounts.views.bookings.razorpay_client')
    def test_signature_without_matching_captured_funds_is_rejected(self, factory):
        client = factory.return_value
        client.order.create.return_value = {'id': 'order_1'}
        self.client.post(reverse('checkout', args=[self.item.pk]))
        correct = dict(order_id='order_1', amount=50000, currency='INR', status='captured')
        for changes in [dict(status='authorized'), dict(amount=100), dict(currency='USD'), dict(order_id='other')]:
            client.payment.fetch.return_value = correct | changes
            self.client.post(reverse('payment_complete', args=[self.item.pk]), {
                'razorpay_order_id': 'order_1', 'razorpay_payment_id': 'pay_1', 'razorpay_signature': 'signature',
            })
            self.item.refresh_from_db()
            self.assertFalse(self.item.is_paid)

    @patch('accounts.views.bookings.razorpay_client')
    def test_late_captured_payment_is_retained_for_refund(self, factory):
        client = factory.return_value
        client.order.create.return_value = {'id': 'order_1'}
        self.client.post(reverse('checkout', args=[self.item.pk]))
        Booking.objects.filter(pk=self.item.pk).update(checkout_expires_at=timezone.now() - timedelta(minutes=1))
        self.make_booking(is_paid=True, total_amount=500)
        client.payment.fetch.return_value = dict(order_id='order_1', amount=50000, currency='INR', status='captured')
        self.client.post(reverse('payment_complete', args=[self.item.pk]), {
            'razorpay_order_id': 'order_1', 'razorpay_payment_id': 'pay_1', 'razorpay_signature': 'signature',
        })
        self.item.refresh_from_db()
        self.assertTrue(self.item.is_paid)
        self.assertTrue(self.item.payment_review_required)
        self.assertEqual(self.item.razorpay_payment_id, 'pay_1')
        self.assertContains(self.client.get(reverse('booking_list', args=[self.user.pk])), 'contact owner for refund')

    def test_session_revoked_after_password_change(self):
        self.user.password = hash_password('changed-password')
        self.user.save()
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('login'))
        self.assertNotIn('role', self.client.session)

    def test_owner_revocation_ends_existing_session(self):
        self.as_owner()
        Owner.objects.filter(pk=self.owner.pk).update(accept=False, reject=True)
        self.assertRedirects(self.client.get(reverse('owner_dashboard')), reverse('owner_login'))

    def test_chat_id_collisions_and_legacy_messages_do_not_leak(self):
        # Reverse customer/owner identifiers overlap in independent tables.
        other_user = Customer.objects.create(name='Other', email='other@example.com', phone_number=1234567890,
                                             place='Kochi', password='unused', image='id/other.jpg')
        other_owner = Owner.objects.create(name='Other', email='other-owner@example.com', phone_number=1234567890,
                                           place='Kochi', password='unused', image='id/other.jpg', accept=True)
        Message.objects.create(customer=other_user, owner=self.owner, sender_role='user', body='PRIVATE OTHER THREAD',
                               date=timezone.localdate(), time=time(12), sender_id=str(other_user.pk), receiver_id=str(self.owner.pk))
        Message.objects.create(body='UNTRUSTED LEGACY THREAD', date=timezone.localdate(), time=time(12),
                               sender_id=str(other_owner.pk), receiver_id=str(self.user.pk))
        response = self.client.get(reverse('customer_conversation', args=[other_owner.pk]))
        self.assertNotContains(response, 'PRIVATE OTHER THREAD')
        self.assertNotContains(response, 'UNTRUSTED LEGACY THREAD')
        self.client.post(reverse('customer_conversation', args=[other_owner.pk]), {'message': '<script>alert(1)</script>'})
        response = self.client.get(reverse('customer_conversation', args=[other_owner.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_database_rejects_invalid_booking_and_duplicate_payment(self):
        for invalid in [dict(hourly_rate=-1), dict(duration_hours=0), dict(duration_hours=73), dict(is_refunded=True)]:
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.make_booking(**invalid)
        self.make_booking(razorpay_payment_id='same-payment')
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_booking(razorpay_payment_id='same-payment')

    @patch('owners.views.bookings.razorpay_client')
    def test_uncertain_refund_cannot_be_automatically_retried(self, factory):
        self.item.is_paid, self.item.total_amount = True, 500
        self.item.razorpay_payment_id = 'pay_real'
        self.item.save()
        self.as_owner()
        factory.return_value.payment.refund.side_effect = TimeoutError()
        for _ in range(2):
            self.client.post(reverse('refund_process', args=[self.item.pk]))
        self.assertEqual(factory.return_value.payment.refund.call_count, 1)
        self.item.refresh_from_db()
        self.assertEqual(self.item.refund_state, 'review')
        self.assertFalse(self.item.is_refunded)

    def test_csrf_enforced_on_payment_and_logout(self):
        client = Client(enforce_csrf_checks=True)
        for path in [reverse('payment_complete', args=[self.item.pk]), reverse('logout')]:
            self.assertEqual(client.post(path).status_code, 403)

    def test_login_rate_limit_uses_shared_database_counter(self):
        for _ in range(10):
            response = self.client.post(reverse('login'), {'email': 'absent@example.com', 'password': 'wrong'})
            self.assertEqual(response.status_code, 200)
        other_client = Client()
        response = other_client.post(reverse('login'), {'email': 'absent@example.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '900')
