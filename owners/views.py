from config.pagination import render_page
from datetime import date

from accounts.payments import razorpay_client
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core import signing
from django.urls import reverse
from django.db import transaction, IntegrityError
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Message, Booking, Refund, ServiceRequest, Customer
from config.auth_utils import (
    hash_password,
    session_auth_hash,
    is_valid_email,
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)
from config.validation import (
    MAX_HOURLY_PRICE,
    positive_integer,
    required_text,
    validate_image_upload,
    validate_phone_number,
)
from .models import ServiceAssignment, Technician, Owner, Workspace


def _owner_guard(request):
    """Check if owner is logged in, redirect to login page if not."""
    return require_role(request, 'owner', 'owner_login')


def register(request):
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
            validate_password(password, Owner(name=name, email=email))
            image = request.FILES.get('image')
            proof = request.FILES.get('proof')
            validate_image_upload(image, 'Profile image')
            validate_image_upload(proof, 'Proof document')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/register.html')

        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. vikram@cowork.in)")
            return render(request, 'owners/register.html')

        if password != confirm_password:
            messages.info(request, 'password not match')
            return render(request, 'owners/register.html')

        if Owner.objects.filter(email__iexact=email).exists():
            messages.info(request, "email already exists")
        elif Owner.objects.filter(name=name).exists():
            messages.info(request, "user already exists")
        else:
            try:
                with transaction.atomic():
                    Owner.objects.create(
                        name=name,
                        email=email,
                        phone_number=phone,
                        place=place,
                        gender=gender,
                        password=hash_password(password),
                        image=image,
                        work_experience=workex,
                        proof_document=proof,
                    )
            except IntegrityError:
                messages.error(request, 'This email address is already registered.')
                return render(request, 'owners/register.html')
            messages.info(request, "Registration submitted. Please wait for admin approval.")
            return redirect('owner_login')

    return render(request, 'owners/register.html')


def sign_in(request):
    """Handle owner login - verify credentials and check admin approval."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        owner = Owner.objects.filter(email__iexact=email).first()

        if owner and password_matches(password, owner.password):
            if owner.accept and not owner.reject:
                upgrade_password_if_needed(owner, 'password', password)
                login_role(request, 'owner', owner, owner.name)
                return redirect('owner_dashboard')
            messages.info(request, "Account not approved")
        else:
            messages.info(request, 'Invalid owner')

    return render(request, 'owners/login.html')


def dashboard(request):
    """Display owner home/dashboard page."""
    guard = _owner_guard(request)
    if guard:
        return guard
    return render(request, 'owners/dashboard.html')


def workspace_create(request):
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
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/workspace_create.html')
        Workspace.objects.create(
            name=name,
            square_feet=sqft,
            state=state,
            city=city,
            location=location,
            hourly_rate=str(price),
            image=image,
            postal_code=pincode,
            workspace_type=workspace_type,
            amenities=facility,
            capacity=capability,
            owner_id=request.session['id'],
        )
        messages.info(request, "Workspace added")
        return redirect('owner_workspace_list')

    return render(request, 'owners/workspace_create.html')


def workspace_list(request):
    """Show all workspaces owned by the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    spaces = Workspace.objects.filter(owner_id=request.session['id'])
    return render_page(request, 'owners/workspace_list.html', 'Owvk', spaces)


def workspace_detail(request, workspace_id):
    """Show details of a specific workspace."""
    guard = _owner_guard(request)
    if guard:
        return guard
    work = get_object_or_404(Workspace, id=workspace_id, owner_id=request.session['id'])
    return render(request, 'owners/workspace_detail.html', {'Owvkd': work})


def workspace_edit(request, workspace_id):
    """Update an existing workspace listing."""
    guard = _owner_guard(request)
    if guard:
        return guard
    try:
        workspace_id = positive_integer(workspace_id, 'Workspace')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('owner_workspace_list')
    owner_work = get_object_or_404(Workspace, id=workspace_id, owner_id=request.session['id'])

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
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/workspace_edit.html', {'up': owner_work})
        if request.FILES.get("image"):
            owner_work.image = request.FILES["image"]
        owner_work.name = name
        owner_work.square_feet = sqft
        owner_work.state = state
        owner_work.city = city
        owner_work.location = location
        owner_work.hourly_rate = str(price)
        owner_work.postal_code = pincode
        owner_work.workspace_type = workspace_type
        owner_work.amenities = facility
        owner_work.capacity = capability
        owner_work.save()
        messages.info(request, "Workspace updated")
        return redirect('owner_workspace_list')

    return render(request, 'owners/workspace_edit.html', {'up': owner_work})


