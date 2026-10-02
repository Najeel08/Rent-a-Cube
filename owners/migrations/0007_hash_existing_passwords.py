from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def is_hashed(value):
    try:
        identify_hasher(value)
        return True
    except Exception:
        return False


def hash_passwords(apps, schema_editor):
    for model_name, field_name in (('owner_tb', 'Password'), ('addtech', 'Password')):
        model = apps.get_model('owners', model_name)
        for item in model.objects.all():
            value = getattr(item, field_name)
            if value and not is_hashed(value):
                setattr(item, field_name, make_password(value))
                item.save(update_fields=[field_name])


class Migration(migrations.Migration):

    dependencies = [
        ('owners', '0006_alter_addtech_email_alter_addtech_password_and_more'),
    ]

    operations = [
        migrations.RunPython(hash_passwords, migrations.RunPython.noop),
    ]
