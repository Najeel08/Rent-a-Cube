from django.urls import path
from . import views


urlpatterns = [
    path('register/', views.register, name='register'),
    path('sign-in/', views.sign_in, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('workspaces/', views.workspace_list, name='workspace_list'),
    path('workspaces/overview/', views.workspace_overview, name='workspace_overview'),
    path('cart/', views.cart_list, name='cart_list'),
    path('workspaces/search/', views.workspace_search, name='workspace_search'),
    path('owners/<str:owner_id>/', views.owner_public_profile, name='owner_public_profile'),
    path('workspaces/<str:workspace_id>/book/', views.workspace_book, name='workspace_book'),
    path('owners/<str:owner_id>/workspaces/', views.owner_workspace_catalog, name='owner_workspace_catalog'),
    path('cart/owners/', views.cart_owner_list, name='cart_owner_list'),
    path('cart/owners/<str:pk>/', views.cart_detail, name='cart_detail'),
    path('service-requests/new/', views.service_request_create, name='service_request_create'),
    path('service-requests/', views.service_request_list, name='service_request_list'),
    path('conversations/<int:owner_id>/', views.customer_conversation, name='customer_conversation'),
    path('cart/<int:pk>/remove/', views.cart_remove, name='cart_remove'),
    path('bookings/<str:pk>/', views.booking_list, name='booking_list'),
    path('bookings/<int:booking_id>/checkout/', views.checkout, name='checkout'),
    path('bookings/<int:booking_id>/payment/complete/', views.payment_complete, name='payment_complete'),
]

# Preserve saved links while all internal links use the readable routes.
legacy_urlpatterns = [
    path('ureg', views.register),
    path('ulog', views.sign_in),
    path('uhome', views.dashboard),
    path('uviewwork', views.workspace_list),
    path('uworkdetails', views.workspace_overview),
    path('uviewcart', views.cart_list),
    path('showworkspace1', views.workspace_search),
    path('uviewownerprof<str:owner_id>', views.owner_public_profile),
    path('uviewownerwork<str:workspace_id>', views.workspace_book),
    path('showworkspace<str:owner_id>', views.owner_workspace_catalog),
    path('selectownercart', views.cart_owner_list),
    path('cartdetails<str:pk>', views.cart_detail),
    path('request', views.service_request_create),
    path('viewrequest', views.service_request_list),
    path('chat/<int:owner_id>', views.customer_conversation),
    path('cart_del/<int:pk>', views.cart_remove),
    path('uvieworder<str:pk>', views.booking_list),
    path('checkout<int:booking_id>', views.checkout),
    path('payment_success<int:booking_id>', views.payment_complete),
]

urlpatterns += legacy_urlpatterns