def workspace_delete(request, workspace_id):
    """Delete an unused listing while preserving booking history and shared photos."""
    guard = _owner_guard(request)
    if guard:
        return guard
    work = get_object_or_404(Workspace, id=workspace_id, owner_id=request.session['id'])

    if request.method == "POST":
        if work.bookings.exists():
            messages.error(request, 'This workspace has booking history. It cannot be deleted.')
            return redirect('owner_workspace_list')
        try:
            work.delete()
        except ProtectedError:
            messages.error(request, 'A booking now references this workspace. It cannot be deleted.')
            return redirect('owner_workspace_list')
        messages.info(request, "Workspace deleted")
        return redirect('owner_workspace_list')

    return render(request, 'owners/workspace_delete_confirm.html', {'delete': work})


def profile(request):
    """Display the owner's profile page."""
    guard = _owner_guard(request)
    if guard:
        return guard
    profile = get_object_or_404(Owner, id=request.session['id'])
    return render(request, 'owners/profile.html', {'prof': profile})


def profile_edit(request, profile_id=None):
    """Update owner profile - name, email, phone, password, image."""
    guard = _owner_guard(request)
    if guard:
        return guard
    profile = get_object_or_404(Owner, id=request.session['id'])

    if profile_id:
        try:
            profile_id = positive_integer(profile_id, 'Profile')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return redirect('owner_profile')
        if profile_id != profile.id:
            messages.info(request, "You can update only your own profile")
            return redirect('owner_profile')

    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            new_email = normalize_email(
                required_text(request.POST, 'email', 'Email address', max_length=50)
            )
            if not is_valid_email(new_email):
                raise ValidationError('Please enter a valid email address.')
            if (new_email != profile.email or request.POST.get('password')) and not password_matches(request.POST.get('current_password', ''), profile.password):
                raise ValidationError('Enter your current password to change your email or password.')
            phone = validate_phone_number(request.POST.get('phonenumber'))
            workex = required_text(request.POST, 'workex', 'Work experience', max_length=25)
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            if request.FILES.get('image'):
                validate_image_upload(request.FILES['image'], 'Profile image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'owners/profile_edit.html', {'pl': profile})
        if Owner.objects.exclude(id=profile.id).filter(email=new_email).exists():
            messages.info(request, "email already exists")
            return render(request, 'owners/profile_edit.html', {'pl': profile})

        if request.FILES.get("image"):
            profile.image = request.FILES["image"]

        profile.name = name
        profile.email = new_email
        profile.phone_number = phone
        profile.work_experience = workex
        profile.place = place

        new_password = request.POST.get("password")
        confirm_password = request.POST.get("cpassword")
        if new_password:
            if new_password != confirm_password:
                messages.info(request, 'password not match')
                return render(request, 'owners/profile_edit.html', {'pl': profile})
            try:
                validate_password(new_password, profile)
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages))
                return render(request, 'owners/profile_edit.html', {'pl': profile})
            profile.password = hash_password(new_password)

        try:
            with transaction.atomic():
                profile.save()
        except IntegrityError:
            messages.error(request, 'This email address is already registered.')
            return render(request, 'owners/profile_edit.html', {'pl': profile})
        request.session.cycle_key()
        request.session['auth_hash'] = session_auth_hash(profile)
        request.session['Name'] = profile.name
        messages.info(request, "Profile updated")
        return redirect('owner_profile')

    return render(request, 'owners/profile_edit.html', {'pl': profile})


