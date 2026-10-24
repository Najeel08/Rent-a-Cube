"""Messaging tests and fixtures."""
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from accounts.messaging import create_message
from accounts.models import Message
from accounts.tests.base import UserTestCase
from config.auth_utils import session_auth_hash


class ConversationRecordTests(UserTestCase):
    def test_both_portals_keep_message_length_and_whitespace_rules(self):
        create_message(customer=self.user, owner=self.owner, sender_role='user', body='Earlier message')
        for role, account, route, recipient in [
            ('user', self.user, 'customer_conversation', self.owner),
            ('owner', self.owner, 'owner_conversation', self.user),
        ]:
            self.client = Client()
            session = self.client.session
            session.update({'role': role, 'id': account.pk, 'auth_hash': session_auth_hash(account)})
            session.save()
            for body, saved, warning in [
                ('', False, False), ('   ', False, False),
                ('  ' + 'x' * 500 + '  ', True, False), ('x' * 501, False, True),
            ]:
                with self.subTest(role=role, length=len(body)):
                    before = Message.objects.count()
                    response = self.client.post(reverse(route, args=[recipient.pk]), {'message': body})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(Message.objects.count(), before + saved)
                    if saved:
                        self.assertEqual(Message.objects.latest('pk').body, body.strip())
                    # These pages queue feedback without rendering message alerts.
                    feedback = [str(message) for message in get_messages(response.wsgi_request)]
                    expected = ['Messages must be 500 characters or fewer.'] if warning else []
                    self.assertEqual(feedback, expected)

    def test_both_portals_display_only_the_latest_200_messages_in_chronological_order(self):
        records = [create_message(
            customer=self.user, owner=self.owner, sender_role='user', body=f'Message {index}',
        ) for index in range(205)]
        Message.objects.create(
            body='Unlinked legacy message', date=timezone.localdate(), time='10:00:00',
            sender_id=str(self.user.pk), receiver_id=str(self.owner.pk),
            sender_name=self.user.name, receiver_name=self.owner.name,
        )
        for role, account, route, recipient in [
            ('user', self.user, 'customer_conversation', self.owner),
            ('owner', self.owner, 'owner_conversation', self.user),
        ]:
            session = self.client.session
            session.update({'role': role, 'id': account.pk, 'auth_hash': session_auth_hash(account)})
            session.save()
            with self.subTest(role=role):
                response = self.client.get(reverse(route, args=[recipient.pk]))
                self.assertEqual(response.context['message'], records[-200:])
                self.assertNotContains(response, 'Unlinked legacy message')

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
