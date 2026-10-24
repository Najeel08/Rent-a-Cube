"""Base tests and fixtures."""
from django.test import TestCase
from owners.models import Owner, Workspace
from config.auth_utils import hash_password, session_auth_hash
from accounts.models import Customer


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
