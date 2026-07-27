from app.modules.fleet.constants import SHEET_STATUS_PENDING_ACCEPT


def apply_driver_assignment_to_trip_sheet(trip_sheet, driver_id: str | None, *, reset: bool = False) -> None:
    """Set driver lifecycle fields when admin assigns or changes driver on a trip sheet."""
    if not driver_id:
        trip_sheet.driver_status = None
        trip_sheet.accepted_at = None
        trip_sheet.started_at = None
        trip_sheet.completed_at = None
        return

    if reset or trip_sheet.driver_id != driver_id or not trip_sheet.driver_status:
        trip_sheet.driver_id = driver_id
        trip_sheet.driver_status = SHEET_STATUS_PENDING_ACCEPT
        trip_sheet.accepted_at = None
        trip_sheet.started_at = None
        trip_sheet.completed_at = None
