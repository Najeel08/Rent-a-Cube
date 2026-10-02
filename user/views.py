from datetime import date, datetime

import razorpay
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from owners.models import owner_tb, owvaddwork
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
    positive_integer,
    required_text,
    validate_image_upload,
    validate_phone_number,
)
from .models import Messages_Tb, cart, request_tb, user_tb


def _user_guard(request):
    """Check if user is logged in, redirect to login page if not."""
    return require_role(request, 'user', 'ulog')


def _razorpay_client():
    """Create and return a Razorpay client using API keys from settings."""
    if not settings.RAZORPAY_API_KEY or not settings.RAZORPAY_API_SECRET_KEY:
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY))


def ureg(request):
    """Handle user registration - validate input and create new user."""
    if request.method == "POST":
        try:
            name = required_text(request.POST, 'name', 'Name', max_length=20)
            email = normalize_email(required_text(request.POST, 'email', 'Email address', max_length=50))
            phone = validate_phone_number(request.POST.get('phone'))
            place = required_text(request.POST, 'place', 'Place', max_length=50)
            password = required_text(request.POST, 'password', 'Password')
            confirm_password = required_text(request.POST, 'cpassword', 'Password confirmation')
            image = request.FILES.get('image')
            validate_image_upload(image, 'Profile image')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'user/ureg.html')

        # Validate standard email format
        if not is_valid_email(email):
            messages.info(request, "Please enter a valid email address (e.g. alex@company.com)")
            return render(request, 'user/ureg.html')

        # Check if passwords match
        if password != confirm_password:
            messages.info(request, 'password not match')
            return render(request, 'user/ureg.html')

        # Check for duplicate email or username
        if user_tb.objects.filter(Email__iexact=email).exists():
            messages.info(request, "email already exists")
        elif user_tb.objects.filter(Name=name).exists():
            messages.info(request, "user already exists")
        else:
            # Create new user with hashed password
            user_tb.objects.create(
                Name=name,
                Email=email,
                Phonenumber=phone,
                Place=place,
                Password=hash_password(password),
                Image=image,
            )
            messages.info(request, "Registration successful. Please login.")
            return redirect('ulog')

    return render(request, 'user/ureg.html')


def ulog(request):
    """Handle user login - verify credentials and start session."""
    if request.method == "POST":
        email = normalize_email(request.POST.get('email', ''))
        password = request.POST.get('password', '')
        user = user_tb.objects.filter(Email__iexact=email).first()

        if user and password_matches(password, user.Password):
            # Auto-upgrade plaintext password to hashed if needed
            upgrade_password_if_needed(user, 'Password', password)
            login_role(request, 'user', user, user.Name)
            return redirect('uhome')
        messages.info(request, 'Invalid User')

    return render(request, 'user/ulog.html')


def uhome(request):
    """Display user home/dashboard page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return render(request, 'user/uhome.html')


def uviewwork(request):
    """Show all available workspaces from approved owners."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = owvaddwork.objects.filter(owner__accept=True)
    return render(request, 'user/uviewwork.html', {'Uwvk': workspaces})


def uworkdetails(request):
    """Display workspace details page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return render(request, 'user/uworkdetails.html')


def uvieworder(request, pk=None):
    """Show all orders/bookings for the logged-in user."""
    guard = _user_guard(request)
    if guard:
        return guard
    orders = cart.objects.filter(user_id=request.session['id'])
    return render(request, 'user/uvieworder.html', {'bk': orders})


def uviewcart(request):
    """Show unpaid cart items with calculated totals."""
    guard = _user_guard(request)
    if guard:
        return guard
    items = cart.objects.filter(user_id=request.session['id'], Paystatus=False)
    # Calculate line total for each item and overall total
    total = 0
    for item in items:
        item.line_total = item.Price * item.nohrs
        total += item.line_total
    return render(request, 'user/uviewcart.html', {'book_obj': items, 'sum': total})


def booking(request):
    """Display booking page."""
    guard = _user_guard(request)
    if guard:
        return guard
    return render(request, 'user/booking')


def selectownercart(request):
    """Show list of owners whose workspaces are in the user's cart."""
    guard = _user_guard(request)
    if guard:
        return guard
    # Get distinct owners who have unpaid items in user's cart
    owners = owner_tb.objects.filter(
        cart__user_id=request.session['id'],
        cart__Paystatus=False,
    ).distinct()
    return render(request, "user/selectownercart.html", {"owner_gen": owners})


