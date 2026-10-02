from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Main URL configuration - routes to each app's urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('homeapp.urls')),          # Landing page
    path('user/', include('user.urls')),         # User module
    path('owners/', include('owners.urls')),     # Owner module
    path('workadmin/', include('workadmin.urls')),  # Admin module
    path('technician/', include('technician.urls')),  # Technician module
]

# Serve media and static files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
