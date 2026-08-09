"""POD cancel / trip status cancellation tests."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.order import OrderStatus
from app.modules.fleet.schemas.trip_sheet_driver import TripStatusUpdateRequest
from app.modules.fleet.services.driver_trip_execution_service import update_order_status


def _order(**kwargs):
    defaults = {
        "id": "order-1",
        "status": "In_transit",
        "previous_status": None,
        "meta": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _sheet():
    return SimpleNamespace(id="sheet-1", driver_status="accepted", orders=[])


def _driver():
    return SimpleNamespace(id="driver-1")


@pytest.mark.asyncio
async def test_cancel_sets_cancelled_and_meta():
    order = _order()
    sheet = _sheet()
    driver = _driver()
    db = AsyncMock()
    payload = TripStatusUpdateRequest(
        status="CANCELLED",
        reason="Customer unavailable - No response after 3 phone call attempts",
        phase="PICKUP",
        timestamp=datetime(2026, 8, 8, 0, 52, 0),
        location={"latitude": 10.0284, "longitude": 76.3105},
    )

    with (
        patch(
            "app.modules.fleet.services.driver_trip_execution_service.get_order_on_driver_sheet",
            AsyncMock(return_value=(sheet, order)),
        ),
        patch(
            "app.modules.fleet.services.driver_trip_execution_service.maybe_complete_sheet",
            AsyncMock(),
        ) as complete,
    ):
        result = await update_order_status(db, driver, order.id, payload)

    assert order.status == OrderStatus.CANCELLED.value
    assert order.meta["cancellation"]["reason"].startswith("Customer unavailable")
    assert order.meta["cancellation"]["phase"] == "PICKUP"
    assert order.meta["cancellation"]["driverId"] == "driver-1"
    assert result["status"] == "CANCELLED"
    assert result["reason"] == payload.reason
    assert "CANCELLED successfully" in result["message"]
    complete.assert_awaited_once()
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_cancel_requires_reason():
    order = _order()
    db = AsyncMock()
    payload = TripStatusUpdateRequest(status="CANCELLED", phase="DELIVERY", reason=None)

    with patch(
        "app.modules.fleet.services.driver_trip_execution_service.get_order_on_driver_sheet",
        AsyncMock(return_value=(_sheet(), order)),
    ):
        with pytest.raises(HTTPException) as exc:
            await update_order_status(db, _driver(), order.id, payload)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_cancel_rejects_terminal_order():
    order = _order(status="Delivered")
    db = AsyncMock()
    payload = TripStatusUpdateRequest(
        status="CANCELLED",
        reason="Customer unavailable",
        phase="DELIVERY",
    )

    with patch(
        "app.modules.fleet.services.driver_trip_execution_service.get_order_on_driver_sheet",
        AsyncMock(return_value=(_sheet(), order)),
    ):
        with pytest.raises(HTTPException) as exc:
            await update_order_status(db, _driver(), order.id, payload)
    assert exc.value.status_code == 409
