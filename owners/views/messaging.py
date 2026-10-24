"""Owner conversations and customer inbox views."""
from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.messaging import create_message, recent_messages
from accounts.models import Booking, Customer, Message, ServiceRequest
from config.validation import positive_integer

from ..models import Owner
from .auth import _owner_guard


def conversation(request, user_id):
    """Handle chat between owner and a specific user - send and display messages."""
    guard = _owner_guard(request)
    if guard:
        return guard

    try:
        user_id = positive_integer(user_id, 'User')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('owner_chat_inbox')
    owner_id = request.session['id']
    owner = get_object_or_404(Owner, id=owner_id)
    user = get_object_or_404(Customer, id=user_id)
    has_relationship = (
        Booking.objects.filter(owner_id=owner_id, user_id=user.id).exists()
        or ServiceRequest.objects.filter(owner_id=owner_id, user_id=user.id).exists()
        or Message.objects.filter(owner=owner, customer=user).exists()
    )
    if not has_relationship:
        raise Http404('User is not available in this owner workspace.')

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message and len(message) <= 500:
            create_message(customer=user, owner=owner, sender_role='owner', body=message)
        elif len(message) > 500:
            messages.info(request, 'Messages must be 500 characters or fewer.')

    messages_qs = recent_messages(customer=user, owner=owner)

    return render(
        request,
        'owners/conversation.html',
        {
            'message': messages_qs,
            'name': owner.name,
            'Rname': user.name,
            'sid': owner_id, 'sender_role': 'owner',
            'image': owner.image,
            'Rimage': user.image,
        },
    )


def chat_inbox(request):
    """Show chat inbox - list of users who have messaged this owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    today = date.today()
    owner_id = str(request.session['id'])
    user_ids = Message.objects.filter(owner_id=owner_id).values_list('customer_id', flat=True)
    users = Customer.objects.filter(id__in=user_ids)
    return render(request, 'owners/chat_inbox.html', {'data': users, 'date': today})
