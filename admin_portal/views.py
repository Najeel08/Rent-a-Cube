from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from owners.models import Technician, Owner, Workspace
from accounts.models import Booking, Customer
from config.auth_utils import (
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)
from .models import PlatformAdmin
from home.models import SupportInquiry
from config.pagination import render_page


def _admin_guard(request):
    """Check if admin is logged in, redirect to login page if not."""
    return require_role(request, 'admin', 'admin_login')


def sign_in(request):
    """Handle admin login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        admin = PlatformAdmin.objects.filter(email__iexact=email).first()

        if password_matches(password, admin.password if admin else None) and admin:
            upgrade_password_if_needed(admin, 'password', password)
            login_role(request, 'admin', admin)
            request.session['email'] = admin.email
            return redirect('admin_dashboard')
        messages.info(request, 'Invalid admin')

    return render(request, 'admin_portal/login.html')


def dashboard(request):
    """Display admin dashboard with counts of owners, users, bookings, technicians."""
    guard = _admin_guard(request)
    if guard:
        return guard
    owners = Owner.objects.all()
    users = Customer.objects.all()
    bookings = Booking.objects.select_related('owner', 'user').all()
    technicians = Technician.objects.all()
    return render(
        request,
        'admin_portal/dashboard.html',
        {'ow': owners, 'us': users, 'ct': bookings, 'ad': technicians, 'recent_bookings': bookings.order_by('-pk')[:10]},
    )


def owner_list(request):
    """Show list of all registered owners for admin to approve/reject."""
    guard = _admin_guard(request)
    if guard:
        return guard
    owners = Owner.objects.all()
    return render_page(request, 'admin_portal/owner_list.html', 'Ut', owners)


def workspace_list(request):
    """Show all workspace listings across all owners."""
    guard = _admin_guard(request)
    if guard:
        return guard
    ownerwork = Workspace.objects.select_related('owner').all()
    ownername = Owner.objects.all()
    return render(request, 'admin_portal/workspace_list.html', {'Um': ownerwork, 'Un': ownername})


def customer_list(request):
    """Show list of all registered users."""
    guard = _admin_guard(request)
    if guard:
        return guard
    users = Customer.objects.all()
    return render_page(request, 'admin_portal/customer_list.html', 'Ua', users)


def booking_list(request):
    """Show all booking details across all users."""
    guard = _admin_guard(request)
    if guard:
        return guard
    userdetails = Booking.objects.select_related('owner', 'user').all()
    return render_page(request, 'admin_portal/booking_list.html', 'bk', userdetails)


def order_list(request):
    """Show all workspace orders."""
    guard = _admin_guard(request)
    if guard:
        return guard
    orders = Booking.objects.select_related('owner', 'user').all()
    return render_page(request, 'admin_portal/order_list.html', 'Us', orders)


def support_inquiry_detail(request):
    return support_inquiry_list(request)


def support_inquiry_list(request):
    guard = _admin_guard(request)
    if guard:
        return guard
    if request.method == 'POST':
        inquiry_id = request.POST.get('inquiry_id', '')
        if not inquiry_id.isdecimal():
            raise Http404('Inquiry not found')
        inquiry = get_object_or_404(SupportInquiry, pk=inquiry_id)
        inquiry.resolved = True
        inquiry.save(update_fields=['resolved'])
        return redirect('admin_support_inquiry_list')
    return render_page(request, 'admin_portal/support_inquiry_list.html', 'inquiries', SupportInquiry.objects.all())


def workspace_images(request):
    """Display workspace images page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render_page(request, 'admin_portal/workspace_images.html', 'spaces', Workspace.objects.select_related('owner'))


def owner_proof(request, owner_id):
    """View an owner's uploaded proof/ID document."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if not str(owner_id).isdecimal():
        raise Http404('Owner not found')
    owner = get_object_or_404(Owner, id=owner_id)
    return render(request, "admin_portal/owner_proof.html", {'Umm': owner})


def owner_proof_file(request, owner_id):
    """Serve an owner proof document only to an authenticated platform admin."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if not str(owner_id).isdecimal():
        raise Http404('Owner not found')
    owner = get_object_or_404(Owner, id=owner_id)
    if not owner.proof_document:
        raise Http404('Proof document not found')
    try:
        return FileResponse(owner.proof_document.open('rb'))
    except OSError as exc:
        raise Http404('Proof document not found') from exc


def workspace_image(request, workspace_id):
    """View a workspace's uploaded image."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if not str(workspace_id).isdecimal():
        raise Http404('Workspace not found')
    image = get_object_or_404(Workspace, id=workspace_id)
    return render(request, "admin_portal/workspace_image.html", {'Uii': image})


def profile(request):
    """Display admin profile page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render(request, 'admin_portal/profile.html')


def approve_owner(request, owner_id):
    """Approve an owner's registration - allows them to log in and list workspaces."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        Owner.objects.filter(id=owner_id).update(accept=True, reject=False)
        messages.info(request, "Owner accepted")
    return redirect('admin_owner_list')


def reject_owner(request, owner_id):
    """Reject an owner's registration - blocks them from logging in."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        Owner.objects.filter(id=owner_id).update(reject=True, accept=False)
        messages.info(request, "Owner rejected")
    return redirect('admin_owner_list')
