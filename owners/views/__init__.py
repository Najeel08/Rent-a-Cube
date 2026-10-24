"""Public view imports used by the current and legacy URL routes."""

from .auth import (
    register,
    sign_in,
    dashboard,
    profile,
    profile_edit,
)

from .workspaces import (
    workspace_create,
    workspace_list,
    workspace_detail,
    workspace_edit,
    workspace_delete,
)

from .staff import (
    service_request_list,
    service_assignment_create,
    technician_create,
    technician_list,
    send_technician_login,
)

from .bookings import (
    booking_list,
    confirm_payment,
    refund_list,
    process_refund,
)

from .messaging import (
    conversation,
    chat_inbox,
)


__all__ = [
    "register",
    "sign_in",
    "dashboard",
    "profile",
    "profile_edit",
    "workspace_create",
    "workspace_list",
    "workspace_detail",
    "workspace_edit",
    "workspace_delete",
    "service_request_list",
    "service_assignment_create",
    "technician_create",
    "technician_list",
    "send_technician_login",
    "booking_list",
    "confirm_payment",
    "refund_list",
    "process_refund",
    "conversation",
    "chat_inbox",
]
