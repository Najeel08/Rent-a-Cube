import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('owners', '0009_private_proof_storage'),
        ('user', '0028_refund_tb_booking'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='StartTime',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cart',
            name='workspace',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='bookings',
                to='owners.owvaddwork',
            ),
        ),
    ]
