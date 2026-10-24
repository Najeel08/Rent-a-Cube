from django.test import TestCase
from django.urls import reverse

from owners.models import ServiceAssignment, Technician, Owner
from accounts.models import ServiceRequest, Customer
from config.auth_utils import hash_password, session_auth_hash


class TechnicianAssignmentTests(TestCase):
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
        self.technician = Technician.objects.create(
            name='Tech One',
            email='tech@example.com',
            phone_number=9876543212,
            work_experience='2 years',
            image='id/tech.jpg',
            place='Kochi',
            qualification='Diploma',
            password=hash_password('tech-password'),
            owner=self.owner,
        )
        self.request = ServiceRequest.objects.create(
            name=self.user.name,
            email=self.user.email,
            phone_number=self.user.phone_number,
            subject='Repair projector',
            user=self.user,
            owner=self.owner,
        )
        self.assignment = ServiceAssignment.objects.create(
            name=self.request.name,
            email=self.request.email,
            phone_number=self.request.phone_number,
            request_message=self.request.subject,
            owner=self.owner,
            technician=self.technician,
            request=self.request,
        )
        session = self.client.session
        session['role'] = 'technician'
        session['id'] = self.technician.id
        session['auth_hash'] = session_auth_hash(self.technician)
        session['Name'] = self.technician.name
        session.save()

    def test_assigned_technician_can_accept_request(self):
        response = self.client.post(reverse('assignment_accept', args=[self.assignment.id]))

        self.assertRedirects(response, reverse('technician_service_request_list'))
        self.request.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertTrue(self.request.accept)
        self.assertFalse(self.request.reject)
        self.assertEqual(self.assignment.request_id, self.request.id)

    def test_assigned_technician_can_reject_request(self):
        response = self.client.post(reverse('assignment_reject', args=[self.assignment.pk]))
        self.assertRedirects(response, reverse('technician_service_request_list'))
        self.request.refresh_from_db()
        self.assertFalse(self.request.accept)
        self.assertTrue(self.request.reject)

    def test_other_technicians_cannot_accept_or_reject_assignment(self):
        other = Technician.objects.create(name='Other Tech', email='other@example.test', owner=self.owner)
        self.assignment.technician = other
        self.assignment.save(update_fields=['technician'])
        for route in ['assignment_accept', 'assignment_reject']:
            self.assertEqual(self.client.post(reverse(route, args=[self.assignment.pk])).status_code, 404)
        self.request.refresh_from_db()
        self.assertFalse(self.request.accept)
        self.assertFalse(self.request.reject)

    def test_get_and_unlinked_legacy_assignments_do_not_change_request(self):
        for route in ['assignment_accept', 'assignment_reject']:
            self.assertRedirects(self.client.get(reverse(route, args=[self.assignment.pk])), reverse('technician_service_request_list'))
        self.assignment.request = None
        self.assignment.save(update_fields=['request'])
        for route in ['assignment_accept', 'assignment_reject']:
            response = self.client.post(reverse(route, args=[self.assignment.pk]), follow=True)
            self.assertContains(response, 'This legacy assignment needs an explicit service request link.')
        self.request.refresh_from_db()
        self.assertFalse(self.request.accept)
        self.assertFalse(self.request.reject)
