from django.contrib import admin
from .models import *

# Register owner-related models in Django admin panel
admin.site.register(owner_tb)
admin.site.register(owvaddwork)
admin.site.register(addtech)
admin.site.register(Workassign)
