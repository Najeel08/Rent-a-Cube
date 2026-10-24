"""Owner technician management and service assignments."""
from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import ServiceRequest
from config.auth_utils import is_valid_email, normalize_email, session_auth_hash
from config.pagination import render_page
from config.validation import (
    positive_integer,
    required_text,
    validate_image_upload,
    validate_phone_number,
)

from ..models import ServiceAssignment, Technician
from .auth import _owner_guard


def service_request_list(request):
    """Show all service requests received by the owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    req = ServiceRequest.objects.filter(owner_id=request.session['id'])
    return render_page(request, 'owners/service_request_list.html', 'req', req)


@transaction.atomic
def service_assignment_create(request, request_id):
    """Assign a service request to one of the owner's technicians."""
    guard = _owner_guard(request)
    if guard:
        return guard
    try:
        request_id = positive_integer(request_id, 'Request')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('owner_service_request_list')
    reqs = get_object_or_404(ServiceRequest.objects.select_for_update(), id=request_id, owner_id=request.session['id'])
    options = Technician.objects.filter(owner_id=request.session['id'])

    if request.method == 'POST':
        try:
            technician_id = positive_integer(request.POST.get('tech'), 'Technician')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/service_assignment.html', {'reqs': reqs, 'options': options})
        technician = get_object_or_404(Technician, id=technician_id, owner_id=request.session['id'])
        ServiceAssignment.objects.update_or_create(
            request=reqs, defaults=dict(
            name=reqs.name,
            email=reqs.email,
            phone_number=reqs.phone_number,
            request_message=reqs.subject,
            owner_id=request.session['id'],
            technician=technician,
            ),
        )
        reqs.accept = False
        reqs.reject = False
        reqs.save(update_fields=['accept', 'reject'])
        messages.info(request, "Request assigned")
        return redirect('owner_service_request_list')

    return render(request, 'owners/service_assignment.html', {'reqs': reqs, 'options': options})


def technician_create(request):
    """Add a new technician under the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard

    if request.method == "POST":
        try:
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=50))
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            phone = validate_phone_number(request.POST.get('phonenumber'))
            workex = required_text(request.POST, 'workex', 'Work experience', max_length=25)
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            qualification = required_text(request.POST, 'qualification', 'Qualification', max_length=60)
            image = request.FILES.get('image')
            validate_image_upload(image, 'Technician image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/technician_create.html')
        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. rahul@example.com)")
            return render(request, 'owners/technician_create.html')
        if Technician.objects.filter(email__iexact=email).exists():
            messages.info(request, "email already exists")
        else:
            try:
                with transaction.atomic():
                    Technician.objects.create(
                        name=name,
                        email=email,
                        phone_number=phone,
                        work_experience=workex,
                        place=place,
                        qualification=qualification,
                        image=image,
                        owner_id=request.session['id'],
                    )
            except IntegrityError:
                messages.error(request, 'This email address is already registered.')
                return render(request, 'owners/technician_create.html')
            messages.info(request, "Technician added. Send login mail to create a password.")
            return redirect('owner_technician_list')

    return render(request, 'owners/technician_create.html')


def technician_list(request):
    """Show all technicians under the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    technicians = Technician.objects.filter(owner_id=request.session['id'])
    return render_page(request, 'owners/technician_list.html', 'viewss', technicians)


def send_technician_login(request, technician_id):
    """Email a short-lived setup link; never email a reusable password."""
    guard = _owner_guard(request)
    if guard:
        return guard
    technician = get_object_or_404(Technician, id=technician_id, owner_id=request.session['id'])

    if request.method == 'POST':
        recipient = technician.email
        name = technician.name

        if not settings.DEBUG and settings.EMAIL_BACKEND in {
            'django.core.mail.backends.console.EmailBackend',
            'config.security.RedactedConsoleEmailBackend',
        }:
            messages.error(request, 'Configure a delivery email backend before sending setup links.')
            return redirect('owner_technician_list')
        token = signing.dumps({'id': technician.pk, 'auth': session_auth_hash(technician)}, salt='technician-setup')
        link = request.build_absolute_uri(reverse('technician_activate', args=[token]))
        subject = 'Hi, ' + name
        message = 'Set your Rent-a-Cube password using this link (expires in one hour):\n' + link
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [recipient], fail_silently=False)
            messages.info(request, "Password setup link sent")
        except Exception:
            messages.info(request, "Email could not be sent. Check email settings.")
        return redirect('owner_technician_list')

    return render(request, 'owners/technician_login_email.html', {"owner": technician})
