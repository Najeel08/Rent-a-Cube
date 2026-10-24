"""Portals tests and fixtures."""
from datetime import date, time, timedelta
from django.urls import reverse
from owners.models import ServiceAssignment, Technician
from admin_portal.models import PlatformAdmin
from config.auth_utils import hash_password, session_auth_hash
from accounts.models import Booking, Customer, ServiceRequest
from accounts.tests.base import UserTestCase


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
