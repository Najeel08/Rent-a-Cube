from django.urls import path
from . import views

# Owner URLs - registration, login, workspace management, chat, refund
urlpatterns = [
    path("vreg", views.vreg, name="vreg"),                    # Owner registration
    path("vlog", views.vlog, name="vlog"),                    # Owner login
    path("vhome", views.vhome, name="vhome"),                 # Owner dashboard
    path("vaddwork", views.vaddwork, name="vaddwork"),         # Add workspace
    path("oviewwork", views.oviewwork, name="oviewwork"),      # View own workspaces
    path("Workdetail<int:pik>", views.Workdetail, name="Workdetail"),  # Workspace detail
    path("ovupdate<str:pin>", views.Ovupdate, name="ovupdate"),    # Update workspace
    path("ovdelete<int:pid>", views.Ovdelete, name="ovdelete"),    # Delete workspace
    path("PROFILE", views.PROFILE, name="PROFILE"),                # Owner profile
    path("ownerprofileupdate<str:pim>", views.ownerprofileupdate, name="ownerprofileupdate"),
    path("ownerorder<str:pk>", views.ownerorder, name="ownerorder"),      # View orders
    path("confirmpayment/<str:pk>", views.confirmpayment, name="confirmpayment"),
    path("addtechnician", views.addtechnician, name="addtechnician"),     # Add technician
    path("viewtechnician", views.viewtechnician, name="viewtechnician"),  # View technicians
    path("sentemail<int:id>", views.sendemail, name="sentemail"),         # Email tech login
    path("requests", views.requests, name="requests"),           # Service requests
    path("assign<str:bid>", views.assign, name="assign"),        # Assign to tech
    path("chat", views.chat, name="chat"),                       # Chat inbox
    path("achat/<str:uid>", views.owner_chat, name="achat"),     # Chat with user
    path("refund", views.refund, name="refund"),                 # Refund list
    path("refundcheck<int:uid>", views.checkout, name="refundcheck"),  # Process refund
]
