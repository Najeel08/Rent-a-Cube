from django.db import migrations, models
import django.db.models.deletion


def link_unambiguous_refunds(apps, schema_editor):
    Cart = apps.get_model('user', 'cart')
    Refund = apps.get_model('user', 'refund_tb')
    for refund in Refund.objects.filter(booking__isnull=True):
        matches = Cart.objects.filter(
            user_id=refund.user_id,
            owner_id=refund.owner_id,
            totalsum=refund.Price,
            Refundstatus=True,
        ).order_by('id')
        if matches.count() == 1:
            refund.booking_id = matches.first().id
            refund.save(update_fields=['booking'])


class Migration(migrations.Migration):
    dependencies = [('user', '0027_cart_razorpayorderid_cart_razorpaypaymentid_and_more')]

    operations = [
        migrations.AddField(
            model_name='refund_tb',
            name='booking',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='refund_record', to='user.cart'),
        ),
        migrations.RunPython(link_unambiguous_refunds, migrations.RunPython.noop),
    ]
