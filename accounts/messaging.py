"""Store customer-owner messages after the portal checks access and input."""
from django.utils import timezone

from .models import Message


def recent_messages(*, customer, owner):
    """Return the latest 200 messages in display order for one conversation."""
    newest_first = Message.objects.filter(customer=customer, owner=owner).order_by('-id')[:200]
    return list(reversed(newest_first))


def create_message(*, customer, owner, sender_role, body):
    if sender_role == 'user':
        sender, receiver = customer, owner
    elif sender_role == 'owner':
        sender, receiver = owner, customer
    else:
        raise ValueError('Messages must be sent by a customer or owner.')
    now = timezone.localtime()
    return Message.objects.create(
        customer=customer, owner=owner, sender_role=sender_role, body=body,
        date=now.date(), time=now.strftime('%H:%M:%S'),
        sender_id=str(sender.pk), receiver_id=str(receiver.pk),
        sender_name=sender.name, receiver_name=receiver.name,
    )
