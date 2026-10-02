from django.db import migrations, models
import django.db.models.deletion


def link_unambiguous_requests(apps, schema_editor):
    Workassign = apps.get_model('owners', 'Workassign')
    Request = apps.get_model('user', 'request_tb')
    for assignment in Workassign.objects.filter(request__isnull=True):
        matches = Request.objects.filter(
            Name=assignment.Name,
            Email=assignment.Email,
            Phone=assignment.Phonenumber,
            Subject=assignment.requestmssg,
            owner_id=assignment.owner_id,
        ).order_by('id')
        if matches.count() == 1:
            assignment.request_id = matches.first().id
            assignment.save(update_fields=['request'])


class Migration(migrations.Migration):
    dependencies = [
        ('owners', '0007_hash_existing_passwords'),
        ('user', '0027_cart_razorpayorderid_cart_razorpaypaymentid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='workassign',
            name='request',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='user.request_tb'),
        ),
        migrations.RunPython(link_unambiguous_requests, migrations.RunPython.noop),
    ]
