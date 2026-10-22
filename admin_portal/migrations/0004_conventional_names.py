from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('workadmin', '0003_hash_existing_passwords')]

    # Keep existing SQLite tables and columns while updating Django state.
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterModelTable(name='projectadmin', table='workadmin_projectadmin'),
                migrations.RenameModel(old_name='Projectadmin', new_name='PlatformAdmin'),
            ],
        ),
    ]
