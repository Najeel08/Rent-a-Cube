"""Payments tests and fixtures."""
from datetime import date, time, timedelta
from unittest.mock import patch
from django.test import override_settings
from django.urls import reverse
from config.auth_utils import hash_password, session_auth_hash
from accounts.models import Booking, Customer, Refund
from accounts.tests.base import UserTestCase


@override_settings(DEBUG=True, ALLOW_DEMO_PAYMENTS=True)
class PaymentFlowTests(UserTestCase):
    @patch('accounts.views.bookings.razorpay_client')
    def test_order_creation_failure_does_not_save_an_order_or_hold(self, client_factory):
        client_factory.return_value.order.create.side_effect = RuntimeError('Provider unavailable')
        self.assertRedirects(
            self.client.post(reverse('checkout', args=[self.booking.pk])),
            reverse('cart_detail', args=[self.owner.pk]),
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.razorpay_order_id, '')
        self.assertEqual(self.booking.payment_mode, '')
        self.assertEqual(self.booking.total_amount, 0)
        self.assertIsNone(self.booking.checkout_expires_at)
        self.assertFalse(self.booking.is_paid)

    @patch('owners.views.bookings.razorpay_client')
    def test_demo_refund_is_recorded_once_without_a_provider_refund(self, client_factory):
        self.booking.is_paid = True
        self.booking.payment_mode = 'demo'
        self.booking.total_amount = 500
        self.booking.save()
        session = self.client.session
        session.update({'role': 'owner', 'id': self.owner.pk, 'auth_hash': session_auth_hash(self.owner)})
        session.save()
        for _ in range(2):
            self.assertRedirects(
                self.client.post(reverse('refund_process', args=[self.booking.pk])),
                reverse('owner_refund_list'),
            )
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.is_refunded)
        self.assertEqual(self.booking.refund_state, 'processed')
        self.assertEqual(self.booking.razorpay_refund_id, f'demo_refund_{self.booking.pk}')
        self.assertEqual(Refund.objects.filter(booking=self.booking).count(), 1)
        refund = Refund.objects.get(booking=self.booking)
        self.assertTrue(refund.is_processed)
        self.assertEqual(refund.amount, 500)
        client_factory.return_value.payment.refund.assert_not_called()

    @patch('owners.views.bookings.razorpay_client')
    def test_live_refund_preserves_provider_amount_and_pending_or_processed_status(self, client_factory):
        session = self.client.session
        session.update({'role': 'owner', 'id': self.owner.pk, 'auth_hash': session_auth_hash(self.owner)})
        session.save()
        for status in ['pending', 'processed']:
            with self.subTest(status=status):
                booking = Booking.objects.create(
                    workspace_name='Desk', location='Kochi', date=self.booking.date,
                    hourly_rate=250, duration_hours=2, user=self.user, owner=self.owner,
                    is_paid=True, total_amount=500, payment_mode='razorpay',
                    razorpay_payment_id=f'pay_{status}',
                )
                client_factory.return_value.payment.refund.return_value = {'id': f'refund_{status}', 'status': status}
                self.assertRedirects(
                    self.client.post(reverse('refund_process', args=[booking.pk])),
                    reverse('owner_refund_list'),
                )
                client_factory.return_value.payment.refund.assert_called_with(
                    f'pay_{status}', {'amount': 50000, 'speed': 'normal', 'notes': {'booking_id': str(booking.pk)}},
                )
                booking.refresh_from_db()
                self.assertEqual(booking.refund_state, status)
                self.assertEqual(booking.is_refunded, status == 'processed')
                self.assertEqual(booking.razorpay_refund_id, f'refund_{status}')
                refund = Refund.objects.get(booking=booking)
                self.assertEqual(refund.is_processed, status == 'processed')
                self.assertEqual(refund.amount, 500)

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_renamed_booking_flow_from_workspace_to_confirmation(self, _client_factory):
        booking_date = (date.today() + timedelta(days=7)).isoformat()
        response = self.client.post(reverse('workspace_book', args=[self.workspace.id]), {
            'nohrs': '3', 'date': booking_date, 'start_time': '14:00',
            'price': '1', 'total_amount': '1',
        })
        self.assertRedirects(response, reverse('cart_owner_list'))
        booking = Booking.objects.get(workspace=self.workspace, date=booking_date, start_time=time(14))
        self.assertEqual(booking.hourly_rate, 250)
        self.assertEqual(booking.total_amount, 750)
        self.assertContains(self.client.get(reverse('cart_detail', args=[self.owner.id])), self.workspace.name)
        self.assertContains(self.client.post(reverse('checkout', args=[booking.id])), 'Payment Gateway')
        booking.refresh_from_db()
        pending = {'order_id': booking.razorpay_order_id}
        response = self.client.post(reverse('payment_complete', args=[booking.id]), {
            'demo_payment': '1', 'razorpay_order_id': pending['order_id'],
        }, follow=True)
        booking.refresh_from_db()
        self.assertTrue(booking.is_paid)
        self.assertEqual(booking.total_amount, 750)
        self.assertContains(response, booking.razorpay_payment_id)
        cart_response = self.client.get(reverse('cart_detail', args=[self.owner.id]))
        self.assertNotIn(booking, cart_response.context['book_obj'])

    def setUp(self):
        super().setUp()
        self.booking = Booking.objects.create(
            workspace_name=self.workspace.name,
            hourly_rate=250,
            location=self.workspace.location,
            image='id/desk.jpg',
            user=self.user,
            owner=self.owner,
            duration_hours=2,
            date=(date.today() + timedelta(days=7)).isoformat(), workspace=self.workspace, start_time=time(10),
        )
        self.login_as_user()

    @patch('accounts.views.bookings.razorpay_client')
    def test_verified_payment_marks_only_the_logged_in_users_booking_paid(self, client_factory):
        class FakeOrder:
            @staticmethod
            def create(_payload):
                return {'id': 'order_test_123'}

        class FakeUtility:
            @staticmethod
            def verify_payment_signature(_payment_data):
                return None

        class FakePayment:
            @staticmethod
            def fetch(payment_id):
                return {'id': payment_id, 'order_id': 'order_test_123', 'amount': 50000, 'currency': 'INR', 'status': 'captured'}

        class FakeClient:
            payment = FakePayment()
            order = FakeOrder()
            utility = FakeUtility()

        client_factory.return_value = FakeClient()

        checkout_response = self.client.post(reverse('checkout', args=[self.booking.id]))
        self.assertEqual(checkout_response.status_code, 200)

        response = self.client.post(
            reverse('payment_complete', args=[self.booking.id]),
            {
                'razorpay_order_id': 'order_test_123',
                'razorpay_payment_id': 'payment_test_123',
                'razorpay_signature': 'signature_test_123',
            },
        )

        self.assertRedirects(response, reverse('booking_list', args=[self.user.id]))
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.is_paid)
        self.assertEqual(self.booking.total_amount, 500)

        replay_response = self.client.post(
            reverse('payment_complete', args=[self.booking.id]),
            {
                'razorpay_order_id': 'order_test_123',
                'razorpay_payment_id': 'payment_test_123',
                'razorpay_signature': 'signature_test_123',
            },
        )

        self.assertRedirects(replay_response, reverse('booking_list', args=[self.user.id]))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.razorpay_payment_id, 'payment_test_123')

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_demo_payment_marks_booking_paid_and_removes_it_from_cart(self, _client_factory):
        checkout_response = self.client.post(reverse('checkout', args=[self.booking.id]))

        self.assertContains(checkout_response, 'Payment Gateway')
        self.booking.refresh_from_db()
        pending_payment = {'order_id': self.booking.razorpay_order_id}

        response = self.client.post(
            reverse('payment_complete', args=[self.booking.id]),
            {
                'demo_payment': '1',
                'razorpay_order_id': pending_payment['order_id'],
            },
        )

        self.assertRedirects(response, reverse('booking_list', args=[self.user.id]))
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.is_paid)
        self.assertEqual(self.booking.total_amount, 500)
        self.assertTrue(self.booking.razorpay_payment_id.startswith('demo_pay_'))
        self.assertFalse(Booking.objects.filter(id=self.booking.id, is_paid=False).exists())

    @patch('accounts.views.bookings.razorpay_client', return_value=None)
    def test_demo_payment_keeps_cart_item_when_slot_is_already_booked(self, _client_factory):
        self.booking.workspace = self.workspace
        self.booking.start_time = time(10, 0)
        self.booking.date = (date.today() + timedelta(days=7)).isoformat()
        self.booking.image = 'cart/desk.jpg'
        self.booking.save(update_fields=['workspace', 'start_time', 'date', 'image'])
        other_user = Customer.objects.create(
            name='User Two',
            email='other@example.com',
            phone_number=9876543212,
            place='Kochi',
            password=hash_password('user-password'),
            image='id/other-user.jpg',
        )
        Booking.objects.create(
            workspace_name=self.workspace.name,
            hourly_rate=250,
            location=self.workspace.location,
            user=other_user,
            owner=self.owner,
            workspace=self.workspace,
            duration_hours=2,
            date=self.booking.date,
            start_time=time(10, 0),
            is_paid=True,
            total_amount=500,
        )
        response = self.client.post(reverse('checkout', args=[self.booking.id]))
        self.assertRedirects(response, reverse('cart_detail', args=[self.owner.id]))
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.is_paid)
        self.assertEqual(self.booking.razorpay_order_id, '')
