from django.db import models
from django.db.models.functions import Lower


class TechnicianCredential(models.Model):
    name = models.CharField(db_column='Name', max_length=20)
    email = models.EmailField(db_column='Email', max_length=50, unique=True)
    phone_number = models.CharField(db_column='Phonenumber', max_length=15)
    password = models.CharField(db_column='Password', max_length=128)
    work_experience = models.CharField(db_column='Workex', max_length=25)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'technician_tech'
        constraints = [models.UniqueConstraint(Lower('email'), name='legacy_tech_email_ci')]
