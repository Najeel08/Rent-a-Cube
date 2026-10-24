"""Owner booking confirmation and refund views."""
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect

from accounts.models import Booking, Refund
from accounts.payments import razorpay_client
from config.pagination import render_page
from config.validation import positive_integer

from .auth import _owner_guard


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
