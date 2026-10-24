from django.core.files.base import ContentFile
from django.test import Client, TestCase
from django.urls import reverse

from owners.models import Owner, Workspace
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

    def test_owner_hub_sidebar_preserves_navigation_and_active_page(self):
        session = self.client.session
        session['email'] = self.admin.email
        session.save()
        for route in ['admin_owner_list', 'admin_workspace_list']:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, 'id="sidebar"', count=1)
                self.assertContains(response, self.admin.email)
                self.assertContains(response, f'href="{reverse(route)}" class="admin-sidebar-sublink active"')
                self.assertContains(response, 'id="ownerMenu"', count=1)
                self.assertContains(response, 'aria-expanded="true"')
                self.assertContains(response, f'<form method="post" action="{reverse("logout")}"')
                self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_media_views_keep_invalid_and_missing_identifier_responses(self):
        for route in ['admin_owner_proof', 'admin_workspace_image']:
            for identifier in ['not-a-number', '-1', '0', '999999']:
                with self.subTest(route=route, identifier=identifier):
                    url = reverse(route, args=[identifier])
                    self.assertEqual(self.client.get(url).status_code, 404)
                    self.assertRedirects(Client().get(url), reverse('admin_login'))

    def test_media_views_keep_valid_lookups_and_private_file_handling(self):
        workspace = Workspace.objects.create(owner=self.owner, name='Desk', hourly_rate='250')
        for route, record, context_key in [
            ('admin_owner_proof', self.owner, 'Umm'),
            ('admin_workspace_image', workspace, 'Uii'),
        ]:
            response = self.client.get(reverse(route, args=[f'00{record.pk}']))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context[context_key], record)

        file_url = reverse('admin_owner_proof_file', args=[self.owner.pk])
        self.assertEqual(self.client.get(file_url).status_code, 404)
        self.owner.proof_document.save('proof.png', ContentFile(b'private proof fixture'), save=True)
        response = self.client.get(file_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'private proof fixture')
        response.close()
        self.owner.proof_document = ''
        self.owner.save(update_fields=['proof_document'])
        self.assertEqual(self.client.get(file_url).status_code, 404)
        self.assertEqual(self.client.get(reverse('admin_owner_proof_file', args=[999999])).status_code, 404)
