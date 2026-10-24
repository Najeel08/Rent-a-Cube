"""Workspaces tests and fixtures."""
from django.test import override_settings
from django.urls import reverse
from accounts.tests.base import UserTestCase
from config.auth_utils import session_auth_hash


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class WorkspaceValidationTests(UserTestCase):
    def setUp(self):
        super().setUp()
        session = self.client.session
        session.update({'role': 'owner', 'id': self.owner.pk, 'auth_hash': session_auth_hash(self.owner)})
        session.save()
        self.fields = dict(
            name='Team Office', sqft='250', state='Kerala', city='Kochi',
            location='Main Road', price='0300', pincode='682001', type='Private Office',
            facility='WiFi, Whiteboard', capability='4 people',
        )

    def test_create_and_edit_use_the_same_fields_without_changing_ownership(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from owners.models import Workspace

        data = BytesIO()
        Image.new('RGB', (2, 2)).save(data, 'PNG')
        fields = dict(self.fields, image=SimpleUploadedFile('office.png', data.getvalue(), content_type='image/png'))
        self.assertRedirects(self.client.post(reverse('workspace_create'), fields), reverse('owner_workspace_list'))
        workspace = Workspace.objects.get(name='Team Office')
        image_name = workspace.image.name
        self.assertEqual(workspace.hourly_rate, '300')
        self.assertEqual(workspace.owner, self.owner)

        self.fields.update(name='Updated Office', price='0350', owner_id='999999')
        self.assertRedirects(
            self.client.post(reverse('workspace_edit', args=[workspace.pk]), self.fields),
            reverse('owner_workspace_list'),
        )
        workspace.refresh_from_db()
        self.assertEqual(workspace.name, 'Updated Office')
        self.assertEqual(workspace.hourly_rate, '350')
        self.assertEqual(workspace.image.name, image_name)
        self.assertEqual(workspace.owner, self.owner)
        self.assertEqual(workspace.amenities, self.fields['facility'])
        self.assertEqual(workspace.capacity, self.fields['capability'])

    def test_both_forms_reject_invalid_fields_without_saving(self):
        from owners.models import Workspace

        for route, args in [('workspace_create', []), ('workspace_edit', [self.workspace.pk])]:
            for changes, error in [
                ({'name': ''}, 'Workspace name is required.'),
                ({'price': '-1'}, 'Hourly price must be greater than zero.'),
                ({'facility': 'x' * 51}, 'Facilities must be 50 characters or fewer.'),
            ]:
                with self.subTest(route=route, fields=changes):
                    response = self.client.post(reverse(route, args=args), self.fields | changes)
                    self.assertContains(response, error)
                    self.assertEqual(Workspace.objects.count(), 1)
                    self.workspace.refresh_from_db()
                    self.assertEqual(self.workspace.name, 'Desk One')

    def test_create_still_requires_a_valid_photo(self):
        response = self.client.post(reverse('workspace_create'), self.fields)
        self.assertContains(response, 'Workspace image is required.')
