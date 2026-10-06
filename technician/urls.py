from django.urls import path
from . import views

urlpatterns = [
    path("tlog", views.tlog, name="tlog"),
    path("thome", views.thome, name="thome"),
    path("requests", views.requests, name="requests"),
    path("gaccept/<int:id>", views.gaccept, name="gaccept"),
    path("greject/<int:id>", views.greject, name="greject"),
]
