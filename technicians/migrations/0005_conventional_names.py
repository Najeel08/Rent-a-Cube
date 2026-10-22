from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('technician', '0004_hash_existing_passwords')]

    # Keep existing SQLite tables and columns while updating Django state.
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterModelTable(name='tech', table='technician_tech'),
                migrations.RenameModel(old_name='tech', new_name='TechnicianCredential'),
                migrations.RenameField(model_name='techniciancredential', old_name='Name', new_name='name'),
                migrations.AlterField(model_name='techniciancredential', name='name', field=models.CharField(db_column='Name', max_length=20)),
                migrations.RenameField(model_name='techniciancredential', old_name='Email', new_name='email'),
                migrations.AlterField(model_name='techniciancredential', name='email', field=models.EmailField(db_column='Email', max_length=50, unique=True)),
                migrations.RenameField(model_name='techniciancredential', old_name='Phonenumber', new_name='phone_number'),
                migrations.AlterField(model_name='techniciancredential', name='phone_number', field=models.BigIntegerField(db_column='Phonenumber')),
                migrations.RenameField(model_name='techniciancredential', old_name='Password', new_name='password'),
                migrations.AlterField(model_name='techniciancredential', name='password', field=models.CharField(db_column='Password', max_length=128)),
                migrations.RenameField(model_name='techniciancredential', old_name='Workex', new_name='work_experience'),
                migrations.AlterField(model_name='techniciancredential', name='work_experience', field=models.CharField(db_column='Workex', max_length=25)),
            ],
        ),
    ]
