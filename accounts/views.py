from config.pagination import render_page
from datetime import timedelta
import secrets

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from .reservations import interval, has_conflict
from .payments import payment_matches, razorpay_client, record_payment
from django.shortcuts import get_object_or_404, redirect, render

from owners.models import Owner, Workspace
from config.auth_utils import (
    hash_password,
    is_valid_email,
    login_role,
    normalize_email,
    password_matches,
    require_role,
    upgrade_password_if_needed,
)
from config.validation import (
    MAX_BOOKING_DURATION_HOURS,
    MAX_HOURLY_PRICE,
    positive_integer,
    required_text,
    validate_booking_date,
    validate_booking_start_time,
    validate_image_upload,
    validate_phone_number,
)
from .models import Message, Booking, ServiceRequest, Customer


def _user_guard(request):
    """Check if user is logged in, redirect to login page if not."""
    return require_role(request, 'user', 'login')


def register(request):
    """Handle user registration - validate input and create new user."""
    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=50))
            phone = validate_phone_number(request.POST.get('phone'))
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            password = required_text(request.POST, 'password', 'Password')
            confirm_password = required_text(request.POST, 'cpassword', 'Password confirmation')
            validate_password(password, Customer(name=name, email=email))
            image = request.FILES.get('image')
            validate_image_upload(image, 'Profile image')
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, 'accounts/register.html')

        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. alex@company.com)")
            return render(request, 'accounts/register.html')

        if password != confirm_password:
            messages.info(request, 'password not match')
            return render(request, 'accounts/register.html')

        if Customer.objects.filter(email__iexact=email).exists():
            messages.info(request, "email already exists")
        elif Customer.objects.filter(name=name).exists():
            messages.info(request, "user already exists")
        else:
            try:
                with transaction.atomic():
                    Customer.objects.create(
                        name=name,
                        email=email,
                        phone_number=phone,
                        place=place,
                        password=hash_password(password),
                        image=image,
                    )
            except IntegrityError:
                messages.error(request, 'This email address is already registered.')
                return render(request, 'accounts/register.html')
            messages.info(request, "Registration successful. Please login.")
            return redirect('login')

    return render(request, 'accounts/register.html')


def sign_in(request):
    """Handle user login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        user = Customer.objects.filter(email__iexact=email).first()

        if password_matches(password, user.password if user else None) and user:
            upgrade_password_if_needed(user, 'password', password)
            login_role(request, 'user', user, user.name)
            return redirect('dashboard')
        messages.info(request, 'Invalid User')

    return render(request, 'accounts/login.html')


def dashboard(request):
    """Display user home/dashboard page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return render(request, 'accounts/dashboard.html')


def workspace_list(request):
    """Show all available workspaces from approved owners."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = Workspace.objects.filter(owner__accept=True, owner__reject=False).select_related('owner')
    return render_page(request, 'accounts/workspace_list.html', 'Uwvk', workspaces)


def workspace_overview(request):
    """Display workspace details page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return redirect('workspace_search')


def booking_list(request, pk=None):
    """Show all orders/bookings for the logged-in user."""
    guard = _user_guard(request)
    if guard:
        return guard
    orders = Booking.objects.select_related('user', 'owner').filter(
        user_id=request.session['id'],
        is_paid=True,
    ).select_related('owner')
    return render_page(request, 'accounts/booking_list.html', 'bk', orders)


def cart_list(request):
    """Show unpaid cart items with calculated totals."""
    guard = _user_guard(request)
    if guard:
        return guard
    items = Booking.objects.filter(user_id=request.session['id'], is_paid=False)
    total = 0
    for item in items:
        item.line_total = item.hourly_rate * item.duration_hours
        total += item.line_total
    return render(request, 'accounts/cart_list.html', {'book_obj': items, 'sum': total})


def cart_owner_list(request):
    """Show list of owners whose workspaces are in the user's cart."""
    guard = _user_guard(request)
    if guard:
        return guard
    owners = Owner.objects.filter(
        booking__user_id=request.session['id'],
        booking__is_paid=False,
    ).distinct()
    return render(request, "accounts/cart_owner_list.html", {"owner_gen": owners})


