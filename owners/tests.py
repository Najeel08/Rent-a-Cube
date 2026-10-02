from django.test import TestCase
from django.urls import reverse

from user.models import user_tb
from workspace.auth_utils import hash_password

from .models import owner_tb, owvaddwork


class OwnerAccessTests(TestCase):
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
            accept=False,
        )

    def login_as_owner(self, owner):
        session = self.client.session
        session['role'] = 'owner'
        session['id'] = owner.id
        session['Name'] = owner.Name
        session.save()

    def test_owner_login_requires_admin_approval(self):
        response = self.client.post(
            reverse('vlog'),
            {'email': self.owner.Email, 'password': 'owner-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('id', self.client.session)

        self.owner.accept = True
        self.owner.save(update_fields=['accept'])
        response = self.client.post(
            reverse('vlog'),
            {'email': self.owner.Email, 'password': 'owner-password'},
        )

        self.assertRedirects(response, reverse('vhome'))

    def test_owner_cannot_view_another_owners_workspace(self):
        self.owner.accept = True
        self.owner.save(update_fields=['accept'])
        other_owner = owner_tb.objects.create(
            Name='Owner Two',
            Email='other-owner@example.com',
            Phonenumber=9876543211,
            Place='Kozhikode',
            Gender='Other',
            Password=hash_password('other-password'),
            Image='id/other-owner.jpg',
            Workex='4 years',
            Proof='id/other-proof.jpg',
            accept=True,
        )
        workspace = owvaddwork.objects.create(
            Name='Private Desk',
            Sqft='100',
            State='Kerala',
            City='Kozhikode',
            Location='Beach Road',
            Price='300',
            Image='id/private-desk.jpg',
            Pincode='673001',
            Type='Desk',
            Facility='WiFi',
            Capability='1 person',
            owner=other_owner,
        )
        self.login_as_owner(self.owner)

        response = self.client.get(reverse('Workdetail', args=[workspace.id]))

        self.assertEqual(response.status_code, 404)

    def test_owner_cannot_open_chat_with_unrelated_user(self):
        self.owner.accept = True
        self.owner.save(update_fields=['accept'])
        unrelated_user = user_tb.objects.create(
            Name='Unrelated User',
            Email='unrelated@example.com',
            Phonenumber=9876543212,
            Place='Kochi',
            Password=hash_password('user-password'),
            Image='id/unrelated-user.jpg',
        )
        self.login_as_owner(self.owner)

        response = self.client.get(reverse('achat', args=[unrelated_user.id]))

        self.assertEqual(response.status_code, 404)
