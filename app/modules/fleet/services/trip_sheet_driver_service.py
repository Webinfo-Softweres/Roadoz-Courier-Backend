from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderStatus
from app.models.trip_sheet import TripSheet, TripSheetOrder
from app.modules.fleet.constants import (
    SHEET_ACTIVE_STATUSES,
    SHEET_STATUS_ACCEPTED,
    SHEET_STATUS_CANCELLED,
    SHEET_STATUS_COMPLETED,
    SHEET_STATUS_DECLINED,
    SHEET_STATUS_IN_PROGRESS,
    SHEET_STATUS_PENDING_ACCEPT,
    TERMINAL_ORDER_STATUSES,
)
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.schemas.trip_sheet_driver import TripRespondRequest
from app.modules.fleet.services.trip_sheet_flatten_mapper import flatten_sheet_orders


async def _load_sheet_for_driver(db: AsyncSession, trip_sheet_id: str, driver: Driver) -> TripSheet:
    result = await db.execute(
        select(TripSheet)
        .options(
            selectinload(TripSheet.orders).selectinload(TripSheetOrder.order).selectinload(Order.pickup_address),
            selectinload(TripSheet.orders).selectinload(TripSheetOrder.order).selectinload(Order.consignee),
        )
        .where(TripSheet.id == trip_sheet_id, TripSheet.driver_id == driver.id)
    )
    sheet = result.scalar_one_or_none()
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip sheet not found")
    return sheet


async def list_new_trips(db: AsyncSession, driver: Driver) -> list:
    if not driver.online or driver.onboarding_status != "approved":
        return []
    result = await db.execute(
        select(TripSheet)
        .options(
            selectinload(TripSheet.orders).selectinload(TripSheetOrder.order).selectinload(Order.pickup_address),
            selectinload(TripSheet.orders).selectinload(TripSheetOrder.order).selectinload(Order.consignee),
        )
        .where(
            TripSheet.driver_id == driver.id,
            TripSheet.driver_status == SHEET_STATUS_PENDING_ACCEPT,
        )
        .order_by(TripSheet.created_at.desc())
    )
    items = []
    for sheet in result.scalars().all():
        items.extend(flatten_sheet_orders(sheet))
    return items


async def list_active_trips(db: AsyncSession, driver: Driver) -> list:
    result = await db.execute(
        select(TripSheet)
        .options(
            selectinload(TripSheet.orders).selectinload(TripSheetOrder.order).selectinload(Order.pickup_address),
            selectinload(TripSheet.orders).selectinload(TripSheetOrder.order).selectinload(Order.consignee),
        )
        .where(
            TripSheet.driver_id == driver.id,
            TripSheet.driver_status.in_(SHEET_ACTIVE_STATUSES),
        )
        .order_by(TripSheet.created_at.desc())
    )
    items = []
    for sheet in result.scalars().all():
        items.extend(flatten_sheet_orders(sheet, include_delivered=False))
    return items


async def respond_to_sheet(
    db: AsyncSession, driver: Driver, trip_sheet_id: str, payload: TripRespondRequest
) -> dict:
    sheet = await _load_sheet_for_driver(db, trip_sheet_id, driver)

    if sheet.driver_status != SHEET_STATUS_PENDING_ACCEPT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Trip sheet is not pending acceptance")

    action = payload.action.upper()
    if action == "ACCEPT":
        sheet.driver_status = SHEET_STATUS_ACCEPTED
        sheet.accepted_at = datetime.utcnow()
        for trip_order in sheet.orders or []:
            order = trip_order.order
            if order and order.status not in TERMINAL_ORDER_STATUSES:
                order.previous_status = order.status
                order.status = OrderStatus.OFD.value
        await db.flush()
        return {
            "tripSheetId": sheet.id,
            "status": "ACCEPTED",
            "nextStep": "ARRIVED_AT_PICKUP",
        }

    if action == "DECLINE":
        sheet.driver_status = SHEET_STATUS_DECLINED
        sheet.driver_id = None
        await db.flush()
        return {"tripSheetId": sheet.id, "status": "DECLINED"}

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid action")


