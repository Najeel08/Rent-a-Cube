from django.db import models
from config.storage import PrivateProofStorage


class owner_tb(models.Model):
    Name = models.CharField(max_length=20)
    Email = models.EmailField(max_length=50, unique=True)
    Phonenumber = models.BigIntegerField()
    Place = models.CharField(max_length=50)
    Gender = models.CharField(max_length=15)
    Password = models.CharField(max_length=128)
    Image = models.ImageField(upload_to="id")
    Workex = models.CharField(max_length=25)
    Proof = models.ImageField(upload_to="proofs", storage=PrivateProofStorage(), null=True)
    accept = models.BooleanField(default=False)
    reject = models.BooleanField(default=False)

    def __str__(self):
        return self.Name


class owvaddwork(models.Model):
    Name = models.CharField(max_length=20)
    Sqft = models.CharField(max_length=50)
    State = models.CharField(max_length=80)
    City = models.CharField(max_length=50)
    Location = models.CharField(max_length=60)
    Price = models.CharField(max_length=50)
    Image = models.ImageField(upload_to="id")
    Pincode = models.CharField(max_length=25)
    Type = models.CharField(max_length=80)
    Facility = models.CharField(max_length=50)
    Capability = models.CharField(max_length=60)
    owner = models.ForeignKey(owner_tb, on_delete=models.CASCADE)

    def __str__(self):
        return self.Name


class addtech(models.Model):
    Name = models.CharField(max_length=20)
    Email = models.EmailField(max_length=50, unique=True)
    Phonenumber = models.BigIntegerField()
    Workex = models.CharField(max_length=25)
    Image = models.ImageField(upload_to="id")
    Place = models.CharField(max_length=50)
    Qualification = models.CharField(max_length=60)
    Password = models.CharField(max_length=128, blank=True)
    owner = models.ForeignKey(owner_tb, on_delete=models.CASCADE)

    def __str__(self):
        return self.Name


class Workassign(models.Model):
    Name = models.CharField(max_length=20)
    Email = models.EmailField(max_length=50)
    Phonenumber = models.BigIntegerField()
    requestmssg = models.CharField(max_length=100)
    owner = models.ForeignKey(owner_tb, on_delete=models.CASCADE)
    tech = models.ForeignKey(addtech, on_delete=models.CASCADE)
    request = models.ForeignKey('user.request_tb', on_delete=models.CASCADE, null=True, blank=True, related_name='assignments')

    def __str__(self):
        return self.Name
