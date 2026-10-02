from django.db import models


class SupportInquiry(models.Model):
    """A public contact request retained for platform administrators to triage."""

    name = models.CharField(max_length=80)
    email = models.EmailField(max_length=254)
    message = models.TextField(max_length=1500)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'support inquiries'

    def __str__(self):
        return f'{self.name} <{self.email}>'
