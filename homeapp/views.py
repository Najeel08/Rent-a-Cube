from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from workspace.auth_utils import is_valid_email, normalize_email
from workspace.validation import required_text

from .models import SupportInquiry


def index(request):
    """Display the landing/home page."""
    return render(request, 'index.html')


def contact4(request):
    """Display and accept validated public support inquiries."""
    if request.method == 'POST':
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=80)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=254))
            message = required_text(request.POST, 'message', 'Message', max_length=1500)
            if not is_valid_email(email):
                raise ValidationError('Please enter a valid email address.')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'contact4.html')
        SupportInquiry.objects.create(name=name, email=email, message=message)
        messages.success(request, 'Your inquiry has been received. Our team will reply by email.')
        return redirect('contact4')
    return render(request, 'contact4.html')


@require_POST
def logout_view(request):
    """End the current custom-auth session for any role."""
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('index')
