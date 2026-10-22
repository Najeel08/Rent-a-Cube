from django.test import TestCase
from django.urls import reverse

from accounts.models import Customer
from config.auth_utils import hash_password, session_auth_hash

from .models import Owner, Workspace


class OwnerAccessTests(TestCase):
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
            accept=False,
        )

    def login_as_owner(self, owner):
        session = self.client.session
        session['role'] = 'owner'
        session['id'] = owner.id
        session['auth_hash'] = session_auth_hash(owner)
        session['Name'] = owner.name
        session.save()

    def test_owner_login_requires_admin_approval(self):
        response = self.client.post(
            reverse('owner_login'),
            {'email': self.owner.email, 'password': 'owner-password'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('id', self.client.session)

        self.owner.accept = True
        self.owner.save(update_fields=['accept'])
        response = self.client.post(
            reverse('owner_login'),
            {'email': self.owner.email, 'password': 'owner-password'},
        )

        self.assertRedirects(response, reverse('owner_dashboard'))

    def test_owner_cannot_view_another_owners_workspace(self):
        self.owner.accept = True
        self.owner.save(update_fields=['accept'])
        other_owner = Owner.objects.create(
            name='Owner Two',
            email='other-owner@example.com',
            phone_number=9876543211,
            place='Kozhikode',
            gender='Other',
            password=hash_password('other-password'),
            image='id/other-owner.jpg',
            work_experience='4 years',
            proof_document='id/other-proof.jpg',
            accept=True,
        )
        workspace = Workspace.objects.create(
            name='Private Desk',
            square_feet='100',
            state='Kerala',
            city='Kozhikode',
            location='Beach Road',
            hourly_rate='300',
            image='id/private-desk.jpg',
            postal_code='673001',
            workspace_type='Desk',
            amenities='WiFi',
            capacity='1 person',
            owner=other_owner,
        )
        self.login_as_owner(self.owner)

        response = self.client.get(reverse('owner_workspace_detail', args=[workspace.id]))

        self.assertEqual(response.status_code, 404)

    def test_owner_cannot_open_chat_with_unrelated_user(self):
        self.owner.accept = True
        self.owner.save(update_fields=['accept'])
        unrelated_user = Customer.objects.create(
            name='Unrelated User',
            email='unrelated@example.com',
            phone_number=9876543212,
            place='Kochi',
            password=hash_password('user-password'),
            image='id/unrelated-user.jpg',
        )
        self.login_as_owner(self.owner)

        response = self.client.get(reverse('owner_conversation', args=[unrelated_user.id]))

        self.assertEqual(response.status_code, 404)
