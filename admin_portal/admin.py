from config.admin import CredentialAdmin
from django.contrib import admin
from .models import PlatformAdmin

admin.site.register(PlatformAdmin, CredentialAdmin)
