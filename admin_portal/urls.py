from django.urls import path
from . import views


urlpatterns = [
    path('sign-in/', views.sign_in, name='admin_login'),
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    path('owners/', views.owner_list, name='admin_owner_list'),
    path('workspaces/', views.workspace_list, name='admin_workspace_list'),
    path('workspace-images/', views.workspace_images, name='admin_workspace_images'),
    path('owners/<str:owner_id>/proof/', views.owner_proof, name='admin_owner_proof'),
    path('owners/<int:owner_id>/proof/file/', views.owner_proof_file, name='admin_owner_proof_file'),
    path('workspaces/<str:workspace_id>/image/', views.workspace_image, name='admin_workspace_image'),
    path('orders/', views.order_list, name='admin_order_list'),
    path('customers/', views.customer_list, name='admin_customer_list'),
    path('bookings/', views.booking_list, name='admin_booking_list'),
    path('support-inquiries/', views.support_inquiry_list, name='admin_support_inquiry_list'),
    path('support-inquiries/detail/', views.support_inquiry_detail, name='admin_support_inquiry_detail'),
    path('profile/', views.profile, name='admin_profile'),
    path('owners/<int:owner_id>/approve/', views.approve_owner, name='admin_owner_approve'),
    path('owners/<int:owner_id>/reject/', views.reject_owner, name='admin_owner_reject'),
]

# Preserve saved links while all internal links use the readable routes.
legacy_urlpatterns = [
    path('alogin', views.sign_in),
    path('aindex', views.dashboard),
    path('ownerlists', views.owner_list),
    path('spaceview', views.workspace_list),
    path('spaceimage', views.workspace_images),
    path('proofview<str:owner_id>', views.owner_proof),
    path('proof-file/<int:owner_id>', views.owner_proof_file),
    path('imageview<str:workspace_id>', views.workspace_image),
    path('worder', views.order_list),
    path('userlist', views.customer_list),
    path('bookingdetail', views.booking_list),
    path('suggestions', views.support_inquiry_list),
    path('viewsuggestion', views.support_inquiry_detail),
    path('profile', views.profile),
    path('accept<int:owner_id>', views.approve_owner),
    path('reject<int:owner_id>', views.reject_owner),
]

urlpatterns += legacy_urlpatterns
