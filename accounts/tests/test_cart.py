"""Cart display totals and account boundaries."""
from django.urls import reverse

from accounts.models import Booking, Customer
from accounts.tests.base import UserTestCase
from owners.models import Owner


class CartTotalTests(UserTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_user()

    def test_empty_carts_have_zero_totals(self):
        for route, args in [('cart_list', []), ('cart_detail', [self.owner.pk])]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['sum'], 0)
                self.assertEqual(list(response.context['book_obj']), [])

    def test_totals_include_only_the_customers_unpaid_items_and_selected_owner(self):
        other_owner = Owner.objects.create(
            name='Other Owner', email='other-owner@example.test',
            password=self.owner.password, accept=True,
        )
        other_customer = Customer.objects.create(
            name='Other Customer', email='other-customer@example.test',
            password=self.user.password,
        )
        bookings = []
        for owner, customer, rate, hours, paid in [
            (self.owner, self.user, 250, 2, False),
            (self.owner, self.user, 125, 3, False),
            (other_owner, self.user, 300, 1, False),
            (self.owner, other_customer, 900, 1, False),
            (self.owner, self.user, 800, 1, True),
        ]:
            bookings.append(Booking.objects.create(
                workspace_name='Desk', location='Kochi', date='2026-11-01',
                owner=owner, user=customer, hourly_rate=rate,
                duration_hours=hours, is_paid=paid,
            ))

        for route, args, expected, total in [
            ('cart_list', [], bookings[:3], 1175),
            ('cart_detail', [self.owner.pk], bookings[:2], 875),
        ]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route, args=args))
                items = list(response.context['book_obj'])
                self.assertEqual(items, expected)
                self.assertEqual(response.context['sum'], total)
                self.assertEqual([item.line_total for item in items], [500, 375, 300][:len(items)])
                self.assertContains(response, str(total))

        for booking in bookings:
            booking.refresh_from_db()
            self.assertEqual(booking.total_amount, 0)
