from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("contact4", views.contact4, name="contact4"),
    path("logout/", views.logout_view, name="logout"),
]
