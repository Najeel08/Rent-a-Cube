"""Public view imports used by the current and legacy URL routes."""

from .auth import (
    register,
    sign_in,
    dashboard,
)

from .workspaces import (
    workspace_list,
    workspace_overview,
    workspace_search,
    workspace_book,
    owner_public_profile,
    owner_workspace_catalog,
)

from .bookings import (
    booking_list,
    cart_list,
    cart_owner_list,
    cart_detail,
    checkout,
    payment_complete,
    cart_remove,
)

from .support import (
    service_request_create,
    service_request_list,
    customer_conversation,
)


__all__ = [
    "register",
    "sign_in",
    "dashboard",
    "workspace_list",
    "workspace_overview",
    "workspace_search",
    "workspace_book",
    "owner_public_profile",
    "owner_workspace_catalog",
    "booking_list",
    "cart_list",
    "cart_owner_list",
    "cart_detail",
    "checkout",
    "payment_complete",
    "cart_remove",
    "service_request_create",
    "service_request_list",
    "customer_conversation",
]
