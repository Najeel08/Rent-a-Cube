from django.db import models
from owners.models import *
from django.utils import timezone


# User model - stores registered user details
class user_tb(models.Model):
    Name = models.CharField(max_length=20)
    Email = models.EmailField(max_length=50, unique=True)
    Phonenumber = models.BigIntegerField()
    Place = models.CharField(max_length=50)
    Password = models.CharField(max_length=128)
    Image = models.ImageField(upload_to="id")

    def __str__(self):
        return self.Name


# Cart/Booking model - stores workspace bookings and payment details
class cart(models.Model):
    WsName = models.CharField(max_length=100)
    Price = models.IntegerField()
    Location = models.CharField(max_length=100)
    Date_book = models.DateField(default=timezone.now)
    user = models.ForeignKey(user_tb, on_delete=models.CASCADE)
    owner = models.ForeignKey(owner_tb, on_delete=models.CASCADE)
    workspace = models.ForeignKey(
        owvaddwork,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )
    Image = models.ImageField(upload_to="cart", null=True)
    Status = models.BooleanField(default=False)           # Owner payment confirmation
    Paystatus = models.BooleanField(default=False)         # Razorpay payment completed
    Refundstatus = models.BooleanField(default=False)      # Refund processed
    RazorpayOrderId = models.CharField(max_length=100, blank=True)
    RazorpayPaymentId = models.CharField(max_length=100, blank=True)
    RazorpaySignature = models.CharField(max_length=200, blank=True)
    RazorpayRefundId = models.CharField(max_length=100, blank=True)
    nohrs = models.IntegerField()
    Date = models.CharField(max_length=100)
    StartTime = models.TimeField(null=True, blank=True)
    totalsum = models.IntegerField(default=0)

    def __str__(self):
        return self.WsName


# Service request model - user sends maintenance/support request to owner
class request_tb(models.Model):
    Name = models.CharField(max_length=50)
    Email = models.EmailField(max_length=50)
    Phone = models.BigIntegerField()
    Subject = models.CharField(max_length=200)
    user = models.ForeignKey(user_tb, on_delete=models.CASCADE)
    owner = models.ForeignKey(owner_tb, on_delete=models.CASCADE)
    accept = models.BooleanField(default=False)
    reject = models.BooleanField(default=False)

    def __str__(self):
        return self.Name


# Chat message model - stores messages between users and owners
class Messages_Tb(models.Model):
    Messages = models.CharField(max_length=500)
    Date = models.DateField(max_length=10)
    Time = models.TimeField(max_length=50)
    Send_id = models.CharField(max_length=50)
    Receiver_id = models.CharField(max_length=50)
    Send_name = models.CharField(max_length=50)
    Receiver_name = models.CharField(max_length=50)

    def __str__(self):
        return self.Send_name


# Refund model - tracks refund records for bookings
class refund_tb(models.Model):
    Price = models.IntegerField()
    user = models.ForeignKey(user_tb, on_delete=models.CASCADE)
    owner = models.ForeignKey(owner_tb, on_delete=models.CASCADE)
    booking = models.OneToOneField(cart, on_delete=models.CASCADE, null=True, blank=True, related_name='refund_record')
    Status = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)
