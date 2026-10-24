"""Store customer-owner messages after the portal checks access and input."""
from django.utils import timezone

from .models import Message


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