async def get_order_on_driver_sheet(db: AsyncSession, driver: Driver, order_id: str) -> tuple[TripSheet, Order]:
    result = await db.execute(
        select(TripSheet, Order)
        .join(TripSheetOrder, TripSheetOrder.trip_sheet_id == TripSheet.id)
        .join(Order, Order.id == TripSheetOrder.order_id)
        .options(
            selectinload(Order.pickup_address),
            selectinload(Order.consignee),
            selectinload(Order.packages),
            selectinload(Order.items),
        )
        .where(
            TripSheet.driver_id == driver.id,
            Order.id == order_id,
            TripSheet.driver_status.notin_([SHEET_STATUS_DECLINED, SHEET_STATUS_CANCELLED]),
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found on your trip sheets")
    return row[0], row[1]


def build_trip_detail(sheet: TripSheet, order: Order) -> dict:
    pickup = order.pickup_address
    consignee = order.consignee
    amount = float(order.cod_amount or order.to_pay_amount or order.total_freight or 0)
    payment_status = "PAID" if (order.payment_method or "").lower() == "prepaid" else "PENDING"

    def stop(stop_type: str, title: str, location, customer_name, phone, role):
        if not location and stop_type == "PICKUP":
            return None
        loc = location
        address = ", ".join(
            p
            for p in [
                getattr(loc, "address_line_1", None),
                getattr(loc, "address_line_2", None),
                getattr(loc, "city", None),
                getattr(loc, "pincode", None),
            ]
            if p
        )
        return {
            "id": f"stop-{stop_type.lower()}-{order.id}",
            "type": stop_type,
            "title": title,
            "location": {
                "name": getattr(loc, "nickname", None) or getattr(loc, "name", None) or title,
                "address": address,
                "latitude": float(getattr(loc, "latitude", 0) or 0) if getattr(loc, "latitude", None) else None,
                "longitude": float(getattr(loc, "longitude", 0) or 0) if getattr(loc, "longitude", None) else None,
                "contactPhone": phone,
            },
            "customer": {
                "name": customer_name or "Contact",
                "role": role,
                "phone": phone,
                "avatarInitials": "".join(w[0] for w in (customer_name or "NA").split()[:2]).upper(),
            },
        }

    return {
        "id": order.id,
        "tripSheetId": sheet.id,
        "orderId": order.order_number,
        "isUrgent": (order.service_type or "").lower() == "express",
        "tripType": "PICKUP_AND_DELIVERY",
        "status": order.status,
        "paymentStatus": payment_status,
        "amount": amount,
        "pickupStop": stop(
            "PICKUP",
            "PICKUP LOCATION",
            pickup,
            pickup.contact_name if pickup else None,
            pickup.phone if pickup else None,
            "Sender",
        ),
        "deliveryStop": stop(
            "DELIVERY",
            "DELIVERY LOCATION",
            consignee,
            consignee.name if consignee else None,
            consignee.mobile if consignee else None,
            "Receiver",
        ),
    }


async def mark_sheet_in_progress(db: AsyncSession, sheet: TripSheet) -> None:
    if sheet.driver_status == SHEET_STATUS_ACCEPTED:
        sheet.driver_status = SHEET_STATUS_IN_PROGRESS
        sheet.started_at = sheet.started_at or datetime.utcnow()
        await db.flush()


async def maybe_complete_sheet(db: AsyncSession, sheet: TripSheet) -> None:
    if not sheet.orders:
        return
    all_terminal = True
    for trip_order in sheet.orders:
        order = trip_order.order
        if not order:
            continue
        if order.status not in TERMINAL_ORDER_STATUSES:
            all_terminal = False
            break
    if all_terminal:
        sheet.driver_status = SHEET_STATUS_COMPLETED
        sheet.completed_at = datetime.utcnow()
        await db.flush()


async def list_order_history(
    db: AsyncSession, driver: Driver, page: int, limit: int
) -> dict:
    offset = (page - 1) * limit
    filters = [
        TripSheet.driver_id == driver.id,
        Order.status.in_(list(TERMINAL_ORDER_STATUSES)),
    ]
    total = (
        await db.execute(
            select(func.count())
            .select_from(TripSheetOrder)
            .join(TripSheet, TripSheet.id == TripSheetOrder.trip_sheet_id)
            .join(Order, Order.id == TripSheetOrder.order_id)
            .where(*filters)
        )
    ).scalar_one()

    result = await db.execute(
        select(Order)
        .join(TripSheetOrder, TripSheetOrder.order_id == Order.id)
        .join(TripSheet, TripSheet.id == TripSheetOrder.trip_sheet_id)
        .options(selectinload(Order.pickup_address), selectinload(Order.consignee))
        .where(*filters)
        .order_by(Order.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    orders = []
    for order in result.scalars().all():
        orders.append(
            {
                "id": order.order_number,
                "sender": order.pickup_address.nickname if order.pickup_address else "",
                "recipient": order.consignee.name if order.consignee else "",
                "status": order.status,
                "weight": f"{float(order.total_weight_kg or 0)} kg",
            }
        )
    return {"orders": orders, "total": total, "page": page, "limit": limit}
