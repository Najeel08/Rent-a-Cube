from datetime import time
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from owners.models import owner_tb, owvaddwork
from config.auth_utils import hash_password

from .models import cart, user_tb


class UserTestCase(TestCase):
    def setUp(self):
        self.owner = owner_tb.objects.create(
            Name='Owner One',
            Email='owner@example.com',
            Phonenumber=9876543210,
            Place='Kochi',
            Gender='Other',
            Password=hash_password('owner-password'),
            Image='id/owner.jpg',
            Workex='5 years',
            Proof='id/proof.jpg',
            accept=True,
        )
        self.user = user_tb.objects.create(
            Name='User One',
            Email='user@example.com',
            Phonenumber=9876543211,
            Place='Kochi',
            Password=hash_password('user-password'),
            Image='id/user.jpg',
        )
        self.workspace = owvaddwork.objects.create(
            Name='Desk One',
            Sqft='100',
            State='Kerala',
            City='Kochi',
            Location='MG Road',
            Price='250',
            Image='id/desk.jpg',
            Pincode='682001',
            Type='Desk',
            Facility='WiFi',
            Capability='1 person',
            owner=self.owner,
        )

    def login_as_user(self, user=None):
        user = user or self.user
        session = self.client.session
        session['role'] = 'user'
        session['id'] = user.id
        session['Name'] = user.Name
        session.save()


class UserRoleIsolationTests(UserTestCase):
    def test_owner_session_cannot_open_user_dashboard(self):
        session = self.client.session
        session['role'] = 'owner'
        session['id'] = self.owner.id
        session.save()

        response = self.client.get(reverse('uhome'))

        self.assertRedirects(response, reverse('ulog'))

    def test_user_cannot_delete_another_users_cart_item(self):
        other_user = user_tb.objects.create(
            Name='User Two',
            Email='other@example.com',
            Phonenumber=9876543212,
            Place='Kochi',
            Password=hash_password('other-password'),
            Image='id/other.jpg',
        )
        other_cart = cart.objects.create(
            WsName=self.workspace.Name,
            Price=250,
            Location=self.workspace.Location,
            user=other_user,
            owner=self.owner,
            nohrs=2,
            Date='2026-10-02',
        )
        self.login_as_user()

        response = self.client.get(reverse('cartdel', args=[other_cart.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(cart.objects.filter(id=other_cart.id).exists())


class PaymentFlowTests(UserTestCase):
    def setUp(self):
        super().setUp()
        self.booking = cart.objects.create(
            WsName=self.workspace.Name,
            Price=250,
            Location=self.workspace.Location,
            user=self.user,
            owner=self.owner,
            nohrs=2,
            Date='2026-10-02',
        )
        self.login_as_user()

    @patch('accounts.views._razorpay_client')
    def test_verified_payment_marks_only_the_logged_in_users_booking_paid(self, client_factory):
        class FakeOrder:
            @staticmethod
            def create(_payload):
                return {'id': 'order_test_123'}

        class FakeUtility:
            @staticmethod
            def verify_payment_signature(_payment_data):
                return None

        class FakeClient:
            order = FakeOrder()
            utility = FakeUtility()

        client_factory.return_value = FakeClient()

        checkout_response = self.client.get(reverse('checkout', args=[self.booking.id]))
        self.assertEqual(checkout_response.status_code, 200)

        response = self.client.post(
            reverse('payment_success', args=[self.booking.id]),
            {
                'razorpay_order_id': 'order_test_123',
                'razorpay_payment_id': 'payment_test_123',
                'razorpay_signature': 'signature_test_123',
            },
        )

        self.assertRedirects(response, reverse('uvieworder', args=[self.user.id]))
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.Paystatus)
        self.assertEqual(self.booking.totalsum, 500)

        replay_response = self.client.post(
            reverse('payment_success', args=[self.booking.id]),
            {
                'razorpay_order_id': 'order_test_123',
                'razorpay_payment_id': 'payment_test_123',
                'razorpay_signature': 'signature_test_123',
            },
        )

        self.assertRedirects(replay_response, reverse('uvieworder', args=[self.user.id]))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.RazorpayPaymentId, 'payment_test_123')

    @patch('accounts.views._razorpay_client', return_value=None)
    def test_demo_payment_marks_booking_paid_and_removes_it_from_cart(self, _client_factory):
        checkout_response = self.client.get(reverse('checkout', args=[self.booking.id]))

        self.assertContains(checkout_response, 'Payment Gateway')
        pending_payment = self.client.session[f'booking_payment_{self.booking.id}']

        response = self.client.post(
            reverse('payment_success', args=[self.booking.id]),
            {
                'demo_payment': '1',
                'razorpay_order_id': pending_payment['order_id'],
            },
        )

        self.assertRedirects(response, reverse('uvieworder', args=[self.user.id]))
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.Paystatus)
        self.assertEqual(self.booking.totalsum, 500)
        self.assertTrue(self.booking.RazorpayPaymentId.startswith('demo_pay_'))
        self.assertFalse(cart.objects.filter(id=self.booking.id, Paystatus=False).exists())

    @patch('accounts.views._razorpay_client', return_value=None)
    def test_demo_payment_keeps_cart_item_when_slot_is_already_booked(self, _client_factory):
        self.booking.workspace = self.workspace
        self.booking.StartTime = time(10, 0)
        self.booking.Date = '2026-10-10'
        self.booking.Image = 'cart/desk.jpg'
        self.booking.save(update_fields=['workspace', 'StartTime', 'Date', 'Image'])
        other_user = user_tb.objects.create(
            Name='User Two',
            Email='other@example.com',
            Phonenumber=9876543212,
            Place='Kochi',
            Password=hash_password('user-password'),
            Image='id/other-user.jpg',
        )
        cart.objects.create(
            WsName=self.workspace.Name,
            Price=250,
            Location=self.workspace.Location,
            user=other_user,
            owner=self.owner,
            workspace=self.workspace,
            nohrs=2,
            Date='2026-10-10',
            StartTime=time(10, 0),
            Paystatus=True,
            totalsum=500,
        )
        self.client.get(reverse('checkout', args=[self.booking.id]))
        pending_payment = self.client.session[f'booking_payment_{self.booking.id}']

        response = self.client.post(
            reverse('payment_success', args=[self.booking.id]),
            {
                'demo_payment': '1',
                'razorpay_order_id': pending_payment['order_id'],
            },
        )

        self.assertRedirects(response, reverse('cartdetails', args=[self.owner.id]))
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.Paystatus)
