from django.contrib import admin
from .models import Messages_Tb, cart, refund_tb, request_tb, user_tb

admin.site.register(user_tb)
admin.site.register(cart)
admin.site.register(request_tb)
admin.site.register(Messages_Tb)
admin.site.register(refund_tb)
