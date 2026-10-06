from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from owners.models import Workassign, addtech
from accounts.models import request_tb
from config.auth_utils import (
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)


def _tech_guard(request):
    """Check if technician is logged in, redirect to login page if not."""
    return require_role(request, 'technician', 'tlog')


def tlog(request):
    """Handle technician login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        technician = addtech.objects.filter(Email__iexact=email).first()

        if technician and password_matches(password, technician.Password):
            upgrade_password_if_needed(technician, 'Password', password)
            login_role(request, 'technician', technician, technician.Name)
            return redirect('thome')
        messages.info(request, 'Invalid Details')

    return render(request, 'technicians/login.html')


def thome(request):
    """Display technician home/dashboard page."""
    guard = _tech_guard(request)
    if guard:
        return guard
    return render(request, 'technicians/dashboard.html')


def requests(request):
    """Show all work assignments for the logged-in technician."""
    guard = _tech_guard(request)
    if guard:
        return guard
    technician = get_object_or_404(addtech, id=request.session['id'])
    assignments = Workassign.objects.filter(tech=technician)
    return render(
        request,
        'technicians/service_request_list.html',
        {'req': assignments, 'duty': technician.Name},
    )


def _update_original_request(assignment, accept):
    """Sync assignment state to its direct request link, with legacy fallback only when needed."""
    if assignment.request_id:
        request_tb.objects.filter(id=assignment.request_id).update(accept=accept, reject=not accept)
        return
    request_tb.objects.filter(
        Name=assignment.Name,
        Email=assignment.Email,
        Phone=assignment.Phonenumber,
        Subject=assignment.requestmssg,
        owner=assignment.owner,
    ).update(accept=accept, reject=not accept)


def gaccept(request, id):
    """Accept a work assignment and update the original request status."""
    guard = _tech_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        assignment = get_object_or_404(Workassign, id=id, tech_id=request.session['id'])
        _update_original_request(assignment, True)
        messages.info(request, "Request accepted")
    return redirect('requests')


def greject(request, id):
    """Reject a work assignment and update the original request status."""
    guard = _tech_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        assignment = get_object_or_404(Workassign, id=id, tech_id=request.session['id'])
        _update_original_request(assignment, False)
        messages.info(request, "Request rejected")
    return redirect('requests')
