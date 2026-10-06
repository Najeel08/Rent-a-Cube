from django.urls import path
from . import views

urlpatterns = [
    path("ureg", views.ureg, name="ureg"),
    path("ulog", views.ulog, name="ulog"),
    path("uhome", views.uhome, name="uhome"),
    path("uviewwork", views.uviewwork, name="uviewwork"),
    path("uworkdetails", views.uworkdetails, name="uworkdetails"),
    path("uviewcart", views.uviewcart, name="uviewcart"),
    path("showworkspace1", views.showworkspace1, name="showworkspace1"),
    path("uviewownerprof<str:id>", views.uviewownerprof, name="uviewownerprof"),
    path("uviewownerwork<str:pi>", views.uviewownerwork, name="uviework"),
    path("showworkspace<str:jk>", views.showworkspace, name="showworkspace"),
    path("selectownercart", views.selectownercart, name="selectownercart"),
    path("cartdetails<str:pk>", views.cartdetails, name="cartdetails"),
    path("request", views.send_request, name="request"),
    path("viewrequest", views.viewrequest, name="viewrequest"),
    path("chat/<int:aid>", views.User_chat, name="chat"),
    path("cart_del/<int:pk>", views.cart_del, name="cartdel"),
    path("uvieworder<str:pk>", views.uvieworder, name="uvieworder"),
    path("checkout<int:aid>", views.checkout, name="checkout"),
    path("payment_success<int:aid>", views.payment_success, name="payment_success"),
]
