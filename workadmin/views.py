from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from owners.models import addtech, owner_tb, owvaddwork
from user.models import cart, user_tb
from workspace.auth_utils import (
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)
from .models import Projectadmin


def _admin_guard(request):
    """Check if admin is logged in, redirect to login page if not."""
    return require_role(request, 'admin', 'alogin')


def alogin(request):
    """Handle admin login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        admin = Projectadmin.objects.filter(email__iexact=email).first()

        if admin and password_matches(password, admin.password):
            # Auto-upgrade plaintext password to hashed if needed
            upgrade_password_if_needed(admin, 'password', password)
            login_role(request, 'admin', admin)
            request.session['email'] = admin.email
            return redirect('aindex')
        messages.info(request, 'Invalid admin')

    return render(request, 'spaceadmin/alogin.html')


def apage(request):
    """Display admin landing page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render(request, 'spaceadmin/index.html')


def aindex(request):
    """Display admin dashboard with counts of owners, users, bookings, technicians."""
    guard = _admin_guard(request)
    if guard:
        return guard
    owners = owner_tb.objects.all()
    users = user_tb.objects.all()
    bookings = cart.objects.all()
    technicians = addtech.objects.all()
    return render(
        request,
        'spaceadmin/adminindex.html',
        {'ow': owners, 'us': users, "ct": bookings, "ad": technicians},
    )


def ownerlists(request):
    """Show list of all registered owners for admin to approve/reject."""
    guard = _admin_guard(request)
    if guard:
        return guard
    owners = owner_tb.objects.all()
    return render(request, 'spaceadmin/ownerlists.html', {'Ut': owners})


def spaceview(request):
    """Show all workspace listings across all owners."""
    guard = _admin_guard(request)
    if guard:
        return guard
    ownerwork = owvaddwork.objects.all()
    ownername = owner_tb.objects.all()
    return render(request, 'spaceadmin/spaceview.html', {'Um': ownerwork, 'Un': ownername})


def userlist(request):
    """Show list of all registered users."""
    guard = _admin_guard(request)
    if guard:
        return guard
    users = user_tb.objects.all()
    return render(request, 'spaceadmin/userlist.html', {'Ua': users})


def bookingdetail(request):
    """Show all booking details across all users."""
    guard = _admin_guard(request)
    if guard:
        return guard
    userdetails = cart.objects.all()
    return render(request, 'spaceadmin/bookingdetail.html', {'bk': userdetails})


def worder(request):
    """Show all workspace orders."""
    guard = _admin_guard(request)
    if guard:
        return guard
    orders = cart.objects.all()
    return render(request, 'spaceadmin/worder.html', {'Us': orders})


def viewsuggestion(request):
    """Display suggestions page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render(request, 'spaceadmin/viewsuggestion.html')


def suggestions(request):
    """Display suggestions form page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render(request, 'spaceadmin/suggestions.html')


def spaceimage(request):
    """Display workspace images page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render(request, 'spaceadmin/spaceimage.html')


def proofview(request, ps):
    """View an owner's uploaded proof/ID document."""
    guard = _admin_guard(request)
    if guard:
        return guard
    owner = get_object_or_404(owner_tb, id=ps)
    return render(request, "spaceadmin/proofview.html", {'Umm': owner})


def proof_file(request, ps):
    """Serve an owner proof document only to an authenticated platform admin."""
    guard = _admin_guard(request)
    if guard:
        return guard
    owner = get_object_or_404(owner_tb, id=ps)
    if not owner.Proof:
        raise Http404('Proof document not found')
    try:
        return FileResponse(owner.Proof.open('rb'), content_type='image/*')
    except OSError as exc:
        raise Http404('Proof document not found') from exc


def imageview(request, pi):
    """View a workspace's uploaded image."""
    guard = _admin_guard(request)
    if guard:
        return guard
    image = get_object_or_404(owvaddwork, id=pi)
    return render(request, "spaceadmin/imageview.html", {'Uii': image})


def profile(request):
    """Display admin profile page."""
    guard = _admin_guard(request)
    if guard:
        return guard
    return render(request, 'spaceadmin/profile.html')


def accept(request, id):
    """Approve an owner's registration - allows them to log in and list workspaces."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        owner_tb.objects.filter(id=id).update(accept=True, reject=False)
        messages.info(request, "Owner accepted")
    return redirect("ownerlists")


def reject(request, id):
    """Reject an owner's registration - blocks them from logging in."""
    guard = _admin_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        owner_tb.objects.filter(id=id).update(reject=True, accept=False)
        messages.info(request, "Owner rejected")
    return redirect("ownerlists")
