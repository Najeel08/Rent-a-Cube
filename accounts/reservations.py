"""Exclusive workspace reservations. Call under an atomic writer/row lock."""
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from config.validation import positive_integer, MAX_BOOKING_DURATION_HOURS
from .models import Booking


def interval(booking):
    if not booking.workspace_id or not booking.start_time:
        raise ValidationError('Select this workspace and a start time again before checkout.')
    try:
        day = datetime.strptime(booking.date, '%Y-%m-%d').date()
    except (TypeError, ValueError) as exc:
        raise ValidationError('Select a valid booking date.') from exc
    start = timezone.make_aware(datetime.combine(day, booking.start_time))
    hours = positive_integer(booking.duration_hours, 'Duration', MAX_BOOKING_DURATION_HOURS)
    return start, start + timedelta(hours=hours)


def has_conflict(booking):
    start, end = interval(booking)
    candidates = Booking.objects.filter(
        Q(workspace_id=booking.workspace_id) |
        Q(workspace__isnull=True, owner_id=booking.workspace.owner_id),
        is_refunded=False,
        payment_review_required=False,
    ).filter(Q(is_paid=True) | Q(checkout_expires_at__gt=timezone.now())).exclude(pk=booking.pk)
    for other in candidates:
        try:
            other_start, other_end = interval(other)
        except ValidationError:
            # An unresolvable paid legacy reservation needs operator review.
            if other.is_paid:
                return True
            continue
        if start < other_end and other_start < end:
            return True
    return False
