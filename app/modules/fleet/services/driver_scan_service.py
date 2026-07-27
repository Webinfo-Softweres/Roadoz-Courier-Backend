from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.trip_sheet import TripSheet, TripSheetOrder
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.services.trip_sheet_driver_service import get_order_on_driver_sheet


async def _resolve_order_by_barcode(db: AsyncSession, barcode: str) -> Order | None:
    decoded = barcode.strip()
    result = await db.execute(
        select(Order).where((Order.barcode == decoded) | (Order.order_number == decoded))
    )
    return result.scalar_one_or_none()


async def lookup_barcode_for_driver(db: AsyncSession, driver: Driver, barcode: str) -> dict:
    order = await _resolve_order_by_barcode(db, barcode)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barcode not found")
    try:
        await get_order_on_driver_sheet(db, driver, order.id)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order not on your active trip sheet")
    return {
        "trackingId": order.order_number,
        "barcode": barcode,
        "customerName": order.consignee.name if order.consignee else "",
        "packageType": order.order_type,
        "assignedRoute": "Trip sheet delivery",
        "scanTime": datetime.utcnow().isoformat(),
        "status": order.status,
        "operation": "DELIVERY",
        "resultStatus": "SUCCESS",
    }


async def execute_scan_for_driver(
    db: AsyncSession, driver: Driver, barcode: str, lat: float, lng: float
) -> dict:
    from app.models.user import User
    from app.routes.order import process_order_scan

    order = await _resolve_order_by_barcode(db, barcode)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barcode not found")
    sheet, _ = await get_order_on_driver_sheet(db, driver, order.id)

    user = (await db.execute(select(User).where(User.id == driver.user_id))).scalar_one()
    result = await process_order_scan(db, order, lat, lng, "000000", user)
    await db.commit()
    return {
        "scanType": "order",
        "tripSheetId": sheet.id,
        "stage": result.get("stage"),
        "orderId": order.id,
        "orderNumber": order.order_number,
        "orderStatus": order.status,
        "success": True,
        "gpsLocation": {"lat": lat, "lng": lng},
    }
