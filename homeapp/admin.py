from django.contrib import admin

from .models import SupportInquiry


@admin.register(SupportInquiry)
class SupportInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'resolved')
    list_filter = ('resolved',)
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)