def cart_detail(request, pk):
    """Show cart items for a specific owner with total price."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        owner_id = positive_integer(pk, 'Workspace provider')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('cart_owner_list')
    owner = get_object_or_404(Owner, id=owner_id)
    cart_items = Booking.objects.filter(
        owner_id=owner.id,
        user_id=request.session['id'],
        is_paid=False,
    )
    # Keep the provider total for display while retaining the true amount per item.
    total = sum(item.hourly_rate * item.duration_hours for item in cart_items)
    for item in cart_items:
        item.line_total = item.hourly_rate * item.duration_hours
    return render(
        request,
        'accounts/cart_detail.html',
        {'book_obj': cart_items, 'sum': total, 'owner': owner.name, 'ownerid': owner.id},
    )


def checkout(request, booking_id):
    """Reserve a short checkout window and persist the server-calculated order."""
    guard = _user_guard(request)
    if guard:
        return guard
    client = razorpay_client()
    demo = client is None
    if demo and not (settings.DEBUG and settings.ALLOW_DEMO_PAYMENTS):
        messages.error(request, 'Payments are unavailable. Please contact support.')
        return redirect('cart_list')
    with transaction.atomic():
        item = get_object_or_404(Booking.objects.select_for_update(), pk=booking_id, user_id=request.session['id'])
        if item.is_paid:
            return redirect('booking_list', pk=request.session['id'])
        if request.method != 'POST':
            # GET is safe: no provider order or reservation is created by links/prefetch.
            return render(request, 'accounts/checkout_start.html', {'booking': item})
        try:
            start, _ = interval(item)
            workspace = Workspace.objects.select_for_update().select_related('owner').get(pk=item.workspace_id)
            if start <= timezone.now():
                raise ValidationError('This booking start time has passed. Add a new time to your cart.')
            if not workspace.owner.accept or workspace.owner.reject:
                raise ValidationError('This workspace is no longer available.')
            if has_conflict(item):
                raise ValidationError('This workspace is reserved for the selected time. Choose another time.')
            positive_integer(item.hourly_rate, 'Hourly price', MAX_HOURLY_PRICE)
        except (ValidationError, Workspace.DoesNotExist) as exc:
            messages.error(request, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Workspace unavailable.')
            return redirect('cart_detail', pk=item.owner_id)
        mode = 'demo' if demo else 'razorpay'
        if item.razorpay_order_id and item.payment_mode != mode:
            messages.error(request, 'Payment configuration changed. Contact support before retrying this order.')
            return redirect('cart_detail', pk=item.owner_id)
        if not item.razorpay_order_id:
            total = item.hourly_rate * item.duration_hours
            try:
                order_id = (f'demo_order_{secrets.token_hex(12)}' if demo else client.order.create({
                    'amount': total * 100, 'currency': 'INR', 'receipt': f'booking-{item.pk}',
                })['id'])
            except Exception:
                messages.error(request, 'Unable to start payment. Please try again.')
                return redirect('cart_detail', pk=item.owner_id)
            item.razorpay_order_id = order_id
            item.total_amount = total
            item.payment_mode = mode
        # Do not extend a live hold on refresh; an expired hold can be reacquired
        # only after the conflict check above. The same provider order is reused.
        if not item.checkout_expires_at or item.checkout_expires_at <= timezone.now():
            item.checkout_expires_at = timezone.now() + timedelta(minutes=settings.BOOKING_HOLD_MINUTES)
        item.save(update_fields=['razorpay_order_id', 'total_amount', 'payment_mode', 'checkout_expires_at'])
    return render(request, 'accounts/checkout.html', {
        'a': item.total_amount, 'amount_paise': item.total_amount * 100,
        'api_key': settings.RAZORPAY_API_KEY, 'order_id': item.razorpay_order_id,
        'booking_id': item.pk, 'owner_id': item.owner_id, 'booking': item,
        'demo_payment': demo,
    })

def payment_complete(request, booking_id):
    """Verify captured funds against a durable order; retain late payments for review."""
    guard = _user_guard(request)
    if guard:
        return guard
    item = get_object_or_404(Booking, pk=booking_id, user_id=request.session['id'])
    if request.method != 'POST':
        return redirect('cart_detail', pk=item.owner_id)
    if item.is_paid:
        return redirect('booking_list', pk=request.session['id'])
    order_id = request.POST.get('razorpay_order_id', '')
    if not order_id or order_id != item.razorpay_order_id:
        messages.error(request, 'Payment order could not be verified.')
        return redirect('cart_detail', pk=item.owner_id)
    if item.payment_mode == 'demo':
        if not (settings.DEBUG and settings.ALLOW_DEMO_PAYMENTS and request.POST.get('demo_payment') == '1'):
            messages.error(request, 'Demo payment is unavailable.')
            return redirect('cart_detail', pk=item.owner_id)
        payment_id, signature = f'demo_pay_{secrets.token_hex(12)}', 'demo_local_payment'
    else:
        payment_id = request.POST.get('razorpay_payment_id', '')
        signature = request.POST.get('razorpay_signature', '')
        client = razorpay_client()
        try:
            if not client or not payment_id or len(payment_id) > 100 or len(signature) > 200:
                raise ValueError('Missing payment verification data')
            client.utility.verify_payment_signature({
                'razorpay_order_id': item.razorpay_order_id,
                'razorpay_payment_id': payment_id, 'razorpay_signature': signature,
            })
            payment = client.payment.fetch(payment_id)
            if not payment_matches(item, payment):
                raise ValueError('Payment is not captured for this order and amount')
        except Exception:
            messages.error(request, 'Payment is not verified as captured. Retry verification or contact support; do not pay again.')
            return redirect('cart_detail', pk=item.owner_id)
    try:
        item = record_payment(item.pk, payment_id, signature)
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
        return redirect('cart_detail', pk=item.owner_id)
    except IntegrityError:
        messages.error(request, 'This payment reference is already recorded. Contact support.')
        return redirect('cart_detail', pk=item.owner_id)
    if item.payment_review_required:
        messages.warning(request, 'Payment received, but the time could not be reserved. Contact the provider for a refund. Your payment reference is saved.')
    else:
        messages.success(request, f'Payment successful. Transaction ID: {payment_id}. Your booking is reserved.')
    return redirect('booking_list', pk=request.session['id'])

def cart_remove(request, pk):
    """Delete a cart item after confirmation."""
    guard = _user_guard(request)
    if guard:
        return guard
    cart_item = get_object_or_404(Booking, id=pk, user_id=request.session['id'], is_paid=False)
    owner_id = cart_item.owner_id
    if cart_item.razorpay_order_id:
        messages.error(request, 'An order has been started for this cart item. Contact support to reconcile it before removal.')
        return redirect('cart_detail', pk=owner_id)
    if request.method == "POST":
        cart_item.delete()
        messages.info(request, "Cart item deleted")
        return redirect('cart_detail', pk=owner_id)
    return render(request, 'accounts/cart_delete_confirm.html', {'carte': cart_item})


def workspace_search(request):
    """Show all workspaces with optional city search filter."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = Workspace.objects.filter(owner__accept=True, owner__reject=False).select_related('owner')
    city = (request.POST if request.method == 'POST' else request.GET).get('city', '').strip()[:50]
    if city:
        workspaces = workspaces.filter(city__icontains=city)
    return render_page(request, 'accounts/workspace_search_results.html', 'Up', workspaces)