def cartdetails(request, pk):
    """Show cart items for a specific owner with total price."""
    guard = _user_guard(request)
    if guard:
        return guard
    owner = get_object_or_404(owner_tb, id=pk)
    cart_items = cart.objects.filter(
        owner_id=owner.id,
        user_id=request.session['id'],
        Paystatus=False,
    )
    # Keep the provider total for display while retaining the true amount per item.
    total = sum(item.Price * item.nohrs for item in cart_items)
    for item in cart_items:
        item.line_total = item.Price * item.nohrs
    return render(
        request,
        'user/cartdetails.html',
        {'book_obj': cart_items, 'sum': total, 'owner': owner.Name, 'ownerid': owner.id},
    )


def checkout(request, aid):
    """Create a Razorpay order and show payment page."""
    guard = _user_guard(request)
    if guard:
        return guard
    booking_item = get_object_or_404(cart, id=aid, user_id=request.session['id'])
    if booking_item.Paystatus:
        messages.info(request, 'This booking has already been paid.')
        return redirect('uvieworder', pk=request.session['id'])

    # Initialize Razorpay client
    client = _razorpay_client()
    if client is None:
        messages.info(request, "Razorpay keys are not configured")
        return redirect('cartdetails', pk=booking_item.owner_id)

    # Calculate total amount in paise (1 INR = 100 paise)
    total = booking_item.Price * booking_item.nohrs
    amount_paise = int(total) * 100

    # Create Razorpay order
    try:
        payment_order = client.order.create(
            dict(amount=amount_paise, currency="INR", payment_capture=1)
        )
    except Exception:
        messages.info(request, "Unable to create Razorpay order")
        return redirect('cartdetails', pk=booking_item.owner_id)

    # Store order details in session to verify the payment callback later
    request.session[f'booking_payment_{booking_item.id}'] = {
        'order_id': payment_order['id'],
        'amount_paise': amount_paise,
    }

    return render(
        request,
        "user/checkout.html",
        {
            'a': total,
            'amount_paise': amount_paise,
            'api_key': settings.RAZORPAY_API_KEY,
            'order_id': payment_order['id'],
            'booking_id': booking_item.id,
            'owner_id': booking_item.owner_id,
        },
    )


def payment_success(request, aid):
    """Verify Razorpay payment and mark booking as paid."""
    guard = _user_guard(request)
    if guard:
        return guard
    booking_item = get_object_or_404(cart, id=aid, user_id=request.session['id'])

    if request.method != "POST":
        return redirect('cartdetails', pk=booking_item.owner_id)

    if booking_item.Paystatus:
        messages.info(request, 'This booking has already been paid.')
        return redirect('uvieworder', pk=request.session['id'])

    # Verify the posted order ID matches the one we stored during checkout
    session_key = f'booking_payment_{booking_item.id}'
    pending_payment = request.session.get(session_key)
    posted_order_id = request.POST.get('razorpay_order_id')

    if not pending_payment or pending_payment.get('order_id') != posted_order_id:
        messages.info(request, "Payment session could not be verified")
        return redirect('cartdetails', pk=booking_item.owner_id)

    client = _razorpay_client()
    if client is None:
        messages.info(request, "Razorpay keys are not configured")
        return redirect('cartdetails', pk=booking_item.owner_id)

    # Collect payment data from Razorpay callback
    payment_data = {
        'razorpay_order_id': posted_order_id,
        'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
        'razorpay_signature': request.POST.get('razorpay_signature'),
    }

    # Verify Razorpay signature to confirm payment is genuine
    try:
        client.utility.verify_payment_signature(payment_data)
    except Exception:
        messages.info(request, "Payment verification failed")
        return redirect('cartdetails', pk=booking_item.owner_id)

    # Persist payment state atomically so a duplicate callback cannot charge the same booking twice.
    with transaction.atomic():
        booking_item = cart.objects.select_for_update().get(id=aid, user_id=request.session['id'])
        if booking_item.Paystatus:
            messages.info(request, 'This booking has already been paid.')
            return redirect('uvieworder', pk=request.session['id'])
        booking_item.Paystatus = True
        booking_item.totalsum = pending_payment['amount_paise'] // 100
        booking_item.RazorpayOrderId = payment_data['razorpay_order_id']
        booking_item.RazorpayPaymentId = payment_data['razorpay_payment_id']
        booking_item.RazorpaySignature = payment_data['razorpay_signature']
        booking_item.save(
            update_fields=[
                'Paystatus',
                'totalsum',
                'RazorpayOrderId',
                'RazorpayPaymentId',
                'RazorpaySignature',
            ]
        )

    # Clear payment session data after successful payment
    request.session.pop(session_key, None)
    messages.info(request, "Payment completed")
    return redirect('uvieworder', pk=request.session['id'])


def cart_del(request, pk):
    """Delete a cart item after confirmation."""
    guard = _user_guard(request)
    if guard:
        return guard
    cart_item = get_object_or_404(cart, id=pk, user_id=request.session['id'])
    owner_id = cart_item.owner_id
    if request.method == "POST":
        cart_item.delete()
        messages.info(request, "Cart item deleted")
        return redirect("cartdetails", pk=owner_id)
    return render(request, 'user/cart_del.html', {'carte': cart_item})


