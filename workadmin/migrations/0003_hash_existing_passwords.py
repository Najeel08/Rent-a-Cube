from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def is_hashed(value):
    try:
        identify_hasher(value)
        return True
    except Exception:
        return False


def hash_passwords(apps, schema_editor):
    admin_model = apps.get_model('workadmin', 'Projectadmin')
    for admin in admin_model.objects.all():
        if admin.password and not is_hashed(admin.password):
            admin.password = make_password(admin.password)
            admin.save(update_fields=['password'])


class Migration(migrations.Migration):

    dependencies = [
        ('workadmin', '0002_alter_projectadmin_email_alter_projectadmin_password'),
    ]

    operations = [
        migrations.RunPython(hash_passwords, migrations.RunPython.noop),
    ]
