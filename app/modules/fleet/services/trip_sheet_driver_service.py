from datetime import date, datetime, time, timedelta
from typing import Any

import pytz
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

IST = pytz.timezone("Asia/Kolkata")
EXPORT_RANGES = frozenset({"this_week", "this_month", "last_month", "all"})
EXPORT_ROW_CAP = 5000
DRIVER_TRIP_HISTORY_REPORT = "Driver Trip History Report"


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

    packages = [
        {
            "id": pkg.id,
            "packageIndex": pkg.package_index,
            "count": pkg.count,
            "weightUnit": pkg.weight_unit,
            "lengthCm": float(pkg.length_cm or 0),
            "breadthCm": float(pkg.breadth_cm or 0),
            "heightCm": float(pkg.height_cm or 0),
            "volWeightKg": float(pkg.vol_weight_kg or 0),
            "physicalWeightKg": float(pkg.physical_weight_kg or 0),
        }
        for pkg in (order.packages or [])
    ]
    items = [
        {
            "id": item.id,
            "productName": item.product_name,
            "sku": item.sku,
            "unitPrice": float(item.unit_price or 0),
            "qty": item.qty,
            "total": float(item.total or 0),
            "packageIndex": item.package_index,
        }
        for item in (order.items or [])
    ]

    return {
        "id": order.id,
        "tripSheetId": sheet.id,
        "orderId": order.order_number,
        "isUrgent": (order.service_type or "").lower() == "express",
        "tripType": "PICKUP_AND_DELIVERY",
        "status": order.status,
        "paymentStatus": payment_status,
        "amount": amount,
        "packageSummary": {
            "type": order.order_type,
            "totalWeightKg": float(order.total_weight_kg or 0),
            "totalPackages": len(packages),
            "totalItems": len(items),
        },
        "packages": packages,
        "items": items,
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


def _ist_day_start(d: date) -> datetime:
    return IST.localize(datetime.combine(d, time.min)).replace(tzinfo=None)


def _ist_day_end(d: date) -> datetime:
    return IST.localize(datetime.combine(d, time.max)).replace(tzinfo=None)


def _ist_now() -> datetime:
    return datetime.now(IST)


def resolve_export_date_range(
    range_value: str | None,
    start_date: date | None,
    end_date: date | None,
    *,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None, date | None, date | None]:
    """Resolve inclusive IST bounds for Order.updated_at.

    Custom start+end win over range. Both custom dates required together.
    range required when custom dates absent. Returns (start_dt, end_dt, date_from, date_to);
    both datetimes None means no date filter (`all`).
    """
    has_start = start_date is not None
    has_end = end_date is not None
    if has_start != has_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="startDate and endDate must both be provided together",
        )
    if has_start and has_end:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="startDate must be on or before endDate",
            )
        return _ist_day_start(start_date), _ist_day_end(end_date), start_date, end_date

    if not range_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="range is required when startDate and endDate are not provided",
        )
    if range_value not in EXPORT_RANGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"range must be one of: {', '.join(sorted(EXPORT_RANGES))}",
        )
    if range_value == "all":
        return None, None, None, None

    if now is None:
        ist_now = _ist_now()
    elif now.tzinfo is None:
        ist_now = IST.localize(now)
    else:
        ist_now = now.astimezone(IST)
    today = ist_now.date()

    if range_value == "this_week":
        # Monday start (ISO weekday 0 = Monday)
        week_start = today - timedelta(days=today.weekday())
        return _ist_day_start(week_start), _ist_day_end(today), week_start, today

    if range_value == "this_month":
        month_start = today.replace(day=1)
        return _ist_day_start(month_start), _ist_day_end(today), month_start, today

    # last_month
    first_this_month = today.replace(day=1)
    last_month_end = first_this_month - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return (
        _ist_day_start(last_month_start),
        _ist_day_end(last_month_end),
        last_month_start,
        last_month_end,
    )


def _format_address(loc: Any) -> str:
    if not loc:
        return ""
    return ", ".join(
        p
        for p in [
            getattr(loc, "address_line_1", None),
            getattr(loc, "address_line_2", None),
            getattr(loc, "city", None),
            getattr(loc, "pincode", None),
        ]
        if p
    )


def _to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return IST.localize(dt)
    return dt.astimezone(IST)


def _map_trip_status(order_status: str | None) -> str:
    s = (order_status or "").strip()
    lower = s.lower()
    if lower == "delivered":
        return "Completed"
    if lower == "cancelled":
        return "Cancelled"
    if lower in {"returned", "rto_delivered"}:
        return "Returned"
    return s


def _order_to_export_row(order: Order) -> dict:
    updated = order.updated_at
    ist_dt = _to_ist(updated) if updated else None
    pickup = order.pickup_address
    consignee = order.consignee
    payment_method = (order.payment_method or "").upper()
    payment_status = "PAID" if (order.payment_method or "").lower() == "prepaid" else "PENDING"
    return {
        "trip_id": order.id,
        "order_id": order.order_number,
        "completed_date": ist_dt.strftime("%Y-%m-%d") if ist_dt else "",
        "completed_time": ist_dt.strftime("%H:%M") if ist_dt else "",
        "pickup_hub": (pickup.nickname if pickup else "") or "",
        "customer_name": (consignee.name if consignee else "") or "",
        "delivery_address": _format_address(consignee),
        "weight": float(order.total_weight_kg or 0),
        "earnings": float(order.total_freight or 0),
        "payment_status": payment_status,
        "payment_method": payment_method,
        "trip_status": _map_trip_status(order.status),
    }


async def export_order_history(
    db: AsyncSession,
    driver: Driver,
    range_value: str | None,
    start_date: date | None,
    end_date: date | None,
) -> dict:
    start_dt, end_dt, date_from, date_to = resolve_export_date_range(
        range_value, start_date, end_date
    )
    filters = [
        TripSheet.driver_id == driver.id,
        Order.status.in_(list(TERMINAL_ORDER_STATUSES)),
    ]
    if start_dt is not None and end_dt is not None:
        filters.append(Order.updated_at >= start_dt)
        filters.append(Order.updated_at <= end_dt)

    result = await db.execute(
        select(Order)
        .join(TripSheetOrder, TripSheetOrder.order_id == Order.id)
        .join(TripSheet, TripSheet.id == TripSheetOrder.trip_sheet_id)
        .options(selectinload(Order.pickup_address), selectinload(Order.consignee))
        .where(*filters)
        .order_by(Order.updated_at.desc())
        .limit(EXPORT_ROW_CAP)
    )
    items = [_order_to_export_row(order) for order in result.scalars().all()]
    report: dict[str, Any] = {
        "report": DRIVER_TRIP_HISTORY_REPORT,
        "items": items,
    }
    if date_from is not None and date_to is not None:
        report["date_from"] = date_from.isoformat()
        report["date_to"] = date_to.isoformat()
    return report
