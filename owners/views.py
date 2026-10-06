from datetime import date, datetime
import os
import secrets
import string

import razorpay
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from user.models import Messages_Tb, cart, refund_tb, request_tb, user_tb
from workspace.auth_utils import (
    hash_password,
    is_valid_email,
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)
from workspace.validation import (
    MAX_HOURLY_PRICE,
    positive_integer,
    required_text,
    validate_image_upload,
    validate_phone_number,
)
from .models import Workassign, addtech, owner_tb, owvaddwork


def _owner_guard(request):
    """Check if owner is logged in, redirect to login page if not."""
    return require_role(request, 'owner', 'vlog')


def _razorpay_client():
    """Create and return a Razorpay client using API keys from settings."""
    if not settings.RAZORPAY_API_KEY or not settings.RAZORPAY_API_SECRET_KEY:
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY))


def _remove_file(field_file):
    """Delete an uploaded file from disk if it exists."""
    if field_file and field_file.name and os.path.exists(field_file.path):
        os.remove(field_file.path)


def vreg(request):
    """Handle owner registration - validate input and create new owner."""
    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=50))
            phone = validate_phone_number(request.POST.get('phonenumber'))
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            gender = required_text(request.POST, 'gender', 'Gender', max_length=15)
            workex = required_text(request.POST, 'workex', 'Work experience', max_length=25)
            password = required_text(request.POST, 'password', 'Password')
            confirm_password = required_text(request.POST, 'cpassword', 'Password confirmation')
            image = request.FILES.get('image')
            proof = request.FILES.get('proof')
            validate_image_upload(image, 'Profile image')
            validate_image_upload(proof, 'Proof document')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'owner/vreg.html')

        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. vikram@cowork.in)")
            return render(request, 'owner/vreg.html')

        if password != confirm_password:
            messages.info(request, 'password not match')
            return render(request, 'owner/vreg.html')

        if owner_tb.objects.filter(Email__iexact=email).exists():
            messages.info(request, "email already exists")
        elif owner_tb.objects.filter(Name=name).exists():
            messages.info(request, "user already exists")
        else:
            owner_tb.objects.create(
                Name=name,
                Email=email,
                Phonenumber=phone,
                Place=place,
                Gender=gender,
                Password=hash_password(password),
                Image=image,
                Workex=workex,
                Proof=proof,
            )
            messages.info(request, "Registration submitted. Please wait for admin approval.")
            return redirect('vlog')

    return render(request, 'owner/vreg.html')


def vlog(request):
    """Handle owner login - verify credentials and check admin approval."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        owner = owner_tb.objects.filter(Email__iexact=email).first()

        if owner and password_matches(password, owner.Password):
            if owner.accept:
                upgrade_password_if_needed(owner, 'Password', password)
                login_role(request, 'owner', owner, owner.Name)
                return redirect('vhome')
            messages.info(request, "Account not approved")
        else:
            messages.info(request, 'Invalid owner')

    return render(request, 'owner/vlog.html')


def vhome(request):
    """Display owner home/dashboard page."""
    guard = _owner_guard(request)
    if guard:
        return guard
    return render(request, 'owner/vhome.html')


def vaddwork(request):
    """Add a new workspace listing for the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard

    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Workspace name', max_length=20)
            sqft = required_text(request.POST, 'sqft', 'Square footage', max_length=50)
            state = required_text(request.POST, 'state', 'State', max_length=80)
            city = required_text(request.POST, 'city', 'City', max_length=50)
            location = required_text(request.POST, 'location', 'Location', max_length=60)
            price = positive_integer(request.POST.get('price'), 'Hourly price', MAX_HOURLY_PRICE)
            pincode = required_text(request.POST, 'pincode', 'Pincode', max_length=25)
            workspace_type = required_text(request.POST, 'type', 'Workspace type', max_length=80)
            facility = required_text(request.POST, 'facility', 'Facilities', max_length=50)
            capability = required_text(request.POST, 'capability', 'Capacity', max_length=60)
            image = request.FILES.get('image')
            validate_image_upload(image, 'Workspace image')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'owner/vaddwork.html')
        owvaddwork.objects.create(
            Name=name,
            Sqft=sqft,
            State=state,
            City=city,
            Location=location,
            Price=str(price),
            Image=image,
            Pincode=pincode,
            Type=workspace_type,
            Facility=facility,
            Capability=capability,
            owner_id=request.session['id'],
        )
        messages.info(request, "Workspace added")
        return redirect('oviewwork')

    return render(request, 'owner/vaddwork.html')


