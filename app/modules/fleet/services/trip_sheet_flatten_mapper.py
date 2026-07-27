from datetime import datetime

from app.models.order import Order
from app.models.trip_sheet import TripSheet
from app.modules.fleet.constants import (
    SHEET_ACTIVE_STATUSES,
    SHEET_STATUS_PENDING_ACCEPT,
    TERMINAL_ORDER_STATUSES,
)
from app.modules.fleet.schemas.trip_sheet_driver import (
    LocationDetailOut,
    MoneyOut,
    SheetSummaryOut,
    TripListItemOut,
)


def _location_from_pickup(pickup) -> LocationDetailOut:
    if not pickup:
        return LocationDetailOut(name="Pickup", address="", latitude=None, longitude=None)
    address = ", ".join(
        p for p in [pickup.address_line_1, pickup.address_line_2, pickup.city, pickup.pincode] if p
    )
    return LocationDetailOut(
        name=pickup.nickname or pickup.contact_name or "Pickup",
        address=address,
        latitude=float(pickup.latitude) if pickup.latitude is not None else None,
        longitude=float(pickup.longitude) if pickup.longitude is not None else None,
        contactPhone=pickup.phone,
    )


def _location_from_consignee(consignee) -> LocationDetailOut:
    if not consignee:
        return LocationDetailOut(name="Delivery", address="", latitude=None, longitude=None)
    address = ", ".join(
        p for p in [consignee.address_line_1, consignee.address_line_2, consignee.city, consignee.pincode] if p
    )
    return LocationDetailOut(
        name=consignee.name or "Delivery",
        address=address,
        latitude=float(consignee.latitude) if consignee.latitude is not None else None,
        longitude=float(consignee.longitude) if consignee.longitude is not None else None,
        contactPhone=consignee.mobile,
    )


def _card_status(sheet: TripSheet, order: Order) -> str:
    if sheet.driver_status == SHEET_STATUS_PENDING_ACCEPT:
        return "NEW"
    order_status = (order.status or "").strip()
    if order_status.lower() in {s.lower() for s in TERMINAL_ORDER_STATUSES}:
        return "COMPLETED"
    if order_status in {"In_transit", "IN_TRANSIT", "In Transit"}:
        return "IN_TRANSIT"
    if order_status in {"Ofd", "OFD", "Out for delivery"}:
        return "NEXT"
    if order_status in {"Picked", "PICKED"}:
        return "READY_FOR_PICKUP"
    return "NEXT"


def _progress_label(status: str) -> str | None:
    return {
        "NEW": "New offer",
        "NEXT": "Ready",
        "READY_FOR_PICKUP": "Ready for pickup",
        "IN_TRANSIT": "In Transit",
        "COMPLETED": "Completed",
    }.get(status)


def flatten_sheet_orders(sheet: TripSheet, *, include_delivered: bool = False) -> list[TripListItemOut]:
    items: list[TripListItemOut] = []
    now = datetime.utcnow()
    expires_in = None
    if sheet.offer_expires_at and sheet.driver_status == SHEET_STATUS_PENDING_ACCEPT:
        expires_in = max(0, int((sheet.offer_expires_at - now).total_seconds()))

    for trip_order in sorted(sheet.orders or [], key=lambda x: x.sl_no):
        order = trip_order.order
        if not order:
            continue
        card_status = _card_status(sheet, order)
        if not include_delivered and card_status == "COMPLETED":
            continue
        if sheet.driver_status in SHEET_ACTIVE_STATUSES and card_status == "NEW":
            continue

        consignee = order.consignee
        pickup = order.pickup_address
        payment_type = (order.payment_method or "Prepaid").upper().replace(" ", "_")

        items.append(
            TripListItemOut(
                id=order.id,
                tripSheetId=sheet.id,
                deliveryId=order.order_number,
                orderId=order.id,
                customerName=consignee.name if consignee else "Customer",
                status=card_status,
                tripType="PICKUP_AND_DELIVERY",
                isExpress=(order.service_type or "").lower() == "express",
                assignedTime=sheet.created_at,
                expiresInSeconds=expires_in,
                pickupLocation=_location_from_pickup(pickup),
                dropLocation=_location_from_consignee(consignee),
                earnings=MoneyOut(amount=float(order.total_freight or 0), currency="INR"),
                package={"type": order.order_type, "weight": f"{float(order.total_weight_kg or 0)} kg"},
                payment={"type": payment_type, "amount": float(order.cod_amount or order.total_freight or 0)},
                progress=_progress_label(card_status),
                sheetSummary=SheetSummaryOut(
                    totalPackages=int(sheet.total_packages or 0),
                    destinationCity=sheet.destination_city,
                ),
                isAccepted=sheet.driver_status in SHEET_ACTIVE_STATUSES
                or sheet.driver_status == "completed",
            )
        )
    return items