def booking_list(request, pk=None):
    """Show all bookings/orders for the logged-in owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    orders = Booking.objects.select_related('user', 'owner').filter(owner_id=request.session['id'])
    return render_page(request, 'owners/booking_list.html', 'bk', orders)


def confirm_payment(request, pk):
    """Mark a booking's payment as confirmed by the owner."""
    guard = _owner_guard(request)
    if guard:
        return guard
    if request.method == "POST":
        try:
            booking_id = positive_integer(pk, 'Booking')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return redirect('owner_booking_list', pk=request.session['id'])
        updated = Booking.objects.filter(
            id=booking_id,
            owner_id=request.session['id'],
            is_paid=True, is_refunded=False, payment_review_required=False,
        ).update(is_confirmed=True)
        messages.info(
            request,
            'Payment confirmed' if updated else 'Paid booking was not found.',
        )
    return redirect('owner_booking_list', pk=request.session['id'])


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

        if not settings.DEBUG and settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
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
            now = timezone.localtime()
            Message.objects.create(
                body=message,
                date=now.date(),
                customer=user, owner=owner, sender_role='owner',
                time=now.strftime("%H:%M:%S"),
                sender_id=str(owner_id),
                receiver_id=str(user.id),
                sender_name=owner.name,
                receiver_name=user.name,
            )
        elif len(message) > 500:
            messages.info(request, 'Messages must be 500 characters or fewer.')

    messages_qs = list(reversed(Message.objects.filter(customer=user, owner=owner).order_by('-id')[:200]))

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


def refund_list(request):
    """Show all paid bookings eligible for refund."""
    guard = _owner_guard(request)
    if guard:
        return guard
    req = Booking.objects.select_related('user').filter(owner_id=request.session['id'], is_paid=True)
    return render_page(request, 'owners/refund_list.html', 'req', req)


def process_refund(request, booking_id):
    """Persist a refund intent before the external call; uncertain outcomes need reconciliation."""
    guard = _owner_guard(request)
    if guard:
        return guard
    if request.method != 'POST':
        return redirect('owner_refund_list')
    client = razorpay_client()
    with transaction.atomic():
        booking = get_object_or_404(Booking.objects.select_for_update(), pk=booking_id,
                                    owner_id=request.session['id'], is_paid=True)
        if booking.is_refunded or booking.refund_state != 'none':
            messages.info(request, 'This refund is already processed or awaiting reconciliation. Do not submit another refund.')
            return redirect('owner_refund_list')
        demo = booking.payment_mode == 'demo' or booking.razorpay_payment_id.startswith('demo_pay_')
        if demo and not (settings.DEBUG and settings.ALLOW_DEMO_PAYMENTS):
            messages.error(request, 'Demo refunds are disabled.')
            return redirect('owner_refund_list')
        if not demo and (not client or not booking.razorpay_payment_id or booking.total_amount <= 0):
            messages.error(request, 'This payment cannot be refunded automatically. Contact support.')
            return redirect('owner_refund_list')
        booking.refund_state = 'pending'
        booking.save(update_fields=['refund_state'])
    try:
        result = ({'id': f'demo_refund_{booking.pk}', 'status': 'processed'} if demo else
                  client.payment.refund(booking.razorpay_payment_id, {
                      'amount': booking.total_amount * 100, 'speed': 'normal',
                      'notes': {'booking_id': str(booking.pk)},
                  }))
        if not result.get('id'):
            raise ValueError('Refund reference missing')
    except Exception:
        Booking.objects.filter(pk=booking.pk).update(refund_state='review')
        messages.error(request, 'Refund outcome is uncertain. Support must reconcile it with Razorpay before any retry.')
        return redirect('owner_refund_list')
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking.pk)
        processed = result.get('status') == 'processed'
        Refund.objects.update_or_create(booking=booking, defaults={
            'user': booking.user, 'owner': booking.owner,
            'amount': booking.total_amount, 'is_processed': processed,
        })
        booking.is_refunded = processed
        booking.refund_state = 'processed' if processed else 'pending'
        booking.razorpay_refund_id = result['id']
        booking.save(update_fields=['is_refunded', 'refund_state', 'razorpay_refund_id'])
    messages.info(request, 'Refund processed.' if processed else 'Refund submitted; awaiting provider confirmation.')
    return redirect('owner_refund_list')
