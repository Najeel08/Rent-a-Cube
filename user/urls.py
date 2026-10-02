from django.urls import path
from . import views

# User URLs - registration, login, workspace browsing, cart, payment, chat
urlpatterns = [
    path("ureg", views.ureg, name="ureg"),                       # User registration
    path("ulog", views.ulog, name="ulog"),                       # User login
    path("uhome", views.uhome, name="uhome"),                     # User dashboard
    path("uviewwork", views.uviewwork, name="uviewwork"),         # View all workspaces
    path("uworkdetails", views.uworkdetails, name="uworkdetails"),  # Workspace details
    path("uviewcart", views.uviewcart, name="uviewcart"),         # View cart
    path("showworkspace1", views.showworkspace1, name="showworkspace1"),  # Search workspaces
    path("uviewownerprof<str:id>", views.uviewownerprof, name="uviewownerprof"),
    path("uviewownerwork<str:pi>", views.uviewownerwork, name="uviework"),  # Book workspace
    path("showworkspace<str:jk>", views.showworkspace, name="showworkspace"),
    path("selectownercart", views.selectownercart, name="selectownercart"),
    path("cartdetails<str:pk>", views.cartdetails, name="cartdetails"),
    path("request", views.send_request, name="request"),          # Send service request
    path("viewrequest", views.viewrequest, name="viewrequest"),    # View sent requests
    path("chat/<int:aid>", views.User_chat, name="chat"),          # Chat with owner
    path("cart_del/<int:pk>", views.cart_del, name="cartdel"),     # Delete cart item
    path("uvieworder<str:pk>", views.uvieworder, name="uvieworder"),  # View orders
    path("checkout<int:aid>", views.checkout, name="checkout"),    # Razorpay checkout
    path("payment_success<int:aid>", views.payment_success, name="payment_success"),
]
