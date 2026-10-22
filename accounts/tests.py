from datetime import date, time, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from owners.models import Owner, ServiceAssignment, Technician, Workspace
from admin_portal.models import PlatformAdmin
from config.auth_utils import hash_password, session_auth_hash

from .models import Booking, Customer, ServiceRequest


class UserTestCase(TestCase):
    def setUp(self):
        self.owner = Owner.objects.create(
            name='Owner One',
            email='owner@example.com',
            phone_number=9876543210,
            place='Kochi',
            gender='Other',
            password=hash_password('owner-password'),
            image='id/owner.jpg',
            work_experience='5 years',
            proof_document='id/proof.jpg',
            accept=True,
        )
        self.user = Customer.objects.create(
            name='User One',
            email='user@example.com',
            phone_number=9876543211,
            place='Kochi',
            password=hash_password('user-password'),
            image='id/user.jpg',
        )
        self.workspace = Workspace.objects.create(
            name='Desk One',
            square_feet='100',
            state='Kerala',
            city='Kochi',
            location='MG Road',
            hourly_rate='250',
            image='id/desk.jpg',
            postal_code='682001',
            workspace_type='Desk',
            amenities='WiFi',
            capacity='1 person',
            owner=self.owner,
        )

    def login_as_user(self, user=None):
        user = user or self.user
        session = self.client.session
        session['role'] = 'user'
        session['id'] = user.id
        session['auth_hash'] = session_auth_hash(user)
        session['Name'] = user.name
        session.save()


class UserRoleIsolationTests(UserTestCase):
    def test_renamed_portal_pages_render_with_existing_records(self):
        booking = Booking.objects.create(
            workspace_name=self.workspace.name, hourly_rate=250,
            location=self.workspace.location, user=self.user, owner=self.owner,
            workspace=self.workspace, duration_hours=2, date='2026-11-01',
            start_time=time(10), image='id/desk.jpg',
        )
        service_request = ServiceRequest.objects.create(
            name=self.user.name, email=self.user.email,
            phone_number=self.user.phone_number, subject='Repair projector',
            user=self.user, owner=self.owner,
        )
        technician = Technician.objects.create(
            name='Tech One', email='tech@example.com', phone_number=9876543212,
            work_experience='2 years', image='id/tech.jpg', place='Kochi',
            qualification='Diploma', password=hash_password('tech-password'), owner=self.owner,
        )
        ServiceAssignment.objects.create(
            name=self.user.name, email=self.user.email,
            phone_number=self.user.phone_number, request_message=service_request.subject,
            owner=self.owner, technician=technician, request=service_request,
        )
        admin = PlatformAdmin.objects.create(email='admin@example.com', password=hash_password('admin-password'))
        portals = [
            ('user', self.user, [
                ('dashboard', []), ('workspace_list', []), ('workspace_search', []),
                ('workspace_book', [self.workspace.id]), ('owner_public_profile', [self.owner.id]),
                ('owner_workspace_catalog', [self.owner.id]), ('cart_list', []),
                ('cart_owner_list', []), ('cart_detail', [self.owner.id]),
                ('cart_remove', [booking.id]), ('booking_list', [self.user.id]),
                ('service_request_create', []), ('service_request_list', []),
                ('customer_conversation', [self.owner.id]),
            ]),
            ('owner', self.owner, [
                ('owner_dashboard', []), ('owner_workspace_list', []), ('workspace_create', []),
                ('owner_workspace_detail', [self.workspace.id]), ('workspace_edit', [self.workspace.id]),
                ('workspace_delete', [self.workspace.id]), ('owner_profile', []),
                ('owner_profile_edit', [self.owner.id]), ('owner_booking_list', [self.owner.id]),
                ('owner_service_request_list', []), ('service_assignment_create', [service_request.id]),
                ('technician_create', []), ('owner_technician_list', []),
                ('technician_login_email', [technician.id]), ('owner_chat_inbox', []),
                ('owner_conversation', [self.user.id]), ('owner_refund_list', []),
            ]),
            ('technician', technician, [
                ('technician_dashboard', []), ('technician_service_request_list', []),
            ]),
            ('admin', admin, [
                ('admin_dashboard', []), ('admin_owner_list', []), ('admin_workspace_list', []),
                ('admin_workspace_images', []), ('admin_owner_proof', [self.owner.id]),
                ('admin_workspace_image', [self.workspace.id]), ('admin_order_list', []),
                ('admin_customer_list', []), ('admin_booking_list', []),
                ('admin_support_inquiry_list', []), ('admin_support_inquiry_detail', []),
                ('admin_profile', []),
            ]),
        ]
        for role, account, routes in portals:
            session = self.client.session
            session['role'] = role
            session['id'] = account.id
            session['auth_hash'] = session_auth_hash(account)
            session['Name'] = getattr(account, 'name', 'Admin')
            session.save()
            for route_name, arguments in routes:
                with self.subTest(role=role, route=route_name):
                    response = self.client.get(reverse(route_name, args=arguments))
                    self.assertEqual(response.status_code, 200)

    def test_owner_session_cannot_open_user_dashboard(self):
        session = self.client.session
        session['role'] = 'owner'
        session['id'] = self.owner.id
        session['auth_hash'] = session_auth_hash(self.owner)
        session.save()

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('login'))

    def test_user_cannot_delete_another_users_cart_item(self):
        other_user = Customer.objects.create(
            name='User Two',
            email='other@example.com',
            phone_number=9876543212,
            place='Kochi',
            password=hash_password('other-password'),
            image='id/other.jpg',
        )
        other_cart = Booking.objects.create(
            workspace_name=self.workspace.name,
            hourly_rate=250,
            location=self.workspace.location,
            user=other_user,
            owner=self.owner,
            duration_hours=2,
            date=(date.today() + timedelta(days=7)).isoformat(), workspace=self.workspace, start_time=time(10),
        )
        self.login_as_user()

        response = self.client.get(reverse('cart_remove', args=[other_cart.id]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Booking.objects.filter(id=other_cart.id).exists())


@override_settings(DEBUG=True, ALLOW_DEMO_PAYMENTS=True)
class PaymentFlowTests(UserTestCase):
    @patch('accounts.views.razorpay_client', return_value=None)
    def test_renamed_booking_flow_from_workspace_to_confirmation(self, _client_factory):
        booking_date = (date.today() + timedelta(days=7)).isoformat()
        response = self.client.post(reverse('workspace_book', args=[self.workspace.id]), {
            'nohrs': '3', 'date': booking_date, 'start_time': '14:00',
        })
        self.assertRedirects(response, reverse('cart_owner_list'))
        booking = Booking.objects.get(workspace=self.workspace, date=booking_date, start_time=time(14))
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

    @patch('accounts.views.razorpay_client')
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

    @patch('accounts.views.razorpay_client', return_value=None)
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

    @patch('accounts.views.razorpay_client', return_value=None)
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
