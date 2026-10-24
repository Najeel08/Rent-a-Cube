"""Customer cart, booking, checkout and payment views."""
from datetime import timedelta
import secrets

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.pagination import render_page
from config.validation import MAX_HOURLY_PRICE, positive_integer
from owners.models import Owner, Workspace

from ..models import Booking
from ..payments import payment_matches, razorpay_client, record_payment
from ..reservations import has_conflict, interval
from .auth import _user_guard


def booking_list(request, pk=None):
    """Show all orders/bookings for the logged-in user."""
    guard = _user_guard(request)
    if guard:
        return guard
    orders = Booking.objects.select_related('user', 'owner').filter(
        user_id=request.session['id'],
        is_paid=True,
    )
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
