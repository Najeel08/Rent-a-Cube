from django.urls import path
from . import views

# Admin URLs - login, dashboard, owner/user management, bookings
urlpatterns = [
    path("alogin", views.alogin, name="alogin"),           # Admin login
    path("aindex", views.aindex, name="aindex"),           # Admin dashboard
    path("ownerlists", views.ownerlists, name="ownerlists"),  # Owner list
    path("spaceview", views.spaceview, name="spaceview"),     # Workspace list
    path("spaceimage", views.spaceimage, name="spaceimage"),  # Workspace images
    path("proofview<str:ps>", views.proofview, name="proofview"),  # View owner proof
    path("proof-file/<int:ps>", views.proof_file, name="proof_file"),
    path("imageview<str:pi>", views.imageview, name="imageview"),  # View workspace image
    path("worder", views.worder, name="worder"),              # All orders
    path("userlist", views.userlist, name="userlist"),          # User list
    path("bookingdetail", views.bookingdetail, name="bookingdetail"),  # Booking details
    path("suggestions", views.suggestions, name="suggestions"),
    path("viewsuggestion", views.viewsuggestion, name="viewsuggestion"),
    path("profile", views.profile, name="profile"),            # Admin profile
    path("accept<int:id>", views.accept, name="accept"),       # Approve owner
    path("reject<int:id>", views.reject, name="reject"),       # Reject owner
]
