from django.db import models


class Projectadmin(models.Model):
    email = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=128)
