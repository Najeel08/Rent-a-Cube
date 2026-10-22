from config.admin import CredentialAdmin
from django.contrib import admin
from .models import TechnicianCredential

admin.site.register(TechnicianCredential, CredentialAdmin)