def showworkspace1(request):
    """Show all workspaces with optional city search filter."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = owvaddwork.objects.filter(owner__accept=True)
    # Filter by city if user submitted search form
    if request.method == "POST":
        city = request.POST.get('city', '').strip()
        workspaces = workspaces.filter(City__icontains=city)
    return render(request, 'user/showworkspace1.html', {'Up': workspaces})


def uviewownerwork(request, pi):
    """Show workspace details and allow user to add it to cart."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspace = get_object_or_404(owvaddwork, id=pi, owner__accept=True)

    if request.method == "POST":
        try:
            hours = positive_integer(request.POST.get('nohrs'), 'Number of hours')
            booking_date = required_text(request.POST, 'date', 'Booking date', max_length=100)
            price = positive_integer(workspace.Price, 'Workspace price')
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, "user/uviewownerwork.html", {'owr': [workspace]})

        # Add workspace to cart
        cart.objects.create(
            WsName=workspace.Name,
            Price=price,
            Location=workspace.Location,
            user_id=request.session['id'],
            owner_id=workspace.owner_id,
            Image=workspace.Image.name,
            nohrs=hours,
            Date=booking_date,
        )
        messages.info(request, "Workspace added to cart")
        return redirect("selectownercart")

    return render(request, "user/uviewownerwork.html", {'owr': [workspace]})


def uviewownerprof(request, id):
    """Show an owner's public profile."""
    guard = _user_guard(request)
    if guard:
        return guard
    owner = get_object_or_404(owner_tb, id=id, accept=True)
    return render(request, 'user/uviewownerprof.html', {'uviewprof': owner})


def showworkspace(request, jk):
    """Show all workspaces belonging to a specific owner."""
    guard = _user_guard(request)
    if guard:
        return guard
    workspaces = owvaddwork.objects.filter(owner_id=jk, owner__accept=True)
    return render(request, "user/showworkspace1.html", {'Up': workspaces})


def send_request(request):
    """Send a service/maintenance request to an owner."""
    guard = _user_guard(request)
    if guard:
        return guard
    owners = owner_tb.objects.filter(accept=True)

    if request.method == "POST":
        try:
            owner_id = positive_integer(request.POST.get('wid'), 'Workspace provider')
            subject = required_text(request.POST, 'subject', 'Request details', max_length=200)
        except ValidationError as exc:
            messages.info(request, exc.message)
            return render(request, 'user/request.html', {'own': owners})
        current_user = get_object_or_404(user_tb, id=request.session['id'])
        owner = get_object_or_404(owner_tb, id=owner_id, accept=True)
        request_tb.objects.create(
            Name=current_user.Name,
            Phone=current_user.Phonenumber,
            Email=current_user.Email,
            Subject=subject,
            user=current_user,
            owner=owner,
        )
        messages.info(request, "Request sent")
        return redirect('viewrequest')

    return render(request, 'user/request.html', {'own': owners})


def viewrequest(request):
    """Show all requests sent by the logged-in user."""
    guard = _user_guard(request)
    if guard:
        return guard
    user_requests = request_tb.objects.filter(user_id=request.session['id'])
    return render(request, 'user/viewrequest.html', {'Usrq': user_requests})


def User_chat(request, aid):
    """Handle chat between user and owner - send and display messages."""
    guard = _user_guard(request)
    if guard:
        return guard

    user_id = request.session['id']
    user = get_object_or_404(user_tb, id=user_id)
    owner = get_object_or_404(owner_tb, id=aid, accept=True)

    # Save new message if user submitted the chat form
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if message and len(message) <= 500:
            now = datetime.now()
            Messages_Tb.objects.create(
                Messages=message,
                Date=date.today(),
                Time=now.strftime("%H:%M:%S"),
                Send_id=str(user_id),
                Receiver_id=str(owner.id),
                Send_name=user.Name,
                Receiver_name=owner.Name,
            )
        elif len(message) > 500:
            messages.info(request, 'Messages must be 500 characters or fewer.')

    # Fetch all messages between this user and owner (both directions)
    messages_qs = Messages_Tb.objects.filter(
        Q(Send_id=str(user_id), Receiver_id=str(owner.id))
        | Q(Send_id=str(owner.id), Receiver_id=str(user_id))
    ).order_by('Date', 'Time', 'id')

    return render(
        request,
        'user/chat.html',
        {
            'message': messages_qs,
            'Name': user.Name,
            'Rname': owner.Name,
            'sid': user_id,
            'Image': user.Image,
            'Rimage': owner.Image,
        },
    )
