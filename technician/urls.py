from django.urls import path
from . import views

# Technician URLs - login, dashboard, work requests
urlpatterns = [
    path("tlog", views.tlog, name="tlog"),              # Technician login
    path("thome", views.thome, name="thome"),            # Technician dashboard
    path("requests", views.requests, name="requests"),    # View assignments
    path("gaccept/<int:id>", views.gaccept, name="gaccept"),  # Accept assignment
    path("greject/<int:id>", views.greject, name="greject"),  # Reject assignment
]
