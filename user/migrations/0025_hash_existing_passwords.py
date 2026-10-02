from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def is_hashed(value):
    try:
        identify_hasher(value)
        return True
    except Exception:
        return False


def hash_passwords(apps, schema_editor):
    user_model = apps.get_model('user', 'user_tb')
    for user in user_model.objects.all():
        if user.Password and not is_hashed(user.Password):
            user.Password = make_password(user.Password)
            user.save(update_fields=['Password'])


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0024_alter_cart_paystatus_alter_cart_status_and_more'),
    ]

    operations = [
        migrations.RunPython(hash_passwords, migrations.RunPython.noop),
    ]