def oviewwork(request):
    """Show all workspaces owned by the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    spaces = owvaddwork.objects.filter(owner_id=request.session['id'])
    return render(request, 'owner/oviewwork.html', {'Owvk': spaces})


def Workdetail(request, pik):
    """Show details of a specific workspace."""
    guard = _owner_guard(request)
    if guard:
        return guard
    work = get_object_or_404(owvaddwork, id=pik, owner_id=request.session['id'])
    return render(request, 'owner/Workdetail.html', {'Owvkd': work})


def Ovupdate(request, pin):
    """Update an existing workspace listing."""
    guard = _owner_guard(request)
    if guard:
        return guard
    try:
        workspace_id = positive_integer(pin, 'Workspace')
    except ValidationError as exc:
        messages.info(request, exc.message)
        return redirect('oviewwork')
    owner_work = get_object_or_404(owvaddwork, id=workspace_id, owner_id=request.session['id'])

    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Workspace name', max_length=20)
            sqft = required_text(request.POST, 'sqft', 'Square footage', max_length=50)
            state = required_text(request.POST, 'state', 'State', max_length=80)
            city = required_text(request.POST, 'city', 'City', max_length=50)
            location = required_text(request.POST, 'location', 'Location', max_length=60)
            price = positive_integer(request.POST.get('price'), 'Hourly price', MAX_HOURLY_PRICE)
            pincode = required_text(request.POST, 'pincode', 'Pincode', max_length=25)
            workspace_type = required_text(request.POST, 'type', 'Workspace type', max_length=80)
            facility = required_text(request.POST, 'facility', 'Facilities', max_length=50)
            capability = required_text(request.POST, 'capability', 'Capacity', max_length=60)
            if request.FILES.get('image'):
                validate_image_upload(request.FILES['image'], 'Workspace image')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'owner/Ovupdate.html', {'up': owner_work})
        if request.FILES.get("image"):
            _remove_file(owner_work.Image)
            owner_work.Image = request.FILES["image"]
        owner_work.Name = name
        owner_work.Sqft = sqft
        owner_work.State = state
        owner_work.City = city
        owner_work.Location = location
        owner_work.Price = str(price)
        owner_work.Pincode = pincode
        owner_work.Type = workspace_type
        owner_work.Facility = facility
        owner_work.Capability = capability
        owner_work.save()
        messages.info(request, "Workspace updated")
        return redirect('oviewwork')

    return render(request, 'owner/Ovupdate.html', {'up': owner_work})


def Ovdelete(request, pid):
    """Delete a workspace listing and its image file."""
    guard = _owner_guard(request)
    if guard:
        return guard
    work = get_object_or_404(owvaddwork, id=pid, owner_id=request.session['id'])

    if request.method == "POST":
        _remove_file(work.Image)
        work.delete()
        messages.info(request, "Workspace deleted")
        return redirect('oviewwork')

    return render(request, 'owner/Ovdelete.html', {'delete': work})


def PROFILE(request):
    """Display the owner's profile page."""
    guard = _owner_guard(request)
    if guard:
        return guard
    profile = get_object_or_404(owner_tb, id=request.session['id'])
    return render(request, 'owner/PROFILE.html', {'prof': profile})


def ownerprofileupdate(request, pim=None):
    """Update owner profile - name, email, phone, password, image."""
    guard = _owner_guard(request)
    if guard:
        return guard
    profile = get_object_or_404(owner_tb, id=request.session['id'])

    if pim:
        try:
            profile_id = positive_integer(pim, 'Profile')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return redirect('PROFILE')
        if profile_id != profile.id:
            messages.info(request, "You can update only your own profile")
            return redirect('PROFILE')

    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            new_email = normalize_email(
                required_text(request.POST, 'email', 'Email address', max_length=50)
            )
            if not is_valid_email(new_email):
                raise ValidationError('Please enter a valid email address.')
            phone = validate_phone_number(request.POST.get('phonenumber'))
            workex = required_text(request.POST, 'workex', 'Work experience', max_length=25)
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            if request.FILES.get('image'):
                validate_image_upload(request.FILES['image'], 'Profile image')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'owner/ownerprofileupdate.html', {'pl': profile})
        if owner_tb.objects.exclude(id=profile.id).filter(Email=new_email).exists():
            messages.info(request, "email already exists")
            return render(request, 'owner/ownerprofileupdate.html', {'pl': profile})

        if request.FILES.get("image"):
            _remove_file(profile.Image)
            profile.Image = request.FILES["image"]

        profile.Name = name
        profile.Email = new_email
        profile.Phonenumber = phone
        profile.Workex = workex
        profile.Place = place

        new_password = request.POST.get("password")
        confirm_password = request.POST.get("cpassword")
        if new_password:
            if new_password != confirm_password:
                messages.info(request, 'password not match')
                return render(request, 'owner/ownerprofileupdate.html', {'pl': profile})
            profile.Password = hash_password(new_password)

        profile.save()
        request.session['Name'] = profile.Name
        messages.info(request, "Profile updated")
        return redirect('PROFILE')

    return render(request, 'owner/ownerprofileupdate.html', {'pl': profile})


