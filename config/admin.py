from django import forms
from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password


class CredentialForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False,
                               help_text='Enter a new password, or leave blank to retain the existing hash.')

    def clean_password(self):
        raw = self.cleaned_data.get('password')
        if not raw and self.instance.pk:
            return self.instance.password
        validate_password(raw or '', self.instance)
        return make_password(raw)


class CredentialAdmin(admin.ModelAdmin):
    form = CredentialForm


class FinancialRecordAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
