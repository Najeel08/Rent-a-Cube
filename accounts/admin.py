from config.admin import CredentialAdmin, FinancialRecordAdmin
from django.contrib import admin
from .models import Message, Booking, Refund, ServiceRequest, Customer

admin.site.register(Customer, CredentialAdmin)
admin.site.register(Booking, FinancialRecordAdmin)
admin.site.register(ServiceRequest)
admin.site.register(Message)
admin.site.register(Refund, FinancialRecordAdmin)
