import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.driver_payment_collection import DriverPaymentCollection
from app.models.operations import PodRecord
from app.models.order import Order, OrderStatus
from app.modules.fleet.constants import TERMINAL_ORDER_STATUSES
from app.modules.fleet.models.driver import Driver
from app.modules.fleet.schemas.trip_sheet_driver import (
    CashPaymentRequest,
    TripStatusUpdateRequest,
    VerifyDropRequest,
    VerifyPickupRequest,
)
from app.modules.fleet.services.trip_sheet_driver_service import (
    build_trip_detail,
    get_order_on_driver_sheet,
    mark_sheet_in_progress,
    maybe_complete_sheet,
)


async def get_trip_detail(db: AsyncSession, driver: Driver, order_id: str) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, order_id)
    return build_trip_detail(sheet, order)


async def update_order_status(
    db: AsyncSession, driver: Driver, order_id: str, payload: TripStatusUpdateRequest
) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, order_id)
    new_status = payload.status
    order.previous_status = order.status
    if new_status in {"IN_TRANSIT", "In_transit"}:
        order.status = OrderStatus.IN_TRANSIT.value
    elif new_status in {"ARRIVED_AT_DROP", "DELIVERY_COMPLETED"}:
        order.status = OrderStatus.OFD.value
    elif new_status == "PICKUP_COMPLETED":
        order.status = OrderStatus.PICKED.value
    await mark_sheet_in_progress(db, sheet)
    await db.flush()
    return {
        "tripId": order.id,
        "tripSheetId": sheet.id,
        "status": new_status,
        "orderStatus": order.status,
        "updatedAt": datetime.utcnow().isoformat(),
    }


async def verify_pickup(
    db: AsyncSession, driver: Driver, order_id: str, payload: VerifyPickupRequest
) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, order_id)
    order.previous_status = order.status
    order.status = OrderStatus.PICKED.value
    await mark_sheet_in_progress(db, sheet)
    await db.flush()
    return {
        "tripId": order.id,
        "tripSheetId": sheet.id,
        "status": "PICKUP_COMPLETED",
        "nextStep": "IN_TRANSIT",
        "message": "Pickup confirmed. Proceed to delivery.",
    }


async def verify_drop(
    db: AsyncSession, driver: Driver, order_id: str, payload: VerifyDropRequest
) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, order_id)

    existing = await db.execute(select(PodRecord).where(PodRecord.order_id == order.id))
    pod = existing.scalar_one_or_none()
    receiver = payload.receiverName or (order.consignee.name if order.consignee else "Receiver")
    if pod:
        pod.receiver_name = receiver
        pod.received_at = payload.confirmedAt or datetime.utcnow()
        pod.signature_url = payload.signatureUrl
        pod.otp_verified = bool(payload.otp)
    else:
        db.add(
            PodRecord(
                id=str(uuid.uuid4()),
                order_id=order.id,
                receiver_name=receiver,
                received_at=payload.confirmedAt or datetime.utcnow(),
                delivery_staff_id=driver.user_id,
                otp_verified=bool(payload.otp),
                signature_url=payload.signatureUrl,
            )
        )

    payment_method = (order.payment_method or "Prepaid").lower()
    payment_required = payment_method in {"cod", "to pay", "topay"}
    if not payment_required:
        order.previous_status = order.status
        order.status = OrderStatus.DELIVERED.value
        await maybe_complete_sheet(db, sheet)

    await db.flush()
    amount = float(order.cod_amount or order.to_pay_amount or order.total_freight or 0)
    return {
        "tripId": order.id,
        "tripSheetId": sheet.id,
        "status": "DELIVERY_COMPLETED",
        "paymentRequired": payment_required,
        "paymentStatus": "PENDING" if payment_required else "PAID",
        "amount": amount,
        "paymentMethod": order.payment_method,
        "upiId": "roadoz@ybl" if payment_required else None,
        "paymentReference": f"PAY-{order.order_number}" if payment_required else None,
        "message": "Delivery confirmed." + (" Collect payment." if payment_required else ""),
    }


async def complete_trip(db: AsyncSession, driver: Driver, order_id: str) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, order_id)
    if order.status in TERMINAL_ORDER_STATUSES and order.status != OrderStatus.DELIVERED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order cannot be completed")
    order.previous_status = order.status
    order.status = OrderStatus.DELIVERED.value
    await maybe_complete_sheet(db, sheet)
    await db.flush()
    return {"success": True, "message": "Trip completed successfully"}


async def get_payment_info(db: AsyncSession, driver: Driver, order_id: str) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, order_id)
    amount = float(order.cod_amount or order.to_pay_amount or order.total_freight or 0)
    paid = (order.payment_method or "").lower() == "prepaid"
    return {
        "tripId": order.id,
        "tripSheetId": sheet.id,
        "orderId": order.order_number,
        "customerName": order.consignee.name if order.consignee else "",
        "amount": amount,
        "currency": "INR",
        "paymentStatus": "PAID" if paid else "PENDING",
        "paymentMethod": order.payment_method,
        "upiId": "roadoz@ybl",
        "merchantName": "Roadoz Courier Pvt Ltd",
        "paymentReference": f"PAY-{order.order_number}",
    }


async def submit_cash_payment(db: AsyncSession, driver: Driver, payload: CashPaymentRequest) -> dict:
    sheet, order = await get_order_on_driver_sheet(db, driver, payload.orderId)
    ref = f"PAY-{order.order_number}"
    existing = await db.execute(
        select(DriverPaymentCollection).where(DriverPaymentCollection.payment_reference == ref)
    )
    record = existing.scalar_one_or_none()
    if not record:
        record = DriverPaymentCollection(
            id=str(uuid.uuid4()),
            order_id=order.id,
            driver_id=driver.id,
            trip_sheet_id=sheet.id,
            amount=payload.amount,
            payment_method="Cash",
            payment_reference=ref,
            status="SUCCESS",
            paid_at=payload.collectedAt or datetime.utcnow(),
        )
        db.add(record)
    else:
        record.status = "SUCCESS"
        record.paid_at = payload.collectedAt or datetime.utcnow()
    order.previous_status = order.status
    order.status = OrderStatus.DELIVERED.value
    await maybe_complete_sheet(db, sheet)
    await db.flush()
    return {"success": True, "message": "Cash collected successfully"}


async def get_payment_status(db: AsyncSession, payment_reference: str) -> dict:
    result = await db.execute(
        select(DriverPaymentCollection).where(DriverPaymentCollection.payment_reference == payment_reference)
    )
    record = result.scalar_one_or_none()
    if not record:
        return {
            "status": "PENDING",
            "paymentReference": payment_reference,
            "amount": 0,
            "transactionId": None,
            "paidAt": None,
            "paymentMethod": "UPI",
        }
    return {
        "status": record.status,
        "paymentReference": record.payment_reference,
        "amount": float(record.amount),
        "transactionId": record.transaction_id,
        "paidAt": record.paid_at.isoformat() if record.paid_at else None,
        "paymentMethod": record.payment_method,
    }
