from django.test import Client, TestCase
from django.urls import reverse

from owners.models import Owner
from config.auth_utils import hash_password, session_auth_hash

from admin_portal.models import PlatformAdmin


class AdminApprovalTests(TestCase):
    def setUp(self):
        self.admin = PlatformAdmin.objects.create(
            email='admin@example.com',
            password=hash_password('admin-password'),
        )
        self.owner = Owner.objects.create(
            name='Pending Owner',
            email='pending@example.com',
            phone_number=9876543210,
            place='Kochi',
            gender='Other',
            password=hash_password('owner-password'),
            image='id/pending-owner.jpg',
            work_experience='3 years',
            proof_document='id/pending-proof.jpg',
        )
        session = self.client.session
        session['role'] = 'admin'
        session['id'] = self.admin.id
        session['auth_hash'] = session_auth_hash(self.admin)
        session.save()

    def test_owner_approval_requires_post(self):
        response = self.client.get(reverse('admin_owner_approve', args=[self.owner.id]))
        self.assertRedirects(response, reverse('admin_owner_list'))
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.accept)

        response = self.client.post(reverse('admin_owner_approve', args=[self.owner.id]))
        self.assertRedirects(response, reverse('admin_owner_list'))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.accept)

    def test_private_proof_file_requires_admin_session(self):
        response = Client().get(reverse('admin_owner_proof_file', args=[self.owner.id]))

        self.assertRedirects(response, reverse('admin_login'))
