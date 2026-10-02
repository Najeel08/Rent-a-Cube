from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def is_hashed(value):
    try:
        identify_hasher(value)
        return True
    except Exception:
        return False


def hash_passwords(apps, schema_editor):
    tech_model = apps.get_model('technician', 'tech')
    for tech in tech_model.objects.all():
        if tech.Password and not is_hashed(tech.Password):
            tech.Password = make_password(tech.Password)
            tech.save(update_fields=['Password'])


class Migration(migrations.Migration):

    dependencies = [
        ('technician', '0003_alter_tech_email_alter_tech_password'),
    ]

    operations = [
        migrations.RunPython(hash_passwords, migrations.RunPython.noop),
    ]
