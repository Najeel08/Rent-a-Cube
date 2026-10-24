"""Messaging tests and fixtures."""
from django.urls import reverse
from django.utils import timezone
from accounts.models import Message
from accounts.tests.base import UserTestCase
from config.auth_utils import session_auth_hash


class ConversationRecordTests(UserTestCase):
    def test_both_portals_store_the_correct_sender_and_conversation(self):
        self.login_as_user()
        self.client.post(reverse('customer_conversation', args=[self.owner.pk]), {'message': '  Is WiFi available?  '})
        session = self.client.session
        session.update({'role': 'owner', 'id': self.owner.pk, 'auth_hash': session_auth_hash(self.owner)})
        session.save()
        self.client.post(reverse('owner_conversation', args=[self.user.pk]), {'message': '  Yes, WiFi is included.  '})

        records = list(Message.objects.order_by('pk'))
        self.assertEqual(len(records), 2)
        for record, sender, receiver, role, body in [
            (records[0], self.user, self.owner, 'user', 'Is WiFi available?'),
            (records[1], self.owner, self.user, 'owner', 'Yes, WiFi is included.'),
        ]:
            self.assertEqual(record.customer, self.user)
            self.assertEqual(record.owner, self.owner)
            self.assertEqual(record.sender_role, role)
            self.assertEqual(record.sender_id, str(sender.pk))
            self.assertEqual(record.receiver_id, str(receiver.pk))
            self.assertEqual(record.sender_name, sender.name)
            self.assertEqual(record.receiver_name, receiver.name)
            self.assertEqual(record.body, body)
            self.assertEqual(record.date, timezone.localdate())
