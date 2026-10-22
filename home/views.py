from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from config.auth_utils import is_valid_email, normalize_email
from config.validation import required_text

from .models import SupportInquiry


def index(request):
    """Display the landing/home page."""
    return render(request, 'public/index.html')


def contact(request):
    """Display and accept validated public support inquiries."""
    if request.method == 'POST':
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=80)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=254))
            message = required_text(request.POST, 'message', 'Message', max_length=1500)
            subject = request.POST.get('subject', '')
            # Keep submissions from the original three-field form compatible.
            subjects = {'general': 'General Enquiries', 'booking': 'Booking Assistance',
                        'workspace': 'Workspace Support', 'payment': 'Payment Issues'}
            if subject:
                if subject not in subjects:
                    raise ValidationError('Select a valid subject.')
                message = f'[{subjects[subject]}]\n\n{message}'
                if len(message) > 1500:
                    raise ValidationError('Keep your message to 1470 characters or fewer when selecting a subject.')
            if not is_valid_email(email):
                raise ValidationError('Please enter a valid email address.')
        except ValidationError as exc:
            messages.error(request, exc.message)
            return render(request, 'public/contact.html')
        SupportInquiry.objects.create(name=name, email=email, message=message)
        messages.success(request, 'Your inquiry has been received. Our team will reply by email.')
        return redirect('contact')
    return render(request, 'public/contact.html')


@require_POST
def logout_view(request):
    """End the current custom-auth session for any role."""
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('index')
