import shutil
from pathlib import Path

from django.conf import settings
from django.db import migrations, models

import workspace.storage


def move_proofs_to_private_storage(apps, schema_editor):
    Owner = apps.get_model('owners', 'owner_tb')
    public_root = Path(settings.MEDIA_ROOT)
    private_root = Path(settings.PRIVATE_MEDIA_ROOT)

    for owner in Owner.objects.exclude(Proof=''):
        old_name = owner.Proof.name
        if not old_name or old_name.startswith('proofs/'):
            continue
        new_name = f'proofs/{owner.id}_{Path(old_name).name}'
        source = public_root / old_name
        destination = private_root / new_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.exists() and not destination.exists():
            shutil.move(str(source), str(destination))
        if destination.exists():
            owner.Proof.name = new_name
            owner.save(update_fields=['Proof'])


class Migration(migrations.Migration):
    dependencies = [('owners', '0008_workassign_request')]

    operations = [
        migrations.AlterField(
            model_name='owner_tb',
            name='Proof',
            field=models.ImageField(null=True, storage=workspace.storage.PrivateProofStorage(), upload_to='proofs'),
        ),
        migrations.RunPython(move_proofs_to_private_storage, migrations.RunPython.noop),
    ]
