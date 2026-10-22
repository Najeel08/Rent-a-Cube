from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Booking, Refund
from accounts.payments import payment_matches, razorpay_client, record_payment


class Command(BaseCommand):
    help = 'Read provider status for one existing order/refund. Never charges or issues a refund.'

    def add_arguments(self, parser):
        parser.add_argument('booking_id', type=int)

    def handle(self, *args, **options):
        client = razorpay_client()
        if not client:
            raise CommandError('Razorpay credentials are required.')
        item = Booking.objects.get(pk=options['booking_id'])
        if item.payment_mode == 'demo' or not item.razorpay_order_id:
            raise CommandError('No real provider order to reconcile.')
        if not item.is_paid:
            matches = [payment for payment in client.order.payments(item.razorpay_order_id).get('items', [])
                       if payment_matches(item, payment)]
            if len(matches) != 1:
                raise CommandError('Expected exactly one matching captured payment; manual review required.')
            item = record_payment(item.pk, matches[0]['id'])
        if item.razorpay_refund_id and not item.is_refunded:
            result = client.refund.fetch(item.razorpay_refund_id)
            if result.get('payment_id') != item.razorpay_payment_id or result.get('amount') != item.total_amount * 100:
                raise CommandError('Refund amount/payment mismatch; manual review required.')
            if result.get('status') == 'processed':
                with transaction.atomic():
                    Booking.objects.filter(pk=item.pk).update(is_refunded=True, refund_state='processed')
                    Refund.objects.filter(booking=item).update(is_processed=True)
        self.stdout.write('Provider status reconciled. Review the booking and refund status in the owner portal.')
