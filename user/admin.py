from django.contrib import admin
from .models import *

# Register user-related models in Django admin panel
admin.site.register(user_tb)
admin.site.register(cart)
admin.site.register(request_tb)
admin.site.register(Messages_Tb)
admin.site.register(refund_tb)
