from django.test import TestCase
from django.urls import reverse

from owners.models import Workassign, addtech, owner_tb
from accounts.models import request_tb, user_tb
from config.auth_utils import hash_password


class TechnicianAssignmentTests(TestCase):
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
            accept=True,
        )
        self.user = user_tb.objects.create(
            Name='User One',
            Email='user@example.com',
            Phonenumber=9876543211,
            Place='Kochi',
            Password=hash_password('user-password'),
            Image='id/user.jpg',
        )
        self.technician = addtech.objects.create(
            Name='Tech One',
            Email='tech@example.com',
            Phonenumber=9876543212,
            Workex='2 years',
            Image='id/tech.jpg',
            Place='Kochi',
            Qualification='Diploma',
            Password=hash_password('tech-password'),
            owner=self.owner,
        )
        self.request = request_tb.objects.create(
            Name=self.user.Name,
            Email=self.user.Email,
            Phone=self.user.Phonenumber,
            Subject='Repair projector',
            user=self.user,
            owner=self.owner,
        )
        self.assignment = Workassign.objects.create(
            Name=self.request.Name,
            Email=self.request.Email,
            Phonenumber=self.request.Phone,
            requestmssg=self.request.Subject,
            owner=self.owner,
            tech=self.technician,
            request=self.request,
        )
        session = self.client.session
        session['role'] = 'technician'
        session['id'] = self.technician.id
        session['Name'] = self.technician.Name
        session.save()

    def test_assigned_technician_can_accept_request(self):
        response = self.client.post(reverse('gaccept', args=[self.assignment.id]))

        self.assertRedirects(response, reverse('requests'))
        self.request.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertTrue(self.request.accept)
        self.assertFalse(self.request.reject)
        self.assertEqual(self.assignment.request_id, self.request.id)
