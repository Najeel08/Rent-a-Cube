from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.crypto import constant_time_compare
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from owners.models import ServiceAssignment, Technician
from accounts.models import ServiceRequest
from config.auth_utils import (
    hash_password,
    session_auth_hash,
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)


def activate(request, token):
    try:
        data = signing.loads(token, salt='technician-setup', max_age=3600)
        technician = get_object_or_404(Technician, pk=data['id'], owner__accept=True, owner__reject=False)
        if not constant_time_compare(data.get('auth', ''), session_auth_hash(technician)):
            raise signing.BadSignature()
    except (signing.BadSignature, KeyError, TypeError):
        return HttpResponseBadRequest('This setup link is invalid or expired. Ask your owner for a new link.')
    if request.method == 'POST':
        password = request.POST.get('password', '')
        try:
            validate_password(password, technician)
            if password != request.POST.get('cpassword'):
                raise ValidationError('Passwords must match.')
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
        else:
            with transaction.atomic():
                technician = Technician.objects.select_for_update().get(pk=technician.pk)
                if not constant_time_compare(data['auth'], session_auth_hash(technician)):
                    return HttpResponseBadRequest('This setup link has already been used.')
                technician.password = hash_password(password)
                technician.save(update_fields=['password'])
            messages.success(request, 'Password set. You can now sign in.')
            return redirect('technician_login')
    return render(request, 'technicians/activate.html')


def _tech_guard(request):
    """Check if technician is logged in, redirect to login page if not."""
    return require_role(request, 'technician', 'technician_login')


def sign_in(request):
    """Handle technician login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        technician = Technician.objects.select_related('owner').filter(email__iexact=email).first()

        if technician and technician.owner.accept and not technician.owner.reject and password_matches(password, technician.password):
            upgrade_password_if_needed(technician, 'password', password)
            login_role(request, 'technician', technician, technician.name)
            return redirect('technician_dashboard')
        messages.info(request, 'Invalid Details')

    return render(request, 'technicians/login.html')


def dashboard(request):
    """Display technician home/dashboard page."""
    guard = _tech_guard(request)
    if guard:
        return guard
    return render(request, 'technicians/dashboard.html')


def service_request_list(request):
    """Show all work assignments for the logged-in technician."""
    guard = _tech_guard(request)
    if guard:
        return guard
    technician = get_object_or_404(Technician, id=request.session['id'])
    assignments = ServiceAssignment.objects.select_related('request', 'owner').filter(technician=technician, owner=technician.owner)
    return render(
        request,
        'technicians/service_request_list.html',
        {'req': assignments, 'duty': technician.name},
    )


def _update_original_request(assignment, accept):
    """Sync only an explicitly linked request belonging to the assignment owner."""
    if assignment.request_id:
        ServiceRequest.objects.filter(id=assignment.request_id, owner_id=assignment.owner_id).update(accept=accept, reject=not accept)
        return
    # Ambiguous legacy assignments must be linked by an operator, not by names.
    raise ValidationError('This legacy assignment needs an explicit service request link.')


@transaction.atomic
def assignment_accept(request, assignment_id):
    """Accept a work assignment and update the original request status."""
    guard = _tech_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        technician = get_object_or_404(Technician, id=request.session['id'])
        assignment = get_object_or_404(ServiceAssignment.objects.select_for_update(), id=assignment_id, technician=technician, owner=technician.owner)
        try:
            _update_original_request(assignment, True)
            messages.info(request, "Request accepted")
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
    return redirect('technician_service_request_list')


@transaction.atomic
def assignment_reject(request, assignment_id):
    """Reject a work assignment and update the original request status."""
    guard = _tech_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        technician = get_object_or_404(Technician, id=request.session['id'])
        assignment = get_object_or_404(ServiceAssignment.objects.select_for_update(), id=assignment_id, technician=technician, owner=technician.owner)
        try:
            _update_original_request(assignment, False)
            messages.info(request, "Request rejected")
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
    return redirect('technician_service_request_list')
