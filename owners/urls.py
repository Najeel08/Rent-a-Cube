from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.register, name='owner_register'),
    path('sign-in/', views.sign_in, name='owner_login'),
    path('dashboard/', views.dashboard, name='owner_dashboard'),
    path('workspaces/new/', views.workspace_create, name='workspace_create'),
    path('workspaces/', views.workspace_list, name='owner_workspace_list'),
    path('workspaces/<int:workspace_id>/', views.workspace_detail, name='owner_workspace_detail'),
    path('workspaces/<str:workspace_id>/edit/', views.workspace_edit, name='workspace_edit'),
    path('workspaces/<int:workspace_id>/delete/', views.workspace_delete, name='workspace_delete'),
    path('profile/', views.profile, name='owner_profile'),
    path('profile/<str:profile_id>/edit/', views.profile_edit, name='owner_profile_edit'),
    path('bookings/<str:pk>/', views.booking_list, name='owner_booking_list'),
    path('bookings/<str:pk>/confirm-payment/', views.confirm_payment, name='owner_payment_confirm'),
    path('technicians/new/', views.technician_create, name='technician_create'),
    path('technicians/', views.technician_list, name='owner_technician_list'),
    path('technicians/<int:technician_id>/send-login/', views.send_technician_login, name='technician_login_email'),
    path('service-requests/', views.service_request_list, name='owner_service_request_list'),
    path('service-requests/<str:request_id>/assign/', views.service_assignment_create, name='service_assignment_create'),
    path('conversations/', views.chat_inbox, name='owner_chat_inbox'),
    path('conversations/<str:user_id>/', views.conversation, name='owner_conversation'),
    path('refunds/', views.refund_list, name='owner_refund_list'),
    path('bookings/<int:booking_id>/refund/', views.process_refund, name='refund_process'),
]

# Preserve saved links while all internal links use the readable routes.
legacy_urlpatterns = [
    path('vreg', views.register),
    path('vlog', views.sign_in),
    path('vhome', views.dashboard),
    path('vaddwork', views.workspace_create),
    path('oviewwork', views.workspace_list),
    path('Workdetail<int:workspace_id>', views.workspace_detail),
    path('ovupdate<str:workspace_id>', views.workspace_edit),
    path('ovdelete<int:workspace_id>', views.workspace_delete),
    path('PROFILE', views.profile),
    path('ownerprofileupdate<str:profile_id>', views.profile_edit),
    path('ownerorder<str:pk>', views.booking_list),
    path('confirmpayment/<str:pk>', views.confirm_payment),
    path('addtechnician', views.technician_create),
    path('viewtechnician', views.technician_list),
    path('sentemail<int:technician_id>', views.send_technician_login),
    path('requests', views.service_request_list),
    path('assign<str:request_id>', views.service_assignment_create),
    path('chat', views.chat_inbox),
    path('achat/<str:user_id>', views.conversation),
    path('refund', views.refund_list),
    path('refundcheck<int:booking_id>', views.process_refund),
]

urlpatterns += legacy_urlpatterns
