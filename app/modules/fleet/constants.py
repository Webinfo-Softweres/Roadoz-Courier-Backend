"""Fleet onboarding constants."""

REQUIRED_DOCUMENT_TYPES = ("vehicle_insurance", "license_front", "license_back")

ONBOARDING_INCOMPLETE = "incomplete"
ONBOARDING_PENDING = "pending_verification"
ONBOARDING_APPROVED = "approved"
ONBOARDING_REJECTED = "rejected"

DRIVER_STATUS_DRAFT = "draft"
DRIVER_STATUS_ACTIVE = "active"
DRIVER_STATUS_INACTIVE = "inactive"
DRIVER_STATUS_SUSPENDED = "suspended"

VEHICLE_STATUS_DRAFT = "draft"
VEHICLE_STATUS_AVAILABLE = "available"

# Trip sheet driver lifecycle (mobile app)
SHEET_STATUS_PENDING_ACCEPT = "pending_accept"
SHEET_STATUS_ACCEPTED = "accepted"
SHEET_STATUS_IN_PROGRESS = "in_progress"
SHEET_STATUS_COMPLETED = "completed"
SHEET_STATUS_DECLINED = "declined"
SHEET_STATUS_CANCELLED = "cancelled"
SHEET_STATUS_EXPIRED = "expired"

SHEET_ACTIVE_STATUSES = (SHEET_STATUS_ACCEPTED, SHEET_STATUS_IN_PROGRESS)
TERMINAL_ORDER_STATUSES = frozenset(
    {"Delivered", "Cancelled", "Returned", "Rto_delivered", "Lost", "RTO_DELIVERED"}
)
