from datetime import datetime, timedelta

from app.core.config import settings
from app.modules.fleet.constants import SHEET_STATUS_PENDING_ACCEPT


def offer_expires_at_from_now() -> datetime:
    return datetime.utcnow() + timedelta(seconds=settings.DRIVER_TRIP_OFFER_EXPIRE_SECONDS)


def apply_driver_assignment_to_trip_sheet(trip_sheet, driver_id: str | None, *, reset: bool = False) -> None:
    """Set driver lifecycle fields when admin assigns or changes driver on a trip sheet."""
    if not driver_id:
        trip_sheet.driver_status = None
        trip_sheet.offer_expires_at = None
        trip_sheet.accepted_at = None
        trip_sheet.started_at = None
        trip_sheet.completed_at = None
        trip_sheet.decline_reason = None
        return

    if reset or trip_sheet.driver_id != driver_id or not trip_sheet.driver_status:
        trip_sheet.driver_id = driver_id
        trip_sheet.driver_status = SHEET_STATUS_PENDING_ACCEPT
        trip_sheet.offer_expires_at = offer_expires_at_from_now()
        trip_sheet.accepted_at = None
        trip_sheet.started_at = None
        trip_sheet.completed_at = None
        trip_sheet.decline_reason = None