@transaction.atomic
def workspace_book(request, workspace_id):
    """Show workspace details and allow user to add it to cart."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        workspace_id = positive_integer(workspace_id, 'Workspace')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('workspace_search')
    workspace = get_object_or_404(Workspace.objects.select_for_update(), id=workspace_id, owner__accept=True, owner__reject=False)

    if request.method == "POST":
        try:
            hours = positive_integer(
                request.POST.get('nohrs'),
                'Number of hours',
                MAX_BOOKING_DURATION_HOURS,
            )
            booking_date = validate_booking_date(request.POST.get('date'))
            start_time = validate_booking_start_time(request.POST.get('start_time'))
            price = positive_integer(workspace.hourly_rate, 'Workspace price', MAX_HOURLY_PRICE)
        except ValidationError as exc:
            messages.info(request, '; '.join(exc.messages))
            return render(request, "accounts/workspace_booking_form.html", {'owr': [workspace]})

        if Booking.objects.filter(
            user_id=request.session['id'],
            workspace=workspace,
            date=booking_date,
            start_time=start_time,
            is_refunded=False,
            payment_review_required=False,
        ).exists():
            messages.info(request, 'This reservation is already in your cart.')
            return render(request, "accounts/workspace_booking_form.html", {'owr': [workspace]})

        candidate = Booking(workspace=workspace, date=booking_date, start_time=start_time, duration_hours=hours)
        if interval(candidate)[0] <= timezone.now():
            messages.error(request, 'Booking start time must be in the future.')
            return render(request, 'accounts/workspace_booking_form.html', {'owr': [workspace]})
        if has_conflict(candidate):
            messages.error(request, 'This workspace is reserved for the selected time.')
            return render(request, 'accounts/workspace_booking_form.html', {'owr': [workspace]})

        Booking.objects.create(
            workspace_name=workspace.name,
            hourly_rate=price,
            location=workspace.location,
            user_id=request.session['id'],
            owner_id=workspace.owner_id,
            image=workspace.image.name,
            duration_hours=hours,
            total_amount=price * hours,
            date=booking_date,
            start_time=start_time,
            workspace=workspace,
        )
        messages.info(request, "Workspace added to cart")
        return redirect('cart_owner_list')

    return render(request, "accounts/workspace_booking_form.html", {'owr': [workspace]})


def owner_public_profile(request, owner_id):
    """Show an owner's public profile."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        owner_id = positive_integer(owner_id, 'Workspace provider')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('workspace_search')
    owner = get_object_or_404(Owner, id=owner_id, accept=True, reject=False)
    return render(request, 'accounts/owner_profile.html', {'uviewprof': owner})


def owner_workspace_catalog(request, owner_id):
    """Show all workspaces belonging to a specific owner."""
    guard = _user_guard(request)
    if guard:
        return guard
    try:
        owner_id = positive_integer(owner_id, 'Workspace provider')
    except ValidationError as exc:
        messages.info(request, '; '.join(exc.messages))
        return redirect('workspace_search')
    workspaces = Workspace.objects.filter(owner_id=owner_id, owner__accept=True)
    return render_page(request, "accounts/workspace_search_results.html", 'Up', workspaces)


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
            now = timezone.localtime()
            Message.objects.create(
                body=message,
                date=now.date(),
                customer=user, owner=owner, sender_role='user',
                time=now.strftime("%H:%M:%S"),
                sender_id=str(user_id),
                receiver_id=str(owner.id),
                sender_name=user.name,
                receiver_name=owner.name,
            )
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
