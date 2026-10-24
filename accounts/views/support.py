"""Customer service requests and owner conversations."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from config.pagination import render_page
from config.validation import positive_integer, required_text
from owners.models import Owner

from ..messaging import create_message
from ..models import Customer, Message, ServiceRequest
from .auth import _user_guard


def service_request_create(request):
    """Send a service/maintenance request to an owner."""
    guard = _user_guard(request)
    if guard:
        return guard
    owners = Owner.objects.filter(accept=True, reject=False)

    if request.method == "POST":
        try:
            owner_id = positive_integer(request.POST.get('wid'), 'Workspace provider')
            subject = required_text(request.POST, 'subject', 'Request details', max_length=200)
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'accounts/service_request_form.html', {'own': owners})
        current_user = get_object_or_404(Customer, id=request.session['id'])
        owner = get_object_or_404(Owner, id=owner_id, accept=True)
        ServiceRequest.objects.create(
            name=current_user.name,
            phone_number=current_user.phone_number,
            email=current_user.email,
            subject=subject,
            user=current_user,
            owner=owner,
        )
        messages.info(request, "Request sent")
        return redirect('service_request_list')

    return render(request, 'accounts/service_request_form.html', {'own': owners})


def service_request_list(request):
    """Show all requests sent by the logged-in user."""
    guard = _user_guard(request)
    if guard:
        return guard
    user_requests = ServiceRequest.objects.select_related('owner').filter(user_id=request.session['id'])
    return render_page(request, 'accounts/service_request_list.html', 'Usrq', user_requests)


def customer_conversation(request, owner_id):
    """Handle chat between user and owner - send and display messages."""
    guard = _user_guard(request)
    if guard:
        return guard

    user_id = request.session['id']
    user = get_object_or_404(Customer, id=user_id)
    owner = get_object_or_404(Owner, id=owner_id, accept=True)

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message and len(message) <= 500:
            create_message(customer=user, owner=owner, sender_role='user', body=message)
        elif len(message) > 500:
            messages.info(request, 'Messages must be 500 characters or fewer.')

    messages_qs = Message.objects.filter(customer=user, owner=owner).order_by('-id')[:200]
    messages_qs = list(reversed(messages_qs))

    return render(
        request,
        'accounts/chat_inbox.html',
        {
            'message': messages_qs,
            'name': user.name,
            'Rname': owner.name,
            'sid': user_id, 'sender_role': 'user',
            'image': user.image,
            'Rimage': owner.image,
        },
    )