def ownerorder(request, pk=None):
    """Show all bookings/orders for the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    orders = cart.objects.filter(owner_id=request.session['id'])
    return render(request, 'owner/ownerorder.html', {'bk': orders})


def confirmpayment(request, pk):
    """Mark a booking's payment as confirmed by the owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        try:
            booking_id = positive_integer(pk, 'Booking')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return redirect('ownerorder', pk=request.session['id'])
        updated = cart.objects.filter(
            id=booking_id,
            owner_id=request.session['id'],
            Paystatus=True,
        ).update(Status=True)
        messages.info(
            request,
            'Payment confirmed' if updated else 'Paid booking was not found.',
        )
    return redirect('ownerorder', pk=request.session['id'])


def requests(request):
    """Show all service requests received by the owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    req = request_tb.objects.filter(owner_id=request.session['id'])
    return render(request, 'owner/requests.html', {'req': req})


def assign(request, bid):
    """Assign a service request to one of the owner's technicians."""
    guard = _owner_guard(request)
    if guard:
        return guard
    try:
        request_id = positive_integer(bid, 'Request')
    except ValidationError as exc:
        messages.info(request, exc.message)
        return redirect('requests')
    reqs = get_object_or_404(request_tb, id=request_id, owner_id=request.session['id'])
    options = addtech.objects.filter(owner_id=request.session['id'])

    if request.method == 'POST':
        try:
            tech_id = positive_integer(request.POST.get('tech'), 'Technician')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'owner/assign.html', {'reqs': reqs, 'options': options})
        technician = get_object_or_404(addtech, id=tech_id, owner_id=request.session['id'])
        Workassign.objects.create(
            Name=reqs.Name,
            Email=reqs.Email,
            Phonenumber=reqs.Phone,
            requestmssg=reqs.Subject,
            owner_id=request.session['id'],
            tech=technician,
            request=reqs,
        )
        messages.info(request, "Request assigned")
        return redirect('requests')

    return render(request, 'owner/assign.html', {'reqs': reqs, 'options': options})


def addtechnician(request):
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
            messages.info(request, exc.message)
            return render(request, 'owner/addtechnician.html')
        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. rahul@example.com)")
            return render(request, 'owner/addtechnician.html')
        if addtech.objects.filter(Email__iexact=email).exists():
            messages.info(request, "email already exists")
        else:
            addtech.objects.create(
                Name=name,
                Email=email,
                Phonenumber=phone,
                Workex=workex,
                Place=place,
                Qualification=qualification,
                Image=image,
                owner_id=request.session['id'],
            )
            messages.info(request, "Technician added. Send login mail to create a password.")
            return redirect('viewtechnician')

    return render(request, 'owner/addtechnician.html')


