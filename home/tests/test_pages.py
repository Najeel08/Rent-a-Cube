"""Pages tests and fixtures."""
from django.test import TestCase
from django.urls import reverse
from home.models import SupportInquiry


class PublicPageTests(TestCase):
    def test_landing_page_is_available(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/index.html')

    def test_contact_page_is_available(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'public/contact.html')

    def test_contact_submission_is_saved(self):
        response = self.client.post(
            reverse('contact'),
            {
                'name': 'Test User',
                'email': 'test@example.com',
                'message': 'Please help with a booking.',
            },
        )

        self.assertRedirects(response, reverse('contact'))
        self.assertTrue(
            SupportInquiry.objects.filter(
                name='Test User', email='test@example.com'
            ).exists()
        )

    def test_logout_is_post_only_and_clears_session(self):
        session = self.client.session
        session['role'] = 'user'
        session['id'] = 99
        session.save()

        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        response = self.client.post(reverse('logout'))

        self.assertRedirects(response, reverse('index'))
        self.assertNotIn('role', self.client.session)
        self.assertNotIn('id', self.client.session)

    def test_contact_subject_is_saved_with_message(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Visitor', 'email': 'visitor@example.test',
            'subject': 'booking', 'message': 'Please check my booking.',
        })
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(SupportInquiry.objects.get().message,
                         '[Booking Assistance]\n\nPlease check my booking.')

    def test_invalid_contact_subject_retains_input_without_saving(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Visitor', 'email': 'visitor@example.test',
            'subject': 'unknown', 'message': 'Please help.',
        })
        self.assertContains(response, 'Select a valid subject.')
        self.assertContains(response, 'Please help.')
        self.assertFalse(SupportInquiry.objects.exists())

    def test_contact_subject_and_message_respect_storage_limit(self):
        for length, valid in [(1470, True), (1500, False)]:
            SupportInquiry.objects.all().delete()
            response = self.client.post(reverse('contact'), {
                'name': 'Visitor', 'email': 'visitor@example.test',
                'subject': 'workspace', 'message': 'x' * length,
            })
            self.assertEqual(response.status_code, 302 if valid else 200)
            self.assertEqual(SupportInquiry.objects.exists(), valid)
