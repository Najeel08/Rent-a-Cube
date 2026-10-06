from django.urls import path
from . import views

urlpatterns = [
    path("vreg", views.vreg, name="vreg"),
    path("vlog", views.vlog, name="vlog"),
    path("vhome", views.vhome, name="vhome"),
    path("vaddwork", views.vaddwork, name="vaddwork"),
    path("oviewwork", views.oviewwork, name="oviewwork"),
    path("Workdetail<int:pik>", views.Workdetail, name="Workdetail"),
    path("ovupdate<str:pin>", views.Ovupdate, name="ovupdate"),
    path("ovdelete<int:pid>", views.Ovdelete, name="ovdelete"),
    path("PROFILE", views.PROFILE, name="PROFILE"),
    path("ownerprofileupdate<str:pim>", views.ownerprofileupdate, name="ownerprofileupdate"),
    path("ownerorder<str:pk>", views.ownerorder, name="ownerorder"),
    path("confirmpayment/<str:pk>", views.confirmpayment, name="confirmpayment"),
    path("addtechnician", views.addtechnician, name="addtechnician"),
    path("viewtechnician", views.viewtechnician, name="viewtechnician"),
    path("sentemail<int:id>", views.sendemail, name="sentemail"),
    path("requests", views.requests, name="requests"),
    path("assign<str:bid>", views.assign, name="assign"),
    path("chat", views.chat, name="chat"),
    path("achat/<str:uid>", views.owner_chat, name="achat"),
    path("refund", views.refund, name="refund"),
    path("refundcheck<int:uid>", views.checkout, name="refundcheck"),
]
