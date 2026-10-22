from config.admin import CredentialAdmin
from django.contrib import admin
from .models import ServiceAssignment, Technician, Owner, Workspace

admin.site.register(Owner, CredentialAdmin)
admin.site.register(Workspace)
admin.site.register(Technician, CredentialAdmin)
admin.site.register(ServiceAssignment)
