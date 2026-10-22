from django.db import models
from django.db.models.functions import Lower


class PlatformAdmin(models.Model):
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)

    class Meta:
        db_table = 'workadmin_projectadmin'
        constraints = [models.UniqueConstraint(Lower('email'), name='admin_email_ci')]