def viewtechnician(request):
    """Show all technicians under the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    technicians = addtech.objects.filter(owner_id=request.session['id'])
    return render(request, 'owner/viewtechnician.html', {'viewss': technicians})


def sendemail(request, id):
    """Generate a random password for a technician and email it to them."""
    guard = _owner_guard(request)
    if guard:
        return guard
    technician = get_object_or_404(addtech, id=id, owner_id=request.session['id'])

    if request.method == 'POST':
        recipient = technician.Email
        name = technician.Name

        characters = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(characters) for _ in range(12))

        subject = 'Hi, ' + name
        message = 'Welcome to Rent-a-Cube.\nYou can login with this password: ' + password
        try:
            send_mail(subject, message, settings.EMAIL_HOST_USER, [recipient], fail_silently=False)
            technician.Password = hash_password(password)
            technician.save(update_fields=['Password'])
            messages.info(request, "Login details sent")
        except Exception:
            messages.info(request, "Email could not be sent. Check email settings.")
        return redirect('viewtechnician')

    return render(request, 'owner/sentemail.html', {"owner": technician})


def owner_chat(request, uid):
    """Handle chat between owner and a specific user - send and display messages."""
    guard = _owner_guard(request)
    if guard:
        return guard

    try:
        user_id = positive_integer(uid, 'User')
    except ValidationError as exc:
        messages.info(request, exc.message)
        return redirect('chat')
    owner_id = request.session['id']
    owner = get_object_or_404(owner_tb, id=owner_id)
    user = get_object_or_404(user_tb, id=user_id)
    has_relationship = (
        cart.objects.filter(owner_id=owner_id, user_id=user.id).exists()
        or request_tb.objects.filter(owner_id=owner_id, user_id=user.id).exists()
        or Messages_Tb.objects.filter(
            Q(Send_id=str(owner_id), Receiver_id=str(user.id))
            | Q(Send_id=str(user.id), Receiver_id=str(owner_id))
        ).exists()
    )
    if not has_relationship:
        raise Http404('User is not available in this owner workspace.')

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message and len(message) <= 500:
            now = datetime.now()
            Messages_Tb.objects.create(
                Messages=message,
                Date=date.today(),
                Time=now.strftime("%H:%M:%S"),
                Send_id=str(owner_id),
                Receiver_id=str(user.id),
                Send_name=owner.Name,
                Receiver_name=user.Name,
            )
        elif len(message) > 500:
            messages.info(request, 'Messages must be 500 characters or fewer.')

    messages_qs = Messages_Tb.objects.filter(
        Q(Send_id=str(owner_id), Receiver_id=str(user.id))
        | Q(Send_id=str(user.id), Receiver_id=str(owner_id))
    ).order_by('Date', 'Time', 'id')

    return render(
        request,
        'owner/chating.html',
        {
            'message': messages_qs,
            'Name': owner.Name,
            'Rname': user.Name,
            'sid': owner_id,
            'Image': owner.Image,
            'Rimage': user.Image,
        },
    )


def chat(request):
    """Show chat inbox - list of users who have messaged this owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    today = date.today()
    owner_id = str(request.session['id'])
    msg = Messages_Tb.objects.filter(Receiver_id=owner_id)
    user_ids = {int(message.Send_id) for message in msg if str(message.Send_id).isdigit()}
    users = user_tb.objects.filter(id__in=user_ids)
    return render(request, 'owner/chat.html', {'data': users, 'date': today})


def refund(request):
    """Show all paid bookings eligible for refund."""
    guard = _owner_guard(request)
    if guard:
        return guard
    req = cart.objects.filter(owner_id=request.session['id'], Paystatus=True)
    return render(request, 'owner/refund.html', {'req': req})


def checkout(request, uid):
    """Process a refund through Razorpay for a paid booking."""
    guard = _owner_guard(request)
    if guard:
        return guard
    if request.method != "POST":
        return redirect('refund')

    client = _razorpay_client()
    if client is None:
        messages.info(request, "Razorpay keys are not configured")
        return redirect('refund')

    # Keep the booking locked while the provider call runs to prevent duplicate refunds.
    with transaction.atomic():
        booking = get_object_or_404(
            cart.objects.select_for_update(),
            id=uid,
            owner_id=request.session['id'],
            Paystatus=True,
            Refundstatus=False,
        )
        if not booking.RazorpayPaymentId:
            messages.info(request, "Refund is unavailable for this older booking because no Razorpay payment ID was saved.")
            return redirect('refund')
        amount_paise = int(booking.totalsum or booking.Price * booking.nohrs) * 100
        try:
            refund_response = client.payment.refund(
                booking.RazorpayPaymentId,
                {
                    "amount": amount_paise,
                    "speed": "normal",
                },
            )
        except Exception:
            messages.info(request, "Unable to process Razorpay refund")
            return redirect('refund')
        refund_tb.objects.update_or_create(
            booking=booking,
            defaults={
                'user': booking.user,
                'owner': booking.owner,
                'Price': amount_paise // 100,
                'Status': True,
            },
        )
        booking.Refundstatus = True
        booking.RazorpayRefundId = refund_response.get('id', '')
        booking.save(update_fields=['Refundstatus', 'RazorpayRefundId'])
    messages.info(request, "Refund processed")
    return redirect('refund')
