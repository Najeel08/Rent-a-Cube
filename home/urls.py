from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('logout/', views.logout_view, name='logout'),
]

# Preserve saved links while all internal links use the readable routes.
legacy_urlpatterns = [
    path('contact4', views.contact),
]

urlpatterns += legacy_urlpatterns
