"""Razorpay connection and settlement shared by checkout and reconciliation."""
import logging

import certifi
import razorpay
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from owners.models import Workspace
from .models import Booking
from .reservations import has_conflict, interval

logger = logging.getLogger(__name__)


class PaymentSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault('timeout', (3.05, 10))
        return super().request(method, url, **kwargs)


def razorpay_client():
    if not settings.RAZORPAY_API_KEY or not settings.RAZORPAY_API_SECRET_KEY:
        return None
    client = razorpay.Client(
        session=PaymentSession(),
        auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET_KEY),
    )
    client.cert_path = certifi.where()
    return client


def payment_matches(booking, payment):
    return (payment.get('order_id') == booking.razorpay_order_id and
            payment.get('amount') == booking.total_amount * 100 and
            payment.get('currency') == 'INR' and payment.get('status') == 'captured')


@transaction.atomic
def record_payment(booking_id, payment_id, signature=''):
    item = Booking.objects.select_for_update().get(pk=booking_id)
    if item.is_paid:
        return item
    workspace = Workspace.objects.select_for_update().filter(pk=item.workspace_id).first()
    try:
        start, _ = interval(item)
        review = (not workspace or not workspace.owner.accept or workspace.owner.reject or
                  start <= timezone.now() or has_conflict(item))
    except ValidationError:
        review = True
    if review and item.payment_mode == 'demo':
        raise ValidationError('This time is no longer available. Choose another time.')
    item.is_paid = True
    item.payment_review_required = review
    item.razorpay_payment_id = payment_id
    item.razorpay_signature = signature
    item.checkout_expires_at = None
    item.save(update_fields=['is_paid', 'payment_review_required', 'razorpay_payment_id',
                             'razorpay_signature', 'checkout_expires_at'])
    logger.info('payment_recorded booking=%s review=%s', item.pk, review)
    return item
