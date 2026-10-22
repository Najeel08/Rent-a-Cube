from django.urls import path
from . import views


urlpatterns = [
    path('activate/<str:token>/', views.activate, name='technician_activate'),
    path('sign-in/', views.sign_in, name='technician_login'),
    path('dashboard/', views.dashboard, name='technician_dashboard'),
    path('service-requests/', views.service_request_list, name='technician_service_request_list'),
    path('assignments/<int:assignment_id>/accept/', views.assignment_accept, name='assignment_accept'),
    path('assignments/<int:assignment_id>/reject/', views.assignment_reject, name='assignment_reject'),
]

# Preserve saved links while all internal links use the readable routes.
legacy_urlpatterns = [
    path('tlog', views.sign_in),
    path('thome', views.dashboard),
    path('requests', views.service_request_list),
    path('gaccept/<int:assignment_id>', views.assignment_accept),
    path('greject/<int:assignment_id>', views.assignment_reject),
]

urlpatterns += legacy_urlpatterns
