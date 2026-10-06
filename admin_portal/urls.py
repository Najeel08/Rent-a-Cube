from django.urls import path
from . import views

urlpatterns = [
    path("alogin", views.alogin, name="alogin"),
    path("aindex", views.aindex, name="aindex"),
    path("ownerlists", views.ownerlists, name="ownerlists"),
    path("spaceview", views.spaceview, name="spaceview"),
    path("spaceimage", views.spaceimage, name="spaceimage"),
    path("proofview<str:ps>", views.proofview, name="proofview"),
    path("proof-file/<int:ps>", views.proof_file, name="proof_file"),
    path("imageview<str:pi>", views.imageview, name="imageview"),
    path("worder", views.worder, name="worder"),
    path("userlist", views.userlist, name="userlist"),
    path("bookingdetail", views.bookingdetail, name="bookingdetail"),
    path("suggestions", views.suggestions, name="suggestions"),
    path("viewsuggestion", views.viewsuggestion, name="viewsuggestion"),
    path("profile", views.profile, name="profile"),
    path("accept<int:id>", views.accept, name="accept"),
    path("reject<int:id>", views.reject, name="reject"),
]
