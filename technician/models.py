from django.db import models


# Technician model - used for technician login (separate from owner's addtech)
class tech(models.Model):
    Name = models.CharField(max_length=20)
    Email = models.EmailField(max_length=50, unique=True)
    Phonenumber = models.BigIntegerField()
    Password = models.CharField(max_length=128)
    Workex = models.CharField(max_length=25)

    def __str__(self):
        return self.Name
