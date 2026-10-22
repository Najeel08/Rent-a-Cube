from django.db import models
from django.db.models.functions import Lower
from config.storage import PrivateProofStorage


class Owner(models.Model):
    name = models.CharField(db_column='Name', max_length=20)
    email = models.EmailField(db_column='Email', max_length=50, unique=True)
    phone_number = models.CharField(db_column='Phonenumber', max_length=15)
    place = models.CharField(db_column='Place', max_length=50)
    gender = models.CharField(db_column='Gender', max_length=15)
    password = models.CharField(db_column='Password', max_length=128)
    image = models.ImageField(db_column='Image', upload_to="id")
    work_experience = models.CharField(db_column='Workex', max_length=25)
    proof_document = models.ImageField(db_column='Proof', upload_to="proofs", storage=PrivateProofStorage(), null=True)
    accept = models.BooleanField(default=False)
    reject = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'owners_owner_tb'
        constraints = [models.UniqueConstraint(Lower('email'), name='owner_email_ci')]


class Workspace(models.Model):
    name = models.CharField(db_column='Name', max_length=20)
    square_feet = models.CharField(db_column='Sqft', max_length=50)
    state = models.CharField(db_column='State', max_length=80)
    city = models.CharField(db_column='City', max_length=50)
    location = models.CharField(db_column='Location', max_length=60)
    hourly_rate = models.CharField(db_column='Price', max_length=50)
    image = models.ImageField(db_column='Image', upload_to="id")
    postal_code = models.CharField(db_column='Pincode', max_length=25)
    workspace_type = models.CharField(db_column='Type', max_length=80)
    amenities = models.CharField(db_column='Facility', max_length=50)
    capacity = models.CharField(db_column='Capability', max_length=60)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'owners_owvaddwork'


class Technician(models.Model):
    name = models.CharField(db_column='Name', max_length=20)
    email = models.EmailField(db_column='Email', max_length=50, unique=True)
    phone_number = models.CharField(db_column='Phonenumber', max_length=15)
    work_experience = models.CharField(db_column='Workex', max_length=25)
    image = models.ImageField(db_column='Image', upload_to="id")
    place = models.CharField(db_column='Place', max_length=50)
    qualification = models.CharField(db_column='Qualification', max_length=60)
    password = models.CharField(db_column='Password', max_length=128, blank=True)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'owners_addtech'
        constraints = [models.UniqueConstraint(Lower('email'), name='technician_email_ci')]


class ServiceAssignment(models.Model):
    name = models.CharField(db_column='Name', max_length=20)
    email = models.EmailField(db_column='Email', max_length=50)
    phone_number = models.CharField(db_column='Phonenumber', max_length=15)
    request_message = models.CharField(db_column='requestmssg', max_length=200)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)
    technician = models.ForeignKey(Technician, db_column='tech_id', on_delete=models.CASCADE)
    request = models.ForeignKey('user.servicerequest', on_delete=models.CASCADE, null=True, blank=True, related_name='assignments')

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'owners_workassign'
        constraints = [models.UniqueConstraint(fields=['request'], condition=models.Q(request__isnull=False), name='one_assignment_per_request')]
