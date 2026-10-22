from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from owners.models import Owner, Workspace


class Customer(models.Model):
    name = models.CharField(db_column='Name', max_length=20)
    email = models.EmailField(db_column='Email', max_length=50, unique=True)
    phone_number = models.CharField(db_column='Phonenumber', max_length=15)
    place = models.CharField(db_column='Place', max_length=50)
    password = models.CharField(db_column='Password', max_length=128)
    image = models.ImageField(db_column='Image', upload_to="id")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'user_user_tb'
        constraints = [models.UniqueConstraint(Lower('email'), name='customer_email_ci')]


class Booking(models.Model):
    workspace_name = models.CharField(db_column='WsName', max_length=100)
    hourly_rate = models.IntegerField(db_column='Price')
    location = models.CharField(db_column='Location', max_length=100)
    created_at = models.DateField(db_column='Date_book', default=timezone.now)
    user = models.ForeignKey(Customer, on_delete=models.PROTECT)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bookings',
    )
    image = models.ImageField(db_column='Image', upload_to="cart", null=True)
    is_confirmed = models.BooleanField(db_column='Status', default=False)
    is_paid = models.BooleanField(db_column='Paystatus', default=False)
    is_refunded = models.BooleanField(db_column='Refundstatus', default=False)
    razorpay_order_id = models.CharField(db_column='RazorpayOrderId', max_length=100, blank=True)
    razorpay_payment_id = models.CharField(db_column='RazorpayPaymentId', max_length=100, blank=True)
    razorpay_signature = models.CharField(db_column='RazorpaySignature', max_length=200, blank=True)
    razorpay_refund_id = models.CharField(db_column='RazorpayRefundId', max_length=100, blank=True)
    duration_hours = models.IntegerField(db_column='nohrs')
    date = models.CharField(db_column='Date', max_length=100)
    start_time = models.TimeField(db_column='StartTime', null=True, blank=True)
    total_amount = models.IntegerField(db_column='totalsum', default=0)
    checkout_expires_at = models.DateTimeField(null=True, blank=True)
    payment_mode = models.CharField(max_length=12, blank=True)
    payment_review_required = models.BooleanField(default=False)
    refund_state = models.CharField(max_length=12, default='none')

    def __str__(self):
        return self.workspace_name

    class Meta:
        db_table = 'user_cart'
        constraints = [
            models.CheckConstraint(condition=models.Q(hourly_rate__gt=0), name='booking_positive_rate'),
            models.CheckConstraint(condition=models.Q(duration_hours__range=(1, 72)), name='booking_valid_duration'),
            models.CheckConstraint(condition=models.Q(total_amount__gte=0), name='booking_nonnegative_total'),
            models.CheckConstraint(condition=models.Q(is_refunded=False) | models.Q(is_paid=True), name='refund_requires_payment'),
            models.CheckConstraint(condition=models.Q(is_confirmed=False) | models.Q(is_paid=True), name='confirmation_requires_payment'),
            models.UniqueConstraint(fields=['razorpay_payment_id'], condition=~models.Q(razorpay_payment_id=''), name='unique_payment_reference'),
            models.UniqueConstraint(fields=['razorpay_order_id'], condition=~models.Q(razorpay_order_id=''), name='unique_order_reference'),
        ]
        indexes = [models.Index(fields=['workspace', 'date'], name='booking_workspace_date')]


class ServiceRequest(models.Model):
    name = models.CharField(db_column='Name', max_length=50)
    email = models.EmailField(db_column='Email', max_length=50)
    phone_number = models.CharField(db_column='Phone', max_length=15)
    subject = models.CharField(db_column='Subject', max_length=200)
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)
    accept = models.BooleanField(default=False)
    reject = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'user_request_tb'


class Message(models.Model):
    # Legacy untyped messages remain stored but are quarantined from portal queries.
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
    owner = models.ForeignKey(Owner, null=True, blank=True, on_delete=models.CASCADE)
    sender_role = models.CharField(max_length=5, blank=True, choices=[('user', 'Customer'), ('owner', 'Owner')])
    body = models.CharField(db_column='Messages', max_length=500)
    date = models.DateField(db_column='Date', max_length=10)
    time = models.TimeField(db_column='Time', max_length=50)
    sender_id = models.CharField(db_column='Send_id', max_length=50)
    receiver_id = models.CharField(db_column='Receiver_id', max_length=50)
    sender_name = models.CharField(db_column='Send_name', max_length=50)
    receiver_name = models.CharField(db_column='Receiver_name', max_length=50)

    def __str__(self):
        return self.sender_name

    class Meta:
        db_table = 'user_messages_tb'
        indexes = [models.Index(fields=['customer', 'owner', 'id'], name='message_conversation')]
        constraints = [models.CheckConstraint(
            condition=(models.Q(customer__isnull=True, owner__isnull=True, sender_role='') |
                       models.Q(customer__isnull=False, owner__isnull=False, sender_role__in=['user', 'owner'])),
            name='message_typed_participants',
        )]


class Refund(models.Model):
    amount = models.IntegerField(db_column='Price')
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='refund_record')
    is_processed = models.BooleanField(db_column='Status', default=False)

    def __str__(self):
        return str(self.user)

    class Meta:
        db_table = 'user_refund_tb'
