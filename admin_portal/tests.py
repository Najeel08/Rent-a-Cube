from django.test import Client, TestCase
from django.urls import reverse

from owners.models import owner_tb
from config.auth_utils import hash_password

from .models import Projectadmin


class AdminApprovalTests(TestCase):
    def setUp(self):
        self.admin = Projectadmin.objects.create(
            email='admin@example.com',
            password=hash_password('admin-password'),
        )
        self.owner = owner_tb.objects.create(
            Name='Pending Owner',
            Email='pending@example.com',
            Phonenumber=9876543210,
            Place='Kochi',
            Gender='Other',
            Password=hash_password('owner-password'),
            Image='id/pending-owner.jpg',
            Workex='3 years',
            Proof='id/pending-proof.jpg',
        )
        session = self.client.session
        session['role'] = 'admin'
        session['id'] = self.admin.id
        session.save()

    def test_owner_approval_requires_post(self):
        response = self.client.get(reverse('accept', args=[self.owner.id]))
        self.assertRedirects(response, reverse('ownerlists'))
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.accept)

        response = self.client.post(reverse('accept', args=[self.owner.id]))
        self.assertRedirects(response, reverse('ownerlists'))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.accept)

    def test_private_proof_file_requires_admin_session(self):
        response = Client().get(reverse('proof_file', args=[self.owner.id]))

        self.assertRedirects(response, reverse('alogin'))
