from django.contrib import admin
from .models import Workassign, addtech, owner_tb, owvaddwork

admin.site.register(owner_tb)
admin.site.register(owvaddwork)
admin.site.register(addtech)
admin.site.register(Workassign)
