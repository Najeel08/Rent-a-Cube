from django.urls import path
from . import views

# Homeapp URLs - landing page and contact page
urlpatterns = [
    path("", views.index, name="index"),            # Landing page
    path("contact4", views.contact4, name="contact4"),  # Contact page
    path("logout/", views.logout_view, name="logout"),
]
