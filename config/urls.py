from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.urls import legacy_urlpatterns as customer_legacy_urls
from admin_portal.urls import legacy_urlpatterns as admin_legacy_urls
from technicians.urls import legacy_urlpatterns as technician_legacy_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('accounts/', include('accounts.urls')),
    path('owners/', include('owners.urls')),
    path('admin-portal/', include('admin_portal.urls')),
    path('technicians/', include('technicians.urls')),
    path('user/', include(customer_legacy_urls)),
    path('workadmin/', include(admin_legacy_urls)),
    path('technician/', include(technician_legacy_urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
